"""Adversarial scorer trajectories (plan section 15 'scorer validation gate': >= 12 hand-built trajectories).
Every trajectory is executed in the real (deterministic) environment; nothing here calls a model or an API."""
import copy
import json

import pytest

from benchmark.build_gold import GOLD_PATH
from evaluation.canonical import canon_class, canon_train_ids, dates_in, numbers_in, times_in
from evaluation.final_answer import CLOSE, OPEN, parse_final_answer
from evaluation.scorer import score
from evaluation.selfcheck import execute, final_json, final_text, gold_calls, gold_for, ideal_result

TASKS = sorted(k for k in json.loads(GOLD_PATH.read_text(encoding="utf-8")) if not k.startswith("_"))  # every task (T01-T75)


def run(tid, calls, *, natural=None, raw_json=None, run_status="completed", **json_override):
    """Execute `calls`, write a final answer (JSON from gold unless overridden) and score it."""
    traj, snap = execute(calls)
    obj = None if raw_json is not None else final_json(tid, snap, **json_override)
    row = {"task_id": f"{tid}_en", "semantic_task_id": tid, "language": "en", "status": run_status, "trajectory": traj,
           "final_text": final_text(tid, obj, natural=natural, raw_json=raw_json), "state_snapshot": snap}
    return score(row, gold_for(tid), snap)


def no_json(tid, calls, natural):
    traj, snap = execute(calls)
    row = {"task_id": f"{tid}_en", "semantic_task_id": tid, "language": "en", "status": "completed",
           "trajectory": traj, "final_text": natural, "state_snapshot": snap}
    return score(row, gold_for(tid), snap)


def has(s, prefix):
    return any(l.startswith(prefix) for l in s["failure_labels"])


# ===================================================================== the known cases from the review
def test_t13_bookings_in_other_order_pass():
    c = gold_calls("T13")
    c[-2], c[-1] = c[-1], c[-2]
    s = run("T13", c)
    assert s["task_success"], s["failure_labels"]


def test_t08_allowed_argument_alternatives_pass():
    unwindowed = [(t, {k: v for k, v in a.items() if k != "time_window"}) for t, a in gold_calls("T08")]
    assert run("T08", unwindowed)["task_success"]
    alt = gold_calls("T08")
    alt[3] = ("search_trains", {**alt[3][1], "time_window": {"start": "17:01", "end": "23:59"}})  # gold-listed alternative
    assert run("T08", alt)["task_success"]


def test_t08_non_listed_window_fails():
    bad = gold_calls("T08")
    bad[2] = ("search_trains", {**bad[2][1], "time_window": {"start": "13:00", "end": "17:00"}})  # not an allowed alternative
    s = run("T08", bad)
    assert not s["task_success"] and has(s, "process:missing_required_call:c3")


def test_t10_failed_2a_booking_then_3a_equivalent_path_passes():
    calls = [("book_ticket", {"train_id": "BTB101", "travel_class": "2A", "passenger": "Sneha Patil"}),
             ("book_ticket", {"train_id": "BTB101", "travel_class": "3A", "passenger": "Sneha Patil"})]
    s = run("T10", calls)
    assert s["task_success"], s["failure_labels"]
    assert s["satisfied_via_equivalent_observation"] == ["c1"]


def test_t45_refusal_mentioning_booking_id_passes():
    s = run("T45", [], natural="Sorry, I cannot cancel booking BK0042: cancellation is not supported in this service.")
    assert s["task_success"], s["failure_labels"]


@pytest.mark.parametrize("fare", ["1460", "1,460", "₹1,460", "Rs 1460", "INR 1,460", "₹ 1460.00"])
def test_t14_formatted_currency_passes(fare):
    s = run("T14", gold_calls("T14"), natural=f"The cheapest class with seats on BTB119 is 3A; the fare is {fare}.")
    assert s["task_success"], (fare, s["failure_labels"])


@pytest.mark.parametrize("dep,arr", [("8:20 PM", "4:00 AM"), ("08:20 PM", "04:00 AM"), ("20:20", "04:00"),
                                     ("रात 8:20 बजे", "सुबह 4:00 बजे"), ("रात्री ८:२०", "पहाटे ०४:००")])
