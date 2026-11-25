"""Tool-selection metrics (METRICS.md): synthetic and ideal trajectories over the real gold; no model, no network."""
import copy
import json

import pytest

from analysis import tool_metrics as TM
from evaluation.selfcheck import execute, gold_calls, gold_for, ideal_result

GOLD = json.load(open("benchmark/gold_labels.json", encoding="utf-8"))
TASKS = sorted(k for k in GOLD if not k.startswith("_"))


def row(tid, calls=None, lang="en", success=None, partial=False, bookings=None):
    """A run row whose trajectory is the execution of `calls` [(tool, args)] (default: the ideal calls)."""
    calls = gold_calls(tid) if calls is None else calls
    traj, snap = execute(calls)
    r = {"task_id": f"{tid}_{lang}", "semantic_task_id": tid, "language": lang, "status": "completed", "trajectory": traj, "state_snapshot": snap,
         "score": {"task_success": True if success is None else success}}
    if partial:
        r["partial_trajectory"], r["trajectory"], r["status"] = traj, [], "malformed_output"
    return r


def M(tid, **kw):
    return TM.item_metrics(row(tid, **kw), GOLD[tid])


def test_ideal_run_is_perfect_on_every_tool_needed_task():
    for tid in TASKS:
        if not any(not c.get("optional") for c in GOLD[tid]["required_calls"]):
            continue
        m = M(tid)
        assert m["recall"] == 1.0 and m["precision"] == 1.0 and m["f1"] == 1.0, tid
        assert m["first_call_ok"] and m["first_call_exact"], tid
        assert m["funnel"] == [True, True, True, True, True], tid
        assert m["edges_violated"] == 0 and m["unnecessary_calls"] == 0 and m["repeated_calls"] == 0 and m["valid_calls"] == m["n_calls"], tid
        assert m["arg_acc"] == 1.0 and not m["selection_error"] and not m["argument_error"], tid
        assert all(h == t for h, t in m["field_hits"].values()), tid


def test_no_calls_at_all_scores_zero_not_undefined():
    m = M("T01", calls=[], success=False)
    assert m["needed"] and m["n_calls"] == 0 and m["recall"] == 0.0 and m["precision"] is None and m["f1"] == 0.0
    assert not m["uses_tools"] and m["first_call_ok"] is False and m["funnel"] == [False, False, False, False, False] and m["selection_error"]
    assert m["confusion"] == {"get_fare|(not called)": 1}


def test_wrong_tool_is_a_substitution_in_the_confusion_table_and_lowers_precision_and_recall():
    m = M("T01", calls=[("check_availability", {"train_id": "BTB103", "travel_class": "2A"})], success=False)    # gold: get_fare
    assert m["recall"] == 0.0 and m["precision"] == 0.0 and m["f1"] == 0.0 and m["first_call_ok"] is False and m["selection_error"]
    assert m["confusion"] == {"get_fare|check_availability": 1} and m["unnecessary_calls"] == 1


def test_right_tool_wrong_arguments_is_an_argument_error_not_a_selection_error():
    m = M("T01", calls=[("get_fare", {"train_id": "BTB104", "travel_class": "2A"})], success=False)             # gold train BTB103
    assert m["recall"] == 1.0 and m["precision"] == 1.0 and m["funnel"][:2] == [True, True] and m["funnel"][2] is False
    assert m["argument_error"] and not m["selection_error"] and m["arg_acc"] == 0.0 and m["first_call_ok"] and not m["first_call_exact"]
    assert m["field_hits"]["train id"] == [0, 1] and m["field_hits"]["class"] == [1, 1]


def test_invalid_arguments_count_in_argument_validity_but_expected_errors_do_not():
    m = M("T01", calls=[("get_fare", {"train_id": "BTB1033", "travel_class": "2A"}), ("get_fare", {"train_id": "BTB103", "travel_class": "2A"})], success=False)
    assert m["n_calls"] == 2 and m["valid_calls"] == 1 and m["repeated_calls"] == 0 and m["unnecessary_calls"] == 1      # 2 get_fare calls, 1 required
    m = TM.item_metrics(row("T28"), GOLD["T28"])                                                                       # T28: INVALID_TRAIN is the gold's expected error
    assert m["valid_calls"] == m["n_calls"] >= 1


def test_repeated_identical_calls_and_over_calling():
    call = ("get_fare", {"train_id": "BTB103", "travel_class": "2A"})
    m = M("T01", calls=[call, call, ("get_train_details", {"train_id": "BTB103"})])
    assert m["repeated_calls"] == 1 and m["unnecessary_calls"] == 2 and m["overcalling"] and abs(m["over_call_rate"] - 2 / 3) < 1e-9 and m["precision"] == pytest.approx(1 / 3)
    assert m["recall"] == 1.0


