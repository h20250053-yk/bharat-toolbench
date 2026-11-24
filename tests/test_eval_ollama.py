"""Offline tests for the local Ollama adapter (httpx.MockTransport: no network, no Ollama server, no API keys)."""
import json

import httpx
import pytest

from agents import ollama_adapter
from agents.base import ModelOutputError, ProviderError, ToolCall
from agents.ollama_adapter import OllamaAdapter
from agents.registry import build_adapter, load_model_config
from environment import RailwayEnv
from evaluation.final_answer import CLOSE, OPEN
from evaluation.runner import RunnerConfig, run_item
from evaluation.scorer import score
from evaluation.selfcheck import gold_for

TOOLS = [{"name": "get_fare", "description": "Fare for a train and class.",
          "parameters": {"type": "object", "properties": {"train_id": {"type": "string"}, "travel_class": {"type": "string"}},
                         "required": ["train_id", "travel_class"]}}]
TAGS = {"models": [{"name": "qwen2.5:3b", "model": "qwen2.5:3b", "digest": "357c53fb659c" + "0" * 52,
                    "details": {"family": "qwen2", "parameter_size": "3.1B", "quantization_level": "Q4_K_M", "context_length": 32768}}]}


@pytest.fixture(autouse=True)
def _clear_model_info_cache():
    ollama_adapter._MODEL_INFO_CACHE.clear()
    yield
    ollama_adapter._MODEL_INFO_CACHE.clear()


def chat_body(content="", tool_calls=None, prompt=100, output=20, cached=None, done_reason="stop"):
    msg = {"role": "assistant", "content": content}
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    body = {"model": "qwen2.5:3b", "message": msg, "done": True, "done_reason": done_reason,
            "prompt_eval_count": prompt, "eval_count": output}
    if cached is not None:
        body["prompt_eval_cached_count"] = cached
    return body


class FakeOllama:
    """Mock Ollama server: serves /api/version and /api/tags; /api/chat replies come from a script (dict body,
    (status, body) tuple, or an exception to raise). Every chat request body is recorded."""

    def __init__(self, script, tags=TAGS, capabilities=("completion", "tools")):
        self.script, self.tags, self.chats, self.paths = list(script), tags, [], []
        self.capabilities, self.shows, self.show_status, self.show_extra = list(capabilities), [], 200, {}
        self.version = "0.40.18"

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.paths.append((request.method, request.url.path))
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": self.version})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json=self.tags)
        if request.url.path == "/api/show":
            self.shows.append(json.loads(request.content))
            if self.show_status != 200:
                return httpx.Response(self.show_status, json={"error": "not found"})
            return httpx.Response(200, json={"capabilities": self.capabilities, **self.show_extra})
        assert request.url.path == "/api/chat"
        self.chats.append(json.loads(request.content))
        step = self.script.pop(0)
        if callable(step) and not isinstance(step, dict):
            step = step(self.chats[-1])
        if isinstance(step, Exception):
            raise step
        if isinstance(step, tuple):
            status, body = step
            return httpx.Response(status, content=body if isinstance(body, bytes) else json.dumps(body).encode())
        return httpx.Response(200, json=step)


def make(script, tags=TAGS, capabilities=("completion", "tools"), version="0.40.18", **kw):
    server = FakeOllama(script, tags, capabilities)
    server.version = version
    params = dict(model_key="local_qwen25_3b", model="qwen2.5:3b", temperature=0, max_tokens=1024, num_ctx=8192, seed=42,
                  timeout_seconds=300, base_url="http://127.0.0.1:11434", keep_alive="10m")
    params.update(kw)
    return OllamaAdapter(client=httpx.Client(transport=httpx.MockTransport(server)), **params), server


# ---------------------------------------------------------------------------------------------------- config / registry
def test_config_entry_and_registry_build_without_api_key(monkeypatch):
    for var in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    cfg = load_model_config()["local_qwen25_3b"]
    assert cfg["provider"] == "ollama" and cfg["model"] == "qwen2.5:3b"
    assert cfg["temperature"] == 0 and cfg["num_ctx"] == 16384 and cfg["max_tokens"] < cfg["num_ctx"]
    adapter = build_adapter("local_qwen25_3b", client=httpx.Client(transport=httpx.MockTransport(FakeOllama([]))))
    assert isinstance(adapter, OllamaAdapter)
    assert (adapter.model_key, adapter.provider, adapter.model) == ("local_qwen25_3b", "ollama", "qwen2.5:3b")
    s = adapter.settings()
    assert s["num_ctx"] == 16384 and s["seed"] == 42 and s["temperature"] == 0 and s["max_tokens"] == 2048 and s["local"] is True


