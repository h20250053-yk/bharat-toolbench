"""Google Gemini (google-genai) adapter with a manual function-calling loop.

- tool results are sent back as types.Part(function_response=types.FunctionResponse(name, response, id)), which
  preserves the tool-call id (Part.from_function_response has no id parameter in google-genai 2.x)
- the configured reasoning level is applied as types.ThinkingConfig(thinking_level=...) ('minimal' -> MINIMAL)
- request timeout from config (plan: 90 s); SDK-internal retries limited to a single attempt, so ONLY the
  runner's explicit, logged retry policy applies
- MALFORMED_FUNCTION_CALL / SAFETY / empty candidate -> ModelOutputError (model failure, never retried)
- the full candidate content (incl. thought signatures) is kept in the history, as Google requires
"""
from __future__ import annotations

import os
import re
from typing import Any

from .base import ModelOutputError, ModelTurn, ProviderError, ToolCall, parse_retry_after

_THINKING_LEVELS = {"minimal": "MINIMAL", "min": "MINIMAL", "low": "LOW", "medium": "MEDIUM", "high": "HIGH"}


def _dump(obj: Any) -> Any:
    try:
        return obj.model_dump(mode="json", exclude_none=True)
    except Exception:  # noqa: BLE001
        return repr(obj)


def _retry_delay(exc: Any) -> float | None:
    headers = getattr(getattr(exc, "response", None), "headers", None)
    ra = parse_retry_after(headers)
    if ra is not None:
        return ra
    details = (getattr(exc, "details", None) or {})
    for d in (details.get("error", details).get("details", []) if isinstance(details, dict) else []):
        if isinstance(d, dict) and str(d.get("@type", "")).endswith("RetryInfo"):
            m = re.fullmatch(r"([\d.]+)s", str(d.get("retryDelay", "")))
            if m:
                return float(m.group(1))
    return None


def _classify(exc: Exception) -> Exception:
    from google.genai import errors
    try:
        import httpx
        if isinstance(exc, httpx.TimeoutException):
            return ProviderError("timeout", str(exc), retryable=True)
        if isinstance(exc, httpx.TransportError):
            return ProviderError("connection", str(exc), retryable=True)
    except ImportError:  # pragma: no cover
        pass
    if isinstance(exc, errors.APIError):
        code = getattr(exc, "code", None)
        if code == 429:
            return ProviderError("rate_limit", str(exc), retryable=True, status_code=429, retry_after=_retry_delay(exc))
        if code == 408:
            return ProviderError("timeout", str(exc), retryable=True, status_code=408)
        if code is not None and code >= 500:
            return ProviderError("server", str(exc), retryable=True, status_code=code, retry_after=_retry_delay(exc))
        if code in (401, 403):
            return ProviderError("auth", str(exc), retryable=False, status_code=code)
        return ProviderError("bad_request" if code == 400 else "http_error", str(exc), retryable=False, status_code=code)
    return exc


