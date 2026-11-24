"""Offline tests for the EXPERIMENTAL NVIDIA Nemotron model (experimental_nemotron): no network, no real key.

The SDK's HTTP module is resolved from openai.DefaultHttpxClient (no extra dependency), as in the OpenRouter tests.
"""
import hashlib
import importlib
import json
from types import SimpleNamespace

import openai
import pytest
from openai._models import construct_type
from openai.types.chat import ChatCompletion

from agents.base import ProviderError
from agents.nvidia_adapter import NvidiaAdapter
from agents.openrouter_adapter import OpenRouterAdapter
from agents.registry import build_adapter, load_model_config
from environment import RailwayEnv
from evaluation import openrouter_smoke as smoke
from evaluation import run_pilot
from evaluation.final_answer import CLOSE, OPEN
from evaluation.quota import QuotaTracker
from evaluation.runner import RunnerConfig, run_item
from evaluation.scorer import NOT_SCORED_STATUSES, score
from evaluation.selfcheck import gold_for

SDK_HTTP = importlib.import_module(openai.DefaultHttpxClient.__mro__[1].__module__.split(".")[0])
KEY = "experimental_nemotron"
MODEL = "nvidia/nemotron-3-super-120b-a12b"
ENV = "NVIDIA_API_KEY"
DUMMY = "nvapi-DUMMY-offline-test-0123456789"   # not a real key
URL = "https://integrate.api.nvidia.com/v1"
REQ = SDK_HTTP.Request("POST", URL + "/chat/completions")
TOOLS = [{"name": "get_fare", "description": "fare", "parameters": {"type": "object", "properties": {
    "train_id": {"type": "string"}, "travel_class": {"type": "string"}}, "required": ["train_id", "travel_class"]}}]
FARE = ("call_1", "get_fare", '{"train_id": "BTB103", "travel_class": "2A"}')
GOOD_JSON = json.dumps({"status": "success", "selected_train": "BTB103", "selected_class": "2A", "booking_ids": [],
                        "requested_passengers": [], "notes": "fare lookup"})
FINAL = f"The 2A fare on BTB103 is 3565.\n{OPEN}\n{GOOD_JSON}\n{CLOSE}"
ITEM = {"task_id": "T01_en", "semantic_task_id": "T01", "language": "en", "query": "What is the fare for 2A class on train BTB103?",
        "allowed_tools": ["resolve_station", "search_trains", "get_train_details", "check_availability", "get_fare", "book_ticket"]}


