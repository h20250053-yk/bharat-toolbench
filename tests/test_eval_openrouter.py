"""Offline tests for the EXPERIMENTAL OpenRouter adapter (experimental_inkling).

Real openai SDK types and error classes, fake transports only: no network, no API calls, no real keys.
"""
import json
from types import SimpleNamespace

import pytest
from openai._models import construct_type
from openai.types.chat import ChatCompletion

from agents.base import ModelTurn, ProviderError, ToolCall
from agents.openrouter_adapter import API_KEY_ENV, OpenRouterAdapter
from agents.registry import build_adapter, load_model_config
from environment import RailwayEnv
from evaluation import run_pilot
from evaluation.final_answer import CLOSE, OPEN
from evaluation.quota import QuotaExceeded, QuotaTracker
from evaluation.runner import RunnerConfig, run_item
from evaluation.scorer import NOT_SCORED_STATUSES, score
from evaluation.selfcheck import gold_for

import importlib

import openai

# The HTTP library is whatever the pinned OpenAI SDK itself is built on (openai==3.24.0 declares
# `Requires-Dist: httpx2<3,>=2.12.0`, installed automatically by `pip install -r requirements.txt`).
# It is resolved FROM the SDK's public `openai.DefaultHttpxClient` instead of being imported by name, so these tests
# add no dependency of their own and always mock exactly the client/transport/response types the SDK uses.
SDK_HTTP = importlib.import_module(openai.DefaultHttpxClient.__mro__[1].__module__.split(".")[0])
assert issubclass(openai.DefaultHttpxClient, SDK_HTTP.Client)

KEY = "experimental_inkling"
DUMMY = "sk-or-DUMMY-offline-test-value"   # never a real key; used only to construct a client that is never called
TOOLS = [{"name": "get_fare", "description": "fare", "parameters": {"type": "object", "properties": {
    "train_id": {"type": "string"}, "travel_class": {"type": "string"}}, "required": ["train_id", "travel_class"]}}]
REQ = SDK_HTTP.Request("POST", "https://openrouter.ai/api/v1/chat/completions")


# ----------------------------------------------------------------------------- helpers
def body(text=None, tool_calls=(), usage=(50, 10, 60), finish=None, **extra):
    """An OpenRouter-shaped chat.completion body (dict)."""
    msg = {"role": "assistant", "content": text}
    if tool_calls:
        msg["tool_calls"] = [{"id": i, "type": "function", "function": {"name": n, "arguments": a}} for i, n, a in tool_calls]
    for k in ("reasoning", "reasoning_details"):
        if k in extra:
            msg[k] = extra.pop(k)
    b = {"id": "gen-1", "object": "chat.completion", "created": 1, "model": "thinkingmachines/inkling:free",
         "provider": "ThinkingMachines",
         "choices": [{"index": 0, "message": msg, "finish_reason": finish or ("tool_calls" if tool_calls else "stop")}]}
    if usage is not None:
        b["usage"] = dict(zip(("prompt_tokens", "completion_tokens", "total_tokens"), usage)) if isinstance(usage, tuple) else usage
    b.update(extra)
    return b


def parsed(b):
    """Build the response object exactly as the SDK does for a 2xx body (construct, no validation)."""
    return construct_type(type_=ChatCompletion, value=b)


class FakeClient:
    def __init__(self, responses):
        self.responses, self.kwargs = list(responses), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.kwargs.append(json.loads(json.dumps(kw)))  # snapshot what was sent at call time
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return parsed(r) if isinstance(r, dict) else r


def adapter(responses, **kw):
    fake = FakeClient(responses)
    cfg = load_model_config()[KEY]
    params = dict(model_key=KEY, model=cfg["model"], temperature=cfg["temperature"], max_tokens=cfg["max_tokens"],
                  timeout_seconds=cfg["timeout_seconds"], client=fake)
    params.update(kw)
    return OpenRouterAdapter(**params), fake


# ----------------------------------------------------------------------------- configuration / registry
EXPECTED_EXISTING = {
    "primary_a": {"provider": "groq", "model": "openai/gpt-oss-120b", "reasoning": "low", "temperature": 0, "max_tokens": 1024,
                  "parallel_tool_calls": False, "timeout_seconds": 60},
    "primary_b": {"provider": "google", "model": "gemini-3.8-flash", "reasoning": "minimal", "temperature": 0, "max_tokens": 1024,
                  "timeout_seconds": 90},
    "fallback_b": {"provider": "groq", "model": "qwen/qwen3.8-27b", "reasoning": "low", "temperature": 0, "max_tokens": 1024,
                   "timeout_seconds": 60},
}