class GeminiAdapter:
    def __init__(self, *, model_key: str, model: str, temperature: float = 0, max_tokens: int = 1024,
                 reasoning: str | None = None, timeout_seconds: float = 90.0, client: Any = None,
                 parallel_tool_calls: bool | None = None):
        from google.genai import types
        self.types = types
        self.model_key, self.provider, self.model = model_key, "google", model
        self.temperature, self.max_tokens, self.reasoning, self.timeout_seconds = temperature, max_tokens, reasoning, timeout_seconds
        if reasoning and reasoning.lower() not in _THINKING_LEVELS:
            raise ValueError(f"Unsupported Gemini reasoning level {reasoning!r}; expected one of {sorted(_THINKING_LEVELS)}")
        if client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is not set")
            from google import genai
            client = genai.Client(api_key=api_key, http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000), retry_options=types.HttpRetryOptions(attempts=1)))
        self.client = client
        self.config: Any = None
        self.contents: list[Any] = []

    def settings(self) -> dict[str, Any]:
        return {"provider": self.provider, "model": self.model, "temperature": self.temperature, "max_output_tokens": self.max_tokens,
                "thinking_level": _THINKING_LEVELS.get((self.reasoning or "").lower()), "timeout_seconds": self.timeout_seconds,
                "sdk_retry_attempts": 1, "parallel_tool_calls": "provider-controlled (not configurable)"}

    def _convert_tools(self, tools: list[dict[str, Any]]) -> Any:
        t = self.types
        return t.Tool(function_declarations=[t.FunctionDeclaration(name=x["name"], description=x["description"],
                                                                    parameters_json_schema=x["parameters"]) for x in tools])

    def _create(self) -> ModelTurn:
        request = {"model": self.model, "contents": [_dump(c) for c in self.contents], "config": _dump(self.config)}
        try:
            response = self.client.models.generate_content(model=self.model, contents=self.contents, config=self.config)
        except Exception as exc:  # noqa: BLE001 - classified, never swallowed
            raise _classify(exc) from exc
        raw = _dump(response)
        cands = response.candidates or []
        if not cands or cands[0].content is None:
            fr = str(getattr(cands[0], "finish_reason", None)) if cands else "NO_CANDIDATE"
            kind = "malformed_function_call" if "MALFORMED_FUNCTION_CALL" in fr else "safety" if "SAFETY" in fr else "empty_response"
            raise ModelOutputError(kind, f"Gemini returned no usable content (finish_reason={fr})", raw=raw)
        cand = cands[0]
        finish = getattr(cand.finish_reason, "value", None) or (str(cand.finish_reason) if cand.finish_reason else None)
        if finish == "MALFORMED_FUNCTION_CALL":
            raise ModelOutputError("malformed_function_call", "Gemini finish_reason MALFORMED_FUNCTION_CALL", raw=raw)
        self.contents.append(cand.content)  # keeps thought signatures for the next turn
        calls, texts = [], []
        for i, part in enumerate(cand.content.parts or []):
            if part.function_call is not None:
                fc = part.function_call
                calls.append(ToolCall(id=fc.id or f"call_{len(self.contents)}_{i}", name=fc.name, arguments=dict(fc.args or {})))
            elif part.text and not part.thought:
                texts.append(part.text)
        usage = {}
        um = response.usage_metadata
        if um is not None:
            inp, cand_t, thought_t = um.prompt_token_count or 0, um.candidates_token_count or 0, um.thoughts_token_count or 0
            usage = {"input_tokens": inp, "output_tokens": cand_t + thought_t, "reasoning_tokens": thought_t,
                     "total_tokens": um.total_token_count or (inp + cand_t + thought_t)}
        return ModelTurn(text="".join(texts), tool_calls=calls, finish_reason=finish, usage=usage, request=request, response=raw)

    def start(self, system_prompt: str, user_prompt: str, tools: list[dict[str, Any]]) -> ModelTurn:
        t = self.types
        thinking = None
        if self.reasoning:
            thinking = t.ThinkingConfig(thinking_level=getattr(t.ThinkingLevel, _THINKING_LEVELS[self.reasoning.lower()]))
        self.config = t.GenerateContentConfig(
            system_instruction=system_prompt, tools=[self._convert_tools(tools)], temperature=self.temperature,
            max_output_tokens=self.max_tokens, thinking_config=thinking,
            automatic_function_calling=t.AutomaticFunctionCallingConfig(disable=True))
        self.contents = [t.Content(role="user", parts=[t.Part(text=user_prompt)])]
        return self._create()

    def continue_turn(self, tool_results: list[tuple[ToolCall, dict[str, Any]]]) -> ModelTurn:
        t = self.types
        parts = [t.Part(function_response=t.FunctionResponse(name=call.name, response=result, id=call.id))
                 for call, result in tool_results]
        self.contents.append(t.Content(role="user", parts=parts))
        return self._create()