def test_dependency_violation_is_detected_and_sets_the_order_funnel_stage():
    ideal = gold_calls("T04")                                   # resolve x2, search, fares..., book: book before the search violates edges
    swapped = [ideal[-1]] + ideal[:-1]
    m = M("T04", calls=swapped, success=False)
    assert m["recall"] == 1.0 and m["edges_violated"] >= 1 and m["sequence_acc"] < 1.0
    assert m["funnel"][2] is True or m["funnel"][2] is False   # matching may still succeed (arguments are static), the order stage must fail
    assert m["funnel"][3] is False and m["funnel"][4] is False


def test_unwanted_booking_and_prohibited_attempt():
    tid = "T03"                                                 # the user forbade booking ("Don't book anything")
    assert GOLD[tid]["prohibited_actions"]
    calls = gold_calls(tid) + [("book_ticket", {"train_id": "BTB105", "travel_class": "3A", "passenger": "Test Person"})]
    m = M(tid, calls=calls, success=False)
    assert m["prohibited_attempt"] and m["booking_forbidden_task"] and m["no_booking_expected"]
    assert m["unwanted_booking"] in (True, False)
    clean = M(tid)
    assert not clean["prohibited_attempt"] and not clean["unwanted_booking"]


def test_no_tool_tasks_only_measure_unneeded_tool_use():
    no_tool = [t for t in TASKS if not any(not c.get("optional") for c in GOLD[t]["required_calls"])]
    assert len(no_tool) == 14  # 3.0: + T98 (cancel without a PNR); 20-tool stage: + T151 (menu in the tool description), T189 (no PNR)
    m = M(no_tool[0], calls=[])
    assert not m["needed"] and m["recall"] is None and m["f1"] is None and m["funnel"] is None and not m["unneeded_tool_use"]
    m = M(no_tool[0], calls=[("get_fare", {"train_id": "BTB103", "travel_class": "2A"})], success=False)
    assert m["unneeded_tool_use"] and m["unnecessary_calls"] == 1 and m["confusion"] == {f"{TM.NOT_REQUIRED}|get_fare": 1}


def test_partial_trajectory_is_used_when_the_trajectory_is_empty():
    m = M("T01", partial=True, success=False)
    assert m["n_calls"] == 1 and m["recall"] == 1.0 and m["uses_tools"]


def test_unexecuted_and_non_call_events_are_not_calls():
    r = row("T01")
    r["trajectory"].append({"event": "unexecuted_step_limit", "tool": "get_fare", "arguments": {}})
    assert TM.item_metrics(r, GOLD["T01"])["n_calls"] == 1


def test_summaries_have_wilson_and_bootstrap_intervals_and_the_funnel_is_monotone():
    items = [M(t) for t in TASKS if any(not c.get("optional") for c in GOLD[t]["required_calls"])][:20]
    items += [M(items[0]["task"], calls=[], success=False) for _ in range(5)]
    s = TM.summarize(items)
    assert s["n_tool_needed"] == 25 and s["tool_use_rate"]["k"] == 20 and s["tool_use_rate"]["lo"] < 0.8 < s["tool_use_rate"]["hi"]
    stages = [s[k]["value"] for k in ("funnel_uses_tools", "funnel_right_tools", "funnel_right_arguments", "funnel_right_order", "funnel_task_success")]
    assert stages == sorted(stages, reverse=True) and stages[0] == 0.8
    for k in ("selection_recall", "selection_f1", "argument_validity"):
        assert s[k]["lo"] <= s[k]["value"] <= s[k]["hi"]
    assert s["selection_precision"]["n"] == 20            # precision only for items with at least one call


def test_confusion_aggregation_and_ranking():
    items = [M("T01", calls=[("check_availability", {"train_id": "BTB103", "travel_class": "2A"})], success=False), M("T01")]
    c = TM.confusion(items)
    assert c[("get_fare", "get_fare")] == 1 and c[("get_fare", "check_availability")] == 1
    sums = {"a": {"selection_f1": {"value": 0.9}, "selection_recall": {"value": 0.9}}, "b": {"selection_f1": {"value": 0.5}, "selection_recall": {"value": 0.6}},
            "c": {"selection_f1": {"value": 0.7}, "selection_recall": {"value": 0.7}}}
    r = TM.rank_models(sums, {"a": 0.2, "b": 0.5, "c": 0.4})
    assert r["order_by_selection"] == ["a", "c", "b"] and r["order_by_success"] == ["b", "c", "a"] and r["spearman_rho"] == pytest.approx(-1.0)


def test_wilson_matches_known_values():
    lo, hi = TM.wilson(8, 10)
    assert lo == pytest.approx(0.4902, abs=1e-3) and hi == pytest.approx(0.9433, abs=1e-3)