def test_existing_model_configs_are_unchanged():
    cfg = load_model_config()
    for k, v in EXPECTED_EXISTING.items():
        assert cfg[k] == v


def test_experimental_config_entry():
    m = load_model_config()[KEY]
    assert m["provider"] == "openrouter" and m["model"] == "thinkingmachines/inkling:free"
    assert "reasoning" not in m and "parallel_tool_calls" not in m  # unverified for this endpoint -> not sent
    assert m["temperature"] == 0 and m["max_tokens"] == 1024


def test_model_id_lives_only_in_config():
    import agents.openrouter_adapter as mod
    import agents.registry as reg
    for src in (mod.__file__, reg.__file__):
        assert "thinkingmachines/" not in open(src, encoding="utf-8").read()  # the model ID itself is config-only


def test_registry_builds_openrouter_with_injected_client():
    fake = FakeClient([])
    a = build_adapter(KEY, client=fake)
    assert isinstance(a, OpenRouterAdapter) and a.client is fake
    assert (a.model_key, a.provider, a.model) == (KEY, "openrouter", "thinkingmachines/inkling:free")
    assert a.timeout_seconds == 90 and a.reasoning is None and a.parallel_tool_calls is None


def test_registry_existing_models_still_use_their_adapters():
    from agents.gemini_adapter import GeminiAdapter
    from agents.groq_adapter import GroqAdapter
    assert isinstance(build_adapter("primary_a", client=object()), GroqAdapter)
    assert isinstance(build_adapter("fallback_b", client=object()), GroqAdapter)
    assert isinstance(build_adapter("primary_b", client=object()), GeminiAdapter)


