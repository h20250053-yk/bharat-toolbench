"""Tool-level tests (A-M from the Phase 0+1 spec, plus edge cases)."""
import pytest

# ---------------------------------------------------------------- A/B: resolve_station
def test_A_resolve_station_success_across_languages(env):
    expected = {
        "Mumbai": "MMCT", "Bombay": "MMCT", "mumbai": "MMCT", "  MUMBAI  ": "MMCT", "मुंबई": "MMCT",
        "Jaipur": "JP", "जयपुर": "JP", "जयपूर": "JP",
        "Pune": "PUNE", "पुणे": "PUNE", "Ahmedabad": "ADI", "अहमदाबाद": "ADI",
        "Nagpur": "NGP", "नागपूर": "NGP", "Bengaluru": "SBC", "Bangalore": "SBC", "बेंगळुरू": "SBC",
        "Kolkata": "HWH", "Howrah": "HWH", "Lucknow": "LKO", "लखनौ": "LKO",
        "New Delhi": "NDLS", "नई दिल्ली": "NDLS", "NDLS": "NDLS", "ndls": "NDLS",
    }
    for name, code in expected.items():
        r = env.resolve_station(name)
        assert r.ok, name
        assert r.data["ambiguous"] is False and [c["code"] for c in r.data["candidates"]] == [code], name


def test_A_resolve_station_ambiguous_delhi(env):
    for name in ["Delhi", "दिल्ली", "Dilli"]:
        r = env.resolve_station(name)
        assert r.ok and r.data["ambiguous"] is True
        assert [c["code"] for c in r.data["candidates"]] == ["NDLS", "NZM"], name


def test_A_resolve_station_nukta_insensitive(env):
    a = env.resolve_station("हज़रत निज़ामुद्दीन")
    b = env.resolve_station("हजरत निजामुद्दीन")
    assert a.ok and b.ok and a.data["candidates"] == b.data["candidates"]
    assert a.data["candidates"][0]["code"] == "NZM"


def test_B_resolve_station_unknown(env):
    for name in ["Atlantis", "", "   ", "Mumbaai", "Delhi Cantt"]:  # no fuzzy matching
        r = env.resolve_station(name)
        assert not r.ok and r.error.code == "STATION_NOT_FOUND", name


# ---------------------------------------------------------------- C/D: search_trains
def test_C_search_trains_basic(env):
    r = env.search_trains("NDLS", "JP", "2026-10-06")
    assert r.ok and r.data["count"] == len(r.data["trains"]) == 3
    assert [t["train_id"] for t in r.data["trains"]] == ["BTB105", "BTB101", "BTB103"]  # sorted by departure
    t = r.data["trains"][0]
    assert (t["departure"], t["arrival"], t["duration_minutes"], t["classes"]) == ("06:05", "10:45", 280, ["CC"])


def test_C_search_intermediate_stops_and_direction(env):
    r = env.search_trains("JP", "ADI", "2026-10-06")  # boarding at an intermediate stop
    ids = [t["train_id"] for t in r.data["trains"]]
    assert "BTB101" in ids and "BTB103" in ids and "BTB107" in ids
    assert env.search_trains("ADI", "NDLS", "2026-10-06").data["count"] >= 1
    # wrong direction for a train never matches: BTB105 is NDLS->JP only
    assert "BTB105" not in [t["train_id"] for t in env.search_trains("JP", "NDLS", "2026-10-06").data["trains"]]


def test_C_time_window_inclusive_and_wrapping(env):
    r = env.search_trains("NDLS", "MMCT", "2026-10-06", {"start": "16:30", "end": "21:15"})
    assert [t["departure"] for t in r.data["trains"]] == ["16:30", "21:15"]  # both bounds inclusive
    night = env.search_trains("NDLS", "MMCT", "2026-10-06", {"start": "21:00", "end": "04:59"})
    assert [t["train_id"] for t in night.data["trains"]] == ["BTB103"]  # wrap past midnight
    r2 = env.search_trains("NDLS", "JP", "2026-10-06", {"start": "00:00", "end": "05:00"})
    assert r2.ok and r2.data["count"] == 0  # empty result is a successful observation, not an error


def test_C_overnight_day_offset(env):
    r = env.search_trains("NDLS", "ADI", "2026-10-06", {"start": "21:00", "end": "22:00"})
    t = r.data["trains"][0]
    assert t["train_id"] == "BTB103" and t["arrival_day_offset"] == 1 and t["duration_minutes"] == 855


def test_C_operating_days_and_past_time_rules(env):
    # BTB108 ADI->JP runs MON/WED/FRI/SUN. 2026-10-05 is Monday, 10-06 Tuesday.
    mon = [t["train_id"] for t in env.search_trains("ADI", "JP", "2026-10-05").data["trains"]]
    tue = [t["train_id"] for t in env.search_trains("ADI", "JP", "2026-10-06").data["trains"]]
    assert "BTB108" in mon and "BTB108" not in tue
    # on the reference date, trains that already left (before 09:00) are excluded
    today = [t["train_id"] for t in env.search_trains("NDLS", "JP", "2026-10-05").data["trains"]]
    assert "BTB105" not in today and "BTB101" in today  # 06:05 gone, 16:30 still ahead


