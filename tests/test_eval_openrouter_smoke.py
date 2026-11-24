"""Offline tests for the one-request OpenRouter smoke test (evaluation/openrouter_smoke.py) and the adapter hardening.

The SDK's own HTTP stack (resolved from openai.DefaultHttpxClient) is driven by its MockTransport: no network, no real key.
"""
import json
from types import SimpleNamespace

import pytest

from agents.base import ProviderError
from agents.openrouter_adapter import API_KEY_ENV
from agents.registry import build_adapter
from environment import RailwayEnv
from evaluation import openrouter_smoke as smoke
from evaluation.runner import RunnerConfig, run_item
from evaluation.scorer import NOT_SCORED_STATUSES

import importlib

import openai

# The HTTP library is whatever the pinned OpenAI SDK itself is built on (openai==3.24.0 declares
# `Requires-Dist: httpx2<3,>=2.12.0`, installed automatically by `pip install -r requirements.txt`).
# It is resolved FROM the SDK's public `openai.DefaultHttpxClient` instead of being imported by name, so these tests
# add no dependency of their own and always mock exactly the client/transport/response types the SDK uses.
SDK_HTTP = importlib.import_module(openai.DefaultHttpxClient.__mro__[1].__module__.split(".")[0])
assert issubclass(openai.DefaultHttpxClient, SDK_HTTP.Client)

DUMMY = "sk-or-DUMMY-offline-test-0123456789"   # not a real key


