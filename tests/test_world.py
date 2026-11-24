"""Static plausibility / consistency checks for the synthetic railway world (stdlib + json only; no pydantic needed)."""
import json
import re
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "environment" / "data"
STATIONS = json.loads((DATA / "stations.json").read_text(encoding="utf-8"))["stations"]
TRAINS = json.loads((DATA / "trains.json").read_text(encoding="utf-8"))["trains"]
CODES = {s["code"] for s in STATIONS}
# Canonical codes (Indian Railways) for the 10 anchored stations.
EXPECTED_CODES = {"NDLS": "New Delhi", "NZM": "Hazrat Nizamuddin", "JP": "Jaipur Junction", "ADI": "Ahmedabad Junction",
                  "MMCT": "Mumbai Central", "PUNE": "Pune Junction", "NGP": "Nagpur Junction", "SBC": "KSR Bengaluru City",
                  "LKO": "Lucknow Charbagh", "HWH": "Howrah Junction"}
BANNED_NAME_WORDS = ["rajdhani", "shatabdi", "duronto", "deccan", "vidarbha", "sahyadri", "purvanchal", "sabarmati",
                     "aravali", "marudhar", "pink city", "gujarat", "konkan", "orange city", "nawab", "gangetic", "jaipur"]
SPEED_RANGE = {"premium": (70, 95), "sf": (55, 80), "mail": (45, 65), "day": (50, 80)}


def _m(t, day):
    return day * 1440 + int(t[:2]) * 60 + int(t[3:])


def test_stations_codes_and_no_obsolete_bct():
    assert {s["code"]: s["name"] for s in STATIONS} == EXPECTED_CODES
    assert "BCT" not in json.dumps(STATIONS) and "BCT" not in json.dumps(TRAINS)


def test_train_ids_and_count():
    ids = [t["train_id"] for t in TRAINS]
    assert ids == [f"BTB{n}" for n in range(101, 131)]


def test_names_are_fictional_and_unique_per_pair():
    for t in TRAINS:
        low = t["train_name"].lower()
        assert not any(w in low for w in BANNED_NAME_WORDS), t["train_name"]
    assert len({t["train_name"] for t in TRAINS}) == 15  # 15 services x 2 directions


@pytest.mark.parametrize("t", TRAINS, ids=lambda t: t["train_id"])
def test_route_distance_time_consistency(t):
    s = t["stops"]
    assert all(x["station"] in CODES for x in s) and len({x["station"] for x in s}) == len(s)
    assert s[0]["station"] == t["source_station"] and s[-1]["station"] == t["destination_station"]
    assert [x["distance_km"] for x in s][0] == 0
    dist = [x["distance_km"] for x in s]
    assert all(b > a for a, b in zip(dist, dist[1:])), "cumulative distance must be strictly increasing"
    # times strictly non-decreasing along the journey
    seq = [_m(s[0]["departure"], s[0]["departure_day"])]
    for x in s[1:]:
        a = _m(x["arrival"], x["arrival_day"]); assert a > seq[-1]
        seq.append(a)
        if x["departure"]:
            d = _m(x["departure"], x["departure_day"]); assert d >= a
            seq.append(d)
    hours = (_m(s[-1]["arrival"], s[-1]["arrival_day"]) - _m(s[0]["departure"], s[0]["departure_day"])) / 60
    speed = dist[-1] / hours
    lo, hi = SPEED_RANGE[t["train_type"]]
    assert lo <= speed <= hi, f"{t['train_id']} avg speed {speed:.1f}"
    assert 100 <= dist[-1] <= 2600
    assert re.fullmatch(r"\d\d:\d\d", s[0]["departure"])


def test_reverse_trains_have_symmetric_distances():
    by = {t["train_id"]: t for t in TRAINS}
    for n in range(101, 131, 2):
        f, r = by[f"BTB{n}"], by[f"BTB{n+1}"]
        assert f["train_name"] == r["train_name"] and f["classes"].keys() == r["classes"].keys()
        fs, rs = f["stops"], r["stops"]
        assert [x["station"] for x in fs] == [x["station"] for x in reversed(rs)]
        tot = fs[-1]["distance_km"]
        assert [x["distance_km"] for x in fs] == [tot - x["distance_km"] for x in reversed(rs)]
        assert {k: v["fare_inr"] for k, v in f["classes"].items()} == {k: v["fare_inr"] for k, v in r["classes"].items()}


def test_fare_relationships():
    for t in TRAINS:
        c = {k: v["fare_inr"] for k, v in t["classes"].items()}
        if "2A" in c and "3A" in c:
            assert c["2A"] >= c["3A"]
        if "3A" in c and "SL" in c:
            assert c["3A"] > c["SL"]
        if "CC" in c:
            assert t["train_type"] == "day" and t["stops"][-1]["arrival_day"] == 0 and t["stops"][-1]["distance_km"] <= 600


def test_availability_variety_preserved():
    seats = [v["seats"] for t in TRAINS for v in t["classes"].values()]
    assert 0 in seats and any(1 <= x <= 3 for x in seats) and any(x >= 20 for x in seats)


def test_generator_output_matches_committed_file():
    from environment import build_world
    assert build_world.render() == (DATA / "trains.json").read_text(encoding="utf-8")
