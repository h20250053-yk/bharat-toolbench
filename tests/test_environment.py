"""Environment-level tests: fixtures, config, pinned time, reset, determinism, schema compatibility."""
import copy
import json
from datetime import datetime, timedelta, timezone

import yaml

from benchmark.schemas import BenchmarkItem, DependencyEdge, FinalStatePredicate, GoldSpec, RequiredCall
from environment import RailwayEnv, TOOL_NAMES, tool_specs
from environment.railway_env import CONFIG_PATH
from environment.schemas import TRAVEL_CLASSES


def test_fixture_sizes_match_config(env):
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert len(env.state.stations) == cfg["environment"]["station_count"] == 10
    assert len(env.state.trains) == cfg["environment"]["train_count"] == 30
    assert tuple(cfg["environment"]["travel_classes"]) == TRAVEL_CLASSES == ("3A", "2A", "SL", "CC")
    assert tuple(cfg["environment"]["tools"]) == TOOL_NAMES
    assert cfg["languages"] == ["en", "hinglish", "hi", "mr", "gu"]


def test_exactly_twenty_tools_with_specs():
    # the six tools of benchmark 1.0-2.1, the six added in 3.0 (T76-T100), then the eight of the 20-tool stage (T101-T200), in this order
    assert TOOL_NAMES == ("resolve_station", "search_trains", "get_train_details",
                          "check_availability", "get_fare", "book_ticket",
                          "get_booking_status", "get_cancellation_refund", "cancel_ticket", "join_waitlist",
                          "get_live_train_status", "get_concession_fare",
                          "check_tatkal_availability", "book_tatkal_ticket", "get_berth_availability", "get_platform_info",
                          "change_boarding_point", "order_meal", "file_tdr", "raise_complaint")
    specs = tool_specs()
    assert [s["name"] for s in specs] == list(TOOL_NAMES)
    assert all(s["description"] and s["parameters"]["type"] == "object" for s in specs)


def test_fixture_internal_consistency(env):
    for t in env.state.trains.values():
        assert len(t.stops) >= 2
        kms = [s.distance_km for s in t.stops]
        assert kms == sorted(kms) and kms[0] == 0
        for info in t.classes.values():
            assert info.fare_inr > 0 and info.seats >= 0
    # every station is served; several sold-out and low-seat classes exist for later recovery tasks
    served = {s.station for t in env.state.trains.values() for s in t.stops}
    assert served == set(env.state.stations)
    sold_out = [(t, c) for (t, c), n in env.state.availability.items() if n == 0]
    assert len(sold_out) >= 4


def test_reference_datetime_is_pinned_not_system_clock(env):
    assert env.reference_datetime == datetime(2026, 10, 5, 9, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))


def test_reset_restores_exact_original_state(env):
    base_snapshot = copy.deepcopy(env.snapshot())
    base_hash = env.state_hash()
    r = env.book_ticket("BTB102", "3A", "Asha Rao")
    assert r.ok
    assert env.state_hash() != base_hash
    assert env.snapshot() != base_snapshot
    env.reset()
    assert env.snapshot() == base_snapshot
    assert env.state_hash() == base_hash
    assert env.snapshot()["bookings"] == [] and env.snapshot()["next_booking_seq"] == 1


def test_booking_ids_restart_after_reset(env):
    assert env.book_ticket("BTB102", "3A", "Asha Rao").data["booking_id"] == "BK0001"
    env.reset()
    assert env.book_ticket("BTB102", "3A", "Asha Rao").data["booking_id"] == "BK0001"


def test_determinism_two_independent_envs_same_everything():
    a, b = RailwayEnv(), RailwayEnv()
    assert a.static_hash == b.static_hash and a.state_hash() == b.state_hash()
    script = [
        ("resolve_station", {"name": "Delhi"}),
        ("search_trains", {"source": "NDLS", "destination": "ADI", "date": "2026-10-07"}),
        ("book_ticket", {"train_id": "BTB103", "travel_class": "2A", "passenger": "Meera Iyer"}),
        ("check_availability", {"train_id": "BTB103", "travel_class": "2A"}),
        ("book_ticket", {"train_id": "BTB103", "travel_class": "3A", "passenger": "Meera Iyer"}),  # sold out
    ]
    out_a = [a.call(t, x) for t, x in script]
    out_b = [b.call(t, x) for t, x in script]
    assert json.dumps(out_a, sort_keys=True) == json.dumps(out_b, sort_keys=True)
    assert a.state_hash() == b.state_hash()


def test_repeated_search_is_pure(env):
    h = env.state_hash()
    r1 = env.call("search_trains", {"source": "NDLS", "destination": "JP", "date": "2026-10-06"})
    r2 = env.call("search_trains", {"source": "NDLS", "destination": "JP", "date": "2026-10-06"})
    assert r1 == r2 and env.state_hash() == h  # read-only tools never mutate state


def test_benchmark_schemas_can_express_a_partial_order_gold():
    """Compatibility check only (no gold generator yet): independent calls have no edge between them."""
    gold = GoldSpec(
        semantic_task_id="T_demo",
        required_calls=[
            RequiredCall(call_id="c1", tool="search_trains", required_args={"source": "MMCT", "destination": "ADI"}),
            RequiredCall(call_id="c2", tool="check_availability", required_args={"travel_class": "3A"},
                         args_from={"train_id": "c1.trains[*].train_id"}),
            RequiredCall(call_id="c3", tool="get_fare", required_args={"travel_class": "3A"},
                         args_from={"train_id": "c1.trains[*].train_id"}),
        ],
        dependency_edges=[DependencyEdge(before="c1", after="c2"), DependencyEdge(before="c1", after="c3")],
        final_state=FinalStatePredicate(status="success", allowed_train_ids=["BTB102"], travel_class="3A"),
        min_calls=3,
    )
    assert {(e.before, e.after) for e in gold.dependency_edges} == {("c1", "c2"), ("c1", "c3")}  # no c2<->c3 edge
    item = BenchmarkItem(task_id="T_demo_en", semantic_task_id="T_demo", language="en", query="...",
                         category="sequential", allowed_tools=list(TOOL_NAMES))
    assert item.review_status == "draft"
