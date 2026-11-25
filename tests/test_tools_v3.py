"""Benchmark 3.0: the six new tools (booking status, refund quote, cancellation, waitlist, live status, concession) and how the
scorer grades the state they change. All offline; values come from environment/data/account.json and live_status.json."""
from __future__ import annotations

import json

import pytest

from benchmark.build_gold import GOLD_PATH
from environment import RailwayEnv
from evaluation.scorer import score

GOLD = json.loads(GOLD_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def env():
    e = RailwayEnv()
    e.reset()
    return e


def call(e, tool, **args):
    return e.call(tool, args)


def code(r):
    return (r.get("error") or {}).get("code")


# --------------------------------------------------------------------------------------------- booking status / refund / cancel
def test_status_of_account_bookings(env):
    d = call(env, "get_booking_status", pnr="7302958146")["data"]
    assert (d["status"], d["waitlist_position"], d["train_id"], d["travel_class"]) == ("WAITLISTED", 3, "BTB101", "2A")
    assert call(env, "get_booking_status", pnr="2894017356")["data"]["status"] == "CANCELLED"
    assert code(call(env, "get_booking_status", pnr="5551234567")) == "PNR_NOT_FOUND"
    assert code(call(env, "get_booking_status", pnr="BK0042")) == "INVALID_PNR"
    assert code(call(env, "get_booking_status", pnr="4518 203 967")) == "INVALID_PNR"  # the tolerance layer, not the tool, fixes spacing


def test_refund_quote_changes_nothing_and_follows_the_charge_rule(env):
    before = env.state_hash()
    q = call(env, "get_cancellation_refund", pnr="4518203967")["data"]
    assert (q["fare_inr"], q["cancellation_charge_inr"], q["refund_inr"]) == (1800, 180, 1620)  # 3A: flat 180
    w = call(env, "get_cancellation_refund", pnr="1385672049")["data"]
    assert (w["status"], w["cancellation_charge_inr"], w["refund_inr"]) == ("WAITLISTED", 60, 2435)  # waitlisted: flat 60
    assert env.state_hash() == before


def test_cancel_frees_a_seat_once_and_blocks_departed_or_cancelled_tickets(env):
    seats = call(env, "check_availability", train_id="BTB120", travel_class="3A")["data"]["seats_available"]
    c = call(env, "cancel_ticket", pnr="9157364820")["data"]
    assert (c["status"], c["refund_inr"]) == ("CANCELLED", 1280)
    assert call(env, "check_availability", train_id="BTB120", travel_class="3A")["data"]["seats_available"] == seats + 1
    assert code(call(env, "cancel_ticket", pnr="9157364820")) == "ALREADY_CANCELLED"
    assert call(env, "get_booking_status", pnr="9157364820")["data"]["status"] == "CANCELLED"
    assert code(call(env, "cancel_ticket", pnr="8803164527")) == "JOURNEY_STARTED"     # BTB125 left ADI at 06:20 today
    assert code(call(env, "get_cancellation_refund", pnr="8803164527")) == "JOURNEY_STARTED"
    assert [x["pnr"] for x in env.snapshot()["cancellations"]] == ["9157364820"]


def test_cancelling_a_waitlisted_ticket_frees_no_seat(env):
    before = dict(env.snapshot()["availability"])
    call(env, "cancel_ticket", pnr="1385672049")
    assert env.snapshot()["availability"] == before


def test_session_booking_can_be_looked_up_and_cancelled(env):
    b = call(env, "book_ticket", train_id="BTB115", travel_class="SL", passenger="Ravi Kumar")["data"]
    assert call(env, "get_booking_status", pnr=b["pnr"])["data"]["status"] == "CONFIRMED"
    assert call(env, "cancel_ticket", pnr=b["pnr"])["ok"]
    assert env.snapshot()["bookings"] == [] and call(env, "get_booking_status", pnr=b["pnr"])["data"]["status"] == "CANCELLED"


# --------------------------------------------------------------------------------------------- waitlist
def test_waitlist_only_when_sold_out_and_positions_count_up(env):
    assert code(call(env, "join_waitlist", train_id="BTB115", travel_class="3A", passenger="Ravi Kumar")) == "SEATS_AVAILABLE"
    a = call(env, "join_waitlist", train_id="BTB101", travel_class="2A", passenger="Kiran Desai")["data"]
    b = call(env, "join_waitlist", train_id="BTB101", travel_class="2A", passenger="Ravi Kumar")["data"]
    assert (a["waitlist_position"], b["waitlist_position"], a["status"]) == (4, 5, "WAITLISTED")
    assert code(call(env, "join_waitlist", train_id="BTB101", travel_class="2A", passenger="kiran desai")) == "DUPLICATE_BOOKING"
    assert env.snapshot()["bookings"] == [] and len(env.snapshot()["waitlist"]) == 2  # a waitlist entry is not a booking


# --------------------------------------------------------------------------------------------- live status
@pytest.mark.parametrize("train,status,delay,last,nxt", [
    ("BTB105", "RUNNING", 25, "NDLS", "JP"),          # left 06:05 today
    ("BTB103", "RUNNING", 120, "JP", "ADI"),          # yesterday's run, overnight
    ("BTB124", "RUNNING", 40, "MMCT", "ADI"),         # scheduled 08:35 arrival, 40 min late -> still running at 09:00
    ("BTB120", "NOT_STARTED", 0, None, None),         # yesterday's run arrived 07:20; today's leaves 18:40
    ("BTB111", "NOT_RUNNING_TODAY", None, None, None),  # TUE/THU/SAT only
])
def test_live_status(env, train, status, delay, last, nxt):
    d = call(env, "get_live_train_status", train_id=train)["data"]
    assert (d["status"], d["delay_minutes"], d["last_station"], d["next_station"]) == (status, delay, last, nxt)


def test_live_expected_times_shift_by_the_delay(env):
    stops = {s["station"]: s for s in call(env, "get_live_train_status", train_id="BTB103")["data"]["stops"]}
    assert (stops["ADI"]["scheduled_arrival"], stops["ADI"]["expected_arrival"], stops["ADI"]["expected_date"]) == ("11:30", "13:30", "2026-10-05")


# --------------------------------------------------------------------------------------------- concession
def test_concession_fares_and_errors(env):
    assert call(env, "get_concession_fare", train_id="BTB115", travel_class="3A", concession="senior_citizen")["data"]["concession_fare_inr"] == 1080
    assert call(env, "get_concession_fare", train_id="BTB127", travel_class="SL", concession="senior citizen")["data"]["concession_fare_inr"] == 369
    assert call(env, "get_concession_fare", train_id="BTB120", travel_class="3A", concession="student")["data"]["concession_fare_inr"] == 1095
    assert code(call(env, "get_concession_fare", train_id="BTB117", travel_class="CC", concession="student")) == "CONCESSION_NOT_AVAILABLE"
    assert code(call(env, "get_concession_fare", train_id="BTB117", travel_class="CC", concession="army")) == "INVALID_CONCESSION"


# --------------------------------------------------------------------------------------------- scoring of the new state
def _row(tid, snap, final):
    return {"task_id": f"{tid}_en", "semantic_task_id": tid, "language": "en", "status": "completed", "trajectory": [],
            "final_text": final, "state_snapshot": snap}


def test_an_unrequested_cancellation_or_waitlist_entry_fails_an_old_task(env):
    """T05 (book only if seats; never anything else): a cancellation or a waitlist entry is a side effect nobody asked for."""
    call(env, "join_waitlist", train_id="BTB103", travel_class="3A", passenger="Vikram Singh")
    s = score(_row("T05", env.snapshot(), ""), GOLD["T05"], env.snapshot())
    assert "state:waitlist_mismatch" in s["failure_labels"]
    env.reset()
    call(env, "cancel_ticket", pnr="4518203967")
    s = score(_row("T05", env.snapshot(), ""), GOLD["T05"], env.snapshot())
    assert "state:cancellations_mismatch" in s["failure_labels"]


def test_t79_cancelling_despite_a_low_refund_is_a_state_failure(env):
    call(env, "cancel_ticket", pnr="5079318462")
    s = score(_row("T79", env.snapshot(), ""), GOLD["T79"], env.snapshot())
    assert "state:cancellations_mismatch" in s["failure_labels"] and not s["task_success"]


def test_frozen_gold_has_no_new_fields():
    for t in (f"T{i:02d}" for i in range(1, 76)):
        assert "expected_cancellations" not in GOLD[t]["final_state"] and "expected_waitlist" not in GOLD[t]["final_state"]
        assert "cancellations" not in GOLD[t]["expected_env_diff"] and "waitlist" not in GOLD[t]["expected_env_diff"]