def test_all_local_models_share_identical_decoding_settings():
    """Fair comparison: every local_* model entry must use the same decoding / context / budget settings."""
    cfg = load_model_config()
    local = {k: v for k, v in cfg.items() if k.startswith("local_")}
    assert {"local_qwen25_3b", "local_llama32_3b"} <= set(local)
    keys = ("provider", "temperature", "seed", "max_tokens", "num_ctx", "timeout_seconds", "keep_alive", "base_url", "think")
    settings = {k: tuple(v.get(x) for x in keys) for k, v in local.items()}
    assert len(set(settings.values())) == 1, settings
    assert cfg["local_llama32_3b"]["model"] == "llama3.2:3b"
    adapter = build_adapter("local_llama32_3b", client=httpx.Client(transport=httpx.MockTransport(FakeOllama([]))))
    assert isinstance(adapter, OllamaAdapter) and adapter.model == "llama3.2:3b" and adapter.model_key == "local_llama32_3b"


def test_run_pilot_cli_accepts_local_qwen():
    import argparse
    from evaluation import run_pilot
    parser_actions = []
    orig = argparse.ArgumentParser.parse_args

    def capture(self, argv=None, namespace=None):
        parser_actions.extend(self._actions)
        raise SystemExit(0)
    argparse.ArgumentParser.parse_args = capture
    try:
        with pytest.raises(SystemExit):
            run_pilot.main(["--model", "local_qwen25_3b"])
    finally:
        argparse.ArgumentParser.parse_args = orig
    model_action = next(a for a in parser_actions if a.dest == "model")
    assert {"local_qwen25_3b", "local_llama32_3b"} <= set(model_action.choices)


@pytest.mark.parametrize("kw", [dict(reasoning="low"), dict(parallel_tool_calls=False), dict(max_tokens=8192, num_ctx=8192)])
def test_invalid_settings_rejected(kw):
    with pytest.raises(ValueError):
        make([], **kw)


# ---------------------------------------------------------------------------------------------------- requests
def test_request_format_and_provenance():
    adapter, server = make([chat_body("hello")])
    turn = adapter.start("SYS", "USER", TOOLS)
    assert turn.text == "hello" and turn.tool_calls == [] and turn.finish_reason == "stop"
    body = server.chats[0]
    assert body["model"] == "qwen2.5:3b" and body["stream"] is False and body["keep_alive"] == "10m"
    assert body["options"] == {"temperature": 0, "num_ctx": 8192, "num_predict": 1024, "seed": 42}
    assert body["messages"] == [{"role": "system", "content": "SYS"}, {"role": "user", "content": "USER"}]
    assert body["tools"] == [{"type": "function", "function": TOOLS[0]}]
    s = adapter.settings()
    assert s["ollama_version"] == "0.40.18" and s["model_digest"].startswith("357c53fb659c")
    assert s["quantization"] == "Q4_K_M" and s["parameter_size"] == "3.1B" and s["endpoint"] == "/api/chat"
    assert turn.request == body  # snapshot of exactly what was sent


def test_model_info_fetched_once_per_model():
    adapter, server = make([chat_body("a"), chat_body("b")])
    adapter.start("S", "U", TOOLS)
    adapter.start("S", "U", TOOLS)
    assert server.paths.count(("GET", "/api/tags")) == 1


def test_tool_call_round_trip_and_history():
    call = {"id": "call_abc", "function": {"index": 0, "name": "get_fare", "arguments": {"train_id": "BTB103", "travel_class": "2A"}}}
    adapter, server = make([chat_body(tool_calls=[call]), chat_body("done")])
    turn = adapter.start("S", "U", TOOLS)
    [tc] = turn.tool_calls
    assert (tc.id, tc.name, tc.arguments, tc.parse_ok) == ("call_abc", "get_fare", {"train_id": "BTB103", "travel_class": "2A"}, True)
    assert json.loads(tc.raw_arguments) == {"train_id": "BTB103", "travel_class": "2A"}
    result = {"ok": True, "data": {"fare_inr": 1234}, "error": None}
    turn2 = adapter.continue_turn([(tc, result)])
    assert turn2.text == "done"
    msgs = server.chats[1]["messages"]
    assert msgs[2] == {"role": "assistant", "content": "", "tool_calls": [call]}
    assert msgs[3] == {"role": "tool", "tool_name": "get_fare", "content": json.dumps(result, ensure_ascii=False)}
    assert server.chats[1]["tools"] == server.chats[0]["tools"]  # tools sent on every turn


