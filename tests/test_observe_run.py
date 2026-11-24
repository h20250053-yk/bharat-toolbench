"""Offline tests for analysis/observe_run.py, analysis/run_manifest.py and analysis/compare_runs.py."""
import hashlib
import json
from pathlib import Path

import pytest

from analysis import compare_runs, observe_run, run_manifest
from analysis.observe_run import ARG_ERROR_CODES, PRIMARY_ORDER, classify, expected_items, select_latest

ROOT = Path(__file__).resolve().parent.parent
GOLD = json.loads((ROOT / "benchmark" / "gold_labels.json").read_text(encoding="utf-8"))
FIXTURE = ROOT / "tests" / "fixtures" / "qwen25_3b_pilot_rows.jsonl"


def row(task="T01", lang="en", status="completed", success=False, labels=(), parse="missing_block", process=True, state=True,
        traj=(), bookings=(), final="some text", attempts=1, error_kind=None, model_key="local_x", done="stop",
        prompt_hash="p", settings=None):
    scored = status not in ("provider_error", "runner_error")  # context_overflow counts as scored (audit I-04)
    return {"task_id": f"{task}_{lang}", "semantic_task_id": task, "language": lang, "model_key": model_key, "status": status,
            "error_kind": error_kind, "attempts": attempts, "turns": 2, "query": "q", "final_text": final,
            "trajectory": list(traj), "state_snapshot": {"bookings": list(bookings)},
            "raw_log": [{"type": "model_response", "finish_reason": done}],
            "usage": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110},
            "started_at": "2026-10-14T00:00:00+00:00", "finished_at": "2026-10-14T00:00:10+00:00",
            "benchmark_version": "0.1.0-foundation", "system_prompt_sha256": prompt_hash, "tool_schema_sha256": "t",
            "adapter_settings": settings or {"temperature": 0, "seed": 42, "num_ctx": 8192, "max_tokens": 1024, "model_digest": "d"},
            "score": {"scored": scored, "task_success": (success if scored else None), "outcome_success": success,
                      "process_success": process, "state_success": state, "status_correct": success,
                      "final_answer_parse": parse, "failure_labels": list(labels)}}


def call(tool, args, ok=True, code=None, turn=1, obs_data=None):
    obs = {"ok": ok, "data": obs_data if ok else None, "error": None if ok else {"code": code, "message": "m"}}
    return {"event": "tool_call", "turn": turn, "tool": tool, "arguments": args, "observation": obs}


def prim(r):
    return classify(r, GOLD[r["semantic_task_id"]])[0]


# ---------------------------------------------------------------------------------------------------- primary categories
def test_every_primary_category_is_reachable():
    t04_booking = GOLD["T04"]["final_state"]["expected_bookings"][0]
    cases = {
        "success": row(success=True, labels=(), parse="ok"),
        "infra_error": row(status="provider_error", error_kind="connection"),
        "context_overflow": row(status="provider_error", error_kind="context_overflow"),
        "output_truncated": row(status="output_truncated", error_kind="output_truncated", labels=("run:output_truncated",)),
        "malformed_model_output": row(status="malformed_output", error_kind="unparsed_model_output", final=""),
        "step_limit": row(status="step_limit_exceeded", labels=("run:step_limit_exceeded",)),
        "unsafe_action": row(labels=("process:prohibited_action:book_ticket:x",)),
        "missing_booking": row(task="T04", state=False, labels=("state:bookings_mismatch",)),
        "tool_argument_error": row(process=False, labels=("process:missing_required_call:c1:get_fare",),
                                   traj=[call("get_fare", {"train_id": "BTB999", "travel_class": "2A"}, ok=False, code="INVALID_TRAIN")]),
        "missing_required_call": row(process=False, labels=("process:missing_required_call:c1:get_fare",)),
        "wrong_answer": row(parse="ok", labels=("status:expected_success_got_cannot_complete",)),
        "format_only": row(labels=("final_answer:missing_block",)),
        "other": row(labels=("something:unexpected",), parse="ok", process=True),
    }
    cases["other"]["score"]["final_answer_parse"] = "malformed_json: x"
    got = {name: prim(r) for name, r in cases.items()}
    assert got == {name: name for name in cases}
    assert set(got.values()) == set(PRIMARY_ORDER)
    assert t04_booking  # T04 gold expects a booking, so an empty state is a missing booking