@pytest.fixture(autouse=True)
def project_data_untouched():
    """Run files, quota files, benchmark data and config must stay byte-identical across every test."""
    def snap():
        out = {}
        for d in (smoke.RUNS_DIR, smoke.ROOT / "benchmark", smoke.ROOT / "config"):
            for f in sorted(d.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts:
                    out[str(f.relative_to(smoke.ROOT))] = hashlib.sha256(f.read_bytes()).hexdigest()
        return out
    before = snap()
    yield
    assert snap() == before


def body(text=None, tool_calls=(), usage=(50, 10, 60), finish=None, **extra):
    msg = {"role": "assistant", "content": text}
    if tool_calls:
        msg["tool_calls"] = [{"id": i, "type": "function", "function": {"name": n, "arguments": a}} for i, n, a in tool_calls]
    if "reasoning_content" in extra:
        msg["reasoning_content"] = extra.pop("reasoning_content")
    b = {"id": "chatcmpl-1", "object": "chat.completion", "created": 1, "model": MODEL,
         "choices": [{"index": 0, "message": msg, "finish_reason": finish or ("tool_calls" if tool_calls else "stop")}]}
    if usage is not None:
        b["usage"] = dict(zip(("prompt_tokens", "completion_tokens", "total_tokens"), usage)) if isinstance(usage, tuple) else usage
    b.update(extra)
    return b


class Fake:
    def __init__(self, responses):
        self.responses, self.kwargs = list(responses), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.kwargs.append(json.loads(json.dumps(kw)))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return construct_type(type_=ChatCompletion, value=r) if isinstance(r, dict) else r


def adapter(responses):
    fake = Fake(responses)
    return build_adapter(KEY, client=fake), fake


def resp(status, headers=None):
    return SDK_HTTP.Response(status, headers=headers or {}, request=REQ)


def cfg(**kw):
    waits = []
    c = RunnerConfig(sleep=waits.append, **kw)
    c.waits = waits
    return c


# ----------------------------------------------------------------------------- configuration / registry
def test_config_entry_and_existing_models_unchanged():
    c = load_model_config()
    assert c[KEY] == {"provider": "nvidia", "model": MODEL, "temperature": 0, "max_tokens": 1024, "timeout_seconds": 120,
                      "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}}
    assert c["primary_a"] == {"provider": "groq", "model": "openai/gpt-oss-120b", "reasoning": "low", "temperature": 0,
                              "max_tokens": 1024, "parallel_tool_calls": False, "timeout_seconds": 60}
    assert c["primary_b"] == {"provider": "google", "model": "gemini-3.8-flash", "reasoning": "minimal", "temperature": 0,
                              "max_tokens": 1024, "timeout_seconds": 90}
    assert c["fallback_b"] == {"provider": "groq", "model": "qwen/qwen3.8-27b", "reasoning": "low", "temperature": 0,
                               "max_tokens": 1024, "timeout_seconds": 60}
    assert c["experimental_inkling"]["provider"] == "openrouter" and "extra_body" not in c["experimental_inkling"]


def test_model_id_only_in_config():
    import agents.nvidia_adapter as mod
    import agents.registry as reg
    for src in (mod.__file__, reg.__file__):
        assert "nemotron-3" not in open(src, encoding="utf-8").read()


def test_registry_builds_nvidia_adapter():
    a = build_adapter(KEY, client=Fake([]))
    assert isinstance(a, NvidiaAdapter) and isinstance(a, OpenRouterAdapter)
    assert (a.model_key, a.provider, a.model, a.timeout_seconds) == (KEY, "nvidia", MODEL, 120)
    s = a.settings()
    assert s["base_url"] == URL and s["sdk_max_retries"] == 0 and s["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}


def test_inkling_adapter_unchanged_by_refactor():
    a = build_adapter("experimental_inkling", client=Fake([]))
    assert type(a) is OpenRouterAdapter and a.provider == "openrouter" and a.extra_body is None
    assert a.settings()["base_url"] == "https://openrouter.ai/api/v1" and "extra_body" not in a.settings()


def test_missing_key_raises_and_other_keys_not_used(monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", DUMMY)
    monkeypatch.setenv("OPENAI_API_KEY", DUMMY)
    with pytest.raises(RuntimeError, match=ENV):
        build_adapter(KEY)


def test_real_client_endpoint_timeout_no_retries(monkeypatch):
    monkeypatch.setenv(ENV, DUMMY)  # constructing the client sends nothing
    a = build_adapter(KEY)
    assert str(a.client.base_url).rstrip("/") == URL and a.client.max_retries == 0 and a.client.timeout == 120
    assert DUMMY not in json.dumps(a.settings())


def test_openrouter_reasoning_field_rejected():
    with pytest.raises(ValueError):
        NvidiaAdapter(model_key=KEY, model=MODEL, reasoning="low", client=Fake([]))


# ----------------------------------------------------------------------------- request formatting
def test_request_format():
    a, fake = adapter([body("hi")])
    a.start("SYS", "USER", TOOLS)
    kw = fake.kwargs[0]
    assert kw["model"] == MODEL and kw["temperature"] == 0 and kw["max_tokens"] == 1024 and kw["tool_choice"] == "auto"
    assert kw["messages"] == [{"role": "system", "content": "SYS"}, {"role": "user", "content": "USER"}]
    assert kw["tools"] == [{"type": "function", "function": TOOLS[0]}]
    assert kw["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    for absent in ("max_completion_tokens", "reasoning_effort", "parallel_tool_calls", "reasoning"):
        assert absent not in kw and absent not in kw["extra_body"]


def test_extra_body_not_shared_between_requests_or_adapters():
    a, fake = adapter([body("a"), body("b")])
    a.start("s", "q", TOOLS)
    fake.kwargs[0]["extra_body"]["chat_template_kwargs"]["enable_thinking"] = True  # mutate the snapshot only
    a.continue_turn([])
    assert fake.kwargs[1]["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert load_model_config()[KEY]["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False


# ----------------------------------------------------------------------------- tool-call parsing
def test_tool_call_round_trip_role_tool():
    a, fake = adapter([body(tool_calls=[FARE]), body("The fare is 3565.")])
    t1 = a.start("s", "q", TOOLS)
    assert [(c.id, c.name, c.arguments, c.parse_ok) for c in t1.tool_calls] == \
        [("call_1", "get_fare", {"train_id": "BTB103", "travel_class": "2A"}, True)]
    res = {"ok": True, "data": {"fare_inr": 3565}, "error": None}
    t2 = a.continue_turn([(t1.tool_calls[0], res)])
    msgs = fake.kwargs[1]["messages"]
    assert msgs[2]["tool_calls"][0]["id"] == "call_1"
    assert msgs[3] == {"role": "tool", "tool_call_id": "call_1", "content": json.dumps(res, ensure_ascii=False)}  # role tool, not function
    assert fake.kwargs[1]["tools"] == fake.kwargs[0]["tools"] and t2.text == "The fare is 3565."


@pytest.mark.parametrize("raw", ['{"train_id": "BTB103",', "[1]", "nope"])
def test_malformed_arguments_flagged_not_raised(raw):
    a, _ = adapter([body(tool_calls=[("t", "get_fare", raw)])])
    c = a.start("s", "q", TOOLS).tool_calls[0]
    assert c.parse_ok is False and c.arguments == {} and c.raw_arguments == raw


def test_tool_call_written_into_content_is_not_executed():
    """NVIDIA docs: if the server fails to parse a tool call it stays in `content`; we never guess-parse it."""
    a, _ = adapter([body('<tool_call>{"name": "get_fare", "arguments": {}}</tool_call>')])
    t = a.start("s", "q", TOOLS)
    assert t.tool_calls == [] and "tool_call" in t.text


def test_reasoning_content_is_not_answer_text():
    a, _ = adapter([body("answer", reasoning_content="hidden thoughts")])
    t = a.start("s", "q", TOOLS)
    assert t.text == "answer" and t.response["choices"][0]["message"]["reasoning_content"] == "hidden thoughts"


# ----------------------------------------------------------------------------- usage
def test_usage_normalised_and_missing_usage_safe():
    a, _ = adapter([body("x", usage={"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13,
                                     "completion_tokens_details": {"reasoning_tokens": 0}}), body("y", usage=None),
                    body("z", usage={"prompt_tokens": 5})])
    assert a.start("s", "q", TOOLS).usage == {"input_tokens": 9, "output_tokens": 4, "total_tokens": 13, "reasoning_tokens": 0}
    assert a.continue_turn([]).usage == {}
    assert a.continue_turn([]).usage == {"input_tokens": 5, "output_tokens": 0, "total_tokens": 5}


# ----------------------------------------------------------------------------- errors
@pytest.mark.parametrize("exc,kind,retryable,retry_after", [
    (openai.AuthenticationError("a", response=resp(401), body=None), "auth", False, None),
    (openai.APIStatusError("p", response=resp(402), body=None), "insufficient_credits", False, None),
    (openai.PermissionDeniedError("f", response=resp(403), body=None), "forbidden", False, None),
    (openai.NotFoundError("n", response=resp(404), body=None), "not_found", False, None),
    (openai.BadRequestError("b", response=resp(400), body=None), "bad_request", False, None),
    (openai.UnprocessableEntityError("u", response=resp(422), body=None), "http_error", False, None),
    (openai.APIStatusError("t", response=resp(408), body=None), "timeout", True, None),
    (openai.RateLimitError("r", response=resp(429, {"retry-after": "30"}), body=None), "rate_limit", True, 30.0),
    (openai.InternalServerError("s", response=resp(500), body=None), "server", True, None),
    (openai.APIStatusError("s", response=resp(502), body=None), "server", True, None),
    (openai.InternalServerError("s", response=resp(503), body=None), "server", True, None),
    (openai.APITimeoutError(request=REQ), "timeout", True, None),
    (openai.APIConnectionError(request=REQ), "connection", True, None),
])
def test_error_classification(exc, kind, retryable, retry_after):
    a, _ = adapter([exc])
    with pytest.raises(ProviderError) as e:
        a.start("s", "q", TOOLS)
    assert (e.value.kind, e.value.retryable, e.value.retry_after) == (kind, retryable, retry_after)


def test_error_body_with_200_labelled_nvidia():
    a, _ = adapter([{"error": {"code": 500, "message": "boom"}}])
    with pytest.raises(ProviderError) as e:
        a.start("s", "q", TOOLS)
    assert e.value.kind == "server" and str(e.value).startswith("NVIDIA response error 500")


def test_runner_does_not_retry_non_retryable_and_does_not_score():
    made = []

    def make():
        made.append(1)
        return build_adapter(KEY, client=Fake([openai.AuthenticationError("a", response=resp(401), body=None)]))
    c = cfg(max_attempts=5)
    row = run_item(ITEM, make, RailwayEnv(), c)
    assert row["status"] == "provider_error" and row["status"] in NOT_SCORED_STATUSES and len(made) == 1 and c.waits == []


# ----------------------------------------------------------------------------- secret redaction
def test_nvidia_key_redacted_in_errors_and_rows(monkeypatch):
    monkeypatch.setenv(ENV, DUMMY)
    exc = openai.AuthenticationError(f"bad key {DUMMY}", response=resp(401), body=None)
    a, _ = adapter([exc])
    with pytest.raises(ProviderError) as e:
        a.start("s", "q", TOOLS)
    assert DUMMY not in str(e.value) and "[REDACTED]" in str(e.value)
    row = run_item(ITEM, lambda: build_adapter(KEY, client=Fake([exc])), RailwayEnv(), cfg())
    assert DUMMY not in json.dumps(row, ensure_ascii=False)


# ----------------------------------------------------------------------------- runner + CLI (offline)
def test_runner_end_to_end_scores_t01():
    fake = Fake([body(tool_calls=[FARE], usage=(100, 20, 120)), body(FINAL, usage=(150, 30, 180))])
    q = QuotaTracker(None)
    row = run_item(ITEM, lambda: build_adapter(KEY, client=fake), RailwayEnv(), cfg(), quota=q, run_name="experimental_nemotron_pilot")
    assert row["status"] == "completed" and (row["model_key"], row["provider"], row["model"]) == (KEY, "nvidia", MODEL)
    assert row["usage"] == {"input_tokens": 250, "output_tokens": 50, "total_tokens": 300}
    assert q.state["by_provider"]["nvidia"]["requests"] == 2
    assert score(row, gold_for("T01"), row["state_snapshot"])["task_success"] is True


def test_cli_separate_files_and_resume(tmp_path, monkeypatch):
    run_file = tmp_path / "experimental_nemotron_pilot.jsonl"
    seq = [[openai.InternalServerError("s", response=resp(503), body=None)]] + [[body("no")]] * 5

    def build(model_key):
        return build_adapter(model_key, client=Fake(seq.pop(0)))
    monkeypatch.setattr(run_pilot, "build_adapter", build)
    run_pilot.main(["--model", KEY, "--languages", "en", "--run-file", str(run_file), "--max-attempts", "1"])
    run_pilot.main(["--model", KEY, "--languages", "en", "--run-file", str(run_file), "--max-attempts", "1", "--resume"])
    rows = [json.loads(l) for l in run_file.read_text(encoding="utf-8").splitlines()]
    assert [r["status"] for r in rows] == ["provider_error"] + ["completed"] * 5 and {r["model_key"] for r in rows} == {KEY}
    assert {r["provider"] for r in rows} == {"nvidia"} and (tmp_path / "experimental_nemotron_pilot.quota.json").exists()


# ----------------------------------------------------------------------------- one-request smoke test
class Server:
    def __init__(self, *responses):
        self.responses, self.requests = list(responses), []
        self.transport = SDK_HTTP.MockTransport(self._handle)

    def _handle(self, request):
        self.requests.append({"url": str(request.url), "headers": dict(request.headers), "body": json.loads(request.content or b"{}")})
        return self.responses.pop(0) if self.responses else SDK_HTTP.Response(500, json={"error": {"message": "extra"}})


def live(tmp_path, server, monkeypatch, secret=DUMMY):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    if secret:
        monkeypatch.setenv(ENV, secret)
    else:
        monkeypatch.delenv(ENV, raising=False)
    printed, out = [], tmp_path / "smoke.json"
    v, report = smoke.run_smoke(live=True, out_path=out, transport=server.transport, printer=printed.append, model_key=KEY)
    return v, report, printed, out


def test_smoke_tool_call_one_request_to_nvidia(tmp_path, monkeypatch):
    server = Server(SDK_HTTP.Response(200, json=body(tool_calls=[FARE])))
    v, report, printed, out = live(tmp_path, server, monkeypatch)
    assert v == "OK_TOOL_CALL" and len(server.requests) == 1 and report["http_requests_sent"] == 1
    r = server.requests[0]
    assert r["url"] == URL + "/chat/completions" and r["headers"]["authorization"] == f"Bearer {DUMMY}"
    b = r["body"]
    assert b["model"] == MODEL and b["chat_template_kwargs"] == {"enable_thinking": False} and len(b["messages"]) == 2
    assert "extra_body" not in b and "reasoning_effort" not in b and "max_completion_tokens" not in b
    saved = out.read_text(encoding="utf-8")
    assert DUMMY not in saved and all(DUMMY not in l for l in printed) and json.loads(saved)["api_key_env"] == ENV


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 503])
def test_smoke_errors_single_request_no_retry(tmp_path, monkeypatch, status):
    server = Server(SDK_HTTP.Response(status, json={"status": status, "title": "err", "detail": f"x {DUMMY}"}), SDK_HTTP.Response(200, json=body("x")))
    v, report, printed, out = live(tmp_path, server, monkeypatch)
    assert v == "REJECTED" and len(server.requests) == 1 and report["retried"] is False and report["status_code"] == status
    assert DUMMY not in out.read_text(encoding="utf-8") and all(DUMMY not in l for l in printed)


def test_smoke_redirect_blocked(tmp_path, monkeypatch):
    server = Server(SDK_HTTP.Response(307, headers={"location": URL + "/elsewhere"}), SDK_HTTP.Response(200, json=body("x")))
    v, report, _, _ = live(tmp_path, server, monkeypatch)
    assert v == "REJECTED" and report["error_kind"] == "request_limit" and len(server.requests) == 1


def test_smoke_missing_nvidia_key_sends_nothing_even_with_openrouter_key(tmp_path, monkeypatch):
    server = Server(SDK_HTTP.Response(200, json=body("x")))
    monkeypatch.setenv("OPENROUTER_API_KEY", DUMMY)
    monkeypatch.delenv(ENV, raising=False)
    v, report = smoke.run_smoke(live=True, out_path=tmp_path / "s.json", transport=server.transport, printer=lambda s: None,
                                model_key=KEY)
    assert v == "NOT_SENT" and server.requests == [] and ENV in report["error"]


def test_smoke_existing_report_not_overwritten(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV, DUMMY)
    out = tmp_path / "keep.json"
    out.write_text("KEEP", encoding="utf-8")
    server = Server(SDK_HTTP.Response(200, json=body("x")))
    v, report = smoke.run_smoke(live=True, out_path=out, transport=server.transport, printer=lambda s: None, model_key=KEY)
    assert v == "NOT_SENT" and server.requests == [] and out.read_text(encoding="utf-8") == "KEEP" and "report_file" not in report


def test_smoke_dry_run_and_cli(monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    v, report = smoke.run_smoke(live=False, printer=lambda s: None, model_key=KEY)
    assert v == "DRY_RUN" and report["http_requests_sent"] == 0 and report["base_url"] == URL
    assert report["request"]["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert smoke.main(["--model", KEY]) == 0
    with pytest.raises(SystemExit):
        smoke.main(["--model", "primary_a"])
    with pytest.raises(ValueError):
        smoke.run_smoke(live=False, printer=lambda s: None, model_key="primary_a")


# ----------------------------------------------------------------------------- run_smoke variable scoping (regression)
def test_run_smoke_does_not_shadow_module_constants():
    """MODEL_KEY / API_KEY_ENV must never be local names in run_smoke (a local rebinding makes any earlier read raise
    UnboundLocalError); the selected model lives only in the `model_key` parameter."""
    import symtable
    src = open(smoke.__file__, encoding="utf-8").read()
    fn = next(c for c in symtable.symtable(src, smoke.__file__, "exec").get_children() if c.get_name() == "run_smoke")
    local_names = {s.get_name() for s in fn.get_symbols() if s.is_local()}
    assert not {"MODEL_KEY", "API_KEY_ENV"} & local_names
    assert smoke.MODEL_KEY == "experimental_inkling"  # module default unchanged


@pytest.mark.parametrize("argv,model_key,model,base_url,key_env", [
    ([], "experimental_inkling", "thinkingmachines/inkling:free", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    (["--model", "experimental_inkling"], "experimental_inkling", "thinkingmachines/inkling:free", "https://openrouter.ai/api/v1",
     "OPENROUTER_API_KEY"),
    (["--model", KEY], KEY, MODEL, URL, ENV),
])
def test_cli_model_selection(monkeypatch, argv, model_key, model, base_url, key_env):
    seen = {}
    real = smoke.run_smoke

    def spy(**kw):
        v, report = real(**kw, printer=lambda s: None) if "printer" not in kw else real(**kw)
        seen.update(report)
        return v, report
    monkeypatch.setattr(smoke, "run_smoke", spy)
    assert smoke.main(argv) == 0   # dry run (no --live): nothing is sent
    assert (seen["model_key"], seen["model"], seen["base_url"], seen["api_key_env"]) == (model_key, model, base_url, key_env)
    assert seen["request"]["model"] == model and seen["http_requests_sent"] == 0


def test_default_live_selects_inkling_key_env_not_nvidia(tmp_path, monkeypatch):
    """With no model_key, a live run looks only for OPENROUTER_API_KEY (an NVIDIA key alone sends nothing)."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv(ENV, DUMMY)
    server = Server(SDK_HTTP.Response(200, json=body("x")))
    v, report = smoke.run_smoke(live=True, out_path=tmp_path / "d.json", transport=server.transport, printer=lambda s: None)
    assert v == "NOT_SENT" and server.requests == [] and "OPENROUTER_API_KEY" in report["error"]
    assert report["model_key"] == "experimental_inkling"