def test_unknown_provider_still_rejected(tmp_path):
    p = tmp_path / "m.yaml"
    p.write_text("models:\n  x: {provider: nope, model: m}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        build_adapter("x", path=p)


# ----------------------------------------------------------------------------- initialisation / key handling
def test_missing_key_raises_without_network(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    with pytest.raises(RuntimeError, match=API_KEY_ENV):
        build_adapter(KEY)


def test_empty_key_counts_as_missing(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, "")
    with pytest.raises(RuntimeError):
        build_adapter(KEY)


def test_other_provider_keys_are_not_used(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    monkeypatch.setenv("GROQ_API_KEY", DUMMY)
    monkeypatch.setenv("OPENAI_API_KEY", DUMMY)
    with pytest.raises(RuntimeError):
        build_adapter(KEY)


def test_real_client_base_url_timeout_no_sdk_retries_and_key_not_exposed(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, DUMMY)  # constructing the client performs no request
    a = build_adapter(KEY)
    assert str(a.client.base_url).rstrip("/") == "https://openrouter.ai/api/v1"
    assert a.client.max_retries == 0 and a.client.timeout == 90
    s = a.settings()
    assert s["base_url"] == "https://openrouter.ai/api/v1" and s["sdk_max_retries"] == 0 and s["experimental"] is True
    assert DUMMY not in json.dumps(s) and DUMMY not in repr(vars(a).get("messages"))


# ----------------------------------------------------------------------------- request shape
def test_tool_schema_conversion():
    assert OpenRouterAdapter._convert_tools(TOOLS) == [{"type": "function", "function": TOOLS[0]}]


def test_initial_request_shape_and_omitted_params():
    a, fake = adapter([body("hi")])
    t = a.start("SYS", "USER", TOOLS)
    kw = fake.kwargs[0]
    assert kw["model"] == "thinkingmachines/inkling:free"
    assert kw["messages"] == [{"role": "system", "content": "SYS"}, {"role": "user", "content": "USER"}]
    assert kw["tools"] == [{"type": "function", "function": TOOLS[0]}] and kw["tool_choice"] == "auto"
    assert kw["temperature"] == 0 and kw["max_tokens"] == 1024
    for absent in ("max_completion_tokens", "reasoning_effort", "parallel_tool_calls", "extra_body"):
        assert absent not in kw
    assert t.request == kw and t.text == "hi" and t.finish_reason == "stop"


def test_optional_params_sent_only_when_configured():
    a, fake = adapter([body("hi")], reasoning="low", parallel_tool_calls=False)
    a.start("s", "u", TOOLS)
    kw = fake.kwargs[0]
    assert kw["extra_body"] == {"reasoning": {"effort": "low"}} and kw["parallel_tool_calls"] is False
    assert "reasoning_effort" not in kw


# ----------------------------------------------------------------------------- multi-turn tool use
def test_multi_turn_round_trip_tools_resent_and_ids_preserved():
    a, fake = adapter([body(tool_calls=[("call_1", "get_fare", '{"train_id": "BTB103", "travel_class": "2A"}')]),
                       body("The fare is 3565.")])
    t1 = a.start("sys", "q", TOOLS)
    assert [(c.id, c.name, c.arguments, c.parse_ok) for c in t1.tool_calls] == \
        [("call_1", "get_fare", {"train_id": "BTB103", "travel_class": "2A"}, True)]
    assert t1.finish_reason == "tool_calls"
    res = {"ok": True, "data": {"fare_inr": 3565}, "error": None}
    t2 = a.continue_turn([(t1.tool_calls[0], res)])
    msgs = fake.kwargs[1]["messages"]
    assert msgs[2]["role"] == "assistant" and msgs[2]["tool_calls"][0]["id"] == "call_1"
    assert msgs[3] == {"role": "tool", "tool_call_id": "call_1", "content": json.dumps(res, ensure_ascii=False)}
    assert fake.kwargs[1]["tools"] == fake.kwargs[0]["tools"]  # OpenRouter: tools on every request
    assert t2.text == "The fare is 3565." and t2.tool_calls == []


def test_multiple_tool_calls_in_one_turn_all_kept_in_order():
    a, fake = adapter([body(tool_calls=[("a", "get_fare", '{"train_id": "BTB103", "travel_class": "2A"}'),
                                        ("b", "get_fare", '{"train_id": "BTB104", "travel_class": "3A"}')]), body("done")])
    t1 = a.start("s", "q", TOOLS)
    assert [c.id for c in t1.tool_calls] == ["a", "b"]
    a.continue_turn([(c, {"ok": True}) for c in t1.tool_calls])
    assert [m["tool_call_id"] for m in fake.kwargs[1]["messages"] if m["role"] == "tool"] == ["a", "b"]


def test_missing_tool_call_id_gets_stable_synthetic_id():
    a, fake = adapter([body(tool_calls=[(None, "get_fare", '{"train_id": "BTB103", "travel_class": "2A"}')]), body("x")])
    t1 = a.start("s", "q", TOOLS)
    cid = t1.tool_calls[0].id
    assert cid == "or-1-1"
    a.continue_turn([(t1.tool_calls[0], {"ok": True})])
    msgs = fake.kwargs[1]["messages"]
    assert msgs[2]["tool_calls"][0]["id"] == cid and msgs[3]["tool_call_id"] == cid


def test_reasoning_details_passed_back_but_not_answer_text():
    rd = [{"type": "reasoning.text", "text": "think", "format": "unknown", "index": 0}]
    a, fake = adapter([body(None, tool_calls=[("c", "get_fare", '{"train_id": "BTB103", "travel_class": "2A"}')],
                            reasoning="think", reasoning_details=rd), body("ok")])
    t1 = a.start("s", "q", TOOLS)
    assert t1.text == ""
    a.continue_turn([(t1.tool_calls[0], {"ok": True})])
    assert fake.kwargs[1]["messages"][2]["reasoning_details"] == rd
    assert t1.response["choices"][0]["message"]["reasoning_details"] == rd  # raw response kept for the audit log


def test_response_metadata_preserved_in_raw_response():
    a, _ = adapter([body("hi", usage={"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7, "cost": 0})])
    t = a.start("s", "q", TOOLS)
    assert t.response["provider"] == "ThinkingMachines" and t.response["id"] == "gen-1"
    assert t.response["usage"]["cost"] == 0
    json.dumps(t.request), json.dumps(t.response)  # both JSON-serialisable for the raw log


# ----------------------------------------------------------------------------- malformed arguments
@pytest.mark.parametrize("raw", ['{"train_id": "BTB103",', "[1, 2]", "not json", '"str"'])
def test_malformed_arguments_do_not_crash(raw):
    a, _ = adapter([body(tool_calls=[("t1", "get_fare", raw)])])
    c = a.start("s", "q", TOOLS).tool_calls[0]
    assert c.parse_ok is False and c.raw_arguments == raw and c.arguments == {} and c.parse_error


def test_empty_arguments_parse_as_empty_object():
    a, _ = adapter([body(tool_calls=[("t1", "get_fare", "")])])
    c = a.start("s", "q", TOOLS).tool_calls[0]
    assert c.parse_ok is True and c.arguments == {}


# ----------------------------------------------------------------------------- usage normalisation
def test_usage_with_reasoning_tokens():
    u = {"prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140, "cost": 0.0,
         "completion_tokens_details": {"reasoning_tokens": 30}, "prompt_tokens_details": {"cached_tokens": 0}}
    a, _ = adapter([body("x", usage=u)])
    assert a.start("s", "q", TOOLS).usage == {"input_tokens": 100, "output_tokens": 40, "total_tokens": 140, "reasoning_tokens": 30}


def test_missing_usage_is_empty_dict():
    a, _ = adapter([body("x", usage=None)])
    t = a.start("s", "q", TOOLS)
    assert t.usage == {}


def test_partial_usage_fills_total_and_tolerates_nulls():
    a, _ = adapter([body("x", usage={"prompt_tokens": 7, "completion_tokens": None})])
    assert a.start("s", "q", TOOLS).usage == {"input_tokens": 7, "output_tokens": 0, "total_tokens": 7}


def test_usage_values_are_integers_only():
    a, _ = adapter([body("x", usage={"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3, "cost": 0.0123})])
    assert all(isinstance(v, int) for v in a.start("s", "q", TOOLS).usage.values())


def test_missing_optional_fields_content_none_no_finish_reason():
    b = body(None)
    b["choices"][0].pop("finish_reason")
    del b["provider"], b["id"]
    a, _ = adapter([b])
    t = a.start("s", "q", TOOLS)
    assert t.text == "" and t.tool_calls == [] and t.finish_reason is None


# ----------------------------------------------------------------------------- errors raised by the SDK
def resp(status, headers=None):
    return SDK_HTTP.Response(status, headers=headers or {}, request=REQ)


@pytest.mark.parametrize("exc,kind,retryable,retry_after,status", [
    (openai.AuthenticationError("a", response=resp(401), body=None), "auth", False, None, 401),
    (openai.APIStatusError("p", response=resp(402), body={"error": {"code": 402}}), "insufficient_credits", False, None, 402),
    (openai.PermissionDeniedError("thinkingmachines/inkling:free is only available on agentic harnesses", response=resp(403),
                                  body=None), "forbidden", False, None, 403),
    (openai.NotFoundError("n", response=resp(404), body=None), "not_found", False, None, 404),
    (openai.BadRequestError("b", response=resp(400), body={"error": {"code": 400}}), "bad_request", False, None, 400),
    (openai.UnprocessableEntityError("u", response=resp(422), body=None), "http_error", False, None, 422),
    (openai.APIStatusError("t", response=resp(408), body=None), "timeout", True, None, 408),
    (openai.RateLimitError("r", response=resp(429, {"retry-after": "7"}), body=None), "rate_limit", True, 7.0, 429),
    (openai.RateLimitError("r", response=resp(429, {"x-ratelimit-reset": "1760000000000"}), body=None), "rate_limit", True, None, 429),
    (openai.RateLimitError("r", response=resp(429), body=None), "rate_limit", True, None, 429),
    (openai.InternalServerError("s", response=resp(500), body=None), "server", True, None, 500),
    (openai.APIStatusError("s", response=resp(502), body=None), "server", True, None, 502),
    (openai.InternalServerError("s", response=resp(503, {"retry-after": "20"}), body=None), "server", True, 20.0, 503),
    (openai.APITimeoutError(request=REQ), "timeout", True, None, None),
    (openai.APIConnectionError(request=REQ), "connection", True, None, None),
])
def test_error_classification(exc, kind, retryable, retry_after, status):
    a, _ = adapter([exc])
    with pytest.raises(ProviderError) as e:
        a.start("s", "q", TOOLS)
    assert (e.value.kind, e.value.retryable, e.value.retry_after, e.value.status_code) == (kind, retryable, retry_after, status)


def test_unexpected_exception_is_not_disguised():
    a, _ = adapter([KeyError("bug")])
    with pytest.raises(KeyError):
        a.start("s", "q", TOOLS)


# ----------------------------------------------------------------------------- errors delivered with HTTP 200
@pytest.mark.parametrize("code,kind,retryable", [
    (502, "server", True), (None, "server", True), (429, "rate_limit", True), (408, "timeout", True),
    (403, "forbidden", False), (402, "insufficient_credits", False), (400, "http_error", False)])
def test_top_level_error_in_200_body(code, kind, retryable):
    a, _ = adapter([{"error": {"code": code, "message": "upstream failed", "metadata": {"provider_name": "X"}}}])
    with pytest.raises(ProviderError) as e:
        a.start("s", "q", TOOLS)
    assert (e.value.kind, e.value.retryable) == (kind, retryable)


def test_choice_level_error_finish_reason_is_provider_error():
    b = body("partial", finish="error")
    b["choices"][0]["error"] = {"code": 502, "message": "provider died mid-generation"}
    a, _ = adapter([b])
    with pytest.raises(ProviderError) as e:
        a.start("s", "q", TOOLS)
    assert e.value.kind == "server" and e.value.retryable is True


def test_no_choices_and_no_error_is_retryable_provider_error():
    b = body("x")
    b["choices"] = []
    a, _ = adapter([b])
    with pytest.raises(ProviderError) as e:
        a.start("s", "q", TOOLS)
    assert e.value.kind == "empty_response" and e.value.retryable is True


def test_length_with_empty_content_is_a_model_turn_not_an_error():
    a, _ = adapter([body("", finish="length")])
    t = a.start("s", "q", TOOLS)
    assert t.finish_reason == "length" and t.text == "" and t.tool_calls == []


# ----------------------------------------------------------------------------- runner integration (offline)
GOOD_JSON = json.dumps({"status": "success", "selected_train": "BTB103", "selected_class": "2A", "booking_ids": [],
                        "requested_passengers": [], "notes": "fare lookup"})
FINAL = f"The 2A fare on BTB103 is 3565.\n{OPEN}\n{GOOD_JSON}\n{CLOSE}"
ITEM = {"task_id": "T01_en", "semantic_task_id": "T01", "language": "en", "query": "What is the fare for 2A class on train BTB103?",
        "allowed_tools": ["resolve_station", "search_trains", "get_train_details", "check_availability", "get_fare", "book_ticket"]}


def cfg(**kw):
    waits = []
    c = RunnerConfig(sleep=waits.append, **kw)
    c.waits = waits
    return c


def test_runner_end_to_end_with_fake_openrouter_client(tmp_path):
    fake = FakeClient([body(tool_calls=[("c1", "get_fare", '{"train_id": "BTB103", "travel_class": "2A"}')], usage=(100, 20, 120)),
                       body(FINAL, usage=(150, 30, 180))])
    q = QuotaTracker(tmp_path / "q.json")
    row = run_item(ITEM, lambda: build_adapter(KEY, client=fake), RailwayEnv(), cfg(), quota=q, run_name="experimental_inkling_pilot")
    assert row["status"] == "completed" and row["model_key"] == KEY and row["provider"] == "openrouter"
    assert row["model"] == "thinkingmachines/inkling:free" and row["adapter_settings"]["experimental"] is True
    assert row["usage"] == {"input_tokens": 250, "output_tokens": 50, "total_tokens": 300}
    assert q.state["by_provider"]["openrouter"]["requests"] == 2 and q.state["total_tokens"] == 300
    assert [e["event"] for e in row["trajectory"]] == ["tool_call"] and row["trajectory"][0]["observation"]["ok"] is True
    types_ = [e["type"] for e in row["raw_log"]]
    assert types_.count("model_request") == 2 and types_.count("model_response") == 2 and "tool_response" in types_
    sc = score(row, gold_for("T01"), row["state_snapshot"])
    assert sc["task_success"] is True


def test_runner_retries_429_with_retry_after_then_succeeds():
    seq = [[openai.RateLimitError("r", response=resp(429, {"retry-after": "3"}), body=None)], [body(FINAL)]]
    c = cfg(max_attempts=2)
    row = run_item(ITEM, lambda: build_adapter(KEY, client=FakeClient(seq.pop(0))), RailwayEnv(), c)
    assert row["status"] == "completed" and row["attempts"] == 2 and row["retries"][0]["kind"] == "rate_limit"
    assert c.waits == [3.0]


def test_runner_403_harness_gate_is_unscored_provider_error_not_retried():
    exc = openai.PermissionDeniedError("thinkingmachines/inkling:free is only available on agentic harnesses",
                                       response=resp(403), body=None)
    made = []

    def make():
        made.append(1)
        return build_adapter(KEY, client=FakeClient([exc]))
    c = cfg(max_attempts=2)
    row = run_item(ITEM, make, RailwayEnv(), c)
    assert row["status"] == "provider_error" and row["error_kind"] == "forbidden" and len(made) == 1 and c.waits == []
    assert row["status"] in NOT_SCORED_STATUSES
    assert score(row, gold_for("T01"), row["state_snapshot"]).get("task_success") is not True


def test_runner_retry_cap_respected_for_persistent_5xx():
    seq = [[openai.InternalServerError("s", response=resp(503), body=None)] for _ in range(3)]
    c = cfg(max_attempts=2)
    row = run_item(ITEM, lambda: build_adapter(KEY, client=FakeClient(seq.pop(0))), RailwayEnv(), c)
    assert row["status"] == "provider_error" and row["attempts"] == 2 and len(c.waits) == 1


# ----------------------------------------------------------------------------- CLI, separate files, resume, quota
def scripted_build(responses_per_item):
    seq = list(responses_per_item)

    def build(model_key):
        return build_adapter(model_key, client=FakeClient(seq.pop(0)))
    return build


def test_cli_accepts_experimental_and_writes_separate_files(tmp_path, monkeypatch):
    run_file = tmp_path / "experimental_inkling_pilot.jsonl"
    monkeypatch.setattr(run_pilot, "build_adapter", scripted_build([[body("I cannot answer.")]] * 5))
    assert run_pilot.main(["--model", KEY, "--languages", "en", "--run-file", str(run_file), "--max-attempts", "2"]) == 0
    rows = [json.loads(l) for l in run_file.read_text(encoding="utf-8").splitlines()]
    assert [r["task_id"] for r in rows] == ["T01_en", "T02_en", "T03_en", "T04_en", "T05_en"]
    assert {r["model_key"] for r in rows} == {KEY} and {r["provider"] for r in rows} == {"openrouter"}
    assert {r["run_id"].split(":")[0] for r in rows} == {"experimental_inkling_pilot"}
    assert (tmp_path / "experimental_inkling_pilot.quota.json").exists()
    assert json.loads((tmp_path / "experimental_inkling_pilot.quota.json").read_text())["by_provider"]["openrouter"]["requests"] == 5


def test_cli_rejects_unknown_model():
    with pytest.raises(SystemExit):
        run_pilot.main(["--model", "inkling", "--languages", "en"])


def test_cli_existing_choices_still_accepted(tmp_path, monkeypatch):
    def build(model_key):
        a = SimpleNamespace(model_key=model_key, provider="fake", model="m", settings=lambda: {},
                            start=lambda *a: ModelTurn(text="x", usage={"total_tokens": 1}), continue_turn=None)
        return a
    monkeypatch.setattr(run_pilot, "build_adapter", build)
    for k in ("primary_a", "primary_b", "fallback_b"):
        rf = tmp_path / f"{k}.jsonl"
        assert run_pilot.main(["--model", k, "--languages", "en", "--run-file", str(rf)]) == 0
        assert {json.loads(l)["model_key"] for l in rf.read_text().splitlines()} == {k}


def test_resume_reruns_only_provider_errors_for_experimental(tmp_path, monkeypatch):
    run_file = tmp_path / "experimental_inkling_pilot.jsonl"
    forbidden = openai.PermissionDeniedError("gate", response=resp(403), body=None)
    monkeypatch.setattr(run_pilot, "build_adapter", scripted_build([[forbidden]] + [[body("no")]] * 4))
    run_pilot.main(["--model", KEY, "--languages", "en", "--run-file", str(run_file), "--max-attempts", "2"])
    monkeypatch.setattr(run_pilot, "build_adapter", scripted_build([[body("no")]]))
    run_pilot.main(["--model", KEY, "--languages", "en", "--run-file", str(run_file), "--resume", "--max-attempts", "2"])
    rows = [json.loads(l) for l in run_file.read_text().splitlines()]
    assert [r["status"] for r in rows] == ["provider_error"] + ["completed"] * 5
    assert rows[0]["task_id"] == rows[-1]["task_id"] == "T01_en"
    latest = run_pilot.latest_rows(run_file)
    assert latest[f"T01_en|{KEY}"]["status"] == "completed" and len(latest) == 5


def test_experimental_run_does_not_touch_other_run_or_quota_files(tmp_path, monkeypatch):
    other = tmp_path / "primary_a_pilot.jsonl"
    other_q = tmp_path / "primary_a_pilot.quota.json"
    other.write_text('{"task_id": "T01_en", "model_key": "primary_a", "status": "completed"}\n', encoding="utf-8")
    other_q.write_text('{"requests": 105}', encoding="utf-8")
    before = (other.read_bytes(), other_q.read_bytes())
    monkeypatch.setattr(run_pilot, "build_adapter", scripted_build([[body("no")]] * 5))
    run_pilot.main(["--model", KEY, "--languages", "en", "--run-file", str(tmp_path / "experimental_inkling_pilot.jsonl")])
    assert (other.read_bytes(), other_q.read_bytes()) == before


# Quota semantics (documented in evaluation/README.md; NOT changed by this integration)
def test_quota_is_checked_before_items_so_one_item_can_overshoot(tmp_path, monkeypatch):
    run_file = tmp_path / "experimental_inkling_pilot.jsonl"
    call = ("c", "get_fare", '{"train_id": "BTB103", "travel_class": "2A"}')
    three_requests = [body(tool_calls=[call]), body(tool_calls=[call]), body("done")]
    monkeypatch.setattr(run_pilot, "build_adapter", scripted_build([three_requests] * 5))
    run_pilot.main(["--model", KEY, "--languages", "en", "--run-file", str(run_file), "--max-requests", "1"])
    rows = run_file.read_text().splitlines()
    q = json.loads((tmp_path / "experimental_inkling_pilot.quota.json").read_text())
    assert len(rows) == 1 and q["requests"] == 3  # cap 1, but the single item made 3 requests


def test_quota_is_cumulative_across_invocations(tmp_path, monkeypatch):
    run_file = tmp_path / "experimental_inkling_pilot.jsonl"
    monkeypatch.setattr(run_pilot, "build_adapter", scripted_build([[body("no")]] * 10))
    run_pilot.main(["--model", KEY, "--languages", "en", "--run-file", str(run_file), "--max-requests", "2"])
    assert len(run_file.read_text().splitlines()) == 2
    # same cap on resume: the stored count (2) already meets it, so nothing more runs until the cap is raised
    run_pilot.main(["--model", KEY, "--languages", "en", "--run-file", str(run_file), "--resume", "--max-requests", "2"])
    assert len(run_file.read_text().splitlines()) == 2
    run_pilot.main(["--model", KEY, "--languages", "en", "--run-file", str(run_file), "--resume", "--max-requests", "3"])
    assert len(run_file.read_text().splitlines()) == 3


def test_failed_requests_are_not_counted_as_requests(tmp_path):
    """Only successful model responses increment `requests`/tokens; failed calls show up as retries/provider_errors."""
    q = QuotaTracker(tmp_path / "q.json", max_requests=1)
    exc = openai.RateLimitError("r", response=resp(429), body=None)
    seq = [[exc], [exc]]
    run_item(ITEM, lambda: build_adapter(KEY, client=FakeClient(seq.pop(0))), RailwayEnv(), cfg(max_attempts=2), quota=q)
    assert q.state["requests"] == 0 and q.state["retries"] == 1 and q.state["provider_errors"] == 1
    q.check()  # does NOT raise: a request cap does not bound failed calls
    q.state["requests"] = 1
    with pytest.raises(QuotaExceeded):
        q.check()


def test_missing_key_in_cli_records_runner_error_rows_not_scored(tmp_path, monkeypatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    run_file = tmp_path / "experimental_inkling_pilot.jsonl"
    run_pilot.main(["--model", KEY, "--languages", "en", "--run-file", str(run_file)])
    rows = [json.loads(l) for l in run_file.read_text().splitlines()]
    assert {r["status"] for r in rows} == {"runner_error"} and all(API_KEY_ENV in r["error"] for r in rows)
    assert all(r["status"] in NOT_SCORED_STATUSES for r in rows)