def test_extra_booking_is_unsafe_even_without_prohibition_label():
    r = row(task="T01", state=False, labels=("state:bookings_mismatch",),
            bookings=[{"train_id": "BTB103", "travel_class": "2A", "passenger": "X"}])
    assert prim(r) == "unsafe_action"


def test_priority_order_respected():
    r = row(status="step_limit_exceeded", labels=("run:step_limit_exceeded", "process:prohibited_action:book_ticket:x"))
    assert prim(r) == "step_limit"
    r = row(task="T04", state=False, process=False, labels=("state:bookings_mismatch", "process:missing_required_call:c6:book_ticket"),
            traj=[call("search_trains", {"source": "XX", "destination": "PUNE", "date": "2026-10-07"}, ok=False, code="INVALID_STATION")])
    assert prim(r) == "missing_booking"


def test_gold_expected_error_codes_are_not_argument_errors():
    task, code = next((t, c["expected_error"]) for t, g in GOLD.items() if t != "_meta"
                      for c in g.get("required_calls", []) if c.get("expected_error") in ARG_ERROR_CODES)
    r = row(task=task, process=False, labels=("process:missing_required_call:c9:x",), traj=[call("x", {}, ok=False, code=code)])
    assert prim(r) == "missing_required_call"


# ---------------------------------------------------------------------------------------------------- secondary tags
def test_secondary_tags():
    traj = [call("search_trains", {"source": "NAG", "destination": "PUNE", "date": "2026-10-07"}, ok=False, code="INVALID_STATION"),
            call("get_fare", {"train_id": "<train_id_from_search>", "travel_class": "3A"}, ok=False, code="INVALID_TRAIN"),
            call("check_availability", {"train_id": "BTB127", "travel_class": "3A"}, obs_data={"seats": 3})]
    r = row(lang="hi", process=False, labels=("process:missing_required_call:c1:x",), traj=traj,
            final="\n".join(["same line"] * 8), attempts=2, done="length")
    _, tags, ev = classify(r, GOLD["T01"])
    for t in ("invalid_train_id_format", "ungrounded_train_id", "parallel_dependent_calls", "guessed_station_code",
              "repetition_or_truncation", "reply_language_mismatch", "no_final_block", "retried"):
        assert t in tags, t
    assert ("search_trains", "INVALID_STATION") in ev["argument_errors"]


def test_grounded_id_and_matching_language_not_tagged():
    traj = [call("search_trains", {"source": "NGP", "destination": "PUNE", "date": "2026-10-07"}, obs_data={"trains": [{"train_id": "BTB127"}]}),
            call("get_fare", {"train_id": "BTB127", "travel_class": "3A"}, turn=2, obs_data={"fare_inr": 1})]
    _, tags, _ = classify(row(lang="hi", traj=traj, final="किराया 1 रुपये है।"), GOLD["T01"])
    assert "ungrounded_train_id" not in tags and "parallel_dependent_calls" not in tags and "reply_language_mismatch" not in tags
    _, tags, _ = classify(row(final=""), GOLD["T01"])
    assert "empty_final_text" in tags


def test_booking_tags_visible_behind_higher_priority_primary():
    # mirrors full-run T11_mr: step limit reached after an unrequested booking (gold T11 expects no booking)
    r = row(task="T11", lang="mr", status="step_limit_exceeded", labels=("run:step_limit_exceeded", "state:bookings_mismatch"),
            state=False, bookings=[{"train_id": "BTB109", "travel_class": "2A", "passenger": "Rahul"}])
    primary, tags, ev = classify(r, GOLD["T11"])
    assert primary == "step_limit" and "unexpected_booking" in tags and ev["extra_bookings"] == [("BTB109", "2A", "rahul")]
    primary, tags, _ = classify(row(task="T04", status="provider_error", error_kind="context_overflow"), GOLD["T04"])
    assert primary == "context_overflow" and "missing_expected_booking" in tags
    _, tags, _ = classify(row(task="T01"), GOLD["T01"])
    assert "unexpected_booking" not in tags and "missing_expected_booking" not in tags


def test_tool_call_as_text_tag():
    # mirrors Llama 3.2 pilot T04_hinglish: two native-format calls joined with '; ' returned by Ollama as plain text
    text = ('{"name":"search_trains","parameters":{"source":"Mumbai","destination":"Pune","date":"2026-10-07"}}; '
            '{"name":"book_ticket","parameters":{"passenger":"Ananya Kulkarni"}}')
    _, tags, _ = classify(row(task="T04", final=text), GOLD["T04"])
    assert "tool_call_as_text" in tags
    _, tags, _ = classify(row(final="The fare is 3565."), GOLD["T01"])
    assert "tool_call_as_text" not in tags


