"""Deterministic generator for environment/data/trains.json (the SYNTHETIC BharatToolBench railway world).

Everything in here is synthetic: train IDs (BTB101..BTB130), train names, schedules, distances, fares, seats.
Only the 10 stations (codes/names/cities/states) are real-world anchored (see benchmark/data_provenance.md).
Distances are synthetic plausibility fixtures, NOT claims of exact live railway distances.

Usage:  python -m environment.build_world            # rewrites environment/data/trains.json
        python -m environment.build_world --check    # exits 1 if the committed file differs from regeneration
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(__file__).parent / "data" / "trains.json"
ALL_DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

# Segment distances (km, synthetic plausibility fixtures). Reverse trains reuse the same segments, so
# cumulative distances are symmetric by construction.
CORRIDORS = {
    "NDLS-MMCT": [("NDLS", "JP", 308), ("JP", "ADI", 627), ("ADI", "MMCT", 491)],
    "NDLS-HWH": [("NDLS", "LKO", 510), ("LKO", "HWH", 940)],
    "MMCT-SBC": [("MMCT", "PUNE", 192), ("PUNE", "SBC", 838)],
    "NZM-SBC": [("NZM", "NGP", 1090), ("NGP", "SBC", 1310)],
    "ADI-PUNE": [("ADI", "MMCT", 491), ("MMCT", "PUNE", 192)],
}
DIRECT = {  # direct two-station services: (a, b) -> km
    ("JP", "ADI"): 627, ("NDLS", "JP"): 308, ("NDLS", "LKO"): 510, ("MMCT", "PUNE"): 192,
    ("MMCT", "NGP"): 835, ("ADI", "MMCT"): 491, ("PUNE", "NGP"): 880, ("NZM", "JP"): 310,
}

# Average running speed (km/h, excluding halts) per service type; halt at each intermediate stop in minutes.
SPEED = {"premium": 82, "sf": 66, "mail": 56, "day": 66}
HALT_MIN = 5

# Fare rule (INR per km of the train's FULL journey, per class and type), rounded to the nearest INR 5.
# Fare is per (train, class), not per boarding/alighting pair (documented tool-contract simplification).
FARE_PER_KM = {
    "premium": {"3A": 2.20, "2A": 3.15},
    "sf": {"SL": 0.70, "3A": 1.75, "2A": 2.50},
    "mail": {"SL": 0.66, "3A": 1.65, "2A": 2.35},
    "day": {"CC": 1.60},
}
MIN_FARE = {"SL": 100, "3A": 300, "2A": 450, "CC": 150}

# (forward id, reverse id, name, type, corridor/direct key, fwd origin dep, rev origin dep,
#  fwd op days, rev op days, fwd seats, rev seats).  Seats are synthetic baseline availability.
SERVICES = [
    (101, 102, "Meridian Premium Link", "premium", "NDLS-MMCT", "16:30", "17:00", ALL_DAYS, ALL_DAYS, {"2A": 0, "3A": 8}, {"2A": 28, "3A": 2}),
    (103, 104, "Saffron Arc Superfast", "sf", "NDLS-MMCT", "21:15", "20:30", ALL_DAYS, ALL_DAYS, {"SL": 9, "3A": 0, "2A": 35}, {"SL": 1, "3A": 29, "2A": 42}),
    (105, 106, "Quartz Day Link", "day", ("NDLS", "JP"), "06:05", "15:40", ALL_DAYS, ALL_DAYS, {"CC": 26}, {"CC": 33}),
    (107, 108, "Indigo Night Link", "mail", ("JP", "ADI"), "22:40", "21:50", ALL_DAYS, ["MON", "WED", "FRI", "SUN"], {"SL": 37, "3A": 14}, {"SL": 8, "3A": 21}),
    (109, 110, "Cobalt Eastern Premium", "premium", "NDLS-HWH", "17:20", "16:55", ALL_DAYS, ALL_DAYS, {"2A": 41, "3A": 0}, {"2A": 12, "3A": 35}),
    (111, 112, "Amber Eastern Superfast", "sf", "NDLS-HWH", "20:05", "19:30", ["TUE", "THU", "SAT"], ALL_DAYS, {"SL": 29, "3A": 42, "2A": 19}, {"SL": 36, "3A": 13, "2A": 26}),
    (113, 114, "Teal Plains Day Link", "day", ("NDLS", "LKO"), "06:10", "15:25", ALL_DAYS, ALL_DAYS, {"CC": 10}, {"CC": 0}),
    (115, 116, "Jade Peninsula Superfast", "sf", "MMCT-SBC", "06:00", "05:40", ALL_DAYS, ALL_DAYS, {"SL": 21, "3A": 34, "2A": 11}, {"SL": 28, "3A": 41, "2A": 18}),
    (117, 118, "Opal Ghat Day Link", "day", ("MMCT", "PUNE"), "07:15", "16:10", ALL_DAYS, ALL_DAYS, {"CC": 2}, {"CC": 9}),
    (119, 120, "Garnet Central Superfast", "sf", ("MMCT", "NGP"), "20:25", "18:40", ALL_DAYS, ALL_DAYS, {"SL": 0, "3A": 26, "2A": 39}, {"SL": 20, "3A": 33, "2A": 10}),
    (121, 122, "Onyx Trunk Premium", "premium", "NZM-SBC", "11:10", "06:30", ALL_DAYS, ["MON", "TUE", "THU", "FRI", "SUN"], {"2A": 0, "3A": 40}, {"2A": 24, "3A": 11}),
    (123, 124, "Coral Western Night Mail", "mail", "ADI-PUNE", "22:10", "20:20", ALL_DAYS, ALL_DAYS, {"SL": 41, "3A": 18}, {"SL": 12, "3A": 25}),
    (125, 126, "Topaz Coastal Day Link", "day", ("ADI", "MMCT"), "06:20", "14:05", ALL_DAYS, ALL_DAYS, {"CC": 3}, {"CC": 29}),
    (127, 128, "Citrine Plateau Superfast", "sf", ("PUNE", "NGP"), "18:15", "17:30", ALL_DAYS, ALL_DAYS, {"SL": 33, "3A": 10, "2A": 23}, {"SL": 40, "3A": 17, "2A": 30}),
    (129, 130, "Ruby Shuttle Link", "day", ("NZM", "JP"), "07:30", "17:45", ["MON", "WED", "FRI"], ALL_DAYS, {"CC": 14}, {"CC": 1}),
]


def _stops_for(key) -> list[tuple[str, int]]:
    """Forward stop list [(station, cumulative_km)]."""
    if isinstance(key, tuple):
        return [(key[0], 0), (key[1], DIRECT[key])]
    stops, cum = [(CORRIDORS[key][0][0], 0)], 0
    for _a, b, km in CORRIDORS[key]:
        cum += km
        stops.append((b, cum))
    return stops


def _hhmm(total_min: int) -> tuple[str, int]:
    return f"{(total_min % 1440) // 60:02d}:{total_min % 60:02d}", total_min // 1440


def _r5(x: float) -> int:
    return int(5 * round(x / 5))


def _fares(ttype: str, total_km: int, seats: dict[str, int]) -> dict:
    out = {}
    for cls in seats:
        fare = max(MIN_FARE[cls], _r5(total_km * FARE_PER_KM[ttype][cls]))
        out[cls] = {"fare_inr": fare, "seats": seats[cls]}
    return out


def _build_train(tid: int, name: str, ttype: str, stops: list[tuple[str, int]], dep: str, days: list[str], seats: dict) -> dict:
    t0 = int(dep[:2]) * 60 + int(dep[3:])
    rows, clock = [], t0
    total = stops[-1][1]
    for i, (st, km) in enumerate(stops):
        if i == 0:
            d, dd = _hhmm(t0)
            rows.append({"station": st, "arrival": None, "arrival_day": None, "departure": d, "departure_day": dd, "distance_km": 0})
            continue
        clock = t0 + _r5((km / SPEED[ttype]) * 60) + HALT_MIN * (i - 1)
        # clock is a multiple of 5 only if t0 is; t0 values are all multiples of 5.
        a, ad = _hhmm(clock)
        if i == len(stops) - 1:
            rows.append({"station": st, "arrival": a, "arrival_day": ad, "departure": None, "departure_day": None, "distance_km": km})
        else:
            d, dd = _hhmm(clock + HALT_MIN)
            rows.append({"station": st, "arrival": a, "arrival_day": ad, "departure": d, "departure_day": dd, "distance_km": km})
    return {
        "train_id": f"BTB{tid}", "train_name": name, "train_type": ttype,
        "source_station": stops[0][0], "destination_station": stops[-1][0],
        "operating_days": list(days), "stops": rows, "classes": _fares(ttype, total, seats),
    }


def build() -> dict:
    trains = []
    for fid, rid, name, ttype, key, fdep, rdep, fdays, rdays, fseats, rseats in SERVICES:
        fwd = _stops_for(key)
        total = fwd[-1][1]
        rev = [(st, total - km) for st, km in reversed(fwd)]
        trains.append(_build_train(fid, name, ttype, fwd, fdep, fdays, fseats))
        trains.append(_build_train(rid, name, ttype, rev, rdep, rdays, rseats))
    return {"_comment": "SYNTHETIC railway services for BharatToolBench. NOT actual Indian Railways services. "
                        "Generated by environment/build_world.py; do not hand-edit.",
            "trains": trains}


def render() -> str:
    return json.dumps(build(), indent=1, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    text = render()
    if "--check" in sys.argv:
        sys.exit(0 if OUT.read_text(encoding="utf-8") == text else 1)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({len(build()['trains'])} trains)")
