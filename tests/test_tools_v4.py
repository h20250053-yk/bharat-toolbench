"""The 20-tool stage: the eight service tools (Tatkal check/booking, berths, platform, boarding change, meals, TDR, complaints), the
tiered tool offering, the batch T101-T200 and how the scorer grades the new state changes. All offline; values come from
environment/data/services.json, account.json and live_status.json at the pinned now (2026-10-05 09:00)."""
from __future__ import annotations

import json

import pytest

from benchmark import batch_t101_t200 as b6
from benchmark.build_gold import GOLD_PATH, SPEC_PATH
from environment import TOOL_NAMES, RailwayEnv
from environment import build_services
from evaluation.runner import offered_tools
from evaluation.scorer import EQUIVALENT_PATHS, STRUCTURED_VALUE_CHECKS, score
from evaluation.selfcheck import ideal_result

GOLD = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
SPECS = {t["semantic_task_id"]: t for t in json.loads(SPEC_PATH.read_text(encoding="utf-8"))["tasks"]}
NEW = ["check_tatkal_availability", "book_tatkal_ticket", "get_berth_availability", "get_platform_info", "change_boarding_point",
       "order_meal", "file_tdr", "raise_complaint"]


@pytest.fixture
def env():
    e = RailwayEnv()
    e.reset()
    return e


def call(e, tool, **args):
    return e.call(tool, args)


def code(r):
    return (r.get("error") or {}).get("code")


def _row(tid, snap, final):
    return {"task_id": f"{tid}_en", "semantic_task_id": tid, "language": "en", "status": "completed", "trajectory": [],
            "final_text": final, "state_snapshot": snap}


# --------------------------------------------------------------------------------------------- tools and fixtures
def test_twenty_tools_and_services_file_is_generated():
    assert len(TOOL_NAMES) == 20 and list(TOOL_NAMES[12:]) == NEW
    assert build_services.main(["--check"]) == 0, "services.json differs from python -m environment.build_services"


def test_tiered_offering_gives_each_stage_its_own_tools():
    en = {json.loads(l)["semantic_task_id"]: json.loads(l) for l in open("benchmark/languages/en.jsonl", encoding="utf-8")}
    assert len(offered_tools(en["T01"])) == 6 and len(offered_tools(en["T76"])) == 12 and len(offered_tools(en["T150"])) == 20
    assert offered_tools(en["T150"]) == list(TOOL_NAMES)


def test_tatkal_window_fare_and_booking(env):
    t = call(env, "check_tatkal_availability", train_id="BTB109", travel_class="3A", date="2026-10-05")["data"]
    assert (t["status"], t["tatkal_seats"], t["tatkal_fare_inr"], t["concessions_allowed"]) == ("OPEN", 6, 3540, False)
    t = call(env, "check_tatkal_availability", train_id="BTB112", travel_class="SL", date="2026-10-06")["data"]
    assert (t["status"], t["opens_at"]) == ("NOT_YET_OPEN", "2026-10-05 11:00")
    assert call(env, "check_tatkal_availability", train_id="BTB105", travel_class="CC", date="2026-10-05")["data"]["status"] == "DEPARTED"
    assert code(call(env, "check_tatkal_availability", train_id="BTB111", travel_class="3A", date="2026-10-07")) == "NOT_RUNNING_ON_DATE"
    assert code(call(env, "book_tatkal_ticket", train_id="BTB110", travel_class="3A", passenger="Sunil Verma", date="2026-10-06")) == "TATKAL_NOT_OPEN"
    assert code(call(env, "book_tatkal_ticket", train_id="BTB103", travel_class="3A", passenger="Kavya Reddy", date="2026-10-05")) == "TATKAL_SOLD_OUT"
    before = env.snapshot()["availability"]
    b = call(env, "book_tatkal_ticket", train_id="BTB101", travel_class="2A", passenger="Rohan Gupta", date="2026-10-05")["data"]
    assert (b["booking_id"], b["fare_inr"], b["quota"]) == ("BK0001", 4940, "TATKAL")
    assert env.snapshot()["availability"] == before  # the general quota is untouched
    assert call(env, "check_tatkal_availability", train_id="BTB101", travel_class="2A", date="2026-10-05")["data"]["tatkal_seats"] == 3
    assert call(env, "get_booking_status", pnr=b["pnr"])["data"]["status"] == "CONFIRMED"
    assert code(call(env, "book_tatkal_ticket", train_id="BTB101", travel_class="2A", passenger="rohan  gupta", date="2026-10-05")) == "DUPLICATE_BOOKING"


