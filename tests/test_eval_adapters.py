"""Offline adapter tests: real SDK types, fake transports. No network, no API calls, no real keys."""
import json
from types import SimpleNamespace

import httpx
import openai
import pytest
from google.genai import errors, types

from agents.base import ModelOutputError, ProviderError, ToolCall
from agents.gemini_adapter import GeminiAdapter
from agents.groq_adapter import GroqAdapter
from agents.registry import build_adapter, load_model_config

TOOLS = [{"name": "get_fare", "description": "fare", "parameters": {"type": "object", "properties": {
    "train_id": {"type": "string"}, "travel_class": {"type": "string"}}, "required": ["train_id", "travel_class"]}}]


# ============================================================================ Gemini
def gem_response(parts, finish=types.FinishReason.STOP, usage=(100, 20, 5)):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=parts), finish_reason=finish)],
        usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=usage[0], candidates_token_count=usage[1],
                                                                  thoughts_token_count=usage[2], total_token_count=sum(usage)))


class FakeGemini:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []
        self.models = SimpleNamespace(generate_content=self._gen)

    def _gen(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": list(contents), "config": config})
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def gemini(responses, reasoning="minimal"):
    fake = FakeGemini(responses)
    return GeminiAdapter(model_key="primary_b", model="gemini-test", reasoning=reasoning, client=fake), fake


def test_gemini_tool_result_round_trip_preserves_call_id():
    call = types.Part(function_call=types.FunctionCall(name="get_fare", args={"train_id": "BTB103", "travel_class": "2A"}, id="fc-123"))
    a, fake = gemini([gem_response([call]), gem_response([types.Part(text="The fare is 3565.")])])
    t1 = a.start("sys", "user question", TOOLS)
    assert [(c.id, c.name, c.arguments) for c in t1.tool_calls] == [("fc-123", "get_fare", {"train_id": "BTB103", "travel_class": "2A"})]
    result = {"ok": True, "data": {"train_id": "BTB103", "travel_class": "2A", "fare_inr": 3565}, "error": None}
    t2 = a.continue_turn([(t1.tool_calls[0], result)])          # crashed before the fix (no `id` on from_function_response)
    sent = fake.calls[1]["contents"][-1]
    assert sent.role == "user"
    fr = sent.parts[0].function_response
    assert (fr.id, fr.name, fr.response) == ("fc-123", "get_fare", result)
    # the history kept the model's own content (thought signatures live there) and round-trips through JSON
    assert fake.calls[1]["contents"][1].parts[0].function_call.id == "fc-123"
    json.dumps([c.model_dump(mode="json", exclude_none=True) for c in fake.calls[1]["contents"]])
    assert t2.text == "The fare is 3565." and t2.tool_calls == []
    assert t1.usage == {"input_tokens": 100, "output_tokens": 25, "reasoning_tokens": 5, "total_tokens": 125}
    json.dumps(t2.request), json.dumps(t2.response)  # raw logs are JSON-serializable


def test_gemini_applies_minimal_thinking_and_disables_auto_calling():
    a, fake = gemini([gem_response([types.Part(text="hi")])])
    a.start("sys", "q", TOOLS)
    cfg = fake.calls[0]["config"]
    assert cfg.thinking_config.thinking_level == types.ThinkingLevel.MINIMAL
    assert cfg.automatic_function_calling.disable is True and cfg.temperature == 0 and cfg.max_output_tokens == 1024
    assert a.settings()["thinking_level"] == "MINIMAL"


def test_gemini_thought_parts_are_not_answer_text():
    a, _ = gemini([gem_response([types.Part(text="internal reasoning", thought=True), types.Part(text="Answer.")])])
    assert a.start("sys", "q", TOOLS).text == "Answer."


def test_gemini_malformed_function_call_is_model_output_error():
    bad = types.GenerateContentResponse(candidates=[types.Candidate(finish_reason=types.FinishReason.MALFORMED_FUNCTION_CALL)])
    a, _ = gemini([bad])
    with pytest.raises(ModelOutputError) as e:
        a.start("sys", "q", TOOLS)
    assert e.value.kind == "malformed_function_call"


def test_gemini_error_classification():
    rl = errors.APIError(code=429, response_json={"error": {"code": 429, "message": "quota", "details": [
        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "30s"}]}})
    a, _ = gemini([rl])
    with pytest.raises(ProviderError) as e:
        a.start("sys", "q", TOOLS)
    assert (e.value.kind, e.value.retryable, e.value.retry_after) == ("rate_limit", True, 30.0)
    a, _ = gemini([errors.APIError(code=503, response_json={"error": {"message": "unavailable"}})])
    with pytest.raises(ProviderError) as e:
        a.start("sys", "q", TOOLS)
    assert e.value.retryable
    a, _ = gemini([errors.APIError(code=400, response_json={"error": {"message": "bad"}})])
    with pytest.raises(ProviderError) as e:
        a.start("sys", "q", TOOLS)
    assert not e.value.retryable
    a, _ = gemini([httpx.ReadTimeout("slow")])
    with pytest.raises(ProviderError) as e:
        a.start("sys", "q", TOOLS)
    assert e.value.kind == "timeout" and e.value.retryable