@pytest.fixture(autouse=True)
def project_data_untouched():
    """Every test must leave run files, quota files, benchmark data (tasks, translations, gold) and config byte-identical."""
    import hashlib

    def snapshot():
        out = {}
        for d in (smoke.RUNS_DIR, smoke.ROOT / "benchmark", smoke.ROOT / "config"):
            for f in sorted(d.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts:
                    out[str(f.relative_to(smoke.ROOT))] = hashlib.sha256(f.read_bytes()).hexdigest()
        return out
    before = snapshot()
    yield
    assert snapshot() == before, "a test created, changed or removed a run/quota/benchmark/config file"


def completion(content=None, tool_calls=(), finish=None, usage=(900, 40, 940), **extra):
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = [{"id": i, "type": "function", "function": {"name": n, "arguments": a}} for i, n, a in tool_calls]
    b = {"id": "gen-smoke", "object": "chat.completion", "created": 1, "model": "thinkingmachines/inkling:free",
         "provider": "ThinkingMachines",
         "choices": [{"index": 0, "message": msg, "finish_reason": finish or ("tool_calls" if tool_calls else "stop")}]}
    if usage:
        b["usage"] = {"prompt_tokens": usage[0], "completion_tokens": usage[1], "total_tokens": usage[2]}
    b.update(extra)
    return b


class Server:
    """Mock OpenRouter: answers each request with the next scripted SDK HTTP Response and records what it received."""
    def __init__(self, *responses):
        self.responses, self.requests = list(responses), []
        self.transport = SDK_HTTP.MockTransport(self._handle)

    def _handle(self, request):
        self.requests.append({"url": str(request.url), "headers": dict(request.headers), "body": json.loads(request.content or b"{}")})
        r = self.responses.pop(0) if self.responses else SDK_HTTP.Response(500, json={"error": {"code": 500, "message": "extra"}})
        return r


def ok(body):
    return SDK_HTTP.Response(200, json=body)


def live(tmp_path, server, monkeypatch, secret=DUMMY):
    if secret:
        monkeypatch.setenv(API_KEY_ENV, secret)
    else:
        monkeypatch.delenv(API_KEY_ENV, raising=False)
    printed = []
    out = tmp_path / "smoke.json"
    verdict, report = smoke.run_smoke(live=True, out_path=out, transport=server.transport, printer=printed.append)
    return verdict, report, printed, out


FARE = ("call_1", "get_fare", '{"train_id": "BTB103", "travel_class": "2A"}')


# ----------------------------------------------------------------------------- one-request guarantee
def test_guard_blocks_second_request():
    g = smoke.OneShotGuard(1)
    g(object())
    with pytest.raises(smoke.RequestLimitExceeded):
        g(object())
    assert g.count == 1


def test_guard_blocks_second_request_at_the_http_layer():
    server = Server(ok(completion("a")), ok(completion("b")))
    guard = smoke.OneShotGuard(1)
    client = smoke.make_client(DUMMY, 5, guard, transport=server.transport)
    client.chat.completions.create(model="m", messages=[{"role": "user", "content": "x"}])
    with pytest.raises(smoke.RequestLimitExceeded):
        client.chat.completions.create(model="m", messages=[{"role": "user", "content": "x"}])
    assert len(server.requests) == 1 and guard.count == 1 and client.max_retries == 0


def test_success_with_tool_call_uses_exactly_one_request(tmp_path, monkeypatch):
    server = Server(ok(completion(tool_calls=[FARE])))
    verdict, report, printed, out = live(tmp_path, server, monkeypatch)
    assert verdict == "OK_TOOL_CALL" and smoke.EXIT[verdict] == 0
    assert len(server.requests) == 1 and report["http_requests_sent"] == 1
    req = server.requests[0]
    assert req["url"] == "https://openrouter.ai/api/v1/chat/completions"
    body = req["body"]
    assert body["model"] == "thinkingmachines/inkling:free" and body["max_tokens"] == 1024 and body["temperature"] == 0
    assert body["tool_choice"] == "auto" and {t["function"]["name"] for t in body["tools"]} >= {"get_fare"}
    for absent in ("reasoning_effort", "max_completion_tokens", "parallel_tool_calls", "reasoning"):
        assert absent not in body
    assert body["messages"][0]["content"] == smoke.SYSTEM_PROMPT and body["messages"][1]["role"] == "user"
    assert len(body["messages"]) == 2  # no tool result was ever sent back
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["verdict"] == "OK_TOOL_CALL" and saved["response"]["tool_calls"][0]["name"] == "get_fare"
    assert saved["response"]["upstream_provider"] == "ThinkingMachines"


@pytest.mark.parametrize("resp,verdict", [
    (ok(completion("The fare is ...")), "OK_NO_TOOL_CALL"),
    (ok(completion(tool_calls=[("c", "get_fare", '{"train_id": "BTB103",')])), "INCOMPATIBLE"),
    (ok(completion(tool_calls=[("c", "delete_everything", "{}")])), "INCOMPATIBLE"),
    (ok(completion(tool_calls=[("c", "get_fare", '{"train_id": "BTB103"}')])), "INCOMPATIBLE"),   # missing travel_class
    (ok(completion("", finish="length")), "INCOMPATIBLE"),
    (ok(completion(None, usage=None)), "INCOMPATIBLE"),
])
def test_response_classification_single_request(tmp_path, monkeypatch, resp, verdict):
    server = Server(resp)
    v, report, _, _ = live(tmp_path, server, monkeypatch)
    assert v == verdict and len(server.requests) == 1 and report["http_requests_sent"] == 1


@pytest.mark.parametrize("status,kind,retryable", [
    (401, "auth", False), (402, "insufficient_credits", False), (403, "forbidden", False), (404, "not_found", False),
    (400, "bad_request", False), (408, "timeout", True), (429, "rate_limit", True), (500, "server", True),
    (502, "server", True), (503, "server", True)])
def test_http_errors_are_rejected_without_any_retry(tmp_path, monkeypatch, status, kind, retryable):
    server = Server(SDK_HTTP.Response(status, json={"error": {"code": status, "message": f"err {status}"}},
                                    headers={"retry-after": "5"} if status == 429 else {}))
    v, report, printed, out = live(tmp_path, server, monkeypatch)
    assert v == "REJECTED" and smoke.EXIT[v] == 20
    assert len(server.requests) == 1 and report["http_requests_sent"] == 1     # retryable or not: ONE request
    assert (report["error_kind"], report["status_code"], report["retryable_in_runner"], report["retried"]) == \
        (kind, status, retryable, False)
    assert "response" not in report  # an error is never recorded as a model answer


def test_harness_gate_403_is_rejected_not_an_answer(tmp_path, monkeypatch):
    msg = "thinkingmachines/inkling:free is only available on agentic harnesses"
    server = Server(SDK_HTTP.Response(403, json={"error": {"code": 403, "message": msg}}))
    v, report, printed, _ = live(tmp_path, server, monkeypatch)
    assert v == "REJECTED" and report["error_kind"] == "forbidden" and msg in report["error"]
    assert any("verdict: REJECTED" in line for line in printed)


@pytest.mark.parametrize("resp,kind", [
    (ok({"error": {"code": 502, "message": "upstream died"}}), "server"),
    (ok({"error": {"code": 403, "message": "only available on agentic harnesses"}}), "forbidden"),
    (SDK_HTTP.Response(200, text="<html>blocked</html>", headers={"content-type": "text/html"}), "invalid_response"),
    (SDK_HTTP.Response(200, text="{not json", headers={"content-type": "application/json"}), "invalid_response"),
])
def test_bad_200_bodies_are_rejected_safely(tmp_path, monkeypatch, resp, kind):
    server = Server(resp)
    v, report, _, _ = live(tmp_path, server, monkeypatch)
    assert v == "REJECTED" and report["error_kind"] == kind and len(server.requests) == 1


def test_choice_level_error_rejected(tmp_path, monkeypatch):
    b = completion("partial", finish="error")
    b["choices"][0]["error"] = {"code": 502, "message": "died mid-generation"}
    server = Server(ok(b))
    v, report, _, _ = live(tmp_path, server, monkeypatch)
    assert v == "REJECTED" and report["error_kind"] == "server"


def test_redirect_is_not_followed_beyond_one_request(tmp_path, monkeypatch):
    server = Server(SDK_HTTP.Response(307, headers={"location": "https://openrouter.ai/api/v1/elsewhere"}), ok(completion("x")))
    v, report, _, _ = live(tmp_path, server, monkeypatch)
    assert len(server.requests) == 1 and report["http_requests_sent"] == 1      # the redirect hop was never sent
    assert v == "REJECTED" and report["error_kind"] == "request_limit" and report["retried"] is False


def test_live_client_has_sdk_retries_disabled_and_is_the_one_used(tmp_path, monkeypatch):
    """The client the live path builds has max_retries=0 and carries the guard; a retryable 503 is sent once."""
    built = []
    real = smoke.make_client

    def spy(*a, **kw):
        c = real(*a, **kw)
        built.append(c)
        return c
    monkeypatch.setattr(smoke, "make_client", spy)
    server = Server(SDK_HTTP.Response(503, json={"error": {"code": 503, "message": "busy"}}), ok(completion("x")))
    v, report, _, _ = live(tmp_path, server, monkeypatch)
    assert len(built) == 1 and built[0].max_retries == 0 and str(built[0].base_url).rstrip("/") == "https://openrouter.ai/api/v1"
    assert v == "REJECTED" and report["error_kind"] == "server" and len(server.requests) == 1


def test_missing_key_sends_nothing(tmp_path, monkeypatch):
    server = Server(ok(completion("x")))
    v, report, _, _ = live(tmp_path, server, monkeypatch, secret=None)
    assert v == "NOT_SENT" and smoke.EXIT[v] == 40 and server.requests == [] and report["http_requests_sent"] == 0


def test_existing_report_path_sends_nothing_and_is_not_overwritten(tmp_path, monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, DUMMY)
    out = tmp_path / "exists.json"
    out.write_text("KEEP", encoding="utf-8")
    server = Server(ok(completion("x")))
    runs_before = sorted(p.name for p in smoke.RUNS_DIR.iterdir())
    v, report = smoke.run_smoke(live=True, out_path=out, transport=server.transport, printer=lambda s: None)
    assert v == "NOT_SENT" and server.requests == [] and out.read_text(encoding="utf-8") == "KEEP"
    assert "report_file" not in report and sorted(p.name for p in smoke.RUNS_DIR.iterdir()) == runs_before


def test_dry_run_sends_nothing_and_needs_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    server = Server()
    printed = []
    v, report = smoke.run_smoke(live=False, transport=server.transport, printer=printed.append)
    assert v == "DRY_RUN" and server.requests == [] and report["http_requests_sent"] == 0 and "report_file" not in report
    assert report["request"]["model"] == "thinkingmachines/inkling:free" and "get_fare" in report["request"]["tools"]
    assert smoke.main([]) == 0


def test_main_refuses_existing_out(tmp_path):
    out = tmp_path / "x.json"
    out.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit):
        smoke.main(["--live", "--out", str(out)])