def test_berths_platforms_and_coach_order(env):
    assert call(env, "get_berth_availability", train_id="BTB110", travel_class="3A")["data"]["lower"] == 9
    assert call(env, "get_berth_availability", train_id="BTB122", travel_class="2A")["data"]["lower"] == 0
    assert code(call(env, "get_berth_availability", train_id="BTB117", travel_class="CC")) == "NO_BERTHS_IN_CLASS"
    p = call(env, "get_platform_info", train_id="BTB104", station="MMCT")["data"]
    assert p["coach_order"].index("B1") + 1 == 7
    assert code(call(env, "get_platform_info", train_id="BTB127", station="MMCT")) == "NOT_A_STOP"


def test_boarding_change_rules(env):
    r = call(env, "change_boarding_point", pnr="3051962847", station="JP")["data"]
    assert (r["new_boarding"], r["boarding_date"], r["boarding_time"]) == ("JP", "2026-10-08", "20:20")
    assert call(env, "get_booking_status", pnr="3051962847")["data"]["boarding_station"] == "JP"
    assert code(call(env, "change_boarding_point", pnr="4429610385", station="PUNE")) == "TOO_LATE_TO_CHANGE"
    assert code(call(env, "change_boarding_point", pnr="3398217604", station="NGP")) == "NOT_EN_ROUTE"
    assert code(call(env, "change_boarding_point", pnr="7302958146", station="ADI")) == "NOT_CONFIRMED"
    assert code(call(env, "change_boarding_point", pnr="2894017356", station="ADI")) == "ALREADY_CANCELLED"


def test_meal_rules_follow_the_live_arrival(env):
    m = call(env, "order_meal", pnr="6187340925", station="ADI", meal="veg_thali", quantity=1)["data"]
    assert (m["amount_inr"], m["delivery_time"]) == (180, "13:30")  # timetable 11:30 + 120 min delay
    assert call(env, "order_meal", pnr="5803917264", station="NGP", meal="jain_thali", quantity=2)["data"]["amount_inr"] == 400
    for pnr, st, meal, err in (("2370495816", "PUNE", "veg_thali", "ORDER_TOO_LATE"), ("8162039475", "NGP", "veg_thali", "STATION_ALREADY_PASSED"),
                               ("3051962847", "ADI", "nonveg_thali", "MEAL_NOT_SERVED_AT_THIS_TIME"), ("1937406528", "NGP", "veg_thali", "NOT_CONFIRMED"),
                               ("9157364820", "NGP", "veg_thali", "NOT_EN_ROUTE"), ("3051962847", "JP", "veg_thali", "CATERING_NOT_AVAILABLE"),
                               ("6187340925", "ADI", "biryani", "INVALID_MEAL")):
        assert code(call(env, "order_meal", pnr=pnr, station=st, meal=meal, quantity=1)) == err, (pnr, st, meal)


def test_tdr_and_complaint_rules(env):
    t = call(env, "file_tdr", pnr="6620194835")["data"]
    assert (t["refund_inr"], t["delay_minutes"]) == (495, 200)
    assert code(call(env, "file_tdr", pnr="6620194835")) == "DUPLICATE_TDR"
    assert code(call(env, "file_tdr", pnr="3875061294")) == "TDR_NOT_ELIGIBLE"
    assert code(call(env, "file_tdr", pnr="9045127368")) == "TDR_WINDOW_CLOSED"
    assert call(env, "raise_complaint", pnr="6187340925", category="ac_not_working")["data"]["status"] == "REGISTERED"
    assert call(env, "raise_complaint", pnr="8741203659", category="cleanliness", description="dirty coach")["ok"]  # description optional
    assert code(call(env, "raise_complaint", pnr="2289016475", category="ac_not_working")) == "CATEGORY_NOT_APPLICABLE"
    assert code(call(env, "raise_complaint", pnr="3051962847", category="cleanliness")) == "JOURNEY_NOT_IN_PROGRESS"


def test_reset_restores_every_new_state_list(env):
    base = env.state_hash()
    call(env, "book_tatkal_ticket", train_id="BTB101", travel_class="2A", passenger="Rohan Gupta", date="2026-10-05")
    call(env, "change_boarding_point", pnr="3051962847", station="JP")
    call(env, "order_meal", pnr="6187340925", station="ADI", meal="veg_thali", quantity=1)
    call(env, "file_tdr", pnr="6620194835")
    call(env, "raise_complaint", pnr="6187340925", category="ac_not_working")
    assert env.state_hash() != base
    env.reset()
    assert env.state_hash() == base