def test_C_no_trains_on_route_is_empty_not_error(env):
    r = env.search_trains("HWH", "ADI", "2026-10-07")
    assert r.ok and r.data["count"] == 0 and r.data["trains"] == []
    assert env.search_trains("NDLS", "NGP", "2026-10-07").data["count"] == 0  # only NZM serves Nagpur


def test_D_search_invalid_inputs(env):
    cases = [
        (("XXX", "JP", "2026-10-06"), "INVALID_STATION"),
        (("NDLS", "Jaipur", "2026-10-06"), "INVALID_STATION"),   # names are not codes
        (("JP", "JP", "2026-10-06"), "SAME_STATION"),
        (("NDLS", "JP", "06/10/2026"), "INVALID_DATE"),
        (("NDLS", "JP", "2026-13-40"), "INVALID_DATE"),
        (("NDLS", "JP", "2026-10-04"), "PAST_DATE"),
    ]
    for args, code in cases:
        r = env.search_trains(*args)
        assert not r.ok and r.error.code == code, (args, r)
    for tw in [{"start": "6pm", "end": "23:00"}, {"start": "18:00"}, "evening"]:
        r = env.search_trains("NDLS", "JP", "2026-10-06", tw)
        assert not r.ok and r.error.code == "INVALID_TIME_WINDOW", tw


# ---------------------------------------------------------------- E: get_train_details
def test_E_train_details(env):
    r = env.get_train_details("BTB101")
    assert r.ok
    d = r.data
    assert d["train_name"] == "Meridian Premium Link" and d["source_station"] == "NDLS" and d["destination_station"] == "MMCT"
    assert [s["station"] for s in d["stops"]] == ["NDLS", "JP", "ADI", "MMCT"] and d["classes"] == ["2A", "3A"]
    assert d["stops"][0]["arrival"] is None and d["stops"][-1]["departure"] is None
    assert "fare_inr" not in d and "seats_available" not in d  # fare/availability only via their own tools


# ---------------------------------------------------------------- F: check_availability
def test_F_availability_values(env):
    assert env.check_availability("BTB102", "3A").data == {"train_id": "BTB102", "travel_class": "3A", "seats_available": 2, "status": "AVAILABLE"}
    sold = env.check_availability("BTB101", "2A")
    assert sold.ok and sold.data["seats_available"] == 0 and sold.data["status"] == "SOLD_OUT"


def test_F_availability_class_case_insensitive_but_strict_enum(env):
    assert env.check_availability("BTB102", "3a").data["travel_class"] == "3A"
    for bad in ["AC3", "3AC", "1A", "", "third ac"]:
        assert env.check_availability("BTB102", bad).error.code == "INVALID_CLASS", bad


# ---------------------------------------------------------------- G: get_fare
def test_G_fare(env):
    r = env.get_fare("BTB102", "3A")
    assert r.ok and r.data == {"train_id": "BTB102", "travel_class": "3A", "fare_inr": 3135, "currency": "INR"}
    assert env.get_fare("BTB102", "2A").data["fare_inr"] > r.data["fare_inr"]  # 2A costs more than 3A
    assert env.get_fare("BTB103", "SL").data["fare_inr"] < env.get_fare("BTB103", "3A").data["fare_inr"]


# ---------------------------------------------------------------- H/I: booking + state change
def test_H_successful_booking(env):
    r = env.book_ticket("BTB102", "3A", "Rohan Mehta")
    assert r.ok
    d = r.data
    assert d["booking_id"] == "BK0001" and d["status"] == "CONFIRMED" and d["fare_inr"] == 3135
    assert d["train_id"] == "BTB102" and d["travel_class"] == "3A" and d["passenger"] == "Rohan Mehta"
    assert len(d["pnr"]) == 10 and d["pnr"].isdigit()
    assert env.snapshot()["bookings"][0]["booking_id"] == "BK0001"


def test_I_booking_reduces_availability_by_exactly_one(env):
    before = env.check_availability("BTB102", "3A").data["seats_available"]
    env.book_ticket("BTB102", "3A", "Rohan Mehta")
    assert env.check_availability("BTB102", "3A").data["seats_available"] == before - 1
    assert env.check_availability("BTB102", "2A").data["seats_available"] == 28  # other classes untouched
    assert env.check_availability("BTB104", "3A").data["seats_available"] == 29  # other trains untouched


def test_I_booking_until_sold_out_then_rejected_without_mutation(env):
    assert env.book_ticket("BTB104", "SL", "Kiran Patil").ok  # BTB104 SL had exactly 1 seat
    assert env.check_availability("BTB104", "SL").data["status"] == "SOLD_OUT"
    h = env.state_hash()
    r = env.book_ticket("BTB104", "SL", "Sana Khan")
    assert not r.ok and r.error.code == "SOLD_OUT"
    assert env.state_hash() == h  # failed booking leaves state byte-identical


