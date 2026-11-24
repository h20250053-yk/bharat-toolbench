"""Runner behaviour with a scripted fake adapter (no network, no API keys, no model)."""
import json

import pytest

from agents.base import ModelOutputError, ModelTurn, ProviderError, ToolCall
from environment import RailwayEnv
from evaluation import run_pilot
from evaluation.final_answer import CLOSE, OPEN
from evaluation.quota import QuotaExceeded, QuotaTracker
from evaluation.runner import MAX_TURNS, SYSTEM_PROMPT, SYSTEM_PROMPT_SHA256, RunnerConfig, run_item, sha256_text
from evaluation.scorer import score
from evaluation.selfcheck import gold_for

ITEM = {"task_id": "T01_en", "semantic_task_id": "T01", "language": "en", "query": "What is the fare for 2A class on train BTB103?",
        "allowed_tools": ["resolve_station", "search_trains", "get_train_details", "check_availability", "get_fare", "book_ticket"]}
GOOD_JSON = json.dumps({"status": "success", "selected_train": "BTB103", "selected_class": "2A", "booking_ids": [],
                        "requested_passengers": [], "notes": "fare lookup"})
FINAL = f"The 2A fare on BTB103 is 3565.\n{OPEN}\n{GOOD_JSON}\n{CLOSE}"


def turn(text="", calls=(), usage=(10, 5)):
    return ModelTurn(text=text, tool_calls=list(calls), finish_reason="stop",
                     usage={"input_tokens": usage[0], "output_tokens": usage[1], "total_tokens": sum(usage)},
                     request={"fake": True}, response={"fake": True})


class Scripted:
    """Adapter that replays a script; each element is a ModelTurn or an exception to raise."""
    def __init__(self, script, log):
        self.script, self.log = list(script), log
        self.model_key, self.provider, self.model = "fake", "fake", "fake-model"

    def settings(self):
        return {"provider": "fake"}

    def _next(self, *a):
        self.log.append(a)
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

    def start(self, system_prompt, user_prompt, tools):
        return self._next("start", system_prompt, user_prompt)

    def continue_turn(self, results):
        return self._next("continue", results)


def factory(scripts):
    """Each call returns a fresh adapter for the next attempt's script."""
    seq, calls = list(scripts), []

    def make():
        return Scripted(seq.pop(0), calls)
    make.calls = calls
    return make


FARE_CALL = ToolCall(id="c1", name="get_fare", arguments={"train_id": "BTB103", "travel_class": "2A"})
GOOD_SCRIPT = [turn(calls=[FARE_CALL]), turn(text=FINAL)]


def cfg(**kw):
    waits = []
    c = RunnerConfig(sleep=waits.append, **kw)
    c.waits = waits
    return c


def test_happy_path_provenance_usage_rawlog_and_score():
    env, c = RailwayEnv(), cfg()
    row = run_item(ITEM, factory([GOOD_SCRIPT]), env, c, run_name="unit")
    assert row["status"] == "completed" and row["attempts"] == 1 and row["retries"] == []
    for k in ("run_id", "benchmark_version", "task_id", "language", "model", "system_prompt_sha256", "env_hash_before", "env_hash_after"):
        assert row[k], k
    assert row["system_prompt_sha256"] == SYSTEM_PROMPT_SHA256 == sha256_text(SYSTEM_PROMPT)
    assert row["usage"] == {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30}  # SUMMED over 2 turns
    types = [e["type"] for e in row["raw_log"]]
    for t in ("model_request", "model_response", "tool_request", "tool_response", "final_answer"):
        assert t in types
    assert all("ts" in e for e in row["raw_log"])
    assert row["final_answer"]["ok"] and row["final_answer"]["answer"]["selected_train"] == "BTB103"
    assert score(row, gold_for("T01"))["task_success"] is True


def test_system_prompt_contains_contract_and_plan_rules():
    assert OPEN in SYSTEM_PROMPT and CLOSE in SYSTEM_PROMPT
    assert "2026-10-05 09:00 IST (Monday)" in SYSTEM_PROMPT and "Only call book_ticket when the user asked you to book." in SYSTEM_PROMPT


def test_retryable_provider_error_is_retried_with_retry_after():
    env, c = RailwayEnv(), cfg()
    f = factory([[ProviderError("rate_limit", "429", retryable=True, status_code=429, retry_after=7.0)], GOOD_SCRIPT])
    row = run_item(ITEM, f, env, c)
    assert row["status"] == "completed" and row["attempts"] == 2
    assert row["retries"][0]["kind"] == "rate_limit" and row["retries"][0]["wait_seconds"] == 7.0 and c.waits == [7.0]