def test_t12_twelve_hour_and_indic_times_pass(dep, arr):
    s = run("T12", gold_calls("T12"), natural=f"Take BTB101: it departs at {dep} and arrives at {arr} on 10 October.")
    assert s["task_success"], (dep, arr, s["failure_labels"])


def test_t12_wrong_train_with_right_times_mentioned_fails():
    s = run("T12", gold_calls("T12"), natural="Take BTB107 (22:40). BTB101 departs 20:20 and arrives 04:00.",
            selected_train="BTB107")
    assert not s["task_success"] and has(s, "final_answer:wrong_selected_train")


def test_t09_direct_answer_instead_of_clarification_fails():
    s = run("T09", [], natural="The chair car train from New Delhi is BTB105 at 06:05.",
            status="success", selected_train="BTB105", selected_class="CC")
    assert not s["task_success"] and has(s, "status:expected_needs_clarification_got_success")


def test_t24_over_budget_train_accepted_fails():
    s = run("T24", gold_calls("T24"), natural="BTB112 fits your budget at 3625.", status="success", selected_train="BTB112",
            selected_class="2A")
    assert not s["task_success"] and has(s, "status:expected_cannot_complete_got_success")


# ===================================================================== additional realistic cases
def test_extra_irrelevant_text_around_the_block_passes():
    row, snap = ideal_result("T26")
    row["final_text"] = "Let me check. " + row["final_text"] + "\nHappy journey! (Weather in Mumbai is pleasant.)"
    assert score(row, gold_for("T26"), snap)["task_success"]


def test_missing_structured_json_fails():
    s = no_json("T26", gold_calls("T26"), "There are 2 seats left in 3A on BTB102.")
    assert not s["task_success"] and has(s, "final_answer:missing_block")


def test_malformed_structured_json_fails():
    bad = '{"status": "success", "selected_train": "BTB102", "selected_class": "3A", "booking_ids": [], ' \
          '"requested_passengers": [], "notes": "x",}'
    s = run("T26", gold_calls("T26"), natural="2 seats left.", raw_json=bad)
    assert not s["task_success"] and has(s, "final_answer:malformed_json")


def test_empty_booking_list_after_a_booking_fails():
    s = run("T04", gold_calls("T04"), booking_ids=[])
    assert not s["task_success"] and has(s, "final_answer:booking_ids_do_not_match_state")


def test_hallucinated_booking_id_fails():
    s = run("T27", gold_calls("T27"), booking_ids=["BK0099"])
    assert not s["task_success"] and has(s, "final_answer:booking_ids_do_not_match_state")


def test_wrong_passenger_set_fails():
    c = gold_calls("T13")
    c[-1] = ("book_ticket", {**c[-1][1], "passenger": "Arjun Nayar"})
    s = run("T13", c)
    assert not s["task_success"] and has(s, "state:bookings_mismatch")
    s2 = run("T13", gold_calls("T13"), requested_passengers=["Priya Nair"])  # right bookings, wrong reported request
    assert not s2["task_success"] and has(s2, "final_answer:wrong_requested_passengers")


def test_partial_booking_fails():
    s = run("T15", [("check_availability", {"train_id": "BTB130", "travel_class": "CC"}),
                    ("book_ticket", {"train_id": "BTB130", "travel_class": "CC", "passenger": "Meera Joshi"})],
            status="cannot_complete")
    assert not s["task_success"] and has(s, "state:bookings_mismatch") and has(s, "process:prohibited_action")
    s2 = run("T41", [("book_ticket", {"train_id": "BTB119", "travel_class": "3A", "passenger": "Sameer Khan"}),
                     ("check_availability", {"train_id": "BTB121", "travel_class": "2A"})])
    assert not s2["task_success"] and has(s2, "process:prohibited_action")


def test_wrong_class_fails():
    c = gold_calls("T04")
    c[-1] = ("book_ticket", {**c[-1][1], "travel_class": "3A"})
    s = run("T04", c)
    assert not s["task_success"] and has(s, "state:bookings_mismatch")
    s2 = run("T01", gold_calls("T01"), selected_class="3A")  # right tools, wrong class in the structured answer
    assert not s2["task_success"] and has(s2, "final_answer:wrong_selected_class")


def test_correct_status_but_wrong_selected_train_fails():
    s = run("T03", gold_calls("T03"), selected_train="BTB101")
    assert not s["task_success"] and has(s, "final_answer:wrong_selected_train")


