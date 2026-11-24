"""OpenRouter (OpenAI-compatible chat completions) adapter with native function calling. EXPERIMENTAL models only.

Mirrors agents/groq_adapter.py (same ModelTurn / ToolCall normalisation, same error taxonomy from agents/base.py) with the
OpenRouter-specific differences below. Model ID and settings come ONLY from config/models.yaml.

- API key read ONLY from the OPENROUTER_API_KEY environment variable; never logged, never stored in a row
- SDK retries disabled (max_retries=0): the runner's explicit, logged retry policy is the only one
- sends OpenRouter's `max_tokens` (NOT Groq's `max_completion_tokens`); per OpenRouter docs this budget covers reasoning
  AND visible output on most providers
- `reasoning_effort` (an OpenAI/Groq parameter) is never sent; if `reasoning` is configured it is sent as OpenRouter's
  unified `reasoning: {"effort": ...}` object. `parallel_tool_calls` is sent only if configured. Neither is configured
  for experimental_inkling, because support by that endpoint is unverified
- `tools` is sent on EVERY request (OpenRouter docs: "The tools parameter must be included in every request")
- assistant `reasoning_details` are passed back unmodified in the history (OpenRouter docs: preserve them for tool calling)
- OpenRouter can return HTTP 200 whose body holds only an `error` object (no `choices`), or a choice with
  finish_reason "error": both are PROVIDER failures (ProviderError), never model outputs and never scored
- 401 auth, 402 insufficient credits, 403 forbidden (e.g. ':free only available on agentic harnesses', moderation,
  guardrail/budget block), 404 not found / no endpoint -> non-retryable; 408 / 429 / 5xx / timeout / connection -> retryable
- a 2xx body that is not a chat completion (e.g. an HTML page, or invalid JSON) -> non-retryable ProviderError
  'invalid_response' (never a model answer; not retried, so a gate/HTML page cannot burn the request budget)
- odd tool-call shapes (missing function/name, arguments given as an object instead of a JSON string) are normalised
  or returned as ToolCall(parse_ok=False); they never crash the evaluation
- the value of OPENROUTER_API_KEY is redacted from every error message this adapter creates (defence in depth)
"""
from __future__ import annotations

import copy
import json
import os
from typing import Any

from .base import ModelTurn, ProviderError, ToolCall, parse_retry_after

API_KEY_ENV = "OPENROUTER_API_KEY"

# status -> (kind, retryable) for errors reported inside an HTTP-200 body (no exception raised by the SDK)
_BODY_ERROR_KINDS = {401: ("auth", False), 402: ("insufficient_credits", False), 403: ("forbidden", False),
                     404: ("not_found", False), 408: ("timeout", True), 429: ("rate_limit", True)}


def _redact(text: Any) -> str:
    """Remove the configured API key value from any text that may end up in a row, log or console."""
    text = str(text)
    key = os.getenv(API_KEY_ENV)
    if key and len(key) >= 8:
        text = text.replace(key, "[REDACTED]")
    return text


def _classify(exc: Exception) -> Exception:
    out = _classify_raw(exc)
    if isinstance(out, ProviderError):
        out.args = (_redact(out.args[0] if out.args else ""),)
    return out