def test_synthetic_ids_when_missing():
    calls = [{"function": {"name": "get_fare", "arguments": {"train_id": "BTB101", "travel_class": "3A"}}},
             {"function": {"name": "get_fare", "arguments": {"train_id": "BTB102", "travel_class": "3A"}}}]
    adapter, _ = make([chat_body(tool_calls=calls)])
    turn = adapter.start("S", "U", TOOLS)
    assert [c.id for c in turn.tool_calls] == ["ollama-1-1", "ollama-1-2"]


def test_string_arguments_are_decoded():
    adapter, _ = make([chat_body(tool_calls=[{"id": "x", "function": {"name": "get_fare", "arguments": '{"train_id": "BTB103"}'}}])])
    [tc] = adapter.start("S", "U", TOOLS).tool_calls
    assert tc.parse_ok and tc.arguments == {"train_id": "BTB103"} and tc.raw_arguments == '{"train_id": "BTB103"}'


@pytest.mark.parametrize("fn", [{"name": "get_fare", "arguments": '{"train_id": "BTB103",'},
                                {"name": "get_fare", "arguments": [1, 2]},
                                {"name": "get_fare", "arguments": "nope"},
                                {"name": "", "arguments": {"train_id": "BTB103"}}])
def test_malformed_arguments_flagged_not_raised(fn):
    adapter, _ = make([chat_body(tool_calls=[{"id": "m1", "function": fn}])])
    [tc] = adapter.start("S", "U", TOOLS).tool_calls
    assert tc.parse_ok is False and tc.arguments == {} and tc.parse_error and tc.id == "m1"


def test_usage_normalised_including_cache():
    adapter, _ = make([chat_body("x", prompt=300, output=40, cached=250)])
    turn = adapter.start("S", "U", TOOLS)
    assert turn.usage == {"input_tokens": 300, "output_tokens": 40, "total_tokens": 340, "cached_input_tokens": 250}