# ----------------------------------------------------------------------------- secrets never leak
def test_key_never_in_output_report_or_exceptions_even_if_echoed(tmp_path, monkeypatch, capsys):
    server = Server(SDK_HTTP.Response(401, json={"error": {"code": 401, "message": f"bad key {DUMMY}"}}))
    v, report, printed, out = live(tmp_path, server, monkeypatch)
    assert v == "REJECTED"
    assert server.requests[0]["headers"]["authorization"] == f"Bearer {DUMMY}"   # it is sent to the endpoint only
    assert DUMMY not in out.read_text(encoding="utf-8") and DUMMY not in json.dumps(report)
    assert all(DUMMY not in line for line in printed) and "[REDACTED]" in report["error"]
    assert DUMMY not in capsys.readouterr().out


def test_key_not_in_success_report(tmp_path, monkeypatch):
    server = Server(ok(completion(tool_calls=[FARE])))
    _, report, printed, out = live(tmp_path, server, monkeypatch)
    assert DUMMY not in out.read_text(encoding="utf-8") and all(DUMMY not in line for line in printed)


def test_smoke_never_touches_runs_dir(tmp_path, monkeypatch):
    before = sorted(p.name for p in smoke.RUNS_DIR.iterdir())
    server = Server(ok(completion("x")))
    live(tmp_path, server, monkeypatch)
    smoke.run_smoke(live=False, printer=lambda s: None)
    assert sorted(p.name for p in smoke.RUNS_DIR.iterdir()) == before