def _classify_raw(exc: Exception) -> Exception:
    import openai
    status = getattr(exc, "status_code", None)
    headers = getattr(getattr(exc, "response", None), "headers", None)
    if isinstance(exc, (openai.APIResponseValidationError, json.JSONDecodeError)):
        return ProviderError("invalid_response", f"response is not a valid chat completion: {exc}", retryable=False,
                             status_code=status)
    if isinstance(exc, openai.RateLimitError):
        return ProviderError("rate_limit", str(exc), retryable=True, status_code=429, retry_after=parse_retry_after(headers))
    if isinstance(exc, openai.APITimeoutError):
        return ProviderError("timeout", str(exc), retryable=True)
    if isinstance(exc, openai.APIConnectionError):
        return ProviderError("connection", str(exc), retryable=True)
    if isinstance(exc, openai.AuthenticationError):
        return ProviderError("auth", str(exc), retryable=False, status_code=status)
    if isinstance(exc, openai.PermissionDeniedError):
        return ProviderError("forbidden", str(exc), retryable=False, status_code=status)
    if isinstance(exc, openai.BadRequestError):
        return ProviderError("bad_request", str(exc), retryable=False, status_code=status)
    if isinstance(exc, openai.NotFoundError):
        return ProviderError("not_found", str(exc), retryable=False, status_code=status)
    if isinstance(exc, openai.APIStatusError):
        if status == 402:
            return ProviderError("insufficient_credits", str(exc), retryable=False, status_code=status)
        if status == 408:
            return ProviderError("timeout", str(exc), retryable=True, status_code=status, retry_after=parse_retry_after(headers))
        if status is not None and status >= 500:
            return ProviderError("server", str(exc), retryable=True, status_code=status, retry_after=parse_retry_after(headers))
        return ProviderError("http_error", str(exc), retryable=False, status_code=status)
    return exc


def _body_error(err: Any, where: str) -> ProviderError:
    """ProviderError for an error object delivered with HTTP 200 (top level, or inside a choice)."""
    if not isinstance(err, dict):
        err = {"message": str(err)}
    code = err.get("code")
    try:
        code = int(code)
    except (TypeError, ValueError):
        code = None
    kind, retryable = _BODY_ERROR_KINDS.get(code, ("server", True) if code is None or code >= 500 else ("http_error", False))
    return ProviderError(kind, _redact(f"OpenRouter {where} error {code}: {err.get('message', '')}")[:1000],
                         retryable=retryable, status_code=code)


def _as_int(v: Any) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _usage(u: Any) -> dict[str, int]:
    """Normalised integer usage. Missing usage -> {}; missing total -> input + output. (Cost is kept in the raw response
    only, because the runner sums usage values as integers.)"""
    if u is None:
        return {}
    get = (lambda k: u.get(k)) if isinstance(u, dict) else (lambda k: getattr(u, k, None))
    usage = {"input_tokens": _as_int(get("prompt_tokens")), "output_tokens": _as_int(get("completion_tokens"))}
    usage["total_tokens"] = _as_int(get("total_tokens")) or usage["input_tokens"] + usage["output_tokens"]
    details = get("completion_tokens_details")
    if details is not None:
        r = details.get("reasoning_tokens") if isinstance(details, dict) else getattr(details, "reasoning_tokens", None)
        if r is not None:
            usage["reasoning_tokens"] = _as_int(r)
    return usage