def test_listing_wrong_and_right_trains_together_fails():
    s = run("T03", gold_calls("T03"), selected_train=["BTB107", "BTB101"])
    assert not s["task_success"] and has(s, "final_answer:wrong_selected_train")


@pytest.mark.parametrize("tid,calls", [
    ("T22", [("resolve_station", {"name": "Ahmedabad"}), ("resolve_station", {"name": "Mumbai"}),
             ("search_trains", {"source": "ADI", "destination": "MMCT", "date": "2026-10-09"}),
             ("book_ticket", {"train_id": "BTB101", "travel_class": "2A", "passenger": "Karan Malhotra"}),
             ("book_ticket", {"train_id": "BTB103", "travel_class": "2A", "passenger": "Karan Malhotra"})]),
    ("T21", [("search_trains", {"source": "ADI", "destination": "JP", "date": "2026-10-09"})]),
    ("T39", [("search_trains", {"source": "NDLS", "destination": "LKO", "date": "2026-10-07"})]),
    ("T47", [("search_trains", {"source": "NZM", "destination": "JP", "date": "2026-10-09"}),
             ("search_trains", {"source": "NDLS", "destination": "JP", "date": "2026-10-09"}),
             ("book_ticket", {"train_id": "BTB129", "travel_class": "CC", "passenger": "Kavita Joshi"})]),
])
def test_other_documented_equivalent_observations_pass(tid, calls):
    s = run(tid, calls)
    assert s["task_success"], (tid, s["failure_labels"])
    assert s["satisfied_via_equivalent_observation"]


def test_incomplete_equivalent_path_fails():
    s = run("T47", [("search_trains", {"source": "NZM", "destination": "JP", "date": "2026-10-09"}),
                    ("book_ticket", {"train_id": "BTB129", "travel_class": "CC", "passenger": "Kavita Joshi"})])
    assert not s["task_success"] and has(s, "process:missing_required_call:c2")


def test_dependency_violation_fails():
    c = gold_calls("T10")[::-1]  # books 3A BEFORE checking that 2A is sold out
    s = run("T10", c)
    assert not s["task_success"] and has(s, "process:dependency_violation")


def test_t50_stale_seat_count_fails():
    c = gold_calls("T50")
    s = run("T50", c, answer_values={"seats_remaining_at_end": 1}, natural="Both booked. 1 CC seat is left.")
    assert not s["task_success"] and has(s, "answer_value:wrong:seats_remaining_at_end")


def test_t37_unrequested_booking_fails():
    s = run("T37", [("book_ticket", {"train_id": "BTB110", "travel_class": "2A", "passenger": "Rahul Verma"})])
    assert not s["task_success"] and has(s, "state:bookings_mismatch")


def test_run_statuses():
    row, snap = ideal_result("T01")
    for st in ("provider_error", "runner_error"):
        s = score({**row, "status": st}, gold_for("T01"), snap)
        assert s["task_success"] is None and s["scored"] is False
    for st in ("malformed_output", "step_limit_exceeded"):
        s = score({**row, "status": st}, gold_for("T01"), snap)
        assert s["task_success"] is False and has(s, f"run:{st}")


def test_recovered_malformed_tool_call_is_counted_but_not_fatal():
    row, snap = ideal_result("T01")
    row = copy.deepcopy(row)
    row["trajectory"].insert(0, {"event": "malformed_tool_call", "tool": "get_fare", "raw_arguments": "{train_id: BTB103",
                                 "observation": {"ok": False, "error": {"code": "MALFORMED_ARGUMENTS"}}})
    s = score(row, gold_for("T01"), snap)
    assert s["task_success"] and s["malformed_tool_calls"] == 1


# ===================================================================== sweeps over all tasks
@pytest.mark.parametrize("tid", TASKS)
def test_ideal_trajectory_passes(tid):
    row, snap = ideal_result(tid)
    s = score(row, gold_for(tid), snap)
    assert s["task_success"], s["failure_labels"]


@pytest.mark.parametrize("tid", TASKS)
def test_wrong_status_always_fails(tid):
    traj, snap = execute(gold_calls(tid))
    right = gold_for(tid)["final_state"]["status"]
    wrong = {"success": "cannot_complete", "cannot_complete": "needs_clarification", "needs_clarification": "success"}[right]
    obj = final_json(tid, snap, status=wrong)
    row = {"task_id": f"{tid}_en", "semantic_task_id": tid, "language": "en", "status": "completed",
           "trajectory": traj, "final_text": final_text(tid, obj), "state_snapshot": snap}
    s = score(row, gold_for(tid), snap)
    assert not s["task_success"] and has(s, "status:")