# ---------------------------------------------------------------------------------------------------- real rows
def test_real_pilot_rows_classified_from_evidence():
    rows = [json.loads(l) for l in FIXTURE.read_text(encoding="utf-8").splitlines()]
    got = {r["task_id"]: prim(r) for r in rows}
    assert got == {"T01_en": "format_only", "T02_hi": "step_limit", "T04_en": "missing_booking", "T05_hinglish": "unsafe_action"}
    assert all(r["score"]["task_success"] is False for r in rows)  # official labels untouched


# ---------------------------------------------------------------------------------------------------- item accounting
def test_select_latest_dedupes_and_reports():
    rows = [row(task="T01", status="provider_error", error_kind="rate_limit"), row(task="T01", success=True, parse="ok"),
            row(task="T02", status="runner_error", model_key=None), row(task="T02"),
            row(task="T03", status="runner_error", model_key=None), row(task="T09")]
    for i, r in enumerate(rows):
        r["_source"] = {"file": "f", "line": i + 1}
    sel, rep = select_latest(rows, expected_items("pilot", ["en"]))
    assert sel["T01_en"]["status"] == "completed" and sel["T02_en"]["status"] == "completed"
    assert sel["T03_en"]["status"] == "runner_error"  # only row available
    assert rep["missing_items"] == ["T04_en", "T05_en"] and rep["unexpected_items"] == ["T09_en"]
    assert rep["items_with_multiple_rows"] == ["T01_en", "T02_en"] and rep["complete"] is False
    assert len(sel) == 3  # only expected items are selected


def test_one_logical_run_must_have_one_model():
    rows = [row(model_key="a"), row(task="T02", model_key="b")]
    for r in rows:
        r["_source"] = {"file": "f", "line": 1}
    with pytest.raises(ValueError):
        select_latest(rows, expected_items("pilot", ["en"]))


