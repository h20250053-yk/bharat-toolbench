"""Offline tests for analysis/format_recovery.py (format-recovery ANALYSIS; never an official score)."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from analysis import format_recovery as fr
from evaluation.final_answer import CLOSE, OPEN, parse_final_answer

ROOT = Path(__file__).resolve().parent.parent
GOLD = json.loads((ROOT / "benchmark" / "gold_labels.json").read_text(encoding="utf-8"))
FIXTURE = ROOT / "tests" / "fixtures" / "qwen25_3b_pilot_rows.jsonl"
FARE = GOLD["T01"]["final_answer"]["fare_inr"]
FARE_CALL = {"event": "tool_call", "turn": 1, "tool": "get_fare", "arguments": {"train_id": "BTB103", "travel_class": "2A"},
             "observation": {"ok": True, "data": {"train_id": "BTB103", "travel_class": "2A", "fare_inr": FARE}, "error": None}}


def row(text, task="T01", lang="en", status="completed", traj=(FARE_CALL,), bookings=(), query="What is the fare for 2A class on train BTB103?",
        process=True, state=True, finish="stop"):
    return {"task_id": f"{task}_{lang}", "semantic_task_id": task, "language": lang, "status": status, "query": query,
            "final_text": text, "trajectory": [copy.deepcopy(t) for t in traj], "state_snapshot": {"bookings": list(bookings)},
            "raw_log": [{"type": "model_response", "finish_reason": finish}], "_source": {"file": "f.jsonl", "line": 1},
            "model_key": "local_x",
            "score": {"scored": status not in ("provider_error", "runner_error"), "task_success": False, "final_answer_parse": "missing_block",
                      "process_success": process, "state_success": state, "failure_labels": ["final_answer:missing_block"]}}


def audit(r, task=None):
    return fr.audit_candidate(r, GOLD[task or r["semantic_task_id"]])


# ---------------------------------------------------------------------------------------------------- recovery paths
def test_prose_extraction_recovers_explicit_answer_and_preserves_original():
    text = f"The fare for 2A class on train BTB103 is {FARE} INR."
    rec = audit(row(text))
    assert rec["classification"] == "format_only_recoverable" and rec["recovery_method"] == "prose_extraction"
    assert rec["original_final_text"] == text
    assert rec["original_final_text_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert rec["recovered_final_text"].startswith(text) and rec["recovered_parse"] == "ok"
    assert parse_final_answer(rec["recovered_final_text"])["natural_text"] == text.strip()
    assert rec["recovered_score"]["task_success"] is True and rec["official"]["task_success"] is False


def test_wrapper_repair_appends_only_the_closing_tag():
    block = json.dumps({"status": "success", "selected_train": "BTB103", "selected_class": "2A", "booking_ids": [],
                        "requested_passengers": [], "notes": "model note"})
    text = f"The fare is {FARE}.\n{OPEN}\n{block}\n"
    rec = audit(row(text))
    assert rec["recovery_method"] == "wrapper_repair" and rec["recovered_final_text"] == text.rstrip() + "\n" + CLOSE
    assert parse_final_answer(rec["recovered_final_text"])["answer"]["notes"] == "model note"  # model's own JSON, untouched
    assert rec["classification"] == "format_only_recoverable"


def test_wrapper_repair_not_used_for_incomplete_json():
    assert fr.wrapper_repair(f"x\n{OPEN}\n{{\"status\": \"success\",") is None


def test_wrong_decision_is_not_reinterpreted_as_correct():
    rec = audit(row("Cannot complete. Cannot book this ticket now."))  # gold T01 is success
    assert rec["classification"] == "task_failure" and "status:expected_success_got_cannot_complete" in rec["reason"]


# ---------------------------------------------------------------------------------------------------- no fabrication
def test_recovered_fields_are_all_stated_in_the_original_text():
    bookings = [{"booking_id": "BK0001", "train_id": "BTB124", "travel_class": "SL", "passenger": "Aditi Rao"}]
    traj = [{"event": "tool_call", "turn": 1, "tool": "book_ticket", "arguments": {"train_id": "BTB124", "travel_class": "SL", "passenger": "Aditi Rao"},
             "observation": {"ok": True, "data": {"booking_id": "BK0001", "fare_inr": 450}, "error": None}}]
    text = "Aditi Rao, you have successfully booked a sleeper (SL) ticket on train BTB124. Your booking ID is BK0001. Fare 450 INR."
    r = row(text, task="T27", traj=traj, bookings=bookings, query="Book a sleeper (SL) ticket on train BTB124 ... for Aditi Rao.")
    rec = audit(r)
    f = rec["extracted_fields"]
    assert f["selected_train"] in text and f["selected_class"] in text
    assert all(b in text for b in f["booking_ids"]) and all(p in text for p in f["requested_passengers"])
    assert f["notes"] == fr.NOTES_MARKER and "answer_values" not in f


def test_extraction_never_reads_gold():
    r = row(f"The fare for 2A class on train BTB103 is {FARE} INR.")
    fake_gold = copy.deepcopy(GOLD["T01"])
    fake_gold["final_state"]["status"] = "cannot_complete"
    a, b = fr.audit_candidate(copy.deepcopy(r), GOLD["T01"]), fr.audit_candidate(copy.deepcopy(r), fake_gold)
    assert a["extracted_fields"] == b["extracted_fields"] and a["recovered_final_text"] == b["recovered_final_text"]
    assert a["classification"] == "format_only_recoverable" and b["classification"] == "task_failure"  # only the scorer differs


# ---------------------------------------------------------------------------------------------------- task_failure rules
@pytest.mark.parametrize("kwargs,needle", [
    (dict(text="", status="completed"), "no final response"),
    (dict(text="anything", status="malformed_output"), "run status"),
    (dict(text="The fare on train BTB999 is 3565 INR."), "train id(s) ['BTB999']"),
    (dict(text="The fare for 2A on train BTB103 is 9999 INR."), "amount(s) [9999.0]"),
    (dict(text="Your ticket has been booked."), "claims a booking"),
    (dict(text="Done. Your booking ID is BK0007."), "BK0007"),
    (dict(text="Let's find the trains available for your journey."), "unfinished plan"),
    (dict(text="Cannot complete. There are no trains available for this route."), "says no trains"),
    (dict(text="The train ID you provided is invalid.", query="Please cancel my ticket with booking ID BK0042."), "user's train id"),
])
def test_task_failure_rules(kwargs, needle):
    text = kwargs.pop("text")
    rec = audit(row(text, **kwargs))
    assert rec["classification"] == "task_failure" and needle in rec["reason"], rec["reason"]


def test_supported_negative_claim_is_allowed():
    traj = [{"event": "tool_call", "turn": 1, "tool": "get_train_details", "arguments": {"train_id": "BTB150"},
             "observation": {"ok": False, "data": None, "error": {"code": "INVALID_TRAIN", "message": "m"}}}]
    assert fr.unsupported_negative_claims(row("The train ID you provided is not recognized.", task="T28", traj=traj,
                                              query="Which stations does train BTB150 stop at?")) == []


# ---------------------------------------------------------------------------------------------------- insufficient_evidence rules
@pytest.mark.parametrize("kwargs,needle", [
    (dict(text=f"2A costs {FARE} INR and 3A is cheaper on BTB103."), "several travel classes"),
    (dict(text="The train ID is not recognized. Could you please provide the correct train ID?",
          traj=({"event": "tool_call", "turn": 1, "tool": "get_fare", "arguments": {"train_id": "BTB103", "travel_class": "2A"},
                 "observation": {"ok": False, "data": None, "error": {"code": "INVALID_TRAIN", "message": "m"}}},)), "conflicting status cues"),
    (dict(text="I found BTB103 with seats. Shall I book a ticket for Rohan?", query="Book a 2A ticket on BTB103 for Rohan Mehta."), "asks permission"),
    (dict(text=f"The fare is {FARE} INR.", finish="length"), "cut off"),
    (dict(text="Train BTB111 runs on Tuesday.", task="T06", traj=(), query="On which days does train BTB111 leave New Delhi?"),
     "structured answer_values"),
])
def test_insufficient_evidence_rules(kwargs, needle):
    text = kwargs.pop("text")
    rec = audit(row(text, **kwargs))
    assert rec["classification"] == "insufficient_evidence" and needle in rec["reason"], rec["reason"]
    assert rec["recovered_final_text"] is None


def test_booking_not_stated_is_insufficient():
    bookings = [{"booking_id": "BK0001", "train_id": "BTB104", "travel_class": "SL", "passenger": "Leela Das"}]
    traj = [{"event": "tool_call", "turn": 1, "tool": "book_ticket", "arguments": {"train_id": "BTB104", "travel_class": "SL", "passenger": "Leela Das"},
             "observation": {"ok": True, "data": {"booking_id": "BK0001"}, "error": None}}]
    rec = audit(row("Tickets are confirmed for Leela Das on BTB104.", task="T48", traj=traj, bookings=bookings,
                    query="Book sleeper (SL) tickets on train BTB104 ... for Leela Das ..."))
    assert rec["classification"] == "insufficient_evidence" and "not stated in the reply" in rec["reason"]


def test_non_string_passenger_argument_does_not_crash():
    # regression: Llama 3.2 full run passed passenger as a list in book_ticket calls
    traj = [FARE_CALL, {"event": "tool_call", "turn": 2, "tool": "book_ticket",
                        "arguments": {"train_id": "BTB103", "travel_class": "2A", "passenger": ["A B", "C D"]},
                        "observation": {"ok": False, "data": None, "error": {"code": "INVALID_ARGUMENTS", "message": "m"}}}]
    rec = audit(row(f"The fare for 2A class on train BTB103 is {FARE} INR.", traj=traj))
    assert rec["classification"] in fr.CATEGORIES and rec["extracted_fields"]["requested_passengers"] == []


def test_status_only_passes_carry_a_caveat():
    traj = [{"event": "tool_call", "turn": 1, "tool": "book_ticket", "arguments": {"train_id": "BTB101"},
             "observation": {"ok": False, "data": None, "error": {"code": "INVALID_TRAIN", "message": "m"}}}]
    rec = audit(row("Cannot complete. There was an issue with the booking ID.", task="T45", traj=traj,
                    query="Please cancel my ticket with booking ID BK0042."))
    assert rec["classification"] == "format_only_recoverable" and rec["caveats"]


# ---------------------------------------------------------------------------------------------------- accounting
def test_build_denominators_and_universe_reconcile():
    ok = row(f"The fare for 2A class on train BTB103 is {FARE} INR.", lang="en")
    off = row("x", lang="hi")
    off["score"].update(task_success=True, final_answer_parse="ok", failure_labels=[])
    proc_fail = row("y", lang="mr", process=False)
    unscored = row("", lang="hinglish", status="provider_error")
    unscored["score"].update(scored=False, task_success=None)
    rows = {r["task_id"]: r for r in (ok, off, proc_fail, unscored)}
    records, s = fr.build(rows, GOLD, {"T01": "single_tool"})
    assert s["official"]["scored_denominator"] == 3 and s["official"]["not_scored"] == ["T01_hinglish"]
    assert s["universe"]["candidates"] == 1 and s["universe"]["excluded_process_failed"] == 1
    assert [r["task_id"] for r in records] == ["T01_en"] and s["candidate_ids_unique"]
    assert s["format_recovery_score_strict"]["successes"] == 1
    assert s["format_recovery_score_extended"]["successes"] == 2 == s["format_recovery_score_conservative"]["successes"]
    assert sum(s["classification"].values()) == s["universe"]["candidates"]


def test_real_pilot_row_t01_en_is_recoverable():
    rows = [json.loads(l) for l in FIXTURE.read_text(encoding="utf-8").splitlines()]
    r = next(x for x in rows if x["task_id"] == "T01_en")
    r["_source"] = {"file": "fixture", "line": 1}
    rec = fr.audit_candidate(r, GOLD["T01"])
    assert rec["classification"] == "format_only_recoverable" and rec["original_final_text"] == r["final_text"]


def test_main_refuses_overwrite_and_leaves_input_unchanged(tmp_path):
    rows = []
    for i in range(1, 6):
        for lang in ("en", "hinglish", "hi", "mr"):
            r = row(f"The fare for 2A class on train BTB103 is {FARE} INR.", task=f"T{i:02d}", lang=lang)
            r.pop("_source")
            rows.append(r)
    f = tmp_path / "run.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    before = hashlib.sha256(f.read_bytes()).hexdigest()
    out = tmp_path / "rec"
    assert fr.main(["--run-file", str(f), "--split", "pilot", "--out", str(out)]) == 0
    assert hashlib.sha256(f.read_bytes()).hexdigest() == before
    for name in ("recovery_candidates.jsonl", "recovery_summary.json", "recovery_summary.md", "recovery_diff.md"):
        assert (out / name).exists()
    with pytest.raises(SystemExit):
        fr.main(["--run-file", str(f), "--split", "pilot", "--out", str(out)])
