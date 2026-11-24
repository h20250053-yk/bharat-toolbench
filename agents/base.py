"""Provider-neutral model adapter interface for BharatToolBench.

Error taxonomy (decides what the runner may retry):
  ProviderError(retryable=True)   rate limit (429), server error (5xx), timeout, connection error -> retried with backoff
  ProviderError(retryable=False)  auth / permission / bad request / unknown provider failure     -> NOT retried, row = provider_error
  ModelOutputError                the MODEL produced unusable output (e.g. Gemini MALFORMED_FUNCTION_CALL, Groq
                                  tool_use_failed, safety stop, empty candidate)                 -> NOT retried, model failure
A malformed tool call whose call id is known is NOT an exception: it is returned as ToolCall(parse_ok=False) so the
runner can record it as a trajectory event and tell the model, without crashing the evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class ProviderError(Exception):
    def __init__(self, kind: str, message: str, *, retryable: bool, status_code: int | None = None,
                 retry_after: float | None = None):
        super().__init__(message)
        self.kind, self.retryable, self.status_code, self.retry_after = kind, retryable, status_code, retry_after


class ModelOutputError(Exception):
    def __init__(self, kind: str, message: str, *, raw: Any = None):
        super().__init__(message)
        self.kind, self.raw = kind, raw


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    raw_arguments: str | None = None
    parse_ok: bool = True
    parse_error: str | None = None


@dataclass
class ModelTurn:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)      # normalized: input_tokens, output_tokens, total_tokens, ...
    request: Any = None                                       # JSON-serializable snapshot of what was sent
    response: Any = None                                      # JSON-serializable raw provider response


class ModelAdapter(Protocol):
    model_key: str
    provider: str
    model: str

    def settings(self) -> dict[str, Any]: ...

    def start(self, system_prompt: str, user_prompt: str, tools: list[dict[str, Any]]) -> ModelTurn: ...

    def continue_turn(self, tool_results: list[tuple[ToolCall, dict[str, Any]]]) -> ModelTurn: ...


def attach_openai_style_tool_calls(messages: list[dict[str, Any]], calls: list[ToolCall]) -> None:
    """The last assistant message becomes the tool-call message of `calls` (OpenAI-compatible chat history). Used when a tool call
    was written as text and recovered: the following tool results must reference ids that the assistant message declares."""
    if messages and messages[-1].get("role") == "assistant":
        import json
        messages[-1]["content"] = ""
        messages[-1]["tool_calls"] = [{"id": c.id, "type": "function",
                                       "function": {"name": c.name, "arguments": c.raw_arguments or json.dumps(c.arguments, ensure_ascii=False)}}
                                      for c in calls]


def parse_retry_after(headers: Any) -> float | None:
    """Seconds to wait from Retry-After / x-ratelimit-reset-* headers ('7', '2.5', '1m3s', '450ms'); None if absent."""
    if not headers:
        return None
    import re
    getter = headers.get if hasattr(headers, "get") else (lambda k: None)
    for key in ("retry-after", "Retry-After", "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens"):
        v = getter(key)
        if not v:
            continue
        v = str(v).strip()
        try:
            return float(v)
        except ValueError:
            pass
        total, ok = 0.0, False
        for num, unit in re.findall(r"([\d.]+)\s*(ms|h|m|s)", v):
            ok = True
            total += float(num) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]
        if ok:
            return total
    return None