def test_exponential_backoff_and_attempt_cap():
    env, c = RailwayEnv(), cfg(max_attempts=3, jitter=0.0)
    err = lambda: [ProviderError("server", "503", retryable=True, status_code=503)]  # noqa: E731
    row = run_item(ITEM, factory([err(), err(), err()]), env, c)
    assert row["status"] == "provider_error" and row["attempts"] == 3
    assert c.waits == [2.0, 4.0] and len(row["retries"]) == 3
    assert score(row, gold_for("T01"))["task_success"] is None  # provider errors are re-run, never scored 0


def test_non_retryable_provider_error_is_not_retried():
    env, c = RailwayEnv(), cfg()
    row = run_item(ITEM, factory([[ProviderError("auth", "401", retryable=False, status_code=401)]]), env, c)
    assert row["status"] == "provider_error" and row["attempts"] == 1 and c.waits == []


def test_malformed_tool_call_is_recorded_and_run_continues():
    env, c = RailwayEnv(), cfg()
    bad = ToolCall(id="m1", name="get_fare", arguments={}, raw_arguments='{"train_id": "BTB103",', parse_ok=False, parse_error="EOF")
    f = factory([[turn(calls=[bad]), turn(calls=[FARE_CALL]), turn(text=FINAL)]])
    row = run_item(ITEM, f, env, c)
    assert row["status"] == "completed" and row["attempts"] == 1
    ev = row["trajectory"][0]
    assert ev["event"] == "malformed_tool_call" and ev["raw_arguments"].startswith('{"train_id"')
    assert ev["observation"]["error"]["code"] == "MALFORMED_ARGUMENTS"
    # the model was told about the malformed call
    assert f.calls[1][0] == "continue" and f.calls[1][1][0][1]["error"]["code"] == "MALFORMED_ARGUMENTS"
    s = score(row, gold_for("T01"))
    assert s["task_success"] and s["malformed_tool_calls"] == 1


def test_model_output_error_is_a_model_failure_not_retried():
    env, c = RailwayEnv(), cfg()
    row = run_item(ITEM, factory([[ModelOutputError("malformed_function_call", "MALFORMED_FUNCTION_CALL")], GOOD_SCRIPT]), env, c)
    assert row["status"] == "malformed_output" and row["attempts"] == 1 and c.waits == []
    s = score(row, gold_for("T01"))
    assert s["task_success"] is False and "run:malformed_output" in s["failure_labels"]


def test_invalid_model_arguments_are_deterministic_tool_errors_not_retries():
    env, c = RailwayEnv(), cfg()
    wrong = ToolCall(id="w", name="get_fare", arguments={"train_id": "BTB103", "travel_class": "9Z"})
    row = run_item(ITEM, factory([[turn(calls=[wrong]), turn(text=FINAL)]]), env, c)
    assert row["status"] == "completed" and row["attempts"] == 1
    assert row["trajectory"][0]["observation"]["ok"] is False


def test_step_limit_is_exactly_8_turns_and_not_retried():
    assert MAX_TURNS == 8 and RunnerConfig().max_turns == 8
    env, c = RailwayEnv(), cfg()
    looping = [turn(calls=[ToolCall(id=f"x{i}", name="get_fare", arguments={"train_id": "BTB103", "travel_class": "2A"})]) for i in range(8)]
    f = factory([looping, GOOD_SCRIPT])
    row = run_item(ITEM, f, env, c)
    assert row["status"] == "step_limit_exceeded" and row["attempts"] == 1 and row["turns"] == 8
    assert len(f.calls) == 8  # exactly 8 model requests
    assert sum(e["event"] == "tool_call" for e in row["trajectory"]) == 7
    assert row["trajectory"][-1]["event"] == "unexecuted_step_limit"
    assert score(row, gold_for("T01"))["task_success"] is False


def test_disallowed_tool_is_recorded():
    env, c = RailwayEnv(), cfg()
    item = {**ITEM, "allowed_tools": ["get_fare"]}
    f = factory([[turn(calls=[ToolCall(id="b", name="book_ticket", arguments={})]), turn(calls=[FARE_CALL]), turn(text=FINAL)]])
    row = run_item(item, f, env, c)
    assert row["trajectory"][0]["event"] == "tool_not_allowed"


def test_quota_accounting_and_caps(tmp_path):
    q = QuotaTracker(tmp_path / "q.json", max_requests=2)
    run_item(ITEM, factory([GOOD_SCRIPT]), RailwayEnv(), cfg(), quota=q)
    assert q.state["requests"] == 2 and q.state["total_tokens"] == 30 and q.state["by_provider"]["fake"]["requests"] == 2
    with pytest.raises(QuotaExceeded):
        q.check()
    q.save()
    assert json.loads((tmp_path / "q.json").read_text())["requests"] == 2


