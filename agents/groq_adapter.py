"""Groq (OpenAI-compatible chat completions) adapter with native function calling.

- request timeout from config (plan: 60 s); the SDK's own retries are disabled (max_retries=0) so that ONLY the
  runner's explicit, logged retry policy applies
- parallel_tool_calls comes from config (false for openai/gpt-oss-120b, as required by the plan)
- malformed tool-call arguments are returned as ToolCall(parse_ok=False) instead of raising
- Groq 'tool_use_failed' (the model generated an invalid tool call) -> ModelOutputError (model failure, not retried)
"""
from __future__ import annotations

import copy
import json
import os
from typing import Any

from .base import ModelOutputError, ModelTurn, ProviderError, ToolCall, parse_retry_after


def _classify(exc: Exception) -> Exception:
    import openai
    status = getattr(exc, "status_code", None)
    headers = getattr(getattr(exc, "response", None), "headers", None)
    if isinstance(exc, openai.BadRequestError):
        body = getattr(exc, "body", None) or {}
        err = body.get("error", body) if isinstance(body, dict) else {}
        if isinstance(err, dict) and err.get("code") == "tool_use_failed":
            return ModelOutputError("tool_use_failed", str(exc), raw=body)
        return ProviderError("bad_request", str(exc), retryable=False, status_code=status)
    if isinstance(exc, openai.RateLimitError):
        retry_after = parse_retry_after(headers)
        if retry_after is None:
            import re
            match = re.search(r"Please try again in\s+([\d.]+)\s*(ms|seconds?|secs?|s)\b", str(exc), re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2).lower()
                retry_after = value / 1000 if unit == "ms" else value
        return ProviderError("rate_limit", str(exc), retryable=True, status_code=429, retry_after=retry_after)
    if isinstance(exc, openai.APITimeoutError):
        return ProviderError("timeout", str(exc), retryable=True)
    if isinstance(exc, openai.APIConnectionError):
        return ProviderError("connection", str(exc), retryable=True)
    if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return ProviderError("auth", str(exc), retryable=False, status_code=status)
    if isinstance(exc, openai.APIStatusError):
        if status is not None and status >= 500:
            return ProviderError("server", str(exc), retryable=True, status_code=status, retry_after=parse_retry_after(headers))
        return ProviderError("http_error", str(exc), retryable=False, status_code=status)
    return exc


class GroqAdapter:
    BASE_URL = "https://api.groq.com/openai/v1"
    SUPPORTS_TEXT_TOOL_RECOVERY = True

    def attach_recovered_tool_calls(self, calls: list[ToolCall]) -> None:
        from .base import attach_openai_style_tool_calls
        attach_openai_style_tool_calls(self.messages, calls)

    def __init__(self, *, model_key: str, model: str, temperature: float = 0, max_tokens: int = 1024,
                 reasoning: str | None = None, parallel_tool_calls: bool | None = None,
                 timeout_seconds: float = 60.0, client: Any = None):
        self.model_key, self.provider, self.model = model_key, "groq", model
        self.temperature, self.max_tokens, self.reasoning = temperature, max_tokens, reasoning
        self.parallel_tool_calls, self.timeout_seconds = parallel_tool_calls, timeout_seconds
        if client is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError("GROQ_API_KEY is not set")
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=self.BASE_URL, timeout=timeout_seconds, max_retries=0)
        self.client = client
        self.messages: list[dict[str, Any]] = []
        self.tools: list[dict[str, Any]] = []

    def settings(self) -> dict[str, Any]:
        return {"provider": self.provider, "model": self.model, "temperature": self.temperature, "max_tokens": self.max_tokens,
                "reasoning_effort": self.reasoning, "parallel_tool_calls": self.parallel_tool_calls,
                "timeout_seconds": self.timeout_seconds, "sdk_max_retries": 0}

    @staticmethod
    def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
                for t in tools]

    def _create(self) -> ModelTurn:
        kwargs: dict[str, Any] = {"model": self.model, "messages": self.messages, "tools": self.tools, "tool_choice": "auto",
                                  "temperature": self.temperature, "max_completion_tokens": self.max_tokens}
        if self.reasoning:
            kwargs["reasoning_effort"] = self.reasoning
        if self.parallel_tool_calls is not None:
            kwargs["parallel_tool_calls"] = self.parallel_tool_calls
        request = copy.deepcopy(kwargs)
        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 - classified, never swallowed
            raise _classify(exc) from exc
        raw = response.model_dump(mode="json") if hasattr(response, "model_dump") else response
        choice = response.choices[0]
        msg = choice.message
        calls: list[ToolCall] = []
        for tc in msg.tool_calls or []:
            raw_args = tc.function.arguments or "{}"
            try:
                args = json.loads(raw_args)
                if not isinstance(args, dict):
                    raise ValueError("arguments are not a JSON object")
                calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args, raw_arguments=raw_args))
            except (json.JSONDecodeError, ValueError) as exc:
                calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments={}, raw_arguments=raw_args,
                                      parse_ok=False, parse_error=str(exc)))
        assistant: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant["tool_calls"] = [{"id": tc.id, "type": "function",
                                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in msg.tool_calls]
        self.messages.append(assistant)
        u = response.usage
        usage = {}
        if u is not None:
            usage = {"input_tokens": int(getattr(u, "prompt_tokens", 0) or 0), "output_tokens": int(getattr(u, "completion_tokens", 0) or 0),
                     "total_tokens": int(getattr(u, "total_tokens", 0) or 0)}
            details = getattr(u, "completion_tokens_details", None)
            if details is not None and getattr(details, "reasoning_tokens", None) is not None:
                usage["reasoning_tokens"] = int(details.reasoning_tokens)
        return ModelTurn(text=msg.content or "", tool_calls=calls, finish_reason=choice.finish_reason, usage=usage,
                         request=request, response=raw)

    def start(self, system_prompt: str, user_prompt: str, tools: list[dict[str, Any]]) -> ModelTurn:
        self.messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        self.tools = self._convert_tools(tools)
        return self._create()

    def continue_turn(self, tool_results: list[tuple[ToolCall, dict[str, Any]]]) -> ModelTurn:
        for call, result in tool_results:
            self.messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, ensure_ascii=False)})
        return self._create()