# ----------------------------------------------------------------------------- adapter hardening (runner level)
REQ = SDK_HTTP.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
ITEM = {"task_id": "T01_en", "semantic_task_id": "T01", "language": "en", "query": "What is the fare for 2A class on train BTB103?",
        "allowed_tools": ["get_fare"]}


class Fake:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls += 1
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        if isinstance(r, dict):
            from openai._models import construct_type
            from openai.types.chat import ChatCompletion
            return construct_type(type_=ChatCompletion, value=r)
        return r


def cfg(**kw):
    waits = []
    c = RunnerConfig(sleep=waits.append, **kw)
    c.waits = waits
    return c


@pytest.mark.parametrize("exc", [
    openai.AuthenticationError("a", response=SDK_HTTP.Response(401, request=REQ), body=None),
    openai.APIStatusError("p", response=SDK_HTTP.Response(402, request=REQ), body=None),
    openai.PermissionDeniedError("f", response=SDK_HTTP.Response(403, request=REQ), body=None),
    openai.NotFoundError("n", response=SDK_HTTP.Response(404, request=REQ), body=None),
    openai.BadRequestError("b", response=SDK_HTTP.Response(400, request=REQ), body=None),
])
def test_runner_never_retries_non_retryable(exc):
    fakes = []

    def make():
        f = Fake([exc, {"choices": []}])
        fakes.append(f)
        return build_adapter("experimental_inkling", client=f)
    c = cfg(max_attempts=5)
    row = run_item(ITEM, make, RailwayEnv(), c)
    assert row["status"] == "provider_error" and row["status"] in NOT_SCORED_STATUSES
    assert len(fakes) == 1 and fakes[0].calls == 1 and c.waits == [] and row["attempts"] == 1