class OpenRouterAdapter:
    BASE_URL = "https://openrouter.ai/api/v1"
    SUPPORTS_TEXT_TOOL_RECOVERY = True

    def attach_recovered_tool_calls(self, calls: list[ToolCall]) -> None:
        from .base import attach_openai_style_tool_calls
        attach_openai_style_tool_calls(self.messages, calls)

    def __init__(self, *, model_key: str, model: str, temperature: float = 0, max_tokens: int = 1024,
                 reasoning: str | None = None, parallel_tool_calls: bool | None = None,
                 timeout_seconds: float = 60.0, client: Any = None):
        self.model_key, self.provider, self.model = model_key, "openrouter", model
        self.temperature, self.max_tokens, self.reasoning = temperature, max_tokens, reasoning
        self.parallel_tool_calls, self.timeout_seconds = parallel_tool_calls, timeout_seconds
        if client is None:
            api_key = os.getenv(API_KEY_ENV)
            if not api_key:
                raise RuntimeError(f"{API_KEY_ENV} is not set")
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=self.BASE_URL, timeout=timeout_seconds, max_retries=0)
        self.client = client
        self.messages: list[dict[str, Any]] = []
        self.tools: list[dict[str, Any]] = []
        self._turn = 0

    def settings(self) -> dict[str, Any]:
        return {"provider": self.provider, "model": self.model, "base_url": self.BASE_URL, "temperature": self.temperature,
                "max_tokens": self.max_tokens, "reasoning": self.reasoning, "parallel_tool_calls": self.parallel_tool_calls,
                "timeout_seconds": self.timeout_seconds, "sdk_max_retries": 0, "experimental": True}

    @staticmethod
    def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
                for t in tools]

    def _create(self) -> ModelTurn:
        self._turn += 1
        kwargs: dict[str, Any] = {"model": self.model, "messages": self.messages, "tools": self.tools, "tool_choice": "auto",
                                  "temperature": self.temperature, "max_tokens": self.max_tokens}
        if self.parallel_tool_calls is not None:
            kwargs["parallel_tool_calls"] = self.parallel_tool_calls
        if self.reasoning:
            kwargs["extra_body"] = {"reasoning": {"effort": self.reasoning}}
        request = copy.deepcopy(kwargs)
        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 - classified, never swallowed
            raise _classify(exc) from exc
        if not hasattr(response, "model_dump"):  # e.g. an HTML page served with 200: the SDK hands back a plain str
            raise ProviderError("invalid_response", _redact(f"response is not a chat completion: {str(response)[:300]!r}"),
                                retryable=False)
        raw = response.model_dump(mode="json")
        top_error = getattr(response, "error", None)
        if top_error:
            raise _body_error(top_error, "response")
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise ProviderError("empty_response", "OpenRouter returned no choices and no error object", retryable=True)
        choice = choices[0]
        if choice.finish_reason == "error" or getattr(choice, "error", None):
            raise _body_error(getattr(choice, "error", None) or {"message": "finish_reason=error"}, "choice")
        msg = getattr(choice, "message", None)
        if msg is None:
            raise ProviderError("empty_response", "OpenRouter returned a choice without a message", retryable=True)
        calls: list[ToolCall] = []
        history_calls: list[dict[str, Any]] = []
        for i, tc in enumerate(msg.tool_calls or [], 1):
            call_id = getattr(tc, "id", None) or f"or-{self._turn}-{i}"   # some upstreams omit ids; the reply must reference one
            fn = getattr(tc, "function", None)
            name = (getattr(fn, "name", None) if fn is not None else None) or ""
            arguments = getattr(fn, "arguments", None) if fn is not None else None
            if isinstance(arguments, (dict, list)):        # non-standard: arguments already decoded -> re-encode
                arguments = json.dumps(arguments, ensure_ascii=False)
            elif arguments is not None and not isinstance(arguments, str):
                arguments = str(arguments)
            raw_args = arguments or "{}"
            history_calls.append({"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments or ""}})
            try:
                if not name:
                    raise ValueError("tool call has no function name")
                args = json.loads(raw_args)
                if not isinstance(args, dict):
                    raise ValueError("arguments are not a JSON object")
                calls.append(ToolCall(id=call_id, name=name, arguments=args, raw_arguments=raw_args))
            except (json.JSONDecodeError, ValueError) as exc:
                calls.append(ToolCall(id=call_id, name=name, arguments={}, raw_arguments=raw_args,
                                      parse_ok=False, parse_error=str(exc)))
        assistant: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
        if history_calls:
            assistant["tool_calls"] = history_calls
        reasoning_details = getattr(msg, "reasoning_details", None)
        if reasoning_details:
            assistant["reasoning_details"] = copy.deepcopy(reasoning_details)
        self.messages.append(assistant)
        return ModelTurn(text=msg.content or "", tool_calls=calls, finish_reason=choice.finish_reason,
                         usage=_usage(getattr(response, "usage", None)), request=request, response=raw)

    def start(self, system_prompt: str, user_prompt: str, tools: list[dict[str, Any]]) -> ModelTurn:
        self.messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        self.tools = self._convert_tools(tools)
        self._turn = 0
        return self._create()

    def continue_turn(self, tool_results: list[tuple[ToolCall, dict[str, Any]]]) -> ModelTurn:
        for call, result in tool_results:
            self.messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, ensure_ascii=False)})
        return self._create()