def write_run(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pilot_rows(success_tasks=(), prompt_hash="p", model_key="local_x"):
    return [row(task=f"T{i:02d}", lang=l, success=f"T{i:02d}" in success_tasks, parse="ok" if f"T{i:02d}" in success_tasks else "missing_block",
                labels=() if f"T{i:02d}" in success_tasks else ("final_answer:missing_block",), prompt_hash=prompt_hash, model_key=model_key)
            for i in range(1, 6) for l in ("en", "hinglish", "hi", "mr")]


def test_main_end_to_end_across_two_files_inputs_unchanged(tmp_path):
    rows = pilot_rows()
    orig = tmp_path / "run.jsonl"
    h1 = write_run(orig, rows[:18] + [row(task="T05", lang="hi", status="provider_error", error_kind="timeout")])
    copy = tmp_path / "run_resume1.jsonl"
    h2 = write_run(copy, rows[:18] + [row(task="T05", lang="hi", status="provider_error", error_kind="timeout")] + rows[18:])
    out = tmp_path / "res"
    assert observe_run.main(["--run-file", str(orig), "--run-file", str(copy), "--split", "pilot", "--languages", "en", "hinglish", "hi", "mr", "--out", str(out)]) == 0
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["integrity"]["complete"] and s["official"]["items"] == 20 and s["official"]["scored"] == 20
    obs = [json.loads(l) for l in (out / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(obs) == 20 and len({o["task_id"] for o in obs}) == 20
    assert next(o for o in obs if o["task_id"] == "T05_hi")["source_file"].endswith("run_resume1.jsonl")
    assert hashlib.sha256(orig.read_bytes()).hexdigest() == h1 and hashlib.sha256(copy.read_bytes()).hexdigest() == h2
    assert (out / "summary.md").read_text(encoding="utf-8").startswith("# Run summary")
    with pytest.raises(SystemExit):  # never overwrite
        observe_run.main(["--run-file", str(orig), "--split", "pilot", "--languages", "en", "hinglish", "hi", "mr", "--out", str(out)])


def test_main_exit_code_2_when_incomplete(tmp_path):
    f = tmp_path / "run.jsonl"
    write_run(f, pilot_rows()[:10])
    assert observe_run.main(["--run-file", str(f), "--split", "pilot", "--languages", "en", "hinglish", "hi", "mr", "--out", str(tmp_path / "res")]) == 2


# ---------------------------------------------------------------------------------------------------- manifest
def test_run_manifest_records_hashes_and_detects_changed_benchmark(tmp_path):
    (tmp_path / "benchmark").mkdir()
    data = tmp_path / "benchmark" / "gold.json"
    data.write_text("{}", encoding="utf-8")
    run = tmp_path / "x.jsonl"
    write_run(run, pilot_rows()[:2])
    (tmp_path / "x.quota.json").write_text('{"requests": 4}', encoding="utf-8")
    prerun = {"git_commit": "abc", "file_sha256": {"benchmark/gold.json": hashlib.sha256(b"{}").hexdigest()}}
    m = run_manifest.build(prerun, [run], root=tmp_path)
    assert m["benchmark_files_unchanged_since_prerun"] is True
    assert m["run_files"][0]["rows"] == 2 and m["run_files"][1]["quota"] == {"requests": 4}
    data.write_text('{"x": 1}', encoding="utf-8")
    assert run_manifest.build(prerun, [run], root=tmp_path)["changed_since_prerun"] == ["benchmark/gold.json"]
    out = tmp_path / "x.manifest.json"
    out.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit):
        run_manifest.main(["--prerun", str(tmp_path / "x.quota.json"), "--run-file", str(run), "--out", str(out)])


# ---------------------------------------------------------------------------------------------------- comparison
def make_result(tmp_path, name, rows):
    f = tmp_path / f"{name}.jsonl"
    write_run(f, rows)
    out = tmp_path / "results" / name
    observe_run.main(["--run-file", str(f), "--split", "pilot", "--languages", "en", "hinglish", "hi", "mr", "--out", str(out)])
    return out


def test_compare_paired_counts_and_deterministic_bootstrap(tmp_path):
    a = make_result(tmp_path, "a", pilot_rows(success_tasks=("T01", "T02"), model_key="m3b"))
    b = make_result(tmp_path, "b", pilot_rows(success_tasks=("T02", "T03", "T04"), model_key="m7b"))
    out = tmp_path / "cmp"
    assert compare_runs.main([str(a), str(b), "--out", str(out)]) == 0
    c = json.loads((out / "comparison.json").read_text(encoding="utf-8"))
    p = c["paired"]["a vs b"]
    assert (p["both_success"], p["only_a"], p["only_b"], p["both_fail"]) == (4, 4, 8, 4)
    assert p["diff_b_minus_a"] == pytest.approx(0.2)
    assert c["runs"]["a"]["task_success"] == 8 and c["runs"]["b"]["task_success"] == 12
    out2 = tmp_path / "cmp2"
    compare_runs.main([str(a), str(b), "--out", str(out2)])
    assert json.loads((out2 / "comparison.json").read_text(encoding="utf-8"))["paired"] == c["paired"]


def test_compare_self_has_zero_difference(tmp_path):
    a = make_result(tmp_path, "a", pilot_rows(success_tasks=("T01",)))
    b = make_result(tmp_path, "b", pilot_rows(success_tasks=("T01",)))
    compare_runs.main([str(a), str(b), "--out", str(tmp_path / "cmp")])
    p = json.loads((tmp_path / "cmp" / "comparison.json").read_text(encoding="utf-8"))["paired"]["a vs b"]
    assert p["diff_b_minus_a"] == 0 and p["bootstrap_95ci_diff"] == [0.0, 0.0]


def test_compare_refuses_incomparable_runs(tmp_path):
    a = make_result(tmp_path, "a", pilot_rows())
    b = make_result(tmp_path, "b", pilot_rows(prompt_hash="other"))
    assert compare_runs.main([str(a), str(b), "--out", str(tmp_path / "c1")]) == 2
    c = make_result(tmp_path, "c", pilot_rows()[:12])  # incomplete
    assert compare_runs.main([str(a), str(c), "--out", str(tmp_path / "c2")]) == 2
    assert not (tmp_path / "c1").exists() and not (tmp_path / "c2").exists()


def test_dataset_hashes_read_from_run_manifest_and_compared(tmp_path, capsys):
    """Regression: run_manifest nests file hashes under 'prerun'; observe_run must read them so compare can verify."""
    def result(name, gold_hash):
        f = tmp_path / f"{name}.jsonl"
        write_run(f, pilot_rows())
        m = tmp_path / f"{name}.manifest.json"
        m.write_text(json.dumps({"prerun": {"file_sha256": {"benchmark/gold_labels.json": gold_hash}}}), encoding="utf-8")
        out = tmp_path / "results" / name
        observe_run.main(["--run-file", str(f), "--split", "pilot", "--languages", "en", "hinglish", "hi", "mr", "--manifest", str(m), "--out", str(out)])
        return out
    a, b, c = result("a", "h1"), result("b", "h1"), result("c", "h2")
    assert json.loads((a / "summary.json").read_text(encoding="utf-8"))["dataset_sha256"] == {"benchmark/gold_labels.json": "h1"}
    assert compare_runs.main([str(a), str(b), "--out", str(tmp_path / "ab")]) == 0
    assert "dataset hashes not recorded" not in capsys.readouterr().out
    assert compare_runs.main([str(a), str(c), "--out", str(tmp_path / "ac")]) == 2  # differing benchmark data refused


def test_compare_excludes_unscored_items_from_paired_stats(tmp_path, capsys):
    a_rows = pilot_rows(success_tasks=("T01",))
    a_rows[0] = row(task="T01", lang="en", status="provider_error", error_kind="context_overflow")  # T01_en unscored in A
    a = make_result(tmp_path, "a", a_rows)
    b = make_result(tmp_path, "b", pilot_rows(success_tasks=("T01",)))
    assert compare_runs.main([str(a), str(b), "--out", str(tmp_path / "c")]) == 0
    c = json.loads((tmp_path / "c" / "comparison.json").read_text(encoding="utf-8"))
    assert c["runs"]["a"]["scored"] == 19 and c["runs"]["a"]["not_scored"] == ["T01_en"] and c["runs"]["a"]["task_success"] == 3
    assert c["runs"]["b"]["task_success"] == 4 and c["paired"]["a vs b"]["items"] == 19
    assert "not scored" in capsys.readouterr().out


def test_compare_warns_on_decoding_differences(tmp_path, capsys):
    a = make_result(tmp_path, "a", pilot_rows())
    rows = pilot_rows()
    for r in rows:
        r["adapter_settings"] = dict(r["adapter_settings"], num_ctx=4096)
    b = make_result(tmp_path, "b", rows)
    assert compare_runs.main([str(a), str(b), "--out", str(tmp_path / "c")]) == 0
    assert "decoding settings differ" in capsys.readouterr().out


# ---------------------------------------------------------------------------------------------------- prerun snapshot
def test_prerun_snapshot_records_identity_and_refuses_overwrite(tmp_path, monkeypatch):
    import httpx
    from analysis import prerun_snapshot

    def handler(request):
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.40.18"})
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": ["completion", "tools"]})
        return httpx.Response(200, json={"models": [{"name": "llama3.2:3b", "digest": "a80c", "details": {"quantization_level": "Q4_K_M"}}]})
    client = httpx.Client(transport=httpx.MockTransport(handler))
    snap = prerun_snapshot.build("local_llama32_3b", "pilot", tmp_path / "x.jsonl", "cmd", client=client,
                                 languages=["en", "hinglish", "hi", "mr"])
    assert snap["model_digest"] == "a80c" and snap["ollama_version"] == "0.40.18" and snap["expected_items"] == 20
    assert snap["model_config"]["model"] == "llama3.2:3b" and "benchmark/gold_labels.json" in snap["file_sha256"]
    (tmp_path / "x.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(SystemExit):
        prerun_snapshot.main(["--model", "local_llama32_3b", "--split", "pilot", "--run-file", str(tmp_path / "x.jsonl"), "--command", "c"])


# ---------------------------------------------------------------------------------------------------- audit C-02: 375 items
def test_expected_items_cover_all_375_items_and_the_old_200():
    from analysis.observe_run import LANGUAGES
    assert LANGUAGES == ["en", "hinglish", "hi", "mr", "gu"]
    full = expected_items("full", LANGUAGES)
    assert len(full) == 375 and full[0] == "T01_en" and full[-1] == "T75_gu" and "T75_gu" in full
    old = expected_items("midsem", ["en", "hinglish", "hi", "mr"])  # the historical 200-item runs
    assert len(old) == 200 and old[-1] == "T50_mr"


def test_prerun_snapshot_counts_languages_and_hashes_gujarati(tmp_path):
    import httpx
    from analysis import prerun_snapshot

    def handler(request):
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.40.18"})
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": ["completion", "tools"]})
        return httpx.Response(200, json={"models": [{"name": "llama3.2:3b", "digest": "a80c", "details": {}}]})
    client = httpx.Client(transport=httpx.MockTransport(handler))
    snap = prerun_snapshot.build("local_llama32_3b", "full", tmp_path / "x.jsonl", "cmd", client=client)
    assert snap["expected_items"] == 375 and snap["languages"] == ["en", "hinglish", "hi", "mr", "gu"]
    assert "benchmark/languages/gu.jsonl" in snap["file_sha256"] and "benchmark/languages/human_review.json" in snap["file_sha256"]


def test_context_overflow_status_is_classified_and_counted_as_scored_failure():
    r = row(task="T04", status="context_overflow", error_kind="context_overflow", labels=("run:context_overflow", "final_answer:missing_block"))
    primary, tags, _ = classify(r, GOLD["T04"])
    assert primary == "context_overflow"
    assert r["score"]["scored"] is True  # context_overflow is a scored model failure since audit I-04


def test_output_truncated_is_its_own_primary_category():
    r = row(task="T04", status="output_truncated", error_kind="output_truncated", labels=("run:output_truncated", "final_answer:missing_block"))
    assert classify(r, GOLD["T04"])[0] == "output_truncated" and "output_truncated" in PRIMARY_ORDER


def test_prerun_snapshot_records_capabilities_and_effective_think(tmp_path):
    import httpx
    from analysis import prerun_snapshot

    def handler(request):
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.40.18"})
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": ["completion", "tools", "thinking"]})
        return httpx.Response(200, json={"models": [{"name": "qwen2.5:7b", "digest": "d7", "details": {}}]})
    info = prerun_snapshot.ollama_model_info("http://x", "qwen2.5:7b", httpx.Client(transport=httpx.MockTransport(handler)), think=False)
    assert info["capabilities"] == ["completion", "tools", "thinking"] and info["thinking_capable"] is True
    assert info["think_config"] is False and info["think_effective"] is False
    snap = prerun_snapshot.build("local_qwen25_7b", "pilot", tmp_path / "x.jsonl", "cmd", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert snap["model_config"]["think"] is False and snap["model_config"]["max_tokens"] == 2048 and snap["model_config"]["num_ctx"] == 16384


def test_prerun_snapshot_refuses_a_model_without_the_tools_capability(tmp_path):
    import httpx
    from analysis import prerun_snapshot

    def handler(request):
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.40.18"})
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": ["completion"]})
        return httpx.Response(200, json={"models": [{"name": "llama3.2:3b", "digest": "a80c", "details": {}}]})
    with pytest.raises(SystemExit, match="tools"):
        prerun_snapshot.build("local_llama32_3b", "pilot", tmp_path / "x.jsonl", "cmd", client=httpx.Client(transport=httpx.MockTransport(handler)))


# ---------------------------------------------------------------------------------------------------- lenient (headline) and strict
def lenient_row(task, lang, lenient_ok, strict_ok, rules=(), unparsed=False):
    r = row(task=task, lang=lang, success=lenient_ok, status="malformed_output" if unparsed else "completed",
            error_kind="unparsed_model_output" if unparsed else None)
    r["score"]["format_recoveries"] = [{"stage": "final_answer", "rule": x} for x in rules]
    r["score"]["lenient_used"] = bool(rules)
    r["score_strict"] = {**r["score"], "task_success": strict_ok, "format_recoveries": [], "lenient_used": False}
    return r


def test_summary_reports_lenient_headline_strict_recoveries_and_transport_category(tmp_path):
    rows = [lenient_row("T01", "en", True, False, ["closing_tag_missing"]), lenient_row("T01", "hinglish", True, True),
            lenient_row("T01", "hi", False, False, unparsed=True), lenient_row("T01", "mr", True, False, ["text_tool_call", "status_spelling"])]
    f = tmp_path / "new.jsonl"
    write_run(f, rows)
    out = tmp_path / "res"
    observe_run.main(["--run-file", str(f), "--split", "pilot", "--languages", "en", "hinglish", "hi", "mr", "--out", str(out)])
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))["strict_vs_lenient"]
    assert s["has_strict_scores"] and s["lenient"]["task_success"] == 3 and s["strict"]["task_success"] == 1
    assert s["items_with_recovery"] == 2 and s["recovery_rules"] == {"closing_tag_missing": 1, "text_tool_call": 1, "status_spelling": 1}
    assert s["items_with_recovery_by_language"] == {"en": 1, "mr": 1}
    assert s["unparsed_model_output"] == {"total": 1, "by_language": {"hi": 1}}
    md = (out / "summary.md").read_text(encoding="utf-8")
    assert "Lenient (headline) and strict (sensitivity)" in md and "reply discarded by the serving layer" in md


def test_runs_without_a_strict_score_count_strict_as_equal(tmp_path):
    f = tmp_path / "old.jsonl"
    write_run(f, [row(task="T01", lang="en", success=True), row(task="T01", lang="hi", success=False)])
    out = tmp_path / "res"
    observe_run.main(["--run-file", str(f), "--split", "pilot", "--languages", "en", "hi", "--out", str(out)])
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))["strict_vs_lenient"]
    assert not s["has_strict_scores"] and s["lenient"] == s["strict"] and s["items_with_recovery"] == 0
    assert "predates benchmark 2.1.0" in (out / "summary.md").read_text(encoding="utf-8")