def test_I_booking_ids_and_pnr_are_deterministic_and_sequential(env):
    a = env.book_ticket("BTB102", "3A", "Rohan Mehta").data
    b = env.book_ticket("BTB102", "2A", "Rohan Mehta").data
    assert (a["booking_id"], b["booking_id"]) == ("BK0001", "BK0002") and a["pnr"] != b["pnr"]
    env.reset()
    assert env.book_ticket("BTB102", "3A", "Rohan Mehta").data["pnr"] == a["pnr"]


def test_I_duplicate_booking_rule(env):
    assert env.book_ticket("BTB102", "3A", "Rohan Mehta").ok
    h = env.state_hash()
    r = env.book_ticket("BTB102", "3A", "  rohan   MEHTA ")  # same person after whitespace/case normalization
    assert not r.ok and r.error.code == "DUPLICATE_BOOKING"
    assert env.state_hash() == h
    assert env.book_ticket("BTB102", "2A", "Rohan Mehta").ok  # different class is a different booking
    assert env.book_ticket("BTB102", "3A", "Asha Rao").ok      # different passenger is allowed


def test_H_booking_invalid_passenger(env):
    h = env.state_hash()
    for bad in ["", "A", "रोहन मेहता", "R0han", "x" * 80]:
        r = env.book_ticket("BTB102", "3A", bad)
        assert not r.ok and r.error.code == "INVALID_PASSENGER", bad
    assert env.state_hash() == h


# ---------------------------------------------------------------- J/K: invalid class / train
def test_J_invalid_class_everywhere(env):
    h = env.state_hash()
    for fn in (env.check_availability, env.get_fare):
        assert fn("BTB102", "1A").error.code == "INVALID_CLASS"
    assert env.book_ticket("BTB102", "1A", "Rohan Mehta").error.code == "INVALID_CLASS"
    assert env.state_hash() == h


def test_J_class_not_offered_on_this_train(env):
    for fn in (env.check_availability, env.get_fare):
        assert fn("BTB105", "3A").error.code == "CLASS_NOT_OFFERED"  # day train: CC only
    h = env.state_hash()
    assert env.book_ticket("BTB101", "SL", "Rohan Mehta").error.code == "CLASS_NOT_OFFERED"
    assert env.state_hash() == h


def test_K_invalid_train_everywhere(env):
    h = env.state_hash()
    for tid in ["99999", "", "abc", "12951"]:
        assert env.get_train_details(tid).error.code == "INVALID_TRAIN"
        assert env.check_availability(tid, "3A").error.code == "INVALID_TRAIN"
        assert env.get_fare(tid, "3A").error.code == "INVALID_TRAIN"
        assert env.book_ticket(tid, "3A", "Rohan Mehta").error.code == "INVALID_TRAIN"
    assert env.state_hash() == h


# ---------------------------------------------------------------- generic dispatch (used by the future runner)
def test_call_dispatch_validation_errors_do_not_raise(env):
    assert env.call("no_such_tool", {})["error"]["code"] == "UNKNOWN_TOOL"
    assert env.call("get_fare", "not a dict")["error"]["code"] == "INVALID_ARGUMENTS"
    assert env.call("get_fare", {"train_id": "BTB102"})["error"]["code"] == "INVALID_ARGUMENTS"          # missing arg
    assert env.call("get_fare", {"train_id": "BTB102", "travel_class": "3A", "x": 1})["error"]["code"] == "INVALID_ARGUMENTS"  # extra arg
    assert env.call("get_fare", {"train_id": 12345, "travel_class": "3A"})["error"]["code"] == "INVALID_ARGUMENTS"  # wrong type
    ok = env.call("search_trains", {"source": "NDLS", "destination": "JP", "date": "2026-10-06", "time_window": None})
    assert ok["ok"] is True and ok["error"] is None


def test_every_error_result_is_machine_readable(env):
    r = env.call("book_ticket", {"train_id": "99999", "travel_class": "3A", "passenger": "Rohan Mehta"})
    assert set(r) == {"ok", "data", "error"} and r["ok"] is False and r["data"] is None
    assert set(r["error"]) == {"code", "message"} and r["error"]["code"] == "INVALID_TRAIN"


# ---------------------------------------------------------------- M: determinism at tool level
@pytest.mark.parametrize("tool,args", [
    ("resolve_station", {"name": "Delhi"}),
    ("search_trains", {"source": "MMCT", "destination": "ADI", "date": "2026-10-07"}),
    ("get_train_details", {"train_id": "BTB121"}),
    ("check_availability", {"train_id": "BTB119", "travel_class": "SL"}),
    ("get_fare", {"train_id": "BTB121", "travel_class": "3A"}),
])
def test_M_same_input_same_state_same_output(tool, args):
    from environment import RailwayEnv
    outs = []
    for _ in range(3):
        e = RailwayEnv()
        e.reset()
        outs.append(e.call(tool, args))
    assert outs[0] == outs[1] == outs[2]