def test_invalid_response_not_retried():
    def make():
        return build_adapter("experimental_inkling", client=Fake(["<html>gate</html>"]))
    c = cfg(max_attempts=5)
    row = run_item(ITEM, make, RailwayEnv(), c)
    assert row["status"] == "provider_error" and row["error_kind"] == "invalid_response" and row["attempts"] == 1


def test_sdk_decode_errors_are_invalid_response():
    a = build_adapter("experimental_inkling", client=Fake([json.JSONDecodeError("x", "{", 1)]))
    with pytest.raises(ProviderError) as e:
        a.start("s", "q", [])
    assert e.value.kind == "invalid_response" and e.value.retryable is False
    vexc = openai.APIResponseValidationError(response=SDK_HTTP.Response(200, request=REQ), body=None)
    a = build_adapter("experimental_inkling", client=Fake([vexc]))
    with pytest.raises(ProviderError) as e:
        a.start("s", "q", [])
    assert e.value.kind == "invalid_response"


def test_odd_tool_call_shapes_do_not_crash_the_run():
    weird = {"id": "g", "object": "chat.completion", "created": 1, "model": "m", "choices": [{"index": 0, "finish_reason": "tool_calls",
             "message": {"role": "assistant", "content": None, "tool_calls": [
                 {"id": "a", "type": "function", "function": {"name": "get_fare", "arguments": {"train_id": "BTB103", "travel_class": "2A"}}},
                 {"id": "b", "type": "function"},
                 {"id": "c", "type": "function", "function": {"arguments": "{}"}},
                 {"id": "d", "type": "function", "function": {"name": "get_fare", "arguments": "{bad"}}]}}]}
    final = {"id": "g2", "object": "chat.completion", "created": 1, "model": "m",
             "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "done"}}]}
    row = run_item(ITEM, lambda: build_adapter("experimental_inkling", client=Fake([weird, final])), RailwayEnv(), cfg())
    assert row["status"] == "completed" and row["usage"] == {}     # no usage anywhere -> {} not a crash
    ev = [(e["event"], e["tool_call_id"]) for e in row["trajectory"]]
    assert ev == [("tool_call", "a"), ("malformed_tool_call", "b"), ("malformed_tool_call", "c"), ("malformed_tool_call", "d")]
    assert row["trajectory"][0]["observation"]["ok"] is True       # dict arguments were normalised and executed


def test_message_none_is_retryable_provider_error():
    b = {"id": "g", "object": "chat.completion", "created": 1, "model": "m", "choices": [{"index": 0, "finish_reason": "stop"}]}
    a = build_adapter("experimental_inkling", client=Fake([b]))
    with pytest.raises(ProviderError) as e:
        a.start("s", "q", [])
    assert e.value.kind == "empty_response" and e.value.retryable is True


def test_adapter_redacts_key_in_provider_errors(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, DUMMY)
    exc = openai.AuthenticationError(f"invalid key {DUMMY}", response=SDK_HTTP.Response(401, request=REQ), body=None)
    a = build_adapter("experimental_inkling", client=Fake([exc]))
    with pytest.raises(ProviderError) as e:
        a.start("s", "q", [])
    assert DUMMY not in str(e.value) and "[REDACTED]" in str(e.value)
    a = build_adapter("experimental_inkling", client=Fake([{"error": {"code": 401, "message": f"key {DUMMY}"}}]))
    with pytest.raises(ProviderError) as e:
        a.start("s", "q", [])
    assert DUMMY not in str(e.value)


def test_runner_row_never_contains_key(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, DUMMY)
    exc = openai.AuthenticationError(f"invalid key {DUMMY}", response=SDK_HTTP.Response(401, request=REQ), body=None)
    row = run_item(ITEM, lambda: build_adapter("experimental_inkling", client=Fake([exc])), RailwayEnv(), cfg())
    assert DUMMY not in json.dumps(row, ensure_ascii=False)