def test_run_pilot_resume_reruns_only_provider_errors(tmp_path, monkeypatch):
    run_file = tmp_path / "pilot.jsonl"
    scripts = {"n": 0}

    def fake_build(model_key):
        scripts["n"] += 1
        if scripts["n"] == 1:  # first item's first attempt hits a non-retryable provider error
            a = Scripted([ProviderError("auth", "401", retryable=False)], [])
        else:
            a = Scripted([turn(text="I cannot answer.")], [])
        a.model_key = model_key  # real adapters carry the requested model key (set by the registry)
        return a
    monkeypatch.setattr(run_pilot, "build_adapter", fake_build)
    run_pilot.main(["--model", "primary_a", "--languages", "en", "--run-file", str(run_file)])
    rows = [json.loads(l) for l in run_file.read_text().splitlines()]
    assert [r["status"] for r in rows] == ["provider_error"] + ["completed"] * 4
    run_pilot.main(["--model", "primary_a", "--languages", "en", "--run-file", str(run_file), "--resume"])
    rows = [json.loads(l) for l in run_file.read_text().splitlines()]
    assert len(rows) == 6 and rows[-1]["task_id"] == "T01_en" and rows[-1]["status"] == "completed"
    assert (tmp_path / "pilot.quota.json").exists()


def test_resume_requires_run_file():
    with pytest.raises(SystemExit):
        run_pilot.main(["--model", "primary_a", "--resume"])


# --- partial_trajectory: executed tool calls of an attempt that ends in an error are kept as DIAGNOSTIC evidence ---
# Regression for the Qwen 2.5 3B full run, where e.g. T41_hinglish executed 50 tool calls (incl. a booking) before a
# context_overflow, but the row recorded trajectory=[] only. `trajectory` and scoring must stay exactly as before.
def test_partial_trajectory_kept_on_model_output_error_and_score_unchanged():
    env, c = RailwayEnv(), cfg()
    row = run_item(ITEM, factory([[turn(calls=[FARE_CALL]), ModelOutputError("unparsed_model_output", "x")]]), env, c)
    assert row["status"] == "malformed_output" and row["trajectory"] == []
    assert [e["tool"] for e in row["partial_trajectory"]] == ["get_fare"] and row["partial_trajectory"][0]["observation"]["ok"]
    without = {k: v for k, v in row.items() if k != "partial_trajectory"}
    assert score(row, gold_for("T01")) == score(without, gold_for("T01"))


def test_partial_trajectory_kept_on_non_retryable_provider_error():
    env, c = RailwayEnv(), cfg()
    err = ProviderError("context_overflow", "too long", retryable=False)
    row = run_item(ITEM, factory([[turn(calls=[FARE_CALL]), err]]), env, c)
    assert row["status"] == "provider_error" and row["trajectory"] == [] and len(row["partial_trajectory"]) == 1
    assert score(row, gold_for("T01"))["scored"] is False


def test_partial_trajectory_only_reflects_the_final_attempt_and_is_empty_on_success():
    env, c = RailwayEnv(), cfg()
    retry = ProviderError("rate_limit", "429", retryable=True, status_code=429)
    row = run_item(ITEM, factory([[turn(calls=[FARE_CALL]), retry], GOOD_SCRIPT]), env, c)
    assert row["status"] == "completed" and row["attempts"] == 2 and row["partial_trajectory"] == []
    assert len([e for e in row["trajectory"] if e["event"] == "tool_call"]) == 1  # only the second attempt's call


# --- audit I-04: a context overflow is a SCORED model failure (status context_overflow, label run:context_overflow) ---
def test_context_overflow_is_scored_as_failure_with_its_own_label():
    env, c = RailwayEnv(), cfg()
    err = ModelOutputError("context_overflow", "prompt too long", raw={"prompt_eval_count": 16000, "num_ctx": 16384})
    row = run_item(ITEM, factory([[turn(calls=[FARE_CALL]), err]]), env, c)
    assert row["status"] == "context_overflow" and row["error_kind"] == "context_overflow" and row["trajectory"] == []
    assert len(row["partial_trajectory"]) == 1  # the calls made before the overflow stay as diagnostic evidence
    s = score(row, gold_for("T01"))
    assert s["scored"] is True and s["task_success"] is False and "run:context_overflow" in s["failure_labels"]


def test_resume_does_not_rerun_context_overflow_rows():
    from evaluation.run_pilot import FINAL_STATUSES
    assert "context_overflow" in FINAL_STATUSES and "provider_error" not in FINAL_STATUSES


def test_output_truncated_is_a_scored_failure_labelled_apart_from_malformed_output():
    env, c = RailwayEnv(), cfg()
    row = run_item(ITEM, factory([[ModelOutputError("output_truncated", "cut off", raw={"done_reason": "length"})]]), env, c)
    assert row["status"] == "output_truncated" and row["error_kind"] == "output_truncated"
    s = score(row, gold_for("T01"))
    assert s["scored"] is True and s["task_success"] is False and "run:output_truncated" in s["failure_labels"]
    assert "run:malformed_output" not in s["failure_labels"]
    from evaluation.run_pilot import FINAL_STATUSES
    assert "output_truncated" in FINAL_STATUSES