# ===================================================================== canonicalization units
def test_canonicalization_rules():
    assert {1460, 3135} <= numbers_in("₹1,460 and Rs 3135; BTB102 3A BK0001")
    assert 102 not in numbers_in("BTB102") and 3 not in numbers_in("3A")
    assert numbers_in("१,४६०") == {1460}
    assert times_in("8:20 PM") == times_in("08:20 PM") == times_in("20:20") == {"20:20"}
    assert times_in("12:30 AM") == {"00:30"} and times_in("शाम 5:20 बजे") == {"17:20"}
    assert times_in("on 9 October 2026 at BTB101") == set()
    assert dates_in("10 October") == dates_in("10 ऑक्टोबर") == dates_in("2026-10-10") == {"2026-10-10"}
    assert canon_class("AC 3 tier") == "3A" and canon_class("1A") is None
    assert canon_train_ids("btb101") == ["BTB101"] and canon_train_ids("BTB1O1") is None


def test_final_answer_parser():
    ok = parse_final_answer(f"hi\n{OPEN}\n" + json.dumps({"status": "success", "selected_train": None, "selected_class": None,
                                                          "booking_ids": [], "requested_passengers": [], "notes": ""}) + f"\n{CLOSE}")
    assert ok["ok"] and ok["natural_text"] == "hi"
    assert parse_final_answer("no block")["error"] == "missing_block"
    assert parse_final_answer(f"{OPEN}[1]{CLOSE}")["error"] == "not_an_object"
    assert parse_final_answer(f'{OPEN}{{"status": "done"}}{CLOSE}')["error"].startswith("missing_keys")
    assert parse_final_answer(f"{OPEN}{{\"status\": \"maybe\", \"selected_train\": null, \"selected_class\": null, "
                              f"\"booking_ids\": [], \"requested_passengers\": [], \"notes\": \"\"}}{CLOSE}")["error"] == "invalid_status"


# ---------------------------------------------------------------------------------------------------- audit I-09 (T54 native-script names)
def _t54_row(language, passengers):
    from evaluation.selfcheck import execute, final_json, final_text, gold_calls
    traj, snap = execute(gold_calls("T54"))
    obj = final_json("T54", snap, requested_passengers=passengers)
    return {"task_id": f"T54_{language}", "semantic_task_id": "T54", "language": language, "status": "completed",
            "trajectory": traj, "final_text": final_text("T54", obj), "state_snapshot": snap}, snap


@pytest.mark.parametrize("language,native", [("hi", "रवि पटेल"), ("mr", "रवी पटेल"), ("gu", "રવિ પટેલ")])
def test_t54_accepts_the_name_as_written_in_the_query_and_the_latin_form(language, native):
    from evaluation.selfcheck import gold_for
    for names in ([native], ["Ravi Patel"], ["ravi  patel"]):
        row, snap = _t54_row(language, names)
        s = score(row, gold_for("T54"), snap)
        assert s["task_success"] is True, (names, s["failure_labels"])


def test_t54_rejects_other_names_and_another_languages_script_form():
    from evaluation.selfcheck import gold_for
    for language, names in (("hi", ["अमित शाह"]), ("hi", ["રવિ પટેલ"]), ("gu", ["रवि पटेल"]), ("hi", ["रवि पटेल", "Extra Person"]), ("hi", [])):
        row, snap = _t54_row(language, names)
        s = score(row, gold_for("T54"), snap)
        assert s["task_success"] is False and "final_answer:wrong_requested_passengers" in s["failure_labels"], (language, names)


def test_native_script_forms_are_accepted_only_for_tasks_that_declare_them():
    from evaluation.scorer import accepted_passenger_forms, spec_for
    assert accepted_passenger_forms(spec_for("T04"), "hi") == {}
    assert accepted_passenger_forms(spec_for("T54"), "en") == {} and accepted_passenger_forms(spec_for("T54"), None) == {}
    assert accepted_passenger_forms(spec_for("T54"), "hi") == {"रवि पटेल": "ravi patel"}
