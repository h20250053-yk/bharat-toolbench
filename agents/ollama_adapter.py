"""Local Ollama adapter (native /api/chat, non-streaming) with native function calling. LOCAL models only.

Implements the provider-neutral interface in agents/base.py (start / continue_turn / settings) for models served by a
local Ollama server (e.g. qwen2.5:3b, later Llama). Model ID and settings come ONLY from config/models.yaml.

- HTTP via httpx (already a project dependency); no API key; base URL from config (default http://127.0.0.1:11434)
- deterministic decoding where Ollama supports it: options.temperature, options.seed
- explicit context window (options.num_ctx) and output budget (options.num_predict = max_tokens). Ollama silently
  truncates prompts that exceed num_ctx, so every response is checked: if prompt_eval_count + max_tokens > num_ctx the
  turn is rejected as ModelOutputError('context_overflow') -> the row gets status context_overflow, which is SCORED as a
  failure (label run:context_overflow): an overflow is caused by the model's own behaviour (e.g. looping tool calls), so
  excluding it would bias comparisons between models. It is never a silently degraded model answer. (prompt_eval_count is the FULL prompt size; cached tokens are reported
  separately as prompt_eval_cached_count.)
- tool calls: Ollama returns `arguments` as a JSON object (re-encoded for raw_arguments); a string is JSON-decoded;
  anything that is not a JSON object becomes ToolCall(parse_ok=False). A missing call id gets a synthetic one
  ('ollama-<turn>-<n>'). Tool results go back as {"role": "tool", "tool_name": ..., "content": <json>}.
- errors (runner retries only retryable ones): timeout / connection / 429 / 5xx -> retryable ProviderError;
  404 (model not pulled) / other 4xx / non-JSON or malformed body -> non-retryable ProviderError
- unparsed model output: when the model generated tokens (eval_count > 0) but Ollama returns neither content nor
  tool_calls, Ollama's tool-call parser has discarded output it could not convert (observed: a <tool_call> block
  without a function name, e.g. the final-answer JSON wrapped in <tool_call> tags). This is raised as
  ModelOutputError('unparsed_model_output') -> status malformed_output (a MODEL failure, scored, never retried;
  same treatment as Groq's tool_use_failed). Nothing is invented: no content or tool call is fabricated.
- tool schemas: Ollama re-serialises them into its own types and drops title / additionalProperties / $defs / $ref, so a
  schema that uses a $ref lost the structure behind it (time_window became anyOf [{}, null]). The adapter therefore INLINES
  every $ref/$defs before sending (`inline_refs`): the model sees the full structure of every parameter, including
  time_window {start, end}. The benchmark's own schema and TOOL_SCHEMA_SHA256 are unchanged; the hash of what was
  actually sent is recorded in settings() as tool_schema_sent_sha256.
- thinking: config `think` is a POLICY, resolved per model from /api/show capabilities (see `effective_think`):
  `think: false` -> thinking OFF for every model that can turn it off; models that cannot (gpt-oss: only low/medium/high)
  get the LOWEST level ("low"); models without the `thinking` capability get no `think` field at all. The effective value
  is sent as the top-level `think` request field and recorded in settings() (and in the pre-run snapshot / manifest).
  A returned `thinking` text is kept in the history (Ollama recommends echoing it during tool loops) and in the raw log.
- truncation: a reply that stops with done_reason "length" and carries no tool call (answer cut off by max_tokens, or the
  whole budget spent on thinking) is raised as ModelOutputError('output_truncated') -> status output_truncated, a scored
  model failure labelled separately from malformed output
- pre-flight (`preflight()`, also run by start()): `ollama show` (/api/show) must list the `tools` capability; a model
  without it, or a server that does not report capabilities, is refused (ProviderError 'tools_unsupported', never sent a
  chat request). It also REFUSES a server older than 0.40.18 (`check_min_version`; 0.40.13 discards valid tool calls). run_pilot calls it
  once before the first item and refuses to start the run; the pre-run snapshot refuses too and records the server version.
  The Modelfile `parameters` (repeat_penalty, top_k, ...) are recorded in settings() as modelfile_parameters.
- provenance: settings() reports the Ollama server version, the model digest, quantization and parameter size,
  read once from /api/version and /api/tags (cached per base URL + model)
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from .base import ModelOutputError, ModelTurn, ProviderError, ToolCall, parse_retry_after

DEFAULT_BASE_URL = "http://127.0.0.1:11434"

_MODEL_INFO_CACHE: dict[tuple[str, str], dict[str, Any]] = {}
MIN_OLLAMA_VERSION = (0, 40, 18)
_THINK_LEVELS = ("low", "medium", "high")


def parse_ollama_version(version: Any) -> tuple[int, int, int] | None:
    """'0.40.18' / 'v0.40.18' / '0.40.18-rc1' -> (0, 40, 18); anything else -> None. Compared numerically, never as strings."""
    m = re.match(r"^\s*v?(\d+)\.(\d+)\.(\d+)", version) if isinstance(version, str) else None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def check_min_version(version: Any) -> None:
    """Refuse (ProviderError 'ollama_too_old', non-retryable) a server older than MIN_OLLAMA_VERSION or one that reports no usable version.
    Older servers (0.40.13 and before) discard valid tool calls of some models (FORMAT_ROBUSTNESS.md, F-23)."""
    parsed = parse_ollama_version(version)
    need = ".".join(map(str, MIN_OLLAMA_VERSION))
    if parsed is None or parsed < MIN_OLLAMA_VERSION:
        raise ProviderError("ollama_too_old",
                            f"Ollama server version {version!r} is older than {need} (or reports no usable version); refusing to run. "
                            f"Servers before {need} discard valid tool-call replies (FORMAT_ROBUSTNESS.md F-23); install >= {need} (see LOCAL_MODELS.md)",
                            retryable=False)
LOWEST_THINK_LEVEL = "low"


def inline_refs(schema: Any) -> Any:
    """Copy of a JSON schema with every local `$ref` (#/$defs/X) replaced by the referenced definition and `$defs` removed.
    Ollama drops `$ref`/`$defs`, which would erase the structure of e.g. `time_window`."""
    defs = schema.get("$defs", {}) if isinstance(schema, dict) else {}

    def walk(node: Any, seen: tuple[str, ...]) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                name = ref.rsplit("/", 1)[1]
                if name in seen or name not in defs:
                    raise ValueError(f"cannot inline $ref {ref!r} (recursive or unknown)")
                merged = {**walk(defs[name], seen + (name,)), **{k: walk(v, seen) for k, v in node.items() if k != "$ref"}}
                return merged
            return {k: walk(v, seen) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [walk(x, seen) for x in node]
        return node
    return walk(schema, ())


def effective_think(model: str, capabilities: list[str] | None, think: Any) -> Any:
    """Value of the `think` request field for `model` under the configured policy `think`.

    None (policy unset)                       -> None (field not sent)
    capabilities unknown or no "thinking"     -> None (the model does not think; sending the field could be rejected)
    think False, model can switch it off      -> False
    think False, gpt-oss (cannot be disabled) -> "low" (the lowest reasoning level)
    think True / "low" / "medium" / "high"    -> passed through
    """
    if think is None or not capabilities or "thinking" not in capabilities:
        return None
    if think is False:
        return LOWEST_THINK_LEVEL if model.casefold().startswith("gpt-oss") else False
    return think


def _classify_http_error(exc: Exception) -> Exception:
    import httpx
    if isinstance(exc, httpx.TimeoutException):
        return ProviderError("timeout", f"Ollama request timed out: {exc}", retryable=True)
    if isinstance(exc, httpx.TransportError):  # connection refused (server not running), reset, DNS, ...
        return ProviderError("connection", f"Ollama connection error: {exc}", retryable=True)
    return exc


def _status_error(status: int, text: str, headers: Any = None) -> ProviderError:
    try:
        message = json.loads(text).get("error", text)
    except (ValueError, AttributeError):
        message = text
    message = f"Ollama HTTP {status}: {str(message)[:500]}"
    if status == 404:
        return ProviderError("not_found", message, retryable=False, status_code=status)
    if status == 429 or status >= 500:
        kind = "rate_limit" if status == 429 else "server"
        return ProviderError(kind, message, retryable=True, status_code=status, retry_after=parse_retry_after(headers))
    return ProviderError("bad_request" if status == 400 else "http_error", message, retryable=False, status_code=status)


class OllamaAdapter:
    PROVIDER = "ollama"
    SUPPORTS_TEXT_TOOL_RECOVERY = True   # the runner may execute a reply that is only tool-call JSON (tolerance.extract_text_tool_calls)

    def attach_recovered_tool_calls(self, calls: list[ToolCall]) -> None:
        """A tool call written as text was recovered: record it as the assistant's tool call so the next `tool` messages follow it."""
        if self.messages and self.messages[-1].get("role") == "assistant":
            self.messages[-1]["content"] = ""
            self.messages[-1]["tool_calls"] = [{"function": {"name": c.name, "arguments": c.arguments}} for c in calls]

    def __init__(self, *, model_key: str, model: str, temperature: float = 0, max_tokens: int = 1024,
                 reasoning: str | None = None, parallel_tool_calls: bool | None = None,
                 timeout_seconds: float = 300.0, num_ctx: int = 16384, seed: int | None = 0,
                 base_url: str | None = None, keep_alive: str | None = None, think: Any = None, client: Any = None):
        if reasoning:
            raise ValueError("Ollama adapter: `reasoning` is not supported; leave it unset for local models")
        if parallel_tool_calls is not None:
            raise ValueError("Ollama adapter: `parallel_tool_calls` is not an Ollama option; leave it unset")
        if think is not None and not (isinstance(think, bool) or think in _THINK_LEVELS):
            raise ValueError(f"Ollama adapter: `think` must be true, false or one of {_THINK_LEVELS}, got {think!r}")
        if max_tokens >= num_ctx:
            raise ValueError(f"Ollama adapter: max_tokens ({max_tokens}) must be smaller than num_ctx ({num_ctx})")
        self.model_key, self.provider, self.model = model_key, self.PROVIDER, model
        self.temperature, self.max_tokens, self.seed = temperature, max_tokens, seed
        self.num_ctx, self.timeout_seconds, self.keep_alive, self.think = num_ctx, timeout_seconds, keep_alive, think
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        if client is None:
            import httpx
            client = httpx.Client(timeout=timeout_seconds)
        self.client = client
        self.messages: list[dict[str, Any]] = []
        self.tools: list[dict[str, Any]] = []
        self._turn = 0
        self.model_info: dict[str, Any] = {}

    # ------------------------------------------------------------------------------------------------ provenance
    def settings(self) -> dict[str, Any]:
        return {"provider": self.provider, "model": self.model, "base_url": self.base_url, "endpoint": "/api/chat",
                "temperature": self.temperature, "seed": self.seed, "num_ctx": self.num_ctx,
                "max_tokens": self.max_tokens, "timeout_seconds": self.timeout_seconds, "keep_alive": self.keep_alive,
                "local": True, "tool_schema_sent_sha256": self._tool_schema_sha(), "think_config": self.think, "think_effective": self._think_value(), **self.model_info}

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        try:
            if method == "GET":
                resp = self.client.get(f"{self.base_url}{path}")
            else:
                resp = self.client.post(f"{self.base_url}{path}", json=payload)
        except Exception as exc:  # noqa: BLE001 - classified, never swallowed
            raise _classify_http_error(exc) from exc
        if resp.status_code >= 400:
            raise _status_error(resp.status_code, resp.text, getattr(resp, "headers", None))
        try:
            return resp.json()
        except ValueError as exc:
            raise ProviderError("invalid_response", f"Ollama returned non-JSON: {resp.text[:300]!r}", retryable=False) from exc

    def _tool_schema_sha(self) -> str | None:
        if not self.tools:
            return None
        return hashlib.sha256(json.dumps(self.tools, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def _think_value(self) -> Any:
        return effective_think(self.model, self.model_info.get("capabilities"), self.think)

    def _load_model_info(self) -> None:
        key = (self.base_url, self.model)
        if key not in _MODEL_INFO_CACHE:
            version = self._request("GET", "/api/version")
            tags = self._request("GET", "/api/tags")
            entry = next((m for m in (tags or {}).get("models", []) if self.model in (m.get("name"), m.get("model"))), None)
            if entry is None:
                raise ProviderError("not_found", f"Ollama model {self.model!r} is not installed (run: ollama pull {self.model})",
                                    retryable=False, status_code=404)
            details = entry.get("details") or {}
            try:  # capabilities (completion / tools / thinking ...) from `ollama show`; older servers may not provide them
                show = self._request("POST", "/api/show", {"model": self.model}) or {}
            except ProviderError:
                show = {}
            caps = show.get("capabilities") if isinstance(show, dict) else None
            modelfile_parameters = show.get("parameters") if isinstance(show, dict) and isinstance(show.get("parameters"), str) else None
            _MODEL_INFO_CACHE[key] = {"ollama_version": (version or {}).get("version"), "model_digest": entry.get("digest"),
                                      "quantization": details.get("quantization_level"),
                                      "parameter_size": details.get("parameter_size"), "model_family": details.get("family"),
                                      "model_max_context": details.get("context_length"),
                                      "capabilities": caps if isinstance(caps, list) else None,
                                      "modelfile_parameters": modelfile_parameters}
        self.model_info = dict(_MODEL_INFO_CACHE[key])

    def preflight(self) -> dict[str, Any]:
        """Refuse an Ollama server older than 0.40.18, then check that the model exists and lists the `tools` capability
        (via /api/show). Raises ProviderError otherwise (never just a warning)."""
        self._load_model_info()
        check_min_version(self.model_info.get("ollama_version"))
        caps = self.model_info.get("capabilities")
        if not caps or "tools" not in caps:
            raise ProviderError("tools_unsupported",
                                f"Ollama model {self.model!r} does not list the 'tools' capability in `ollama show` "
                                f"(capabilities: {caps if caps else 'not reported by this server'}); refusing to run it",
                                retryable=False)
        return dict(self.model_info)

    # ------------------------------------------------------------------------------------------------ chat
    @staticmethod
    def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                  "parameters": inline_refs(t["parameters"])}} for t in tools]

    def _options(self) -> dict[str, Any]:
        opts: dict[str, Any] = {"temperature": self.temperature, "num_ctx": self.num_ctx, "num_predict": self.max_tokens}
        if self.seed is not None:
            opts["seed"] = self.seed
        return opts

    def _create(self) -> ModelTurn:
        self._turn += 1
        payload: dict[str, Any] = {"model": self.model, "messages": self.messages, "tools": self.tools, "stream": False,
                                   "options": self._options()}
        if self.keep_alive is not None:
            payload["keep_alive"] = self.keep_alive
        think = self._think_value()
        if think is not None:
            payload["think"] = think
        request = copy.deepcopy(payload)
        body = self._request("POST", "/api/chat", payload)
        if not isinstance(body, dict):
            raise ProviderError("invalid_response", f"Ollama returned a non-object body: {str(body)[:300]!r}", retryable=False)
        if body.get("error"):
            raise ProviderError("server", f"Ollama error: {str(body['error'])[:500]}", retryable=True)
        msg = body.get("message")
        if not isinstance(msg, dict):
            raise ProviderError("invalid_response", "Ollama response has no message object", retryable=False)

        prompt_tokens = int(body.get("prompt_eval_count") or 0)
        output_tokens = int(body.get("eval_count") or 0)
        if prompt_tokens + self.max_tokens > self.num_ctx:
            raise ModelOutputError("context_overflow",
                                   f"prompt uses {prompt_tokens} of num_ctx={self.num_ctx} tokens, leaving less than "
                                   f"max_tokens={self.max_tokens} for the answer; Ollama may have truncated the prompt.",
                                   raw={"turn": self._turn, "prompt_eval_count": prompt_tokens, "num_ctx": self.num_ctx,
                                        "max_tokens": self.max_tokens})

        if body.get("done_reason") == "length" and not msg.get("tool_calls"):
            raise ModelOutputError("output_truncated",
                                   f"reply stopped at the max_tokens={self.max_tokens} limit without a tool call "
                                   f"({output_tokens} tokens generated; {len(msg.get('content') or '')} characters of content, "
                                   f"{len(msg.get('thinking') or '')} of thinking)",
                                   raw={"turn": self._turn, "done_reason": "length", "eval_count": output_tokens,
                                        "prompt_eval_count": prompt_tokens, "max_tokens": self.max_tokens,
                                        "content_chars": len(msg.get("content") or ""), "thinking_chars": len(msg.get("thinking") or "")})

        if not msg.get("content") and not msg.get("tool_calls") and output_tokens > 0:
            diagnostics = {k: body.get(k) for k in ("model", "done_reason", "prompt_eval_count", "prompt_eval_cached_count",
                                                    "eval_count", "total_duration", "eval_duration")}
            raise ModelOutputError("unparsed_model_output",
                                   f"model generated {output_tokens} tokens but Ollama returned no content and no tool calls "
                                   f"(output discarded by Ollama's tool-call parser, e.g. a malformed <tool_call> block)",
                                   raw={"turn": self._turn, **diagnostics})

        calls: list[ToolCall] = []
        history_calls: list[dict[str, Any]] = []
        for i, tc in enumerate(msg.get("tool_calls") or [], 1):
            tc = tc if isinstance(tc, dict) else {}
            fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
            call_id = tc.get("id") or f"ollama-{self._turn}-{i}"
            name = fn.get("name") or ""
            arguments = fn.get("arguments")
            history_calls.append(copy.deepcopy(tc))
            raw = arguments if isinstance(arguments, str) else json.dumps(arguments, ensure_ascii=False)
            try:
                if not name:
                    raise ValueError("tool call has no function name")
                args = json.loads(arguments) if isinstance(arguments, str) else arguments
                if not isinstance(args, dict):
                    raise ValueError("arguments are not a JSON object")
                calls.append(ToolCall(id=call_id, name=name, arguments=args, raw_arguments=raw))
            except (json.JSONDecodeError, ValueError) as exc:
                calls.append(ToolCall(id=call_id, name=name, arguments={}, raw_arguments=raw, parse_ok=False, parse_error=str(exc)))

        text = msg.get("content") or ""
        assistant: dict[str, Any] = {"role": "assistant", "content": text}
        if history_calls:
            assistant["tool_calls"] = history_calls
        if msg.get("thinking"):  # echoed back for the next turn of a tool loop (thinking models); also kept in the raw log
            assistant["thinking"] = msg["thinking"]
        self.messages.append(assistant)
        usage = {"input_tokens": prompt_tokens, "output_tokens": output_tokens, "total_tokens": prompt_tokens + output_tokens}
        if body.get("prompt_eval_cached_count") is not None:
            usage["cached_input_tokens"] = int(body.get("prompt_eval_cached_count") or 0)
        return ModelTurn(text=text, tool_calls=calls, finish_reason=body.get("done_reason"), usage=usage,
                         request=request, response=body)

    def start(self, system_prompt: str, user_prompt: str, tools: list[dict[str, Any]]) -> ModelTurn:
        self.preflight()
        self.messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        self.tools = self._convert_tools(tools)
        self._turn = 0
        return self._create()

    def continue_turn(self, tool_results: list[tuple[ToolCall, dict[str, Any]]]) -> ModelTurn:
        for call, result in tool_results:
            self.messages.append({"role": "tool", "tool_name": call.name, "content": json.dumps(result, ensure_ascii=False)})
        return self._create()