def test_gemini_real_client_timeout_and_no_sdk_retries(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-not-used")  # constructing the client makes no request
    a = build_adapter("primary_b")
    opts = a.client._api_client._http_options
    assert opts.timeout == 90_000 and opts.retry_options.attempts == 1


# ============================================================================ Groq
def chat(content=None, tool_calls=None, usage=(50, 10)):
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = [{"id": i, "type": "function", "function": {"name": n, "arguments": a}} for i, n, a in tool_calls]
    return openai.types.chat.ChatCompletion.model_validate({
        "id": "x", "object": "chat.completion", "created": 0, "model": "m",
        "choices": [{"index": 0, "message": msg, "finish_reason": "tool_calls" if tool_calls else "stop"}],
        "usage": {"prompt_tokens": usage[0], "completion_tokens": usage[1], "total_tokens": sum(usage)}})


class FakeGroq:
    def __init__(self, responses):
        self.responses, self.kwargs = list(responses), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.kwargs.append(json.loads(json.dumps(kw)))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def groq(responses):
    fake = FakeGroq(responses)
    cfg = load_model_config()["primary_a"]
    return GroqAdapter(model_key="primary_a", model=cfg["model"], reasoning=cfg["reasoning"],
                       parallel_tool_calls=cfg["parallel_tool_calls"], client=fake), fake


def test_groq_disables_parallel_tool_calls_and_sends_config():
    a, fake = groq([chat("hi")])
    a.start("sys", "q", TOOLS)
    kw = fake.kwargs[0]
    assert kw["parallel_tool_calls"] is False and kw["reasoning_effort"] == "low"
    assert kw["temperature"] == 0 and kw["max_completion_tokens"] == 1024 and kw["tool_choice"] == "auto"


def test_groq_malformed_arguments_do_not_crash():
    a, _ = groq([chat(tool_calls=[("t1", "get_fare", '{"train_id": "BTB103",')])])
    t = a.start("sys", "q", TOOLS)
    c = t.tool_calls[0]
    assert c.parse_ok is False and c.raw_arguments == '{"train_id": "BTB103",' and c.arguments == {}


def test_groq_round_trip_and_usage():
    a, fake = groq([chat(tool_calls=[("t1", "get_fare", '{"train_id": "BTB103", "travel_class": "2A"}')]), chat("3565")])
    t1 = a.start("sys", "q", TOOLS)
    t2 = a.continue_turn([(t1.tool_calls[0], {"ok": True, "data": {"fare_inr": 3565}})])
    tool_msg = fake.kwargs[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "t1" and json.loads(tool_msg["content"])["data"]["fare_inr"] == 3565
    assert t2.text == "3565" and t1.usage == {"input_tokens": 50, "output_tokens": 10, "total_tokens": 60}


REQ = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")


@pytest.mark.parametrize("exc,kind,retryable,retry_after", [
    (openai.RateLimitError("r", response=httpx.Response(429, headers={"retry-after": "7"}, request=REQ), body=None), "rate_limit", True, 7.0),
    (openai.RateLimitError("r", response=httpx.Response(429, headers={"x-ratelimit-reset-tokens": "1m3s"}, request=REQ), body=None), "rate_limit", True, 63.0),
    (openai.InternalServerError("s", response=httpx.Response(503, request=REQ), body=None), "server", True, None),
    (openai.APITimeoutError(request=REQ), "timeout", True, None),
    (openai.APIConnectionError(request=REQ), "connection", True, None),
    (openai.AuthenticationError("a", response=httpx.Response(401, request=REQ), body=None), "auth", False, None),
    (openai.BadRequestError("b", response=httpx.Response(400, request=REQ), body={"error": {"code": "invalid"}}), "bad_request", False, None),
])
def test_groq_error_classification(exc, kind, retryable, retry_after):
    a, _ = groq([exc])
    with pytest.raises(ProviderError) as e:
        a.start("sys", "q", TOOLS)
    assert (e.value.kind, e.value.retryable, e.value.retry_after) == (kind, retryable, retry_after)


@pytest.mark.parametrize("message,expected", [
    ("Rate limit reached. Please try again in 315ms.", 0.315),
    ("Rate limit reached. Please try again in 4.5375s.", 4.5375),
])
def test_groq_rate_limit_parses_retry_delay_from_message(message, expected):
    exc = openai.RateLimitError(
        message,
        response=httpx.Response(429, request=REQ),
        body={"error": {"message": message}},
    )
    a, _ = groq([exc])
    with pytest.raises(ProviderError) as e:
        a.start("sys", "q", TOOLS)
    assert e.value.kind == "rate_limit"
    assert e.value.retryable is True
    assert e.value.retry_after == pytest.approx(expected)


def test_groq_tool_use_failed_is_model_output_error():
    exc = openai.BadRequestError("b", response=httpx.Response(400, request=REQ), body={"error": {"code": "tool_use_failed"}})
    a, _ = groq([exc])
    with pytest.raises(ModelOutputError):
        a.start("sys", "q", TOOLS)


def test_groq_real_client_timeout_and_no_sdk_retries(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "dummy-not-used")  # constructing the client makes no request
    a = build_adapter("primary_a")
    assert a.client.max_retries == 0 and a.client.timeout == 60
    assert a.parallel_tool_calls is False


def test_fallback_keeps_parallel_default_and_is_separate():
    cfg = load_model_config()
    assert "parallel_tool_calls" not in cfg["fallback_b"]  # plan: the fallback model may emit parallel calls
    assert cfg["primary_a"]["parallel_tool_calls"] is False


def test_adapters_need_keys_only_for_real_clients(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        build_adapter("primary_a")
    with pytest.raises(RuntimeError):
        build_adapter("primary_b")