def test_missing_usage_is_safe():
    body = chat_body("x")
    del body["prompt_eval_count"], body["eval_count"]
    adapter, _ = make([body])
    assert adapter.start("S", "U", TOOLS).usage == {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def test_context_overflow_is_a_scored_model_failure_not_a_provider_error():
    """Audit I-04: an overflow is the model's own doing (looping tool calls), so it is scored, never excluded."""
    adapter, _ = make([chat_body("truncated?", prompt=7200)])  # 7200 + 1024 > 8192 (this helper adapter uses num_ctx 8192)
    with pytest.raises(ModelOutputError) as e:
        adapter.start("S", "U", TOOLS)
    assert e.value.kind == "context_overflow" and e.value.raw["prompt_eval_count"] == 7200 and e.value.raw["num_ctx"] == 8192


def test_all_local_models_use_16k_context_2048_output_and_thinking_off():
    cfg = load_model_config()
    local = {k: v for k, v in cfg.items() if k.startswith("local_")}
    assert {v["num_ctx"] for v in local.values()} == {16384} and {v["max_tokens"] for v in local.values()} == {2048}
    assert {v["think"] for v in local.values()} == {False}


# ---------------------------------------------------------------------------------------------------- empty output
# Recorded pilot condition (runs/local_qwen25_3b_pilot.jsonl, T03_*): Ollama generated tokens but returned
# message.content == "" and no tool_calls (its tool-call parser discarded a malformed <tool_call> block).
T03_EMPTY_BODY = {"model": "qwen2.5:3b", "message": {"role": "assistant", "content": ""}, "done": True, "done_reason": "stop",
                  "prompt_eval_count": 1242, "prompt_eval_cached_count": 0, "eval_count": 101,
                  "total_duration": 3_000_000_000, "eval_duration": 2_000_000_000}


def test_valid_text_response_unchanged():
    adapter, _ = make([chat_body("The fare is 3565.", output=12)])
    turn = adapter.start("S", "U", TOOLS)
    assert turn.text == "The fare is 3565." and turn.tool_calls == []


def test_valid_tool_call_with_empty_content_is_not_flagged():
    call = {"id": "c1", "function": {"name": "get_fare", "arguments": {"train_id": "BTB103", "travel_class": "2A"}}}
    adapter, _ = make([chat_body("", tool_calls=[call], output=21)])
    [tc] = adapter.start("S", "U", TOOLS).tool_calls
    assert tc.parse_ok and tc.name == "get_fare"


def test_empty_output_with_zero_generated_tokens_is_an_ordinary_empty_answer():
    adapter, _ = make([chat_body("", output=0)])
    turn = adapter.start("S", "U", TOOLS)
    assert turn.text == "" and turn.tool_calls == [] and turn.usage["output_tokens"] == 0


def test_empty_output_with_generated_tokens_raises_model_output_error():
    adapter, _ = make([dict(T03_EMPTY_BODY)])
    with pytest.raises(ModelOutputError) as e:
        adapter.start("SYSTEM PROMPT TEXT", "USER QUERY TEXT", TOOLS)
    assert e.value.kind == "unparsed_model_output" and "101 tokens" in str(e.value)
    assert e.value.raw == {"turn": 1, "model": "qwen2.5:3b", "done_reason": "stop", "prompt_eval_count": 1242,
                           "prompt_eval_cached_count": 0, "eval_count": 101, "total_duration": 3_000_000_000,
                           "eval_duration": 2_000_000_000}
    assert "SYSTEM PROMPT TEXT" not in json.dumps(e.value.raw) and "USER QUERY TEXT" not in json.dumps(e.value.raw)
    assert adapter.messages[-1]["role"] == "user"  # nothing fabricated into the conversation history


def test_empty_output_mid_conversation_raises_after_valid_round_trip():
    call = {"id": "c1", "function": {"name": "get_fare", "arguments": {"train_id": "BTB103", "travel_class": "2A"}}}
    adapter, _ = make([chat_body(tool_calls=[call]), dict(T03_EMPTY_BODY)])
    [tc] = adapter.start("S", "U", TOOLS).tool_calls
    with pytest.raises(ModelOutputError) as e:
        adapter.continue_turn([(tc, {"ok": True, "data": {"fare_inr": 1}, "error": None})])
    assert e.value.raw["turn"] == 2


def test_runner_records_unparsed_output_as_scored_model_failure_not_retried():
    server = FakeOllama([dict(T03_EMPTY_BODY), chat_body("must not be requested")])
    factory = lambda: build_adapter("local_qwen25_3b", client=httpx.Client(transport=httpx.MockTransport(server)))  # noqa: E731
    item = {"task_id": "T03_en", "semantic_task_id": "T03", "language": "en", "query": "q",
            "allowed_tools": ["resolve_station", "search_trains", "get_train_details", "check_availability", "get_fare", "book_ticket"]}
    row = run_item(item, factory, RailwayEnv(), RunnerConfig(sleep=lambda s: None), run_name="t")
    assert row["status"] == "malformed_output" and row["error_kind"] == "unparsed_model_output"
    assert row["attempts"] == 1 and row["retries"] == [] and len(server.chats) == 1
    logged = [x for x in row["raw_log"] if x["type"] == "malformed_output"]
    assert logged and logged[0]["raw"]["eval_count"] == 101
    sc = score(row, gold_for("T03"), row["state_snapshot"])
    assert sc["scored"] is True and sc["task_success"] is False and "run:malformed_output" in sc["failure_labels"]


# ---------------------------------------------------------------------------------------------------- errors
@pytest.mark.parametrize("step,kind,retryable,status", [
    ((404, {"error": "model 'qwen2.5:3b' not found"}), "not_found", False, 404),
    ((400, {"error": "invalid options"}), "bad_request", False, 400),
    ((500, {"error": "llama runner process has terminated"}), "server", True, 500),
    ((503, {"error": "server busy"}), "server", True, 503),
    ((429, {"error": "too many requests"}), "rate_limit", True, 429),
    ((200, b"<html>not json</html>"), "invalid_response", False, None),
    ((200, {"model": "qwen2.5:3b", "done": True}), "invalid_response", False, None),
    ((200, {"error": "unexpected EOF"}), "server", True, None),
    (httpx.ReadTimeout("read timed out"), "timeout", True, None),
    (httpx.ConnectError("connection refused"), "connection", True, None),
])
def test_error_classification(step, kind, retryable, status):
    adapter, _ = make([step])
    with pytest.raises(ProviderError) as e:
        adapter.start("S", "U", TOOLS)
    assert (e.value.kind, e.value.retryable, e.value.status_code) == (kind, retryable, status)


def test_model_not_installed_fails_fast():
    adapter, server = make([], tags={"models": []})
    with pytest.raises(ProviderError) as e:
        adapter.start("S", "U", TOOLS)
    assert e.value.kind == "not_found" and e.value.retryable is False and "ollama pull" in str(e.value)
    assert server.chats == []


def test_server_down_during_metadata_is_retryable():
    def down(request):
        raise httpx.ConnectError("connection refused")
    adapter = OllamaAdapter(model_key="k", model="qwen2.5:3b", client=httpx.Client(transport=httpx.MockTransport(down)))
    with pytest.raises(ProviderError) as e:
        adapter.start("S", "U", TOOLS)
    assert e.value.kind == "connection" and e.value.retryable is True


# ---------------------------------------------------------------------------------------------------- runner + scorer
def test_end_to_end_with_runner_and_scorer_on_t01():
    """A scripted 'model' answers T01 through the real runner, environment and scorer."""
    def final_answer(chat):
        tool_msg = next(m for m in reversed(chat["messages"]) if m["role"] == "tool")
        fare = json.loads(tool_msg["content"])["data"]["fare_inr"]
        block = json.dumps({"status": "success", "selected_train": "BTB103", "selected_class": "2A", "booking_ids": [],
                            "requested_passengers": [], "notes": "fare lookup"})
        return chat_body(f"The 2A fare on BTB103 is {fare}.\n{OPEN}\n{block}\n{CLOSE}", prompt=900, output=60)

    server = FakeOllama([chat_body(tool_calls=[{"id": "call_1", "function": {"name": "get_fare", "arguments": {
        "train_id": "BTB103", "travel_class": "2A"}}}], prompt=800, output=25), final_answer])
    factory = lambda: build_adapter("local_qwen25_3b", client=httpx.Client(transport=httpx.MockTransport(server)))  # noqa: E731
    item = {"task_id": "T01_en", "semantic_task_id": "T01", "language": "en", "query": "What is the fare for 2A class on train BTB103?",
            "allowed_tools": ["resolve_station", "search_trains", "get_train_details", "check_availability", "get_fare", "book_ticket"]}
    row = run_item(item, factory, RailwayEnv(), RunnerConfig(sleep=lambda s: None), run_name="t")
    assert row["status"] == "completed" and row["model_key"] == "local_qwen25_3b" and row["provider"] == "ollama"
    assert row["adapter_settings"]["model_digest"].startswith("357c53fb659c")
    assert [e["tool"] for e in row["trajectory"]] == ["get_fare"] and row["trajectory"][0]["observation"]["ok"] is True
    assert row["usage"]["input_tokens"] == 1700 and row["usage"]["output_tokens"] == 85
    sc = score(row, gold_for("T01"), row["state_snapshot"])
    assert sc["scored"] is True and sc["task_success"] is True, sc["failure_labels"]


def test_retryable_error_is_retried_by_runner():
    server = FakeOllama([httpx.ConnectError("refused"), chat_body("no tools needed")])
    factory = lambda: build_adapter("local_qwen25_3b", client=httpx.Client(transport=httpx.MockTransport(server)))  # noqa: E731
    item = {"task_id": "T01_en", "semantic_task_id": "T01", "language": "en", "query": "q", "allowed_tools": ["get_fare"]}
    row = run_item(item, factory, RailwayEnv(), RunnerConfig(sleep=lambda s: None), run_name="t")
    assert row["status"] == "completed" and row["attempts"] == 2 and row["retries"][0]["kind"] == "connection"


# ---------------------------------------------------------------------------------------------------- audit I-05: think control
from agents.ollama_adapter import effective_think  # noqa: E402

GPT_OSS_TAGS = {"models": [{"name": "gpt-oss:20b", "model": "gpt-oss:20b", "digest": "d" * 64,
                            "details": {"family": "gptoss", "parameter_size": "20.9B", "quantization_level": "MXFP4"}}]}


@pytest.mark.parametrize("model,caps,think,expected", [
    ("qwen3:8b", ["completion", "tools", "thinking"], False, False),           # can be switched off -> off
    ("deepseek-r1:8b", ["completion", "thinking"], False, False),
    ("gpt-oss:20b", ["completion", "tools", "thinking"], False, "low"),        # cannot be switched off -> lowest level
    ("qwen2.5:7b", ["completion", "tools"], False, None),                      # not a thinking model -> field not sent
    ("llama3.1:8b", None, False, None),                                        # capabilities unknown -> not sent
    ("qwen3:8b", ["thinking"], None, None),                                    # policy unset -> not sent
    ("qwen3:8b", ["thinking"], True, True), ("gpt-oss:20b", ["thinking"], "medium", "medium"),
])
def test_effective_think_policy(model, caps, think, expected):
    assert effective_think(model, caps, think) == expected


def test_non_thinking_model_gets_no_think_field_and_records_the_policy():
    adapter, server = make([chat_body("ok")], think=False)
    adapter.start("S", "U", TOOLS)
    assert "think" not in server.chats[0] and server.shows == [{"model": "qwen2.5:3b"}]
    s = adapter.settings()
    assert s["think_config"] is False and s["think_effective"] is None and s["capabilities"] == ["completion", "tools"]


def test_thinking_model_is_sent_think_false():
    tags = {"models": [{"name": "qwen3:8b", "model": "qwen3:8b", "digest": "e" * 64, "details": {}}]}
    adapter, server = make([chat_body("ok")], tags=tags, capabilities=("completion", "tools", "thinking"), model="qwen3:8b", think=False)
    adapter.start("S", "U", TOOLS)
    assert server.chats[0]["think"] is False and adapter.settings()["think_effective"] is False


def test_gpt_oss_cannot_be_switched_off_so_it_gets_the_lowest_level_and_it_is_recorded():
    adapter, server = make([chat_body("ok")], tags=GPT_OSS_TAGS, capabilities=("completion", "tools", "thinking"),
                           model="gpt-oss:20b", think=False)
    adapter.start("S", "U", TOOLS)
    assert server.chats[0]["think"] == "low"
    s = adapter.settings()
    assert s["think_config"] is False and s["think_effective"] == "low" and s["model_family"] == "gptoss"


def test_invalid_think_value_rejected():
    with pytest.raises(ValueError):
        make([], think="maximum")


def test_thinking_is_echoed_back_in_the_history_and_kept_in_the_raw_response():
    call = [{"function": {"name": "get_fare", "arguments": {"train_id": "BTB103", "travel_class": "2A"}}}]
    first = chat_body("", tool_calls=call)
    first["message"]["thinking"] = "I should look up the fare."
    adapter, server = make([first, chat_body("done")], capabilities=("completion", "tools", "thinking"), think=False)
    t = adapter.start("S", "U", TOOLS)
    assert t.response["message"]["thinking"] == "I should look up the fare."
    adapter.continue_turn([(t.tool_calls[0], {"ok": True})])
    assistant = server.chats[1]["messages"][2]
    assert assistant["role"] == "assistant" and assistant["thinking"] == "I should look up the fare."


# ---------------------------------------------------------------------------------------------------- audit I-05: truncation
def test_budget_spent_on_thinking_is_output_truncated_not_malformed():
    body = chat_body("", output=2048, done_reason="length")
    body["message"]["thinking"] = "x" * 9000
    adapter, _ = make([body], max_tokens=2048)
    with pytest.raises(ModelOutputError) as e:
        adapter.start("S", "U", TOOLS)
    assert e.value.kind == "output_truncated" and e.value.raw["thinking_chars"] == 9000 and e.value.raw["content_chars"] == 0


def test_answer_cut_off_by_max_tokens_is_output_truncated():
    adapter, _ = make([chat_body("The fare is 1,0", output=2048, done_reason="length")], max_tokens=2048)
    with pytest.raises(ModelOutputError) as e:
        adapter.start("S", "U", TOOLS)
    assert e.value.kind == "output_truncated" and e.value.raw["content_chars"] == 15


def test_length_stop_with_a_complete_tool_call_is_not_truncation():
    call = [{"function": {"name": "get_fare", "arguments": {"train_id": "BTB103", "travel_class": "2A"}}}]
    adapter, _ = make([chat_body("", tool_calls=call, done_reason="length")])
    assert adapter.start("S", "U", TOOLS).tool_calls[0].name == "get_fare"


def test_unparsed_output_stays_malformed_when_not_truncated():
    adapter, _ = make([dict(T03_EMPTY_BODY)])
    with pytest.raises(ModelOutputError) as e:
        adapter.start("S", "U", TOOLS)
    assert e.value.kind == "unparsed_model_output"


# ---------------------------------------------------------------------------------------------------- audit I-06: full tool schema
from agents.ollama_adapter import inline_refs  # noqa: E402
from environment.railway_env import tool_specs  # noqa: E402


def test_inline_refs_keeps_time_window_structure():
    search = next(t for t in tool_specs() if t["name"] == "search_trains")
    assert "$ref" in json.dumps(search["parameters"]) and "$defs" in search["parameters"]  # the benchmark schema uses a $ref
    sent = inline_refs(search["parameters"])
    assert "$ref" not in json.dumps(sent) and "$defs" not in sent
    tw = sent["properties"]["time_window"]
    branches = tw["anyOf"]
    obj = next(b for b in branches if b.get("type") == "object")
    assert set(obj["properties"]) == {"start", "end"} and obj["required"] == ["start", "end"] and {"type": "null"} in branches
    assert search["parameters"]["$defs"]  # the original is not modified


def test_adapter_sends_the_inlined_schema_and_records_its_hash_without_touching_the_benchmark_schema():
    from evaluation.runner import TOOL_SCHEMA_SHA256
    specs = [t for t in tool_specs() if t["name"] in ("search_trains", "get_fare")]
    adapter, server = make([chat_body("ok")])
    adapter.start("S", "U", specs)
    sent = server.chats[0]["tools"]
    search = next(t for t in sent if t["function"]["name"] == "search_trains")["function"]["parameters"]
    assert "$ref" not in json.dumps(search) and "start" in json.dumps(search["properties"]["time_window"])
    assert len(adapter.settings()["tool_schema_sent_sha256"]) == 64
    import hashlib
    assert TOOL_SCHEMA_SHA256 == hashlib.sha256(json.dumps(tool_specs(), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def test_inline_refs_rejects_recursive_refs():
    with pytest.raises(ValueError):
        inline_refs({"$defs": {"A": {"properties": {"x": {"$ref": "#/$defs/A"}}}}, "properties": {"a": {"$ref": "#/$defs/A"}}})


# ---------------------------------------------------------------------------------------------------- audit I-07: pre-flight
@pytest.mark.parametrize("caps", [("completion",), ("completion", "thinking")])
def test_model_without_tools_capability_is_refused_before_any_chat_request(caps):
    adapter, server = make([chat_body("must not be requested")], capabilities=caps)
    with pytest.raises(ProviderError) as e:
        adapter.start("S", "U", TOOLS)
    assert e.value.kind == "tools_unsupported" and e.value.retryable is False and server.chats == []


def test_server_that_reports_no_capabilities_is_refused():
    adapter, server = make([chat_body("x")])
    server.show_status = 404  # /api/show unavailable
    with pytest.raises(ProviderError) as e:
        adapter.preflight()
    assert e.value.kind == "tools_unsupported" and "not reported" in str(e.value) and server.chats == []


def test_preflight_passes_and_records_modelfile_parameters():
    adapter, server = make([chat_body("x")])
    server.show_extra = {"parameters": "repeat_penalty 1.05\ntop_k 20"}
    info = adapter.preflight()
    assert "tools" in info["capabilities"] and info["modelfile_parameters"] == "repeat_penalty 1.05\ntop_k 20"
    assert adapter.settings()["modelfile_parameters"].startswith("repeat_penalty")


def test_run_pilot_refuses_to_start_with_a_model_without_tools(tmp_path, monkeypatch, capsys):
    from evaluation import run_pilot
    adapter, server = make([chat_body("never")], capabilities=("completion",))
    monkeypatch.setattr(run_pilot, "build_adapter", lambda key: adapter)
    run_file = tmp_path / "r.jsonl"
    rc = run_pilot.main(["--model", "local_qwen25_3b", "--split", "pilot", "--languages", "en", "--run-file", str(run_file)])
    out = capsys.readouterr().out
    assert rc == 3 and "REFUSING TO RUN" in out and server.chats == []
    assert not run_file.exists() or run_file.read_text() == ""


# ---------------------------------------------------------------------------------------------------- minimum server version 0.40.18
from agents.ollama_adapter import MIN_OLLAMA_VERSION, check_min_version, parse_ollama_version  # noqa: E402


@pytest.mark.parametrize("version", ["0.40.13", "0.40.17", "0.40.9", "0.40.3", "0.39.99", "0.9.99", "garbage", "", None, "0.40", "latest"])
def test_old_or_unreadable_server_version_is_refused_before_any_chat_request(version):
    adapter, server = make([chat_body("must not be requested")], version=version)
    with pytest.raises(ProviderError) as e:
        adapter.preflight()
    assert e.value.kind == "ollama_too_old" and e.value.retryable is False and "0.40.18" in str(e.value) and server.chats == []
    with pytest.raises(ProviderError) as e2:          # start() runs the same pre-flight: no item can slip through
        adapter.start("S", "U", TOOLS)
    assert e2.value.kind == "ollama_too_old" and server.chats == []


@pytest.mark.parametrize("version", ["0.40.18", "0.40.19", "0.41.0", "0.100.0", "1.0.0", "v0.40.18", "0.40.18-rc1"])
def test_current_or_newer_server_passes_and_the_version_is_recorded(version):
    adapter, server = make([chat_body("ok")], version=version)
    info = adapter.preflight()
    assert info["ollama_version"] == version and adapter.settings()["ollama_version"] == version
    assert adapter.start("S", "U", TOOLS).text == "ok"


def test_versions_are_compared_numerically_not_as_strings():
    assert parse_ollama_version("0.40.9") < MIN_OLLAMA_VERSION and "0.40.9" > "0.40.18"      # string order would let it through
    assert parse_ollama_version("0.100.0") > MIN_OLLAMA_VERSION and "0.100.0" < "0.40.18"
    check_min_version("0.40.18")
    with pytest.raises(ProviderError):
        check_min_version("0.40.9")


def test_run_pilot_refuses_to_start_on_an_old_server(tmp_path, monkeypatch, capsys):
    from evaluation import run_pilot
    adapter, server = make([chat_body("never")], version="0.40.13")
    monkeypatch.setattr(run_pilot, "build_adapter", lambda key: adapter)
    run_file = tmp_path / "r.jsonl"
    rc = run_pilot.main(["--model", "local_qwen25_3b", "--split", "pilot", "--languages", "en", "--run-file", str(run_file)])
    out = capsys.readouterr().out
    assert rc == 3 and "REFUSING TO RUN" in out and "older than 0.40.18" in out and server.chats == []
    assert not run_file.exists() or run_file.read_text() == ""


# ---------------------------------------------------------------------------------------------------- MODEL_PLAN.md: the eight models
PLAN = {  # run order of MODEL_PLAN.md
    "local_qwen25_3b": "qwen2.5:3b", "local_llama32_3b": "llama3.2:3b", "local_llama31_8b": "llama3.1:8b", "local_deepseek_r1_8b": "deepseek-r1:8b",
    "local_qwen25_14b": "qwen2.5:14b", "local_gpt_oss_20b": "gpt-oss:20b", "local_gemma4_26b": "gemma4:26b", "local_mistral_small32_24b": "mistral-small3.2:24b",
}


def test_the_eight_planned_models_are_configured_with_identical_settings():
    cfg = load_model_config()
    for key, model in PLAN.items():
        assert key in cfg and cfg[key]["model"] == model and cfg[key]["provider"] == "ollama", key
    keys = ("provider", "temperature", "seed", "max_tokens", "num_ctx", "timeout_seconds", "keep_alive", "base_url", "think")
    assert len({tuple(cfg[k].get(x) for x in keys) for k in PLAN}) == 1
    assert {cfg[k]["num_ctx"] for k in PLAN} == {16384} and {cfg[k]["max_tokens"] for k in PLAN} == {2048} and {cfg[k]["think"] for k in PLAN} == {False}


def test_every_planned_model_builds_an_adapter_without_an_api_key(monkeypatch):
    for var in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    for key, model in PLAN.items():
        a = build_adapter(key, client=httpx.Client(transport=httpx.MockTransport(FakeOllama([]))))
        assert isinstance(a, OllamaAdapter) and a.model == model and a.num_ctx == 16384 and a.max_tokens == 2048 and a.think is False