# --------------------------------------------------------------------------------------------- batch T101-T200
def test_batch_has_100_tasks_with_twenty_tools_and_unique_solvers():
    assert b6.BATCH_IDS == [f"T{i}" for i in range(101, 201)]
    assert all(SPECS[t]["allowed_tools"] == list(TOOL_NAMES) for t in b6.BATCH_IDS)
    assert len({SPECS[t]["solver"]["kind"] for t in b6.BATCH_IDS}) == 100
    # all but ten need a new tool; the ten test selection among twenty tools with a new tool as the tempting wrong choice
    without = [t for t in b6.BATCH_IDS if not any(c["tool"] in NEW for c in GOLD[t]["required_calls"])]
    assert without == ["T140", "T167", "T168", "T169", "T175", "T177", "T178", "T189", "T191", "T194"]


def test_every_new_tool_is_used_by_gold():
    used = {c["tool"] for t in b6.BATCH_IDS for c in GOLD[t]["required_calls"]}
    assert set(NEW) <= used


def test_equivalent_paths_exist_for_every_spec_that_declares_them():
    for t in b6.BATCH_IDS:
        if SPECS[t]["final_answer_requirements"].get("equivalent_observations"):
            assert any(k[0] == t for k in EQUIVALENT_PATHS), t


def test_structured_checks_mirror_the_batch():
    for t, checks in b6.STRUCTURED.items():
        assert STRUCTURED_VALUE_CHECKS[t] == checks
        assert all(g in GOLD[t]["final_answer"] for g, _, _ in checks), t


@pytest.mark.parametrize("tid", ["T103", "T112", "T119", "T131", "T143", "T154", "T171", "T180", "T197"])
def test_ideal_trajectory_passes(tid):
    row, snap = ideal_result(tid)
    assert score(row, GOLD[tid], snap)["task_success"]


def test_an_unrequested_new_effect_fails_an_older_task(env):
    """T01 asks for a fare: a meal order, a TDR, a complaint, a boarding change or a Tatkal booking nobody asked for fails the item."""
    for tool, args, label in (("order_meal", dict(pnr="6187340925", station="ADI", meal="veg_thali", quantity=1), "meal_orders"),
                              ("file_tdr", dict(pnr="6620194835"), "tdr_claims"),
                              ("raise_complaint", dict(pnr="6187340925", category="cleanliness"), "complaints"),
                              ("change_boarding_point", dict(pnr="3051962847", station="JP"), "boarding_changes"),
                              ("book_tatkal_ticket", dict(train_id="BTB101", travel_class="2A", passenger="Rohan Gupta", date="2026-10-05"), "tatkal_bookings")):
        env.reset()
        assert env.call(tool, args)["ok"], tool
        s = score(_row("T01", env.snapshot(), ""), GOLD["T01"], env.snapshot())
        assert f"state:{label}_mismatch" in s["failure_labels"], (tool, s["failure_labels"])


def test_prohibited_action_and_wrong_branch_fail(env):
    # T175: eligibility only; filing the TDR is forbidden
    call(env, "file_tdr", pnr="6620194835")
    s = score(_row("T175", env.snapshot(), ""), GOLD["T175"], env.snapshot())
    assert not s["task_success"] and "state:tdr_claims_mismatch" in s["failure_labels"]
    # T171: the better refund is the TDR; cancelling instead is wrong
    env.reset()
    call(env, "cancel_ticket", pnr="6620194835")
    s = score(_row("T171", env.snapshot(), ""), GOLD["T171"], env.snapshot())
    assert "state:cancellations_mismatch" in s["failure_labels"]
    # T152: the veg thali (arrives after 9 PM), not the non-veg one
    env.reset()
    call(env, "order_meal", pnr="5803917264", station="NGP", meal="nonveg_thali", quantity=1)
    s = score(_row("T152", env.snapshot(), ""), GOLD["T152"], env.snapshot())
    assert "state:meal_orders_mismatch" in s["failure_labels"]


def test_t01_t100_gold_has_no_effects():
    for t in (f"T{i:02d}" for i in range(1, 101)):
        assert "expected_effects" not in GOLD[t]["final_state"]