def test_compare_runs_carries_strict_and_recovery_columns(tmp_path):
    tasks = [f"T{i:02d}" for i in range(1, 6)]
    a = make_result(tmp_path, "a", [lenient_row(t, l, t == "T01", False, ["closing_tag_missing"] if t == "T01" else []) for t in tasks for l in ("en", "hinglish", "hi", "mr")])
    b = make_result(tmp_path, "b", [lenient_row(t, l, t == "T01", t == "T01") for t in tasks for l in ("en", "hinglish", "hi", "mr")])
    assert compare_runs.main([str(a), str(b), "--out", str(tmp_path / "c")]) == 0
    runs = json.loads((tmp_path / "c" / "comparison.json").read_text(encoding="utf-8"))["runs"]
    assert runs["a"]["task_success"] == 4 and runs["a"]["task_success_strict"] == 0 and runs["a"]["items_with_recovery"] == 4
    assert runs["b"]["task_success"] == 4 and runs["b"]["task_success_strict"] == 4 and runs["b"]["items_with_recovery"] == 0
    assert "task_success_strict" in (tmp_path / "c" / "comparison.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------------------------------- Ollama server version in snapshot, manifest, summary
def _snapshot_handler(version, caps=("completion", "tools")):
    import httpx

    def handler(request):
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": version})
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": list(caps)})
        return httpx.Response(200, json={"models": [{"name": "llama3.2:3b", "digest": "a80c", "details": {}}]})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_prerun_snapshot_refuses_an_old_server_and_records_the_version_of_a_good_one(tmp_path):
    from analysis import prerun_snapshot
    for old in ("0.40.13", "0.40.3", "garbage"):
        with pytest.raises(SystemExit, match="older than 0.40.18"):
            prerun_snapshot.build("local_llama32_3b", "pilot", tmp_path / "x.jsonl", "cmd", client=_snapshot_handler(old))
    snap = prerun_snapshot.build("local_llama32_3b", "pilot", tmp_path / "x.jsonl", "cmd", client=_snapshot_handler("0.40.18"))
    assert snap["ollama_version"] == "0.40.18" and snap["ollama_min_version"] == "0.40.18"


def test_manifest_records_the_server_version_and_flags_a_mismatch(tmp_path):
    def rows(version):
        return [{"task_id": f"T0{i}_en", "status": "completed", "started_at": "2026-11-24T00:00:00+00:00", "finished_at": "2026-11-24T00:00:05+00:00",
                 "adapter_settings": {"ollama_version": version}} for i in (1, 2)]
    f = tmp_path / "run.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in rows("0.40.18")), encoding="utf-8")
    m = run_manifest.build({"file_sha256": {}, "ollama_version": "0.40.18"}, [f], root=tmp_path)
    assert m["ollama_version"] == "0.40.18" and m["ollama_versions_in_rows"] == {"0.40.18": 2} and m["ollama_version_consistent"] is True
    f.write_text("".join(json.dumps(r) + "\n" for r in rows("0.40.13")), encoding="utf-8")
    m = run_manifest.build({"file_sha256": {}, "ollama_version": "0.40.18"}, [f], root=tmp_path)
    assert m["ollama_version_consistent"] is False and m["ollama_versions_in_rows"] == {"0.40.13": 2}
    m = run_manifest.build({"file_sha256": {}}, [f], root=tmp_path)           # a non-Ollama run: nothing to compare
    assert m["ollama_version"] is None and m["ollama_version_consistent"] is None


def test_summary_lists_the_server_versions_seen(tmp_path):
    settings = {"temperature": 0, "seed": 42, "num_ctx": 16384, "max_tokens": 2048, "model_digest": "d", "ollama_version": "0.40.18"}
    tasks = [f"T{i:02d}" for i in range(1, 6)]
    out = make_result(tmp_path, "v", [row(task=t, lang=l, settings=settings) for t in tasks for l in ("en", "hinglish", "hi", "mr")])
    assert json.loads((out / "summary.json").read_text(encoding="utf-8"))["ollama_versions"] == ["0.40.18"]


# ---------------------------------------------------------------------------------------------------- Ollama server env in the pre-run snapshot
def _server_log(tmp_path, parallel="1", loaded="1", extra_old=True):
    lines = []
    if extra_old:  # an earlier server start in the same (appended) log: only the LAST config line counts
        lines.append('time=2026-11-24T15:29:11.236+05:30 level=INFO source=routes.go:2484 msg="server config" env="map[OLLAMA_MAX_LOADED_MODELS:0 OLLAMA_NUM_PARALLEL:0 OLLAMA_FLASH_ATTENTION:false]"')
    lines.append('time=2026-11-24T18:00:00.000+05:30 level=INFO source=routes.go:2484 msg="server config" env="map[HTTPS_PROXY: OLLAMA_CONTEXT_LENGTH:0 '
                 f'OLLAMA_FLASH_ATTENTION:false OLLAMA_KEEP_ALIVE:5m0s OLLAMA_KV_CACHE_TYPE: OLLAMA_MAX_LOADED_MODELS:{loaded} OLLAMA_MAX_QUEUE:512 OLLAMA_NUM_PARALLEL:{parallel}]"')
    p = tmp_path / "serve.log"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_server_env_is_read_from_the_last_config_line_of_the_server_log(tmp_path):
    from analysis import prerun_snapshot
    e = prerun_snapshot.server_env(_server_log(tmp_path))
    assert e["OLLAMA_NUM_PARALLEL"] == "1" and e["OLLAMA_MAX_LOADED_MODELS"] == "1" and e["planned_ok"] is True
    assert e["OLLAMA_FLASH_ATTENTION"] == "false" and e["OLLAMA_KV_CACHE_TYPE"] == "" and e["OLLAMA_KEEP_ALIVE"] == "5m0s" and e["logged_at"].startswith("2026-11-24T18:00")
    assert prerun_snapshot.server_env(_server_log(tmp_path, parallel="4"))["planned_ok"] is False
    assert prerun_snapshot.server_env(_server_log(tmp_path, loaded="0"))["planned_ok"] is False
    assert prerun_snapshot.server_env(tmp_path / "missing.log") is None
    (tmp_path / "empty.log").write_text("nothing here\n", encoding="utf-8")
    assert prerun_snapshot.server_env(tmp_path / "empty.log") is None


def test_prerun_snapshot_records_both_server_variables_and_refuses_a_wrong_server(tmp_path, monkeypatch):
    from analysis import prerun_snapshot
    snap = prerun_snapshot.build("local_llama32_3b", "pilot", tmp_path / "x.jsonl", "cmd", client=_snapshot_handler("0.40.18"), server_log=_server_log(tmp_path))
    assert snap["server_env"]["OLLAMA_NUM_PARALLEL"] == "1" and snap["server_env"]["OLLAMA_MAX_LOADED_MODELS"] == "1"
    manifest_rows = tmp_path / "r.jsonl"
    manifest_rows.write_text(json.dumps({"task_id": "T01_en", "status": "completed", "started_at": "2026-11-24T00:00:00+00:00", "finished_at": "2026-11-24T00:00:01+00:00"}) + "\n", encoding="utf-8")
    assert run_manifest.build(snap, [manifest_rows])["ollama_server_env"]["OLLAMA_NUM_PARALLEL"] == "1"
    monkeypatch.setattr(prerun_snapshot, "ollama_model_info", lambda *a, **k: {"ollama_version": "0.40.18", "capabilities": ["completion", "tools"]})
    for log in (_server_log(tmp_path, parallel="4"), tmp_path / "missing.log"):
        with pytest.raises(SystemExit):
            prerun_snapshot.main(["--model", "local_llama32_3b", "--split", "pilot", "--run-file", str(tmp_path / "y.jsonl"), "--command", "c", "--server-log", str(log)])
