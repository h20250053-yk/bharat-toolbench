"""Generate benchmark/gold_labels.json by SOLVING each semantic task spec against the deterministic environment.

No LLM, no network, no randomness, no hand-edited values. Run:   python -m benchmark.build_gold
Re-running must reproduce gold_labels.json byte-for-byte (asserted in tests/test_gold.py).

Conventions
  * required_args hold exact canonical values (station CODES, ISO dates, HH:MM, class enum, train ids).
  * resolve_station.name is language-specific, so its gold arg is a matcher {"resolves_to": "<code>"}.
  * `args_from` documents where a derived value comes from (an earlier call's output).
  * dependency edge (a -> b): call b needs the OUTPUT of call a. Calls with no edge may occur in any order.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from environment import RailwayEnv

from .schemas import DependencyEdge, FinalStatePredicate, GoldSpec, RequiredCall
from .task_spec import SemanticTaskSpec

BENCH_DIR = Path(__file__).resolve().parent
SPEC_PATH = BENCH_DIR / "semantic_tasks.json"
GOLD_PATH = BENCH_DIR / "gold_labels.json"
END_OF_DAY = "23:59"


class _Plan:
    """Accumulates required calls (ids c1, c2, ...) and dependency edges."""

    def __init__(self) -> None:
        self.calls: list[RequiredCall] = []
        self.edges: list[DependencyEdge] = []

    def add(self, tool: str, required_args: dict[str, Any], args_from: dict[str, str] | None = None,
            after: list[str] | None = None, alternatives: dict[str, list[Any]] | None = None,
            optional: bool = False, expected_error: str | None = None) -> str:
        cid = f"c{len(self.calls) + 1}"
        self.calls.append(RequiredCall(call_id=cid, tool=tool, required_args=required_args,
                                       args_from=args_from or {}, arg_alternatives=alternatives or {},
                                       optional=optional, expected_error=expected_error))
        self.edges += [DependencyEdge(before=b, after=cid) for b in (after or [])]
        return cid


def _ok(env: RailwayEnv, tool: str, args: dict[str, Any]) -> dict[str, Any]:
    r = env.call(tool, args)
    if not r["ok"]:
        raise ValueError(f"solver call failed: {tool}({args}) -> {r['error']}")
    return r["data"]


def _station_code(env: RailwayEnv, name: str) -> str:
    d = _ok(env, "resolve_station", {"name": name})
    if d["ambiguous"]:
        raise ValueError(f"spec uses ambiguous station name {name!r}: {d['candidates']}")
    return d["candidates"][0]["code"]


def _resolve_calls(env: RailwayEnv, plan: _Plan, src_name: str, dst_name: str) -> tuple[str, str, list[str]]:
    src, dst = _station_code(env, src_name), _station_code(env, dst_name)
    c1 = plan.add("resolve_station", {"name": {"resolves_to": src}})
    c2 = plan.add("resolve_station", {"name": {"resolves_to": dst}})
    return src, dst, [c1, c2]


# ----------------------------------------------------------------------------------------- solvers
def _solve_fare_lookup(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    fare = _ok(env, "get_fare", {"train_id": p["train_id"], "travel_class": p["travel_class"]})
    plan.add("get_fare", {"train_id": p["train_id"], "travel_class": p["travel_class"]})
    answer = {"status": "success", "selected_train_id": p["train_id"], "travel_class": p["travel_class"],
              "fare_inr": fare["fare_inr"]}
    return answer, [p["train_id"]], []


def _solve_route_availability_fare(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    found = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})
    if found["count"] != 1:
        raise ValueError(f"T-spec needs exactly one train on the route, found {found['count']}")
    tid, cls = found["trains"][0]["train_id"], p["travel_class"]
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    avail, fare = _ok(env, "check_availability", {"train_id": tid, "travel_class": cls}), _ok(env, "get_fare", {"train_id": tid, "travel_class": cls})
    ref = {"train_id": f"{c3}.trains[*].train_id"}
    plan.add("check_availability", {"train_id": tid, "travel_class": cls}, ref, after=[c3])
    plan.add("get_fare", {"train_id": tid, "travel_class": cls}, ref, after=[c3])
    answer = {"status": "success", "selected_train_id": tid, "travel_class": cls,
              "available": avail["seats_available"] > 0, "seats_available": avail["seats_available"],
              "fare_inr": fare["fare_inr"]}
    return answer, [tid], []


def _solve_constrained_choice(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    window = {"start": p["departure_not_before"], "end": END_OF_DAY}
    found = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"], "time_window": window})
    cls = p["travel_class"]
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"], "time_window": window},
                  after=resolves, alternatives={"time_window": [None]})  # omitting the window and filtering manually is acceptable
    ref = {"train_id": f"{c3}.trains[*].train_id"}
    candidates = [t["train_id"] for t in found["trains"] if cls in t["classes"]]
    within_budget: list[str] = []
    fares: dict[str, int] = {}
    for tid in candidates:  # a fare check on every in-window candidate is needed to apply the budget
        fares[tid] = _ok(env, "get_fare", {"train_id": tid, "travel_class": cls})["fare_inr"]
        plan.add("get_fare", {"train_id": tid, "travel_class": cls}, ref, after=[c3])
        if fares[tid] <= p["max_fare_inr"]:
            within_budget.append(tid)
    valid: list[str] = []
    seats: dict[str, int] = {}
    for tid in within_budget:  # availability needed for every candidate that survives the budget
        seats[tid] = _ok(env, "check_availability", {"train_id": tid, "travel_class": cls})["seats_available"]
        plan.add("check_availability", {"train_id": tid, "travel_class": cls}, ref, after=[c3])
        if seats[tid] > 0:
            valid.append(tid)
    if len(valid) != 1:
        raise ValueError(f"constraint task must have a unique answer, got {valid}")
    tid = valid[0]
    answer = {"status": "success", "selected_train_id": tid, "travel_class": cls, "fare_inr": fares[tid],
              "seats_available": seats[tid]}
    return answer, valid, []


def _solve_cheapest_booking(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    found = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})
    cls = p["travel_class"]
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    ref = {"train_id": f"{c3}.trains[*].train_id"}
    candidates = [t["train_id"] for t in found["trains"] if cls in t["classes"]]
    fares: dict[str, int] = {}
    fare_calls: list[str] = []
    for tid in candidates:  # to know which train is cheapest, every candidate's fare is needed
        fares[tid] = _ok(env, "get_fare", {"train_id": tid, "travel_class": cls})["fare_inr"]
        fare_calls.append(plan.add("get_fare", {"train_id": tid, "travel_class": cls}, ref, after=[c3]))
    cheapest = min(fares.values())
    winners = [t for t, f in fares.items() if f == cheapest]
    if len(winners) != 1:
        raise ValueError(f"cheapest train is not unique: {winners}")
    tid = winners[0]
    if _ok(env, "check_availability", {"train_id": tid, "travel_class": cls})["seats_available"] <= 0:
        raise ValueError("cheapest train is sold out: that would be a recovery task, not a plain booking task")
    plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": p["passenger"]}, ref, after=[c3] + fare_calls)
    effect = [("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": p["passenger"]})]
    return {"status": "success", "selected_train_id": tid, "travel_class": cls, "fare_inr": fares[tid],
            "passenger": p["passenger"], "booking_id": None}, [tid], effect  # booking_id filled from the replay


def _solve_conditional_booking(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    tid, cls, pax = p["train_id"], p["travel_class"], p["passenger"]
    avail = _ok(env, "check_availability", {"train_id": tid, "travel_class": cls})
    plan.add("check_availability", {"train_id": tid, "travel_class": cls})
    if avail["seats_available"] > 0:
        plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": pax}, after=["c1"])
        return ({"status": "success", "selected_train_id": tid, "travel_class": cls, "passenger": pax, "booking_id": None},
                [tid], [("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": pax})])
    # sold out and no fallback permitted: the correct outcome is NO booking and an honest report
    return ({"status": "cannot_complete", "selected_train_id": None, "travel_class": cls,
             "seats_available": avail["seats_available"], "reason": "sold_out"}, None, [])


# ------------------------------------------------------------------ batch T06-T15 solvers
# Each solver asserts the design property that makes its task meaningful, so a later fixture change that silently
# turns a task into a trivial or duplicate one fails gold generation instead of producing misleading gold.
def _mins(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:])


def _verify_train_serves(env: RailwayEnv, p: dict[str, Any]) -> tuple[str, str]:
    """For named-train tasks that also state a route/date: the named train must really run on that route and date.
    Verification only; these calls are NOT added to the gold plan (the user already named the train)."""
    src, dst = _station_code(env, p["source_name"]), _station_code(env, p["destination_name"])
    found = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})
    if p["train_id"] not in [t["train_id"] for t in found["trains"]]:
        raise ValueError(f"{p['train_id']} does not run {src}->{dst} on {p['date']}")
    return src, dst


def _solve_operating_days_lookup(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    tid = p["train_id"]
    d = _ok(env, "get_train_details", {"train_id": tid})
    board = _station_code(env, p["boarding_station_name"])
    if d["source_station"] != board:  # operating_days are origin weekdays; boarding elsewhere would shift them
        raise ValueError(f"{tid}: boarding station {board} is not the origin {d['source_station']}")
    plan.add("get_train_details", {"train_id": tid})
    answer = {"status": "success", "selected_train_id": tid, "boarding_station": board,
              "operating_days": d["operating_days"], "requested_weekday": p["weekday"],
              "runs_on_requested_weekday": p["weekday"] in d["operating_days"]}
    return answer, [tid], []


def _solve_intermediate_stop_time(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    found = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})
    if found["count"] != 1:
        raise ValueError(f"intermediate-stop task needs exactly one train on the route, found {found['count']}")
    tid = found["trains"][0]["train_id"]
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    det = _ok(env, "get_train_details", {"train_id": tid})
    plan.add("get_train_details", {"train_id": tid}, {"train_id": f"{c3}.trains[*].train_id"}, after=[c3])
    stop = _station_code(env, p["stop_name"])
    codes = [s["station"] for s in det["stops"]]
    if stop not in codes[1:-1]:
        raise ValueError(f"{stop} is not an intermediate stop of {tid}")
    # the stop's code can be read directly from the details output; resolving the stop name is helpful but optional
    plan.add("resolve_station", {"name": {"resolves_to": stop}}, optional=True)
    s = det["stops"][codes.index(stop)]
    answer = {"status": "success", "selected_train_id": tid, "stop_station": stop,
              "stop_arrival_time": s["arrival"], "stop_departure_time": s["departure"]}
    return answer, [tid], []


def _solve_empty_window_fallback(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    window = {"start": p["window_start"], "end": p["window_end"]}
    first = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"], "time_window": window})
    if first["count"] != 0:
        raise ValueError("empty-window task: the requested window must contain no train")
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"], "time_window": window},
                  after=resolves, alternatives={"time_window": [None]})  # an unwindowed search + manual filter is fine
    after = p["fallback_strictly_after"]
    every = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})["trains"]
    if any(t["departure"] == after for t in every):
        raise ValueError("a train departs exactly at the fallback boundary: 'after' would be ambiguous")
    later = [t for t in every if _mins(t["departure"]) > _mins(after)]
    if not later:
        raise ValueError("no fallback train exists")
    first_dep = min(_mins(t["departure"]) for t in later)
    best = [t for t in later if _mins(t["departure"]) == first_dep]
    if len(best) != 1:
        raise ValueError(f"earliest fallback train not unique: {best}")
    nxt = f"{(_mins(after) + 1) // 60:02d}:{(_mins(after) + 1) % 60:02d}"
    plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"],
                               "time_window": {"start": after, "end": END_OF_DAY}},
             after=resolves + [c3],  # the fallback search is only justified by the empty result of c3
             alternatives={"time_window": [None, {"start": nxt, "end": END_OF_DAY}]})
    t = best[0]
    answer = {"status": "success", "requested_window_train_count": 0, "fallback_used": True,
              "selected_train_id": t["train_id"], "departure": t["departure"]}
    return answer, [t["train_id"]], []


def _solve_ambiguous_station_clarification(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    r = _ok(env, "resolve_station", {"name": p["source_name"]})
    if not r["ambiguous"]:
        raise ValueError(f"{p['source_name']!r} is not ambiguous")
    cands = sorted(c["code"] for c in r["candidates"])
    dst, cls = _station_code(env, p["destination_name"]), p["travel_class"]
    viable = {}
    for code in cands:  # the ambiguity must be MATERIAL: each reading leads to a different bookable train
        trains = _ok(env, "search_trains", {"source": code, "destination": dst, "date": p["date"]})["trains"]
        viable[code] = [t["train_id"] for t in trains if cls in t["classes"]
                        and _ok(env, "check_availability", {"train_id": t["train_id"], "travel_class": cls})["seats_available"] > 0]
    if sum(1 for v in viable.values() if v) < 2:
        raise ValueError(f"ambiguity is not material (only one reading is bookable): {viable}")
    if len({tuple(v) for v in viable.values()}) < 2:
        raise ValueError("both readings lead to the same trains")
    # Asking without a tool call is acceptable (the user said only 'Delhi'), so the resolve call is optional.
    plan.add("resolve_station", {"name": {"resolves_ambiguous": cands}}, optional=True)
    answer = {"status": "needs_clarification", "clarification_needed": "source_station",
              "candidate_station_codes": cands, "selected_train_id": None, "travel_class": cls}
    return answer, None, []


def _solve_fallback_class_booking(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    _verify_train_serves(env, p)
    tid, pref, fb, pax = p["train_id"], p["travel_class"], p["fallback_class"], p["passenger"]
    if _ok(env, "check_availability", {"train_id": tid, "travel_class": pref})["seats_available"] > 0:
        raise ValueError("preferred class has seats: the fallback would never trigger")
    if _ok(env, "check_availability", {"train_id": tid, "travel_class": fb})["seats_available"] <= 0:
        raise ValueError("fallback class is also sold out")
    c1 = plan.add("check_availability", {"train_id": tid, "travel_class": pref})
    plan.add("book_ticket", {"train_id": tid, "travel_class": fb, "passenger": pax}, after=[c1])
    fare = _ok(env, "get_fare", {"train_id": tid, "travel_class": fb})["fare_inr"]
    answer = {"status": "success", "selected_train_id": tid, "travel_class": fb, "requested_class": pref,
              "requested_class_status": "SOLD_OUT", "fallback_used": True, "passenger": pax, "fare_inr": fare,
              "booking_id": None}
    return answer, [tid], [("book_ticket", {"train_id": tid, "travel_class": fb, "passenger": pax})]


def _solve_class_not_offered(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    tid, cls = p["train_id"], p["travel_class"]
    r = env.call("get_fare", {"train_id": tid, "travel_class": cls})
    if r["ok"] or r["error"]["code"] != "CLASS_NOT_OFFERED":
        raise ValueError(f"expected CLASS_NOT_OFFERED for {tid}/{cls}, got {r}")
    plan.add("get_fare", {"train_id": tid, "travel_class": cls}, optional=True, expected_error="CLASS_NOT_OFFERED")
    d = _ok(env, "get_train_details", {"train_id": tid})
    plan.add("get_train_details", {"train_id": tid})  # needed to tell the user which classes the train DOES have
    answer = {"status": "cannot_complete", "selected_train_id": None, "train_id": tid, "travel_class": cls,
              "reason": "CLASS_NOT_OFFERED", "offered_classes": d["classes"]}
    return answer, None, []


def _solve_arrival_deadline_latest_departure(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    from datetime import date as _D, datetime as _DT, timedelta as _TD
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    found = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})
    plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    board = _D.fromisoformat(p["date"])
    deadline = _DT.fromisoformat(f"{p['arrive_by_date']}T{p['arrive_by_time']}")

    def arrival(t):
        return _DT.combine(board + _TD(days=t["arrival_day_offset"]), _DT.min.time()) + _TD(minutes=_mins(t["arrival"]))
    ok = [t for t in found["trains"] if arrival(t) <= deadline]
    if len(ok) < 2:
        raise ValueError("deadline must leave a real choice between at least two trains")
    latest_overall = max(found["trains"], key=lambda t: _mins(t["departure"]))
    if latest_overall in ok:
        raise ValueError("deadline does not prune the naive latest-departure answer")
    late = max(_mins(t["departure"]) for t in ok)
    best = [t for t in ok if _mins(t["departure"]) == late]
    if len(best) != 1:
        raise ValueError("latest valid departure is not unique")
    t = best[0]
    answer = {"status": "success", "selected_train_id": t["train_id"], "departure": t["departure"],
              "arrival": t["arrival"], "arrival_date": arrival(t).date().isoformat()}
    return answer, [t["train_id"]], []


def _solve_timed_group_booking(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    found = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})
    match = [t for t in found["trains"] if t["departure"] == p["departure_time"]]
    if len(match) != 1:
        raise ValueError(f"exactly one train must depart at {p['departure_time']}, found {match}")
    tid, cls, pax = match[0]["train_id"], p["travel_class"], p["passengers"]
    if cls not in match[0]["classes"]:
        raise ValueError(f"{tid} does not offer {cls}")
    if len(set(x.casefold() for x in pax)) != len(pax):
        raise ValueError("passenger names must be distinct (duplicate-booking rule)")
    if _ok(env, "check_availability", {"train_id": tid, "travel_class": cls})["seats_available"] < len(pax):
        raise ValueError("not enough seats for the group: that is an all-or-nothing task, not a plain booking")
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    ref = {"train_id": f"{c3}.trains[*].train_id"}
    effect = []
    for name in pax:  # the two bookings are independent of each other: any order is valid
        plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": name}, ref, after=[c3])
        effect.append(("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": name}))
    fare = _ok(env, "get_fare", {"train_id": tid, "travel_class": cls})["fare_inr"]
    answer = {"status": "success", "selected_train_id": tid, "travel_class": cls, "departure": p["departure_time"],
              "passengers": pax, "fare_inr_per_ticket": fare, "booking_ids": None}
    return answer, [tid], effect


def _solve_cheapest_available_class(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    _verify_train_serves(env, p)
    tid = p["train_id"]
    classes = _ok(env, "get_train_details", {"train_id": tid})["classes"]
    seats = {c: _ok(env, "check_availability", {"train_id": tid, "travel_class": c})["seats_available"] for c in classes}
    fares = {c: _ok(env, "get_fare", {"train_id": tid, "travel_class": c})["fare_inr"] for c in classes}
    avail = [c for c in classes if seats[c] > 0]
    low = min(fares[c] for c in avail)
    win = [c for c in avail if fares[c] == low]
    if len(win) != 1:
        raise ValueError(f"cheapest available class not unique: {win}")
    w = win[0]
    if min(fares.values()) == low:
        raise ValueError("cheapest class overall has seats: availability would not matter")
    # the class list may come from get_train_details OR from a search result's `classes`: optional
    plan.add("get_train_details", {"train_id": tid}, optional=True)
    plan.add("check_availability", {"train_id": tid, "travel_class": w})
    plan.add("get_fare", {"train_id": tid, "travel_class": w})
    # minimal PROOF that w is the answer: every cheaper class is shown sold out, every other class is shown pricier
    for c in sorted(classes):
        if c == w:
            continue
        if fares[c] < low:
            plan.add("check_availability", {"train_id": tid, "travel_class": c})
        elif fares[c] > low:
            plan.add("get_fare", {"train_id": tid, "travel_class": c})
        else:
            raise ValueError("fare tie")
    answer = {"status": "success", "selected_train_id": tid, "travel_class": w, "fare_inr": low,
              "seats_available": seats[w], "excluded_cheaper_sold_out": sorted(c for c in classes if fares[c] < low)}
    return answer, [tid], []


def _solve_group_all_or_nothing(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    _verify_train_serves(env, p)
    tid, cls, pax = p["train_id"], p["travel_class"], p["passengers"]
    seats = _ok(env, "check_availability", {"train_id": tid, "travel_class": cls})["seats_available"]
    if seats == 0:
        raise ValueError("sold out: that would duplicate the T05 sold-out pattern; this task needs 0 < seats < group")
    if seats >= len(pax):
        raise ValueError("enough seats: the all-or-nothing condition would be met")
    plan.add("check_availability", {"train_id": tid, "travel_class": cls})
    answer = {"status": "cannot_complete", "selected_train_id": None, "train_id": tid, "travel_class": cls,
              "seats_available": seats, "passengers_requested": len(pax), "reason": "insufficient_seats_for_group"}
    return answer, None, []



# ------------------------------------------------------------------ batch T16-T25 solvers
def _solve_station_identity(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    d = _ok(env, "resolve_station", {"name": p["station_name"]})
    if d["ambiguous"]:
        raise ValueError("station identity task needs an unambiguous name")
    c = d["candidates"][0]
    plan.add("resolve_station", {"name": {"resolves_to": c["code"]}})
    return {"status": "success", "station_code": c["code"], "station_name": c["name"], "city": c["city"]}, None, []


def _solve_segment_distance(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    tid = p["train_id"]
    det = _ok(env, "get_train_details", {"train_id": tid})
    codes = [s["station"] for s in det["stops"]]
    a, b = _station_code(env, p["from_name"]), _station_code(env, p["to_name"])
    if a not in codes or b not in codes or codes.index(a) >= codes.index(b):
        raise ValueError(f"{tid} does not run {a}->{b}")
    if codes.index(a) == 0:
        raise ValueError("segment starts at the origin: the naive cumulative distance would already be correct")
    plan.add("get_train_details", {"train_id": tid})
    plan.add("resolve_station", {"name": {"resolves_to": a}}, optional=True)  # codes are readable from the stop list
    plan.add("resolve_station", {"name": {"resolves_to": b}}, optional=True)
    da, db = det["stops"][codes.index(a)]["distance_km"], det["stops"][codes.index(b)]["distance_km"]
    return {"status": "success", "selected_train_id": tid, "from_station": a, "to_station": b,
            "segment_distance_km": db - da, "naive_cumulative_km_at_destination": db}, [tid], []


def _solve_unknown_station(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    r = env.call("resolve_station", {"name": p["source_name"]})
    if r["ok"] or r["error"]["code"] != "STATION_NOT_FOUND":
        raise ValueError(f"{p['source_name']!r} must be unknown to the environment, got {r}")
    dst = _station_code(env, p["destination_name"])
    plan.add("resolve_station", {"name": {"resolves_to_none": True}}, expected_error="STATION_NOT_FOUND")
    plan.add("resolve_station", {"name": {"resolves_to": dst}}, optional=True)
    return {"status": "cannot_complete", "selected_train_id": None, "reason": "STATION_NOT_FOUND",
            "unknown_station_role": "source", "destination_station": dst}, None, []


def _solve_missing_passenger_clarification(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    _verify_train_serves(env, p)
    tid, cls = p["train_id"], p["travel_class"]
    if _ok(env, "check_availability", {"train_id": tid, "travel_class": cls})["seats_available"] <= 0:
        raise ValueError("seats must exist so that the passenger name is the ONLY missing piece")
    plan.add("check_availability", {"train_id": tid, "travel_class": cls}, optional=True)
    return {"status": "needs_clarification", "clarification_needed": "passenger_name", "selected_train_id": None,
            "train_id": tid, "travel_class": cls}, None, []


def _solve_no_route_booking(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    from datetime import timedelta as _TD
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    start = env.reference_datetime.date()
    for i in range(7):  # the route must be empty on EVERY day of the simulated service window, so the date is not the issue
        d = (start + _TD(days=i)).isoformat()
        if _ok(env, "search_trains", {"source": src, "destination": dst, "date": d})["count"] != 0:
            raise ValueError(f"route {src}->{dst} has a train on {d}: not a no-service task")
    plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    return {"status": "cannot_complete", "selected_train_id": None, "travel_class": p["travel_class"],
            "reason": "no_direct_train", "trains_found": 0}, None, []


def _solve_train_direction_conflict(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    tid = p["train_id"]
    det = _ok(env, "get_train_details", {"train_id": tid})
    codes = [s["station"] for s in det["stops"]]
    src, dst = _station_code(env, p["source_name"]), _station_code(env, p["destination_name"])
    if not (src in codes and dst in codes and codes.index(dst) < codes.index(src)):
        raise ValueError("the named train must run the stated stations in the OPPOSITE direction")
    if not _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})["trains"]:
        raise ValueError("no train runs the stated direction: then the request would be cannot_complete, not a real conflict")
    plan.add("get_train_details", {"train_id": tid})
    return {"status": "needs_clarification", "clarification_needed": "train_route_conflict", "selected_train_id": None,
            "train_id": tid, "train_runs": [det["source_station"], det["destination_station"]],
            "requested": [src, dst]}, None, []


def _solve_earliest_with_seats_booking(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls, pax = p["travel_class"], p["passenger"]
    found = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    ref = {"train_id": f"{c3}.trains[*].train_id"}
    offering = sorted((t for t in found["trains"] if cls in t["classes"]), key=lambda t: (_mins(t["departure"]), t["train_id"]))
    skipped, winner = [], None
    for t in offering:
        seats = _ok(env, "check_availability", {"train_id": t["train_id"], "travel_class": cls})["seats_available"]
        if seats > 0:
            winner = t
            break
        skipped.append(plan.add("check_availability", {"train_id": t["train_id"], "travel_class": cls}, ref, after=[c3]))
    if winner is None or not skipped:
        raise ValueError("the earliest train in the class must be sold out and a later one must have seats")
    plan.add("book_ticket", {"train_id": winner["train_id"], "travel_class": cls, "passenger": pax}, ref, after=[c3] + skipped)
    fare = _ok(env, "get_fare", {"train_id": winner["train_id"], "travel_class": cls})["fare_inr"]
    return ({"status": "success", "selected_train_id": winner["train_id"], "travel_class": cls, "departure": winner["departure"],
             "skipped_sold_out": [t["train_id"] for t in offering[:len(skipped)]], "passenger": pax, "fare_inr": fare, "booking_id": None},
            [winner["train_id"]], [("book_ticket", {"train_id": winner["train_id"], "travel_class": cls, "passenger": pax})])


def _solve_round_trip_booking(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls, pax, legs, effect = p["travel_class"], p["passenger"], [], []
    for a, b, d in ((src, dst, p["date"]), (dst, src, p["return_date"])):
        tr = [t for t in _ok(env, "search_trains", {"source": a, "destination": b, "date": d})["trains"] if cls in t["classes"]]
        if len(tr) != 1:
            raise ValueError(f"each leg needs exactly one {cls} train, {a}->{b} on {d} has {len(tr)}")
        if _ok(env, "check_availability", {"train_id": tr[0]["train_id"], "travel_class": cls})["seats_available"] <= 0:
            raise ValueError("leg sold out")
        cs = plan.add("search_trains", {"source": a, "destination": b, "date": d}, after=resolves)
        legs.append((tr[0]["train_id"], cs))
    if legs[0][0] == legs[1][0]:
        raise ValueError("outbound and return must be different trains")
    for tid, cs in legs:
        plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": pax}, {"train_id": f"{cs}.trains[*].train_id"}, after=[cs])
        effect.append(("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": pax}))
    return ({"status": "success", "outbound_train_id": legs[0][0], "return_train_id": legs[1][0], "travel_class": cls,
             "passenger": pax, "booking_ids": None}, None, effect)  # both legs REQUIRED: checked via expected_bookings


def _solve_infeasible_budget(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls = p["travel_class"]
    found = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    cands = [t["train_id"] for t in found["trains"] if cls in t["classes"]]
    if len(cands) < 2:
        raise ValueError("infeasibility should be shown over at least two candidates")
    fares = {}
    for tid in cands:  # every candidate's fare is needed to PROVE that none fits the budget
        fares[tid] = _ok(env, "get_fare", {"train_id": tid, "travel_class": cls})["fare_inr"]
        plan.add("get_fare", {"train_id": tid, "travel_class": cls}, {"train_id": f"{c3}.trains[*].train_id"}, after=[c3])
    if min(fares.values()) <= p["max_fare_inr"]:
        raise ValueError("a candidate fits the budget: the task would be feasible")
    return {"status": "cannot_complete", "selected_train_id": None, "travel_class": cls, "reason": "no_train_within_budget",
            "max_fare_inr": p["max_fare_inr"], "cheapest_fare_found": min(fares.values())}, None, []


def _solve_cross_midnight_window(env: RailwayEnv, p: dict[str, Any], plan: _Plan):
    from datetime import date as _D, timedelta as _TD
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    d1 = p["date"]
    d2 = (_D.fromisoformat(d1) + _TD(days=1)).isoformat()
    late = {"start": p["window_start"], "end": END_OF_DAY}
    early = {"start": "00:00", "end": p["window_end"]}
    out = []
    for d, w in ((d1, late), (d2, early)):
        for t in _ok(env, "search_trains", {"source": src, "destination": dst, "date": d, "time_window": w})["trains"]:
            out.append({"train_id": t["train_id"], "departure_date": d, "departure": t["departure"]})
        plan.add("search_trains", {"source": src, "destination": dst, "date": d, "time_window": w},
                 after=resolves, alternatives={"time_window": [None]})
    naive = _ok(env, "search_trains", {"source": src, "destination": dst, "date": d1,
                                        "time_window": {"start": p["window_start"], "end": p["window_end"]}})["trains"]
    if not out:
        raise ValueError("window must contain a train")
    if sorted(t["train_id"] for t in naive) == sorted(t["train_id"] for t in out):
        raise ValueError("a single same-date wrap-around search would give the same answer: no cross-date reasoning tested")
    return ({"status": "success", "departures": out, "selected_train_ids": sorted(t["train_id"] for t in out)},
            sorted(t["train_id"] for t in out), [])



# ------------------------------------------------------------------ batch T26-T50 solvers (phases A: T26-T35, B: T36-T45, C: T46-T50)
_AC_CLASSES = ("3A", "2A", "CC")
_WD = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _abs_min(date_iso: str, base_iso: str, day_offset: int, hhmm: str) -> int:
    from datetime import date as _D
    return ((_D.fromisoformat(date_iso) - _D.fromisoformat(base_iso)).days + day_offset) * 1440 + _mins(hhmm)


def _seats(env, tid, cls):
    return _ok(env, "check_availability", {"train_id": tid, "travel_class": cls})["seats_available"]


def _fare(env, tid, cls):
    return _ok(env, "get_fare", {"train_id": tid, "travel_class": cls})["fare_inr"]


def _book_effect(tid, cls, pax):
    return ("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": pax})


def _solve_seat_count_lookup(env, p, plan):
    tid, cls = p["train_id"], p["travel_class"]
    s = _seats(env, tid, cls)
    if s == 0:
        raise ValueError("a sold-out class would make this a status question, not a count")
    plan.add("check_availability", {"train_id": tid, "travel_class": cls})
    return {"status": "success", "selected_train_id": tid, "travel_class": cls, "seats_available": s}, [tid], []


def _solve_direct_named_booking(env, p, plan):
    _verify_train_serves(env, p)
    tid, cls, pax = p["train_id"], p["travel_class"], p["passenger"]
    if _seats(env, tid, cls) <= 0:
        raise ValueError("named train/class must have seats")
    plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": pax})  # nothing else is needed
    return ({"status": "success", "selected_train_id": tid, "travel_class": cls, "passenger": pax,
             "fare_inr": _fare(env, tid, cls), "booking_id": None}, [tid], [_book_effect(tid, cls, pax)])


def _solve_invalid_train_id(env, p, plan):
    r = env.call("get_train_details", {"train_id": p["train_id"]})
    if r["ok"] or r["error"]["code"] != "INVALID_TRAIN":
        raise ValueError("train id must not exist")
    plan.add("get_train_details", {"train_id": p["train_id"]}, expected_error="INVALID_TRAIN")
    return {"status": "cannot_complete", "selected_train_id": None, "train_id": p["train_id"], "reason": "INVALID_TRAIN"}, None, []


def _solve_unsupported_class(env, p, plan):
    _verify_train_serves(env, p)
    tid, cls = p["train_id"], p["travel_class"]
    r = env.call("check_availability", {"train_id": tid, "travel_class": cls})
    if r["ok"] or r["error"]["code"] != "INVALID_CLASS":
        raise ValueError("class must be unsupported by the service (INVALID_CLASS), not merely not offered")
    # the tool descriptions list the only valid classes, so no call is needed to know 1A is unsupported
    plan.add("check_availability", {"train_id": tid, "travel_class": cls}, optional=True, expected_error="INVALID_CLASS")
    offered = _ok(env, "get_train_details", {"train_id": tid})["classes"]
    return ({"status": "cannot_complete", "selected_train_id": None, "train_id": tid, "travel_class": cls,
             "reason": "INVALID_CLASS", "classes_on_train": offered}, None, [])


def _solve_past_date_booking(env, p, plan):
    src, dst = _station_code(env, p["source_name"]), _station_code(env, p["destination_name"])
    r = env.call("search_trains", {"source": src, "destination": dst, "date": p["date"]})
    if r["ok"] or r["error"]["code"] != "PAST_DATE":
        raise ValueError("date must be in the past relative to the pinned 'now'")
    later = _ok(env, "search_trains", {"source": src, "destination": dst, "date": "2026-10-09"})["trains"]
    if not later:
        raise ValueError("the route must be served on future dates, so the date is the only problem")
    # the pinned current date is in the system prompt: the past date is detectable without any call
    plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, optional=True, expected_error="PAST_DATE")
    return {"status": "cannot_complete", "selected_train_id": None, "reason": "PAST_DATE", "requested_date": p["date"]}, None, []


def _solve_alias_retry_earliest(env, p, plan):
    r = env.call("resolve_station", {"name": p["source_name"]})
    if r["ok"]:
        raise ValueError("the user's station name must fail to resolve")
    src, dst = _station_code(env, p["recovered_station"]), _station_code(env, p["destination_name"])
    c0 = plan.add("resolve_station", {"name": {"resolves_to_none": True}}, optional=True, expected_error="STATION_NOT_FOUND")
    c1 = plan.add("resolve_station", {"name": {"resolves_to": src}}, after=[c0])
    c2 = plan.add("resolve_station", {"name": {"resolves_to": dst}})
    tr = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})["trains"]
    plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=[c1, c2])
    first = min(tr, key=lambda t: _mins(t["departure"]))
    if sum(1 for t in tr if t["departure"] == first["departure"]) != 1 or len(tr) < 2:
        raise ValueError("earliest train must be unique among several")
    return {"status": "success", "selected_train_id": first["train_id"], "departure": first["departure"],
            "resolved_source": src}, [first["train_id"]], []


def _solve_fare_conditioned_branch(env, p, plan):
    _verify_train_serves(env, p)
    tid, pref, fb, pax = p["train_id"], p["travel_class"], p["fallback_class"], p["passenger"]
    if _seats(env, tid, pref) <= 0 or _seats(env, tid, fb) <= 0:
        raise ValueError("both classes need seats so that ONLY the fare decides the branch")
    fare = _fare(env, tid, pref)
    branch = pref if fare < p["fare_below_inr"] else fb
    if branch == pref:
        raise ValueError("design: the fare condition must fail, exercising the else-branch")
    c1 = plan.add("get_fare", {"train_id": tid, "travel_class": pref})
    plan.add("book_ticket", {"train_id": tid, "travel_class": branch, "passenger": pax}, after=[c1])
    return ({"status": "success", "selected_train_id": tid, "travel_class": branch, "condition_fare_inr": fare,
             "condition_met": False, "passenger": pax, "booking_id": None}, [tid], [_book_effect(tid, branch, pax)])


def _solve_group_cheapest_any_class(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    pax = p["passengers"]
    tr = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})["trains"]
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    ref = {"train_id": f"{c3}.trains[*].train_id"}
    opts = {(t["train_id"], c): (_fare(env, t["train_id"], c), _seats(env, t["train_id"], c)) for t in tr for c in t["classes"]}
    ok = {k: v for k, v in opts.items() if v[1] >= len(pax)}
    low = min(v[0] for v in ok.values())
    win = [k for k, v in ok.items() if v[0] == low]
    if len(win) != 1 or len({v[0] for v in opts.values()}) != len(opts):
        raise ValueError("winner and fares must be unique")
    w = win[0]
    if min(v[0] for v in opts.values()) == low:
        raise ValueError("the overall cheapest option must lack seats for the whole group")
    proof = [plan.add("get_fare", {"train_id": w[0], "travel_class": w[1]}, ref, after=[c3]),
             plan.add("check_availability", {"train_id": w[0], "travel_class": w[1]}, ref, after=[c3])]
    for (tid, c), (f, s) in sorted(opts.items()):
        if (tid, c) == w:
            continue
        if f < low:   # cheaper: must be shown to lack seats for everyone
            proof.append(plan.add("check_availability", {"train_id": tid, "travel_class": c}, ref, after=[c3]))
        else:         # pricier: shown by its fare
            proof.append(plan.add("get_fare", {"train_id": tid, "travel_class": c}, ref, after=[c3]))
    for x in pax:
        plan.add("book_ticket", {"train_id": w[0], "travel_class": w[1], "passenger": x}, ref, after=[c3] + proof)
    return ({"status": "success", "selected_train_id": w[0], "travel_class": w[1], "fare_inr_per_ticket": low,
             "total_fare_inr": low * len(pax), "passengers": pax, "booking_ids": None},
            [w[0]], [_book_effect(w[0], w[1], x) for x in pax])


def _solve_fastest_within_budget(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls, cap = p["travel_class"], p["max_fare_inr"]
    tr = sorted((t for t in _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})["trains"] if cls in t["classes"]),
                key=lambda t: t["duration_minutes"])
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    ref = {"train_id": f"{c3}.trains[*].train_id"}
    if len({t["duration_minutes"] for t in tr}) != len(tr):
        raise ValueError("durations must be distinct")
    fares = {t["train_id"]: _fare(env, t["train_id"], cls) for t in tr}
    ok = [t for t in tr if fares[t["train_id"]] <= cap]
    if len(ok) < 2 or fares[tr[0]["train_id"]] <= cap:
        raise ValueError("budget must exclude the fastest train AND leave >= 2 trains to rank")
    w = ok[0]
    fc = []
    for t in tr:  # proof: every faster train shown over budget, the winner shown within budget; slower trains need nothing
        fc.append(plan.add("get_fare", {"train_id": t["train_id"], "travel_class": cls}, ref, after=[c3]))
        if t is w:
            break
    plan.add("check_availability", {"train_id": w["train_id"], "travel_class": cls}, ref, after=[c3] + fc)  # user asks about seats
    return ({"status": "success", "selected_train_id": w["train_id"], "duration_minutes": w["duration_minutes"], "fare_inr": fares[w["train_id"]],
             "seats_available": _seats(env, w["train_id"], cls), "excluded_over_budget": [t["train_id"] for t in tr[:tr.index(w)]]}, [w["train_id"]], [])


def _solve_relative_weekday_booking(env, p, plan):
    from datetime import timedelta as _TD
    ref = env.reference_datetime.date()
    want = _WD.index(p["relative_weekday"])
    d = next(ref + _TD(days=i) for i in range(1, 8) if (ref + _TD(days=i)).weekday() == want)  # 'this <weekday>' = next one after today
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls, pax = p["travel_class"], p["passenger"]

    def hits(day):
        return [t["train_id"] for t in _ok(env, "search_trains", {"source": src, "destination": dst, "date": day.isoformat()})["trains"] if cls in t["classes"]]
    got = hits(d)
    if len(got) != 1 or hits(d - _TD(days=1)) or hits(d + _TD(days=1)):
        raise ValueError("exactly one train, and only on the resolved weekday (date resolution must matter)")
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": d.isoformat()}, after=resolves)
    plan.add("book_ticket", {"train_id": got[0], "travel_class": cls, "passenger": pax}, {"train_id": f"{c3}.trains[*].train_id"}, after=[c3])
    return ({"status": "success", "resolved_date": d.isoformat(), "selected_train_id": got[0], "travel_class": cls, "passenger": pax,
             "booking_id": None}, [got[0]], [_book_effect(got[0], cls, pax)])


def _solve_ambiguous_class_term(env, p, plan):
    _verify_train_serves(env, p)
    tid = p["train_id"]
    classes = _ok(env, "get_train_details", {"train_id": tid})["classes"]
    cands = sorted(c for c in classes if c in _AC_CLASSES and _seats(env, tid, c) > 0)
    if len(cands) < 2 or len({_fare(env, tid, c) for c in cands}) < 2:
        raise ValueError("'AC' must match at least two bookable classes with different fares")
    plan.add("get_train_details", {"train_id": tid}, optional=True)
    return ({"status": "needs_clarification", "clarification_needed": "travel_class", "candidate_classes": cands,
             "selected_train_id": None, "train_id": tid}, None, [])


def _solve_ambiguous_intent(env, p, plan):
    _verify_train_serves(env, p)
    tid, cls = p["train_id"], p["travel_class"]
    if _seats(env, tid, cls) <= 0:
        raise ValueError("seats must exist, so an unrequested booking WOULD succeed (the risk being tested)")
    plan.add("check_availability", {"train_id": tid, "travel_class": cls}, optional=True)
    return ({"status": "needs_clarification", "clarification_needed": "check_or_book", "selected_train_id": None,
             "train_id": tid, "travel_class": cls}, None, [])


def _solve_sold_out_cheapest_alternative(env, p, plan):
    src, dst = _verify_train_serves(env, p)
    tid, cls, pax = p["train_id"], p["travel_class"], p["passenger"]
    if _seats(env, tid, cls) != 0:
        raise ValueError("named train/class must be sold out")
    c1 = plan.add("check_availability", {"train_id": tid, "travel_class": cls})
    c2 = plan.add("resolve_station", {"name": {"resolves_to": src}})
    c3 = plan.add("resolve_station", {"name": {"resolves_to": dst}})
    tr = _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})["trains"]
    c4 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=[c2, c3])
    ref = {"train_id": f"{c4}.trains[*].train_id"}
    alts = {t["train_id"]: _fare(env, t["train_id"], cls) for t in tr if t["train_id"] != tid and cls in t["classes"]}
    if len(alts) < 2 or any(_seats(env, a, cls) <= 0 for a in alts):
        raise ValueError("need >= 2 alternatives with seats so that 'cheapest' decides")
    fares = [plan.add("get_fare", {"train_id": a, "travel_class": cls}, ref, after=[c4]) for a in sorted(alts)]
    w = min(alts, key=alts.get)
    if sum(1 for v in alts.values() if v == alts[w]) != 1:
        raise ValueError("cheapest alternative not unique")
    plan.add("book_ticket", {"train_id": w, "travel_class": cls, "passenger": pax}, ref, after=[c1, c4] + fares)
    return ({"status": "success", "requested_train_id": tid, "requested_status": "SOLD_OUT", "selected_train_id": w,
             "travel_class": cls, "fare_inr": alts[w], "passenger": pax, "booking_id": None}, [w], [_book_effect(w, cls, pax)])


def _solve_runs_on_date_conditional(env, p, plan):
    from datetime import date as _D
    src, _ = _verify_route_only(env, p)
    tid, cls = p["train_id"], p["travel_class"]
    det = _ok(env, "get_train_details", {"train_id": tid})
    if det["source_station"] != src:
        raise ValueError("boarding must be at the origin so operating_days apply directly")
    wd = _WD[_D.fromisoformat(p["date"]).weekday()]
    if wd in det["operating_days"]:
        raise ValueError("design: the train must NOT run on the requested date")
    if _seats(env, tid, cls) <= 0:
        raise ValueError("seats must exist so the environment would ACCEPT a wrong booking (only reasoning prevents it)")
    plan.add("get_train_details", {"train_id": tid})
    return ({"status": "cannot_complete", "selected_train_id": None, "train_id": tid, "requested_weekday": wd,
             "operating_days": det["operating_days"], "reason": "train_does_not_run_on_date"}, None, [])


def _verify_route_only(env, p):
    return _station_code(env, p["source_name"]), _station_code(env, p["destination_name"])


def _solve_connection_planning(env, p, plan):
    src, dst = _station_code(env, p["source_name"]), _station_code(env, p["destination_name"])
    via = _station_code(env, p["via_name"])
    d = p["date"]
    if _ok(env, "search_trains", {"source": src, "destination": dst, "date": d})["trains"]:
        raise ValueError("a direct train exists: no connection reasoning needed")
    cs = [plan.add("resolve_station", {"name": {"resolves_to": c}}) for c in (src, via, dst)]
    l1 = _ok(env, "search_trains", {"source": src, "destination": via, "date": d})["trains"]
    s1 = plan.add("search_trains", {"source": src, "destination": via, "date": d}, after=[cs[0], cs[1]])
    l2 = _ok(env, "search_trains", {"source": via, "destination": dst, "date": d})["trains"]
    s2 = plan.add("search_trains", {"source": via, "destination": dst, "date": d}, after=[cs[1], cs[2]])
    pairs = []
    for a in l1:
        arr = _abs_min(d, d, a["arrival_day_offset"], a["arrival"])
        for b in l2:
            dep = _abs_min(d, d, 0, b["departure"])
            if dep - arr >= p["min_connection_minutes"]:
                pairs.append((dep + b["duration_minutes"], a, b))
    if not pairs:
        raise ValueError("no same-day connection")
    best = min(x[0] for x in pairs)
    win = [x for x in pairs if x[0] == best]
    if len(win) != 1:
        raise ValueError("earliest-arrival connection not unique")
    _, a, b = win[0]
    return ({"status": "success", "first_leg_train_id": a["train_id"], "second_leg_train_id": b["train_id"],
             "connection_minutes": _abs_min(d, d, 0, b["departure"]) - _abs_min(d, d, a["arrival_day_offset"], a["arrival"]),
             "final_arrival": b["arrival"], "final_arrival_day_offset": b["arrival_day_offset"]},
            None, [])


def _solve_multi_leg_all_or_nothing(env, p, plan):
    legs, pax = p["legs"], p["passenger"]
    seats = []
    for lg in legs:
        _verify_train_serves(env, {**lg})
        seats.append(_seats(env, lg["train_id"], lg["travel_class"]))
    if seats[0] <= 0 or all(s > 0 for s in seats):
        raise ValueError("design: the FIRST leg must be bookable and a LATER leg must not")
    for lg, s in zip(legs, seats):  # proof of failure = the failing leg's availability; the bookable leg's check is optional
        plan.add("check_availability", {"train_id": lg["train_id"], "travel_class": lg["travel_class"]}, optional=s > 0)
    failing = next(i for i, s in enumerate(seats) if s <= 0) + 1
    return ({"status": "cannot_complete", "selected_train_id": None, "failing_leg": failing,
             "failing_train_id": legs[failing - 1]["train_id"], "reason": "leg_unavailable", "passenger": pax}, None, [])


def _solve_mixed_class_pair_booking(env, p, plan):
    _verify_train_serves(env, p)
    tid, assign = p["train_id"], p["assignments"]
    if len({a["travel_class"] for a in assign}) < 2:
        raise ValueError("passengers must be assigned DIFFERENT classes")
    for a in assign:
        if _seats(env, tid, a["travel_class"]) <= 0:
            raise ValueError("each assigned class needs seats")
        plan.add("book_ticket", {"train_id": tid, "travel_class": a["travel_class"], "passenger": a["passenger"]})  # independent: any order
    return ({"status": "success", "selected_train_id": tid, "bookings": [{"passenger": a["passenger"], "travel_class": a["travel_class"]} for a in assign],
             "booking_ids": None}, [tid], [_book_effect(tid, a["travel_class"], a["passenger"]) for a in assign])


def _solve_multi_constraint_booking(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls, pax, d = p["travel_class"], p["passenger"], p["date"]
    every = _ok(env, "search_trains", {"source": src, "destination": dst, "date": d})["trains"]
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": d}, after=resolves)
    ref = {"train_id": f"{c3}.trains[*].train_id"}
    deadline = _abs_min(p["arrive_by_date"], d, 0, p["arrive_by_time"])
    pruned = {"class": set(), "arrival": set(), "fare": set()}
    timeok = []
    for t in every:
        if cls not in t["classes"]:
            pruned["class"].add(t["train_id"])
        elif _abs_min(d, d, t["arrival_day_offset"], t["arrival"]) > deadline:
            pruned["arrival"].add(t["train_id"])
        else:
            timeok.append(t["train_id"])
    fares, fcalls = {}, []
    for tid in timeok:  # a fare is needed for every class- and deadline-feasible candidate
        fares[tid] = _fare(env, tid, cls)
        fcalls.append(plan.add("get_fare", {"train_id": tid, "travel_class": cls}, ref, after=[c3]))
        if fares[tid] > p["max_fare_inr"]:
            pruned["fare"].add(tid)
    win = [t for t in timeok if t not in pruned["fare"] and _seats(env, t, cls) > 0]
    if len(win) != 1 or not all(pruned.values()):
        raise ValueError(f"each constraint must prune a train and exactly one must remain: {pruned}, {win}")
    plan.add("book_ticket", {"train_id": win[0], "travel_class": cls, "passenger": pax}, ref, after=[c3] + fcalls)
    return ({"status": "success", "selected_train_id": win[0], "travel_class": cls, "fare_inr": fares[win[0]],
             "pruned_by": {k: sorted(v) for k, v in pruned.items()}, "passenger": pax, "booking_id": None},
            [win[0]], [_book_effect(win[0], cls, pax)])


def _solve_overnight_arrival_date(env, p, plan):
    from datetime import date as _D, timedelta as _TD
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    tr = [t for t in _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})["trains"]
          if t["departure"] == p["departure_time"]]
    plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    if len(tr) != 1 or tr[0]["arrival_day_offset"] < 1:
        raise ValueError("needs exactly one matching train that arrives on a LATER date")
    t = tr[0]
    return ({"status": "success", "selected_train_id": t["train_id"], "arrival": t["arrival"],
             "arrival_date": (_D.fromisoformat(p["date"]) + _TD(days=t["arrival_day_offset"])).isoformat()}, [t["train_id"]], [])


def _solve_unsupported_action(env, p, plan):
    # Benchmark 3.0 added cancel_ticket, which works on a 10-digit PNR. T45's reference is a booking ID ("BK0042") that exists
    # neither as a PNR nor among the account's bookings, so the request still cannot be completed and the gold is unchanged
    # (zero required calls; asking for the PNR is accepted as an alternative outcome in evaluation/scorer.py).
    ids = {b.booking_id for b in env.state.account_bookings.values()} | {b.booking_id for b in env.state.bookings}
    if p["booking_id"] in ids or env.call("get_booking_status", {"pnr": p["booking_id"]})["ok"]:
        raise ValueError("the booking reference exists: the cancellation would be possible")
    return {"status": "cannot_complete", "selected_train_id": None, "reason": "unsupported_action",
            "requested_action": p["requested_action"]}, None, []


def _solve_passenger_count_conflict(env, p, plan):
    _verify_train_serves(env, p)
    tid, cls = p["train_id"], p["travel_class"]
    if p["ticket_count"] == len(p["passengers"]):
        raise ValueError("ticket count must disagree with the number of names")
    if _seats(env, tid, cls) < max(p["ticket_count"], len(p["passengers"])):
        raise ValueError("seats must suffice for either reading, so only the conflict blocks the booking")
    plan.add("check_availability", {"train_id": tid, "travel_class": cls}, optional=True)
    return ({"status": "needs_clarification", "clarification_needed": "passenger_count", "tickets_requested": p["ticket_count"],
             "names_given": len(p["passengers"]), "selected_train_id": None}, None, [])


def _solve_disambiguation_by_train(env, p, plan):
    r = _ok(env, "resolve_station", {"name": p["source_name"]})
    if not r["ambiguous"]:
        raise ValueError("source name must be ambiguous on its own")
    cands = sorted(c["code"] for c in r["candidates"])
    tid, cls, pax = p["train_id"], p["travel_class"], p["passenger"]
    dst = _station_code(env, p["destination_name"])
    fits = [c for c in cands if tid in [t["train_id"] for t in _ok(env, "search_trains", {"source": c, "destination": dst, "date": p["date"]})["trains"]]]
    if len(fits) != 1:
        raise ValueError(f"the named train must fit exactly one candidate station: {fits}")
    if _seats(env, tid, cls) <= 0:
        raise ValueError("needs seats")
    plan.add("resolve_station", {"name": {"resolves_ambiguous": cands}}, optional=True)
    c2 = plan.add("get_train_details", {"train_id": tid})
    plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": pax}, after=[c2])
    return ({"status": "success", "selected_train_id": tid, "resolved_source": fits[0], "travel_class": cls,
             "passenger": pax, "booking_id": None}, [tid], [_book_effect(tid, cls, pax)])


def _solve_partial_allowed_group(env, p, plan):
    _verify_train_serves(env, p)
    tid, cls, pax = p["train_id"], p["travel_class"], p["passengers"]
    s = _seats(env, tid, cls)
    if not 0 < s < len(pax):
        raise ValueError("needs 0 < seats < group size, so the partial-booking policy decides")
    c1 = plan.add("check_availability", {"train_id": tid, "travel_class": cls}, optional=True)  # or learn it from SOLD_OUT replies
    for x in pax[:s]:
        plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": x})
    return ({"status": "success", "selected_train_id": tid, "travel_class": cls, "booked_passengers": pax[:s],
             "unbooked_passengers": pax[s:], "booking_ids": None}, [tid], [_book_effect(tid, cls, x) for x in pax[:s]])


def _solve_route_property_booking(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls, pax, goal = p["travel_class"], p["passenger"], _station_code(env, p["continues_to_name"])
    tr = [t for t in _ok(env, "search_trains", {"source": src, "destination": dst, "date": p["date"]})["trains"] if cls in t["classes"]]
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    ref = {"train_id": f"{c3}.trains[*].train_id"}
    hits, dcalls = [], []
    for t in tr:  # the search result does not show where a train terminates: details are required for each candidate
        stops = [s["station"] for s in _ok(env, "get_train_details", {"train_id": t["train_id"]})["stops"]]
        dcalls.append(plan.add("get_train_details", {"train_id": t["train_id"]}, ref, after=[c3]))
        if goal in stops and stops.index(goal) > stops.index(dst):
            hits.append(t["train_id"])
    if len(hits) != 1 or len(tr) < 2:
        raise ValueError("exactly one of several candidates must continue to the goal")
    plan.add("resolve_station", {"name": {"resolves_to": goal}}, optional=True)
    plan.add("book_ticket", {"train_id": hits[0], "travel_class": cls, "passenger": pax}, ref, after=[c3] + dcalls)
    return ({"status": "success", "selected_train_id": hits[0], "travel_class": cls, "continues_to": goal,
             "passenger": pax, "booking_id": None}, [hits[0]], [_book_effect(hits[0], cls, pax)])


def _solve_state_conditional_second_booking(env, p, plan):
    _verify_train_serves(env, p)
    tid, cls, first, second = p["train_id"], p["travel_class"], p["passenger"], p["second_passenger"]
    s = _seats(env, tid, cls)
    if s < 2:
        raise ValueError("design: the post-booking check must show a seat left, so the second booking is due")
    c1 = plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": first})
    c2 = plan.add("check_availability", {"train_id": tid, "travel_class": cls}, after=[c1])  # observe the POST-booking state
    c3 = plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": second}, after=[c2])
    plan.add("check_availability", {"train_id": tid, "travel_class": cls}, after=[c3], optional=True)  # final count can be derived
    return ({"status": "success", "selected_train_id": tid, "travel_class": cls, "seats_before": s, "seats_after_first_booking": s - 1,
             "second_booking_made": True, "seats_remaining_at_end": s - 2, "booking_ids": None}, [tid],
            [_book_effect(tid, cls, first), _book_effect(tid, cls, second)])


# ------------------------------------------------------------------ batch T51-T75 solvers (end-sem batch: failure-targeted + language-focused)
# Same conventions as above: each solver asserts the design property that makes its task meaningful, so a fixture change
# that silently trivialises a task fails gold generation instead of producing misleading gold.
def _trains(env, src, dst, d):
    return _ok(env, "search_trains", {"source": src, "destination": dst, "date": d})["trains"]


def _arr_min(t):  # arrival in minutes after midnight of the boarding date
    return t["arrival_day_offset"] * 1440 + _mins(t["arrival"])


def _date_plus(d: str, days: int) -> str:
    from datetime import date as _D, timedelta as _TD
    return (_D.fromisoformat(d) + _TD(days=days)).isoformat()


def _solve_route_count_latest_departure(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls = p["travel_class"]
    tr = _trains(env, src, dst, p["date"])
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    if len(tr) < 3:
        raise ValueError("a count question needs several trains")
    last = max(tr, key=lambda t: _mins(t["departure"]))
    if sum(1 for t in tr if t["departure"] == last["departure"]) != 1 or cls not in last["classes"]:
        raise ValueError("latest departure must be unique and offer the asked class")
    if all(cls in t["classes"] for t in tr):
        raise ValueError("design: some train must lack the class, so a class-filtered count would be wrong")
    plan.add("check_availability", {"train_id": last["train_id"], "travel_class": cls}, {"train_id": f"{c3}.trains[*].train_id"}, after=[c3])
    return ({"status": "success", "train_count": len(tr), "selected_train_id": last["train_id"], "departure": last["departure"],
             "seats_available": _seats(env, last["train_id"], cls)}, [last["train_id"]], [])


def _solve_earliest_arrival_after_time(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    tr = [t for t in _trains(env, src, dst, p["date"]) if _mins(t["departure"]) >= _mins(p["departure_not_before"])]
    plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    if len(tr) < 2:
        raise ValueError("needs at least two trains after the time bound")
    first_dep = min(tr, key=lambda t: _mins(t["departure"]))
    best = min(tr, key=_arr_min)
    if sum(1 for t in tr if _arr_min(t) == _arr_min(best)) != 1 or best is first_dep:
        raise ValueError("design: the earliest-ARRIVING train must be unique and differ from the earliest-departing one")
    return ({"status": "success", "selected_train_id": best["train_id"], "departure": best["departure"], "arrival": best["arrival"],
             "arrival_date": _date_plus(p["date"], best["arrival_day_offset"])}, [best["train_id"]], [])


def _solve_fare_difference_two_departures(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls = p["travel_class"]
    tr = _trains(env, src, dst, p["date"])
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    ref = {"train_id": f"{c3}.trains[*].train_id"}
    picked = []
    for hhmm in p["departure_times"]:
        m = [t for t in tr if t["departure"] == hhmm and cls in t["classes"]]
        if len(m) != 1:
            raise ValueError(f"exactly one {cls} train must leave at {hhmm}")
        picked.append(m[0]["train_id"])
    fares = {t: _fare(env, t, cls) for t in picked}
    for t in picked:
        plan.add("get_fare", {"train_id": t, "travel_class": cls}, ref, after=[c3])
    if len(set(fares.values())) != 2:
        raise ValueError("fares must differ")
    cheap = min(fares, key=fares.get)
    if cheap == picked[0]:
        raise ValueError("design: the LATER-named departure must be the cheaper one (order must not decide)")
    return ({"status": "success", "selected_train_id": cheap, "travel_class": cls, "fares_inr": fares,
             "fare_difference_inr": max(fares.values()) - min(fares.values())}, [cheap], [])


def _solve_native_script_passenger_booking(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls, pax = p["travel_class"], p["passenger"]
    for lang, form in p["passenger_script_forms"].items():  # the name as written in the native-script variants is rejected as is
        r = env.call("book_ticket", {"train_id": "BTB101", "travel_class": "3A", "passenger": form})
        if r["ok"] or r["error"]["code"] != "INVALID_PASSENGER":
            raise ValueError(f"{lang} form {form!r} must be rejected (INVALID_PASSENGER), so transliteration is required")
    tr = [t for t in _trains(env, src, dst, p["date"]) if cls in t["classes"]]
    if len(tr) != 1 or _seats(env, tr[0]["train_id"], cls) <= 0:
        raise ValueError("exactly one train must offer the class, with seats")
    tid = tr[0]["train_id"]
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": pax}, {"train_id": f"{c3}.trains[*].train_id"}, after=[c3])
    return ({"status": "success", "selected_train_id": tid, "travel_class": cls, "passenger": pax, "fare_inr": _fare(env, tid, cls),
             "booking_id": None}, [tid], [_book_effect(tid, cls, pax)])


def _solve_midroute_boarding_arrival(env, p, plan):
    src, dst = _verify_train_serves(env, p)
    tid, cls = p["train_id"], p["travel_class"]
    det = _ok(env, "get_train_details", {"train_id": tid})
    if det["source_station"] == src:
        raise ValueError("design: boarding must be at an INTERMEDIATE stop (the train starts on an earlier date)")
    t = next(x for x in _trains(env, src, dst, p["date"]) if x["train_id"] == tid)
    origin_dep = _mins(det["stops"][0]["departure"])
    if _mins(t["departure"]) >= origin_dep:
        raise ValueError("design: the train must have left its origin on the PREVIOUS day")
    plan.add("get_train_details", {"train_id": tid})
    plan.add("check_availability", {"train_id": tid, "travel_class": cls})
    s = _seats(env, tid, cls)
    if s <= 0:
        raise ValueError("needs seats")
    return ({"status": "success", "selected_train_id": tid, "boarding_station": src, "boarding_departure": t["departure"],
             "arrival": t["arrival"], "arrival_date": _date_plus(p["date"], t["arrival_day_offset"]), "seats_available": s}, [tid], [])


def _solve_multi_destination_departures(env, p, plan):
    src = _station_code(env, p["source_name"])
    dsts = [_station_code(env, p["destination_name"]), _station_code(env, p["second_destination_name"])]
    c0 = plan.add("resolve_station", {"name": {"resolves_to": src}})
    out, excluded = [], 0
    for dst in dsts:
        c = plan.add("resolve_station", {"name": {"resolves_to": dst}})
        tr = _trains(env, src, dst, p["date"])
        plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=[c0, c])
        for t in tr:
            if _mins(t["departure"]) >= _mins(p["departure_not_before"]):
                out.append({"train_id": t["train_id"], "destination": dst, "departure": t["departure"]})
            else:
                excluded += 1
    if not excluded or len({o["destination"] for o in out}) != 2:
        raise ValueError("design: both destinations contribute and the time bound excludes at least one train")
    if len({o["train_id"] for o in out}) != len(out):
        raise ValueError("a train serving both destinations would make the list ambiguous")
    out.sort(key=lambda o: _mins(o["departure"]))
    return ({"status": "success", "departures": out, "selected_train_ids": [o["train_id"] for o in out],
             "departure_times": [o["departure"] for o in out]}, None, [])


def _solve_relative_day_latest_with_class(env, p, plan):
    offsets = {"tomorrow": 1, "day_after_tomorrow": 2}
    ref = env.reference_datetime.date().isoformat()
    d = _date_plus(ref, offsets[p["relative_day"]])
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls = p["travel_class"]

    def last_with(day):
        tr = [t for t in _trains(env, src, dst, day) if cls in t["classes"]]
        return max(tr, key=lambda t: _mins(t["departure"])) if tr else None
    w = last_with(d)
    if w is None or any((x := last_with(_date_plus(d, k))) is not None and x["train_id"] == w["train_id"] for k in (-1, 1)):
        raise ValueError("design: the answer must change if the relative day is resolved one day off")
    plan.add("search_trains", {"source": src, "destination": dst, "date": d}, after=resolves)
    return ({"status": "success", "resolved_date": d, "selected_train_id": w["train_id"], "departure": w["departure"]}, [w["train_id"]], [])


def _solve_two_intent_count_and_booking(env, p, plan):
    _verify_train_serves(env, p)
    ct, cc = p["count_train_id"], p["count_class"]
    tid, cls, pax = p["train_id"], p["travel_class"], p["passenger"]
    n = _seats(env, ct, cc)
    if n <= 0 or ct == tid or _seats(env, tid, cls) <= 0:
        raise ValueError("two independent intents on two different trains, both answerable")
    plan.add("check_availability", {"train_id": ct, "travel_class": cc})
    plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": pax})  # independent of the count: any order
    return ({"status": "success", "count_train_id": ct, "count_class": cc, "seats_available": n, "selected_train_id": tid,
             "travel_class": cls, "passenger": pax, "booking_id": None}, [tid], [_book_effect(tid, cls, pax)])


def _solve_retracted_booking_fare_only(env, p, plan):
    _verify_train_serves(env, p)
    tid, cls = p["train_id"], p["travel_class"]
    if _seats(env, tid, cls) <= 0:
        raise ValueError("seats must exist so that booking anyway WOULD succeed (the risk being tested)")
    plan.add("get_fare", {"train_id": tid, "travel_class": cls})
    return ({"status": "success", "selected_train_id": tid, "travel_class": cls, "fare_inr": _fare(env, tid, cls),
             "booking_made": False}, [tid], [])


def _solve_cheaper_class_arrival_deadline(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    tr = _trains(env, src, dst, p["date"])
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    ref = {"train_id": f"{c3}.trains[*].train_id"}
    dl = _mins(p["arrive_before_time"])
    opts_all = {(t["train_id"], c): _fare(env, t["train_id"], c) for t in tr for c in p["classes"] if c in t["classes"]}
    on_time = {t["train_id"] for t in tr if _arr_min(t) < dl}
    opts = {k: v for k, v in opts_all.items() if k[0] in on_time}
    for (t, c) in sorted(opts):  # every on-time option's fare is needed to choose the cheaper class
        plan.add("get_fare", {"train_id": t, "travel_class": c}, ref, after=[c3])
    w = min(opts, key=opts.get)
    if sum(1 for v in opts.values() if v == opts[w]) != 1:
        raise ValueError("cheapest on-time option not unique")
    if min(opts_all.values()) >= opts[w]:
        raise ValueError("design: the cheapest option ignoring the deadline must arrive too late")
    t = next(x for x in tr if x["train_id"] == w[0])
    return ({"status": "success", "selected_train_id": w[0], "travel_class": w[1], "fare_inr": opts[w], "arrival": t["arrival"],
             "excluded_late_train_ids": sorted({k[0] for k in opts_all} - on_time)}, [w[0]], [])


def _solve_group_total_budget_check(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls, pax, cap = p["travel_class"], p["passengers"], p["max_total_fare_inr"]
    tr = [t for t in _trains(env, src, dst, p["date"]) if cls in t["classes"]]
    if len(tr) != 1:
        raise ValueError("exactly one train must offer the class, so only the budget decides")
    tid = tr[0]["train_id"]
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    f = _fare(env, tid, cls)
    plan.add("get_fare", {"train_id": tid, "travel_class": cls}, {"train_id": f"{c3}.trains[*].train_id"}, after=[c3])
    if not (f <= cap < f * len(pax)):
        raise ValueError("design: ONE ticket fits the budget but the group TOTAL does not")
    if _seats(env, tid, cls) < len(pax):
        raise ValueError("seats must suffice, so only the total-fare condition blocks the booking")
    return ({"status": "cannot_complete", "selected_train_id": None, "train_id": tid, "travel_class": cls, "fare_inr_per_ticket": f,
             "total_fare_inr": f * len(pax), "max_total_fare_inr": cap, "reason": "group_total_over_budget"}, None, [])


def _solve_deadline_class_sold_out_infeasible(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls, d = p["travel_class"], p["date"]
    deadline = _abs_min(p["arrive_by_date"], d, 0, p["arrive_by_time"])
    tr = [t for t in _trains(env, src, dst, d) if cls in t["classes"] and _arr_min(t) <= deadline]
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": d}, after=resolves)
    if not tr or any(_seats(env, t["train_id"], cls) > 0 for t in tr):
        raise ValueError("every on-time train offering the class must be sold out")
    nxt = [t for t in _trains(env, src, dst, _date_plus(d, 1)) if cls in t["classes"]]
    if any(_abs_min(_date_plus(d, 1), d, t["arrival_day_offset"], t["arrival"]) <= deadline for t in nxt):
        raise ValueError("a next-day train would meet the deadline")
    for t in tr:
        plan.add("check_availability", {"train_id": t["train_id"], "travel_class": cls}, {"train_id": f"{c3}.trains[*].train_id"}, after=[c3])
    other = sorted({c for t in tr for c in t["classes"] if c != cls and _seats(env, t["train_id"], c) > 0})
    if not other:
        raise ValueError("design: another class must have seats (the infeasibility is specific to the requested class)")
    return ({"status": "cannot_complete", "selected_train_id": None, "travel_class": cls, "sold_out_train_ids": [t["train_id"] for t in tr],
             "other_classes_with_seats": other, "reason": "requested_class_sold_out_on_every_on_time_train"}, None, [])


def _solve_earliest_train_party_seats_booking(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls, pax = p["travel_class"], p["passengers"]
    tr = sorted((t for t in _trains(env, src, dst, p["date"]) if cls in t["classes"]), key=lambda t: _mins(t["departure"]))
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    ref = {"train_id": f"{c3}.trains[*].train_id"}
    checks, w = [], None
    for t in tr:
        s = _seats(env, t["train_id"], cls)
        checks.append(plan.add("check_availability", {"train_id": t["train_id"], "travel_class": cls}, ref, after=[c3]))
        if s >= len(pax):
            w = t
            break
    if w is None or w is tr[0] or not 0 < _seats(env, tr[0]["train_id"], cls) < len(pax):
        raise ValueError("design: the earliest train must have SOME seats but fewer than the party; a later one has enough")
    for x in pax:
        plan.add("book_ticket", {"train_id": w["train_id"], "travel_class": cls, "passenger": x}, ref, after=[c3] + checks)
    return ({"status": "success", "selected_train_id": w["train_id"], "travel_class": cls, "departure": w["departure"],
             "skipped_insufficient_seats": [t["train_id"] for t in tr[:tr.index(w)]], "passengers": pax, "booking_ids": None},
            [w["train_id"]], [_book_effect(w["train_id"], cls, x) for x in pax])


def _solve_next_running_day_booking(env, p, plan):
    from datetime import date as _D
    tid, cls, pax = p["train_id"], p["travel_class"], p["passenger"]
    src, dst = _verify_route_only(env, p)
    det = _ok(env, "get_train_details", {"train_id": tid})
    if det["source_station"] != src:
        raise ValueError("boarding must be at the origin so operating_days apply directly")
    days = det["operating_days"]
    if _WD[_D.fromisoformat(p["date"]).weekday()] in days:
        raise ValueError("design: the train must NOT run on the anchor date itself")
    d = next(_date_plus(p["date"], k) for k in range(1, 8) if _WD[_D.fromisoformat(_date_plus(p["date"], k)).weekday()] in days)
    if tid not in [t["train_id"] for t in _trains(env, src, dst, d)] or _seats(env, tid, cls) <= 0:
        raise ValueError("the train must serve the route on the resolved date, with seats")
    c1 = plan.add("get_train_details", {"train_id": tid})
    plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": pax}, after=[c1])
    return ({"status": "success", "resolved_date": d, "selected_train_id": tid, "travel_class": cls, "passenger": pax,
             "operating_days": days, "booking_id": None}, [tid], [_book_effect(tid, cls, pax)])


def _solve_hypothetical_total_no_booking(env, p, plan):
    _verify_train_serves(env, p)
    tid = p["train_id"]
    fares = []
    for a in p["hypothetical_tickets"]:
        if _seats(env, tid, a["travel_class"]) <= 0:
            raise ValueError("seats must exist so that an unrequested booking WOULD succeed")
        fares.append(_fare(env, tid, a["travel_class"]))
        plan.add("get_fare", {"train_id": tid, "travel_class": a["travel_class"]})
    if len({a["travel_class"] for a in p["hypothetical_tickets"]}) != len(p["hypothetical_tickets"]):
        raise ValueError("classes must differ (two lookups, one sum)")
    return ({"status": "success", "selected_train_id": tid, "fares_inr": {a["travel_class"]: f for a, f in zip(p["hypothetical_tickets"], fares)},
             "total_fare_inr": sum(fares), "booking_made": False}, [tid], [])


def _solve_seat_threshold_conditional_booking(env, p, plan):
    _verify_train_serves(env, p)
    tid, cls = p["train_id"], p["travel_class"]
    s = _seats(env, tid, cls)
    if not 0 < s < p["min_seats"]:
        raise ValueError("design: seats must be AVAILABLE but below the threshold")
    plan.add("check_availability", {"train_id": tid, "travel_class": cls})
    return ({"status": "cannot_complete", "selected_train_id": None, "train_id": tid, "travel_class": cls, "seats_available": s,
             "min_seats_required": p["min_seats"], "reason": "seats_below_threshold"}, None, [])


def _solve_sold_out_next_departure_booking(env, p, plan):
    src, dst = _verify_train_serves(env, p)
    tid, cls, pax = p["train_id"], p["travel_class"], p["passenger"]
    if _seats(env, tid, cls) != 0:
        raise ValueError("named train/class must be sold out")
    c1 = plan.add("check_availability", {"train_id": tid, "travel_class": cls})
    c2 = plan.add("resolve_station", {"name": {"resolves_to": src}})
    c3 = plan.add("resolve_station", {"name": {"resolves_to": dst}})
    tr = _trains(env, src, dst, p["date"])
    c4 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=[c2, c3])
    me = next(t for t in tr if t["train_id"] == tid)
    later = sorted((t for t in tr if cls in t["classes"] and _mins(t["departure"]) > _mins(me["departure"])), key=lambda t: _mins(t["departure"]))
    if not later or _seats(env, later[0]["train_id"], cls) <= 0:
        raise ValueError("the next later train in the class must have seats")
    if any(cls in t["classes"] and _mins(t["departure"]) < _mins(me["departure"]) and _seats(env, t["train_id"], cls) > 0 for t in tr):
        raise ValueError("an EARLIER train with seats would make 'next' vs 'any other' ambiguous")
    w = later[0]
    plan.add("book_ticket", {"train_id": w["train_id"], "travel_class": cls, "passenger": pax}, {"train_id": f"{c4}.trains[*].train_id"}, after=[c1, c4])
    return ({"status": "success", "requested_train_id": tid, "requested_status": "SOLD_OUT", "selected_train_id": w["train_id"],
             "travel_class": cls, "departure": w["departure"], "passenger": pax, "booking_id": None}, [w["train_id"]],
            [_book_effect(w["train_id"], cls, pax)])


def _solve_typo_train_id_clarification(env, p, plan):
    typed, likely, cls = p["typed_train_id"], p["likely_train_id"], p["travel_class"]
    r = env.call("get_train_details", {"train_id": typed})
    if r["ok"] or r["error"]["code"] != "INVALID_TRAIN":
        raise ValueError("typed id must not exist")
    if typed.replace("O", "0") != likely:
        raise ValueError("design: the typed id must differ from a real id only by letter O vs digit 0")
    src, dst = _verify_route_only(env, p)
    if likely not in [t["train_id"] for t in _trains(env, src, dst, p["date"])] or _seats(env, likely, cls) <= 0:
        raise ValueError("the look-alike train must serve the stated route with seats, so a silent 'fix' WOULD book")
    plan.add("get_train_details", {"train_id": typed}, optional=True, expected_error="INVALID_TRAIN")
    plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, optional=True)
    return ({"status": "needs_clarification", "clarification_needed": "train_id", "selected_train_id": None, "typed_train_id": typed,
             "suggested_train_id": likely, "reason": "INVALID_TRAIN"}, None, [])


def _solve_class_not_offered_take_offered(env, p, plan):
    _verify_train_serves(env, p)
    tid, cls, pax = p["train_id"], p["travel_class"], p["passenger"]
    r = env.call("get_fare", {"train_id": tid, "travel_class": cls})
    if r["ok"] or r["error"]["code"] != "CLASS_NOT_OFFERED":
        raise ValueError("requested class must be CLASS_NOT_OFFERED on the train")
    offered = _ok(env, "get_train_details", {"train_id": tid})["classes"]
    if len(offered) != 1 or _seats(env, tid, offered[0]) <= 0:
        raise ValueError("design: exactly one offered class, with seats ('whatever class it does have' is then unambiguous)")
    plan.add("get_fare", {"train_id": tid, "travel_class": cls}, optional=True, expected_error="CLASS_NOT_OFFERED")
    c2 = plan.add("get_train_details", {"train_id": tid})
    plan.add("book_ticket", {"train_id": tid, "travel_class": offered[0], "passenger": pax}, after=[c2])
    return ({"status": "success", "selected_train_id": tid, "requested_class": cls, "requested_class_status": "CLASS_NOT_OFFERED",
             "travel_class": offered[0], "fare_inr": _fare(env, tid, offered[0]), "passenger": pax, "booking_id": None},
            [tid], [_book_effect(tid, offered[0], pax)])


def _solve_spoken_time_train_fare(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls = p["travel_class"]
    tr = _trains(env, src, dst, p["date"])
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    m = [t for t in tr if t["departure"] == p["departure_time"]]
    if len(m) != 1 or cls not in m[0]["classes"]:
        raise ValueError("exactly one train at the spoken time, offering the class")
    if not any(t is not m[0] and abs(_mins(t["departure"]) - _mins(p["departure_time"])) <= 30 for t in tr):
        raise ValueError("design: a near-miss train within 30 min must exist (misreading the spoken time picks it)")
    tid = m[0]["train_id"]
    plan.add("get_fare", {"train_id": tid, "travel_class": cls}, {"train_id": f"{c3}.trains[*].train_id"}, after=[c3])
    return ({"status": "success", "selected_train_id": tid, "departure": m[0]["departure"], "travel_class": cls,
             "fare_inr": _fare(env, tid, cls)}, [tid], [])


def _solve_spoken_amount_earliest_under_budget(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls, cap = p["travel_class"], p["max_fare_exclusive_inr"]
    tr = sorted((t for t in _trains(env, src, dst, p["date"]) if cls in t["classes"]), key=lambda t: _mins(t["departure"]))
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    ref = {"train_id": f"{c3}.trains[*].train_id"}
    fares = {t["train_id"]: _fare(env, t["train_id"], cls) for t in tr}
    ok = [t for t in tr if fares[t["train_id"]] < cap]
    if not ok or ok[0] is tr[0]:
        raise ValueError("design: the earliest train must be over budget")
    w = ok[0]
    if fares[w["train_id"]] < cap * 0.8:
        raise ValueError("design: the winner's fare must be close to the cap, so misreading the amount (e.g. 2,000) changes the answer")
    for t in tr[:tr.index(w) + 1]:  # proof: every earlier train shown over budget, the winner shown within it
        plan.add("get_fare", {"train_id": t["train_id"], "travel_class": cls}, ref, after=[c3])
    return ({"status": "success", "selected_train_id": w["train_id"], "travel_class": cls, "departure": w["departure"],
             "fare_inr": fares[w["train_id"]], "excluded_over_budget": [t["train_id"] for t in tr[:tr.index(w)]]}, [w["train_id"]], [])


def _solve_impossible_date_clarification(env, p, plan):
    src, dst = _verify_route_only(env, p)
    bad = p["requested_date"]
    r = env.call("search_trains", {"source": src, "destination": dst, "date": bad})
    if r["ok"] or r["error"]["code"] != "INVALID_DATE":
        raise ValueError("requested date must be an impossible calendar date (INVALID_DATE)")
    y, m, _ = bad.split("-")
    from datetime import date as _D, timedelta as _TD
    first_next = _D(int(y) + (m == "12"), int(m) % 12 + 1, 1)
    for d in (first_next - _TD(days=1), first_next):  # the nearest real readings (last day of the month, 1st of next) are both served
        if not [t for t in _trains(env, src, dst, d.isoformat()) if p["travel_class"] in t["classes"]]:
            raise ValueError("both plausible readings must be bookable, so the date is the ONLY problem")
    plan.add("search_trains", {"source": src, "destination": dst, "date": bad}, optional=True, expected_error="INVALID_DATE")
    return ({"status": "needs_clarification", "clarification_needed": "date", "selected_train_id": None, "requested_date": bad,
             "reason": "INVALID_DATE"}, None, [])


def _solve_same_station_two_names(env, p, plan):
    src, dst = _verify_route_only(env, p)
    if src != dst or p["source_name"].casefold() == p["destination_name"].casefold():
        raise ValueError("design: two DIFFERENT names for the SAME station")
    r = env.call("search_trains", {"source": src, "destination": dst, "date": p["date"]})
    if r["ok"] or r["error"]["code"] != "SAME_STATION":
        raise ValueError("expected SAME_STATION")
    plan.add("resolve_station", {"name": {"resolves_to": src}}, optional=True)
    plan.add("resolve_station", {"name": {"resolves_to": dst}}, optional=True)
    plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, optional=True, expected_error="SAME_STATION")
    return ({"status": "needs_clarification", "clarification_needed": "destination_station", "selected_train_id": None,
             "station_code": src, "reason": "SAME_STATION"}, None, [])


def _solve_duplicate_passenger_dedup(env, p, plan):
    _verify_train_serves(env, p)
    tid, cls, pax = p["train_id"], p["travel_class"], p["passengers"]
    uniq = list(dict.fromkeys(pax))
    if len(uniq) == len(pax):
        raise ValueError("design: a passenger must be listed twice")
    if _seats(env, tid, cls) < len(pax):
        raise ValueError("seats must suffice even for the full list, so only the duplicate rule matters")
    first = {}
    for x in uniq:
        first[x] = plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": x})
    dups = [x for i, x in enumerate(pax) if x in pax[:i]]
    for x in dups:  # a second attempt is harmless (the environment refuses it) but not needed
        plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": x}, after=[first[x]], optional=True,
                 expected_error="DUPLICATE_BOOKING")
    return ({"status": "success", "selected_train_id": tid, "travel_class": cls, "booked_passengers": uniq, "duplicate_names": dups,
             "booking_ids": None}, [tid], [_book_effect(tid, cls, x) for x in uniq])


def _solve_excluded_train_booking(env, p, plan):
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    cls, pax, ex = p["travel_class"], p["passenger"], p["excluded_train_id"]
    tr = sorted((t for t in _trains(env, src, dst, p["date"]) if cls in t["classes"]), key=lambda t: _mins(t["departure"]))
    if not tr or tr[0]["train_id"] != ex or _seats(env, ex, cls) <= 0:
        raise ValueError("design: the excluded train must be the FIRST listed and bookable (ignoring the exclusion would book it)")
    rest = [t for t in tr if t["train_id"] != ex and _seats(env, t["train_id"], cls) > 0]
    if len(rest) != 1:
        raise ValueError("exactly one other train must remain")
    w = rest[0]
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["date"]}, after=resolves)
    plan.add("book_ticket", {"train_id": w["train_id"], "travel_class": cls, "passenger": pax}, {"train_id": f"{c3}.trains[*].train_id"}, after=[c3])
    return ({"status": "success", "selected_train_id": w["train_id"], "excluded_train_id": ex, "travel_class": cls, "passenger": pax,
             "fare_inr": _fare(env, w["train_id"], cls), "booking_id": None}, [w["train_id"]], [_book_effect(w["train_id"], cls, pax)])


SOLVERS = {"fare_lookup": _solve_fare_lookup, "route_availability_fare": _solve_route_availability_fare,
           "constrained_choice": _solve_constrained_choice, "cheapest_booking": _solve_cheapest_booking,
           "conditional_booking": _solve_conditional_booking,
           # batch T06-T15
           "operating_days_lookup": _solve_operating_days_lookup, "intermediate_stop_time": _solve_intermediate_stop_time,
           "empty_window_fallback": _solve_empty_window_fallback,
           "ambiguous_station_clarification": _solve_ambiguous_station_clarification,
           "fallback_class_booking": _solve_fallback_class_booking, "class_not_offered": _solve_class_not_offered,
           "arrival_deadline_latest_departure": _solve_arrival_deadline_latest_departure,
           "timed_group_booking": _solve_timed_group_booking, "cheapest_available_class": _solve_cheapest_available_class,
           "group_all_or_nothing": _solve_group_all_or_nothing,
           # batch T16-T25
           "station_identity": _solve_station_identity, "segment_distance": _solve_segment_distance,
           "unknown_station": _solve_unknown_station, "missing_passenger_clarification": _solve_missing_passenger_clarification,
           "no_route_booking": _solve_no_route_booking,
           "train_direction_conflict": _solve_train_direction_conflict,
           "earliest_with_seats_booking": _solve_earliest_with_seats_booking, "round_trip_booking": _solve_round_trip_booking,
           "infeasible_budget": _solve_infeasible_budget, "cross_midnight_window": _solve_cross_midnight_window,
           # batch T26-T50
           "seat_count_lookup": _solve_seat_count_lookup,
           "direct_named_booking": _solve_direct_named_booking,
           "invalid_train_id": _solve_invalid_train_id,
           "unsupported_class": _solve_unsupported_class,
           "past_date_booking": _solve_past_date_booking,
           "alias_retry_earliest": _solve_alias_retry_earliest,
           "fare_conditioned_branch": _solve_fare_conditioned_branch,
           "group_cheapest_any_class": _solve_group_cheapest_any_class,
           "fastest_within_budget": _solve_fastest_within_budget,
           "relative_weekday_booking": _solve_relative_weekday_booking,
           "ambiguous_class_term": _solve_ambiguous_class_term,
           "ambiguous_intent": _solve_ambiguous_intent,
           "sold_out_cheapest_alternative": _solve_sold_out_cheapest_alternative,
           "runs_on_date_conditional": _solve_runs_on_date_conditional,
           "connection_planning": _solve_connection_planning,
           "multi_leg_all_or_nothing": _solve_multi_leg_all_or_nothing,
           "mixed_class_pair_booking": _solve_mixed_class_pair_booking,
           "multi_constraint_booking": _solve_multi_constraint_booking,
           "overnight_arrival_date": _solve_overnight_arrival_date,
           "unsupported_action": _solve_unsupported_action,
           "passenger_count_conflict": _solve_passenger_count_conflict,
           "disambiguation_by_train": _solve_disambiguation_by_train,
           "partial_allowed_group": _solve_partial_allowed_group,
           "route_property_booking": _solve_route_property_booking,
           "state_conditional_second_booking": _solve_state_conditional_second_booking,
           # batch T51-T75
           "route_count_latest_departure": _solve_route_count_latest_departure,
           "earliest_arrival_after_time": _solve_earliest_arrival_after_time,
           "fare_difference_two_departures": _solve_fare_difference_two_departures,
           "native_script_passenger_booking": _solve_native_script_passenger_booking,
           "midroute_boarding_arrival": _solve_midroute_boarding_arrival,
           "multi_destination_departures": _solve_multi_destination_departures,
           "relative_day_latest_with_class": _solve_relative_day_latest_with_class,
           "two_intent_count_and_booking": _solve_two_intent_count_and_booking,
           "retracted_booking_fare_only": _solve_retracted_booking_fare_only,
           "cheaper_class_arrival_deadline": _solve_cheaper_class_arrival_deadline,
           "group_total_budget_check": _solve_group_total_budget_check,
           "spoken_time_train_fare": _solve_spoken_time_train_fare,
           "deadline_class_sold_out_infeasible": _solve_deadline_class_sold_out_infeasible,
           "spoken_amount_earliest_under_budget": _solve_spoken_amount_earliest_under_budget,
           "earliest_train_party_seats_booking": _solve_earliest_train_party_seats_booking,
           "next_running_day_booking": _solve_next_running_day_booking,
           "impossible_date_clarification": _solve_impossible_date_clarification,
           "hypothetical_total_no_booking": _solve_hypothetical_total_no_booking,
           "same_station_two_names": _solve_same_station_two_names,
           "seat_threshold_conditional_booking": _solve_seat_threshold_conditional_booking,
           "duplicate_passenger_dedup": _solve_duplicate_passenger_dedup,
           "excluded_train_booking": _solve_excluded_train_booking,
           "sold_out_next_departure_booking": _solve_sold_out_next_departure_booking,
           "typo_train_id_clarification": _solve_typo_train_id_clarification,
           "class_not_offered_take_offered": _solve_class_not_offered_take_offered,
           }


# ----------------------------------------------------------------------------------------- benchmark 3.0 solvers (T76-T100)
# They use the six tools added in 3.0 (booking status, refund quote, cancel, waitlist, live status, concession). Every value is
# read from the environment; design conditions are asserted so a fixture change cannot silently change a task's meaning.
def _status(env, pnr):
    return _ok(env, "get_booking_status", {"pnr": pnr})


def _quote(env, pnr):
    return _ok(env, "get_cancellation_refund", {"pnr": pnr})


def _err_code(env, tool, args):
    r = env.call(tool, args)
    return None if r["ok"] else r["error"]["code"]


def _live(env, tid):
    return _ok(env, "get_live_train_status", {"train_id": tid})


def _concession(env, tid, cls, con):
    return _ok(env, "get_concession_fare", {"train_id": tid, "travel_class": cls, "concession": con})


def _cancel_effect(pnr):
    return ("cancel_ticket", {"pnr": pnr})


def _solve_pnr_status_lookup(env, p, plan):
    st = _status(env, p["pnr"])
    if st["status"] != p["expect_status"]:
        raise ValueError(f"design: PNR {p['pnr']} must be {p['expect_status']}")
    plan.add("get_booking_status", {"pnr": p["pnr"]})
    return ({"status": "success", "selected_train_id": st["train_id"], "travel_class": st["travel_class"], "pnr": p["pnr"],
             "booking_status": st["status"], "waitlist_position": st["waitlist_position"]}, [st["train_id"]], [])


def _solve_refund_quote_no_cancel(env, p, plan):
    q, st = _quote(env, p["pnr"]), _status(env, p["pnr"])
    plan.add("get_cancellation_refund", {"pnr": p["pnr"]})
    return ({"status": "success", "selected_train_id": st["train_id"], "travel_class": st["travel_class"], "pnr": p["pnr"],
             "refund_inr": q["refund_inr"], "cancellation_charge_inr": q["cancellation_charge_inr"]}, [st["train_id"]], [])


def _solve_cancel_pnr(env, p, plan):
    q, st = _quote(env, p["pnr"]), _status(env, p["pnr"])
    if st["status"] != "CONFIRMED":
        raise ValueError("design: a confirmed ticket")
    plan.add("cancel_ticket", {"pnr": p["pnr"]})
    return ({"status": "success", "selected_train_id": st["train_id"], "travel_class": st["travel_class"], "pnr": p["pnr"],
             "refund_inr": q["refund_inr"], "booking_status": "CANCELLED"}, [st["train_id"]], [_cancel_effect(p["pnr"])])


def _solve_conditional_cancel_min_refund(env, p, plan):
    q, st = _quote(env, p["pnr"]), _status(env, p["pnr"])
    c1 = plan.add("get_cancellation_refund", {"pnr": p["pnr"]})
    if q["refund_inr"] >= p["min_refund_inr"]:
        plan.add("cancel_ticket", {"pnr": p["pnr"]}, after=[c1])
        return ({"status": "success", "selected_train_id": st["train_id"], "travel_class": st["travel_class"], "pnr": p["pnr"],
                 "refund_inr": q["refund_inr"], "min_refund_inr": p["min_refund_inr"], "booking_status": "CANCELLED"},
                [st["train_id"]], [_cancel_effect(p["pnr"])])
    return ({"status": "cannot_complete", "selected_train_id": None, "train_id": st["train_id"], "pnr": p["pnr"],
             "refund_inr": q["refund_inr"], "min_refund_inr": p["min_refund_inr"], "reason": "refund_below_threshold"}, None, [])


def _solve_conditional_cancel_refund_too_low(env, p, plan):
    out = _solve_conditional_cancel_min_refund(env, p, plan)
    if out[0]["status"] != "cannot_complete":
        raise ValueError("design: the refund must be BELOW the threshold")
    return out


def _solve_conditional_cancel_refund_enough(env, p, plan):
    out = _solve_conditional_cancel_min_refund(env, p, plan)
    if out[0]["status"] != "success":
        raise ValueError("design: the refund must reach the threshold")
    return out


def _solve_cancel_already_cancelled(env, p, plan):
    return _solve_cancel_blocked(env, {**p, "expected_error": "ALREADY_CANCELLED"}, plan)


def _solve_cancel_after_departure(env, p, plan):
    return _solve_cancel_blocked(env, {**p, "expected_error": "JOURNEY_STARTED"}, plan)


def _solve_live_connection_check(env, p, plan):
    if "connection_time" not in p:
        raise ValueError("design: a connection time")
    return _solve_live_expected_arrival(env, p, plan)


def _solve_live_expected_arrival_intermediate(env, p, plan):
    out = _solve_live_expected_arrival(env, p, plan)
    tr = _ok(env, "get_train_details", {"train_id": p["train_id"]})
    if out[0]["station_code"] in (tr["source_station"], tr["destination_station"]):
        raise ValueError("design: an intermediate stop")
    return out


def _solve_conditional_waitlisted_cancel_rebook(env, p, plan):
    if not p.get("only_if_waitlisted"):
        raise ValueError("design: conditional on the waitlist status")
    return _solve_cancel_and_rebook_class(env, p, plan)


def _solve_pnr_not_found(env, p, plan):
    if _err_code(env, "get_booking_status", {"pnr": p["pnr"]}) != "PNR_NOT_FOUND":
        raise ValueError("design: the PNR must not exist")
    plan.add("get_booking_status", {"pnr": p["pnr"]}, expected_error="PNR_NOT_FOUND")
    return {"status": "cannot_complete", "selected_train_id": None, "pnr": p["pnr"], "reason": "pnr_not_found"}, None, []


def _solve_cancel_blocked(env, p, plan):
    code = _err_code(env, "cancel_ticket", {"pnr": p["pnr"]})
    if code != p["expected_error"]:
        raise ValueError(f"design: cancelling must fail with {p['expected_error']}, got {code}")
    st = _status(env, p["pnr"])
    plan.add("cancel_ticket", {"pnr": p["pnr"]}, expected_error=code)  # equivalent observations: evaluation/scorer.EQUIVALENT_PATHS
    return ({"status": "cannot_complete", "selected_train_id": None, "train_id": st["train_id"], "pnr": p["pnr"],
             "booking_status": st["status"], "reason": code.lower()}, None, [])


def _solve_waitlist_fallback_booking(env, p, plan):
    _verify_train_serves(env, p)
    tid, cls, pax = p["train_id"], p["travel_class"], p["passenger"]
    if _seats(env, tid, cls) != 0:
        raise ValueError("design: the class must be sold out")
    c1 = plan.add("check_availability", {"train_id": tid, "travel_class": cls})
    plan.add("join_waitlist", {"train_id": tid, "travel_class": cls, "passenger": pax}, after=[c1])
    probe = RailwayEnv()
    probe.reset()
    wl = _ok(probe, "join_waitlist", {"train_id": tid, "travel_class": cls, "passenger": pax})
    return ({"status": "success", "selected_train_id": tid, "travel_class": cls, "passenger": pax, "booking_status": "WAITLISTED",
             "waitlist_position": wl["waitlist_position"]}, [tid], [("join_waitlist", {"train_id": tid, "travel_class": cls, "passenger": pax})])


def _solve_sold_out_no_waitlist(env, p, plan):
    _verify_train_serves(env, p)
    tid, cls = p["train_id"], p["travel_class"]
    if _seats(env, tid, cls) != 0:
        raise ValueError("design: the class must be sold out")
    plan.add("check_availability", {"train_id": tid, "travel_class": cls})
    return ({"status": "cannot_complete", "selected_train_id": None, "train_id": tid, "travel_class": cls, "requested_status": "SOLD_OUT",
             "reason": "sold_out_waitlist_refused"}, None, [])


def _solve_waitlist_not_needed_booking(env, p, plan):
    _verify_train_serves(env, p)
    tid, cls, pax = p["train_id"], p["travel_class"], p["passenger"]
    if _seats(env, tid, cls) <= 0:
        raise ValueError("design: seats must be available, so the waitlist condition does not apply")
    plan.add("book_ticket", {"train_id": tid, "travel_class": cls, "passenger": pax})
    return ({"status": "success", "selected_train_id": tid, "travel_class": cls, "passenger": pax, "fare_inr": _fare(env, tid, cls),
             "booking_id": None}, [tid], [_book_effect(tid, cls, pax)])


def _solve_live_delay(env, p, plan):
    lv = _live(env, p["train_id"])
    if lv["status"] != "RUNNING" or not lv["delay_minutes"]:
        raise ValueError("design: the train must be running late now")
    plan.add("get_live_train_status", {"train_id": p["train_id"]})
    return ({"status": "success", "selected_train_id": p["train_id"], "running_status": lv["status"],
             "delay_minutes": lv["delay_minutes"]}, [p["train_id"]], [])


def _solve_live_expected_arrival(env, p, plan):
    lv = _live(env, p["train_id"])
    code = _station_code(env, p["station_name"])
    stop = next(s for s in lv["stops"] if s["station"] == code)
    if lv["status"] != "RUNNING" or code in (lv["last_station"],) or stop["expected_arrival"] is None:
        raise ValueError("design: a running train that has not reached the station yet")
    plan.add("get_live_train_status", {"train_id": p["train_id"]})
    out = {"status": "success", "selected_train_id": p["train_id"], "station_code": code, "expected_arrival": stop["expected_arrival"],
           "expected_date": stop["expected_date"], "delay_minutes": lv["delay_minutes"]}
    if "connection_time" in p:  # T90: does the train arrive before the connection leaves?
        out["makes_connection"] = _mins(stop["expected_arrival"]) <= _mins(p["connection_time"])
        if out["makes_connection"] or _mins(stop["scheduled_arrival"]) > _mins(p["connection_time"]):
            raise ValueError("design: on time it would make the connection; the delay must break it")
    return out, [p["train_id"]], []


def _solve_live_running_today(env, p, plan):
    lv = _live(env, p["train_id"])
    if lv["status"] != "NOT_RUNNING_TODAY":
        raise ValueError("design: the train must not run today")
    plan.add("get_live_train_status", {"train_id": p["train_id"]}, alternatives=None)
    return ({"status": "success", "selected_train_id": p["train_id"], "runs_on_requested_weekday": False}, [p["train_id"]], [])


def _solve_concession_fare(env, p, plan):
    c = _concession(env, p["train_id"], p["travel_class"], p["concession"])
    plan.add("get_concession_fare", {"train_id": p["train_id"], "travel_class": p["travel_class"], "concession": p["concession"]})
    return ({"status": "success", "selected_train_id": p["train_id"], "travel_class": p["travel_class"],
             "concession_fare_inr": c["concession_fare_inr"], "base_fare_inr": c["base_fare_inr"]}, [p["train_id"]], [])


def _solve_concession_party_total(env, p, plan):
    _verify_train_serves(env, p)
    c = _concession(env, p["train_id"], p["travel_class"], p["concession"])
    plan.add("get_concession_fare", {"train_id": p["train_id"], "travel_class": p["travel_class"], "concession": p["concession"]})
    plan.add("get_fare", {"train_id": p["train_id"], "travel_class": p["travel_class"]}, optional=True)  # the quote already has the base fare
    total = c["concession_fare_inr"] + p["regular_tickets"] * c["base_fare_inr"]
    return ({"status": "success", "selected_train_id": p["train_id"], "travel_class": p["travel_class"], "total_fare_inr": total,
             "concession_fare_inr": c["concession_fare_inr"], "base_fare_inr": c["base_fare_inr"]}, [p["train_id"]], [])


def _solve_concession_not_available(env, p, plan):
    args = {"train_id": p["train_id"], "travel_class": p["travel_class"], "concession": p["concession"]}
    if _err_code(env, "get_concession_fare", args) != "CONCESSION_NOT_AVAILABLE":
        raise ValueError("design: the concession must not exist in that class")
    plan.add("get_concession_fare", args, expected_error="CONCESSION_NOT_AVAILABLE")
    return ({"status": "cannot_complete", "selected_train_id": None, "train_id": p["train_id"], "travel_class": p["travel_class"],
             "reason": "concession_not_available"}, None, [])


def _solve_concession_budget_check(env, p, plan):
    c = _concession(env, p["train_id"], p["travel_class"], p["concession"])
    if not (c["concession_fare_inr"] <= p["budget_inr"] < c["base_fare_inr"]):
        raise ValueError("design: affordable only WITH the concession")
    if p["budget_inr"] - c["concession_fare_inr"] > 20:
        raise ValueError("design: the margin must be small, so a guessed discount gets it wrong")
    plan.add("get_concession_fare", {"train_id": p["train_id"], "travel_class": p["travel_class"], "concession": p["concession"]})
    return ({"status": "success", "selected_train_id": p["train_id"], "travel_class": p["travel_class"],
             "concession_fare_inr": c["concession_fare_inr"], "affordable": True}, [p["train_id"]], [])


def _solve_cancel_and_rebook_class(env, p, plan):
    st, q = _status(env, p["pnr"]), _quote(env, p["pnr"])
    if st["status"] != p["expect_status"] or st["passenger"] != p["booking_passenger"]:
        raise ValueError("design: PNR status / passenger")
    cls = p["new_class"]
    if _seats(env, st["train_id"], cls) <= 0 or cls == st["travel_class"]:
        raise ValueError("design: the new class must differ and have seats")
    after = []
    if p.get("only_if_waitlisted"):  # T96: the status decides
        after = [plan.add("get_booking_status", {"pnr": p["pnr"]})]
    else:
        plan.add("get_booking_status", {"pnr": p["pnr"]}, optional=True)  # the cancellation reply already names train and passenger
    c_cancel = plan.add("cancel_ticket", {"pnr": p["pnr"]}, after=after)
    plan.add("book_ticket", {"train_id": st["train_id"], "travel_class": cls, "passenger": st["passenger"]},
             {"train_id": f"{c_cancel}.train_id", "passenger": f"{c_cancel}.passenger"},
             after=after)
    return ({"status": "success", "selected_train_id": st["train_id"], "travel_class": cls, "pnr": p["pnr"],
             "previous_status": st["status"], "refund_inr": q["refund_inr"], "passenger": st["passenger"], "booking_id": None},
            [st["train_id"]], [_cancel_effect(p["pnr"]), _book_effect(st["train_id"], cls, st["passenger"])])


def _solve_conditional_waitlisted_noop(env, p, plan):
    st = _status(env, p["pnr"])
    if st["status"] != "CONFIRMED":
        raise ValueError("design: the ticket must be confirmed, so nothing may be cancelled")
    plan.add("get_booking_status", {"pnr": p["pnr"]})
    return ({"status": "success", "selected_train_id": st["train_id"], "travel_class": st["travel_class"], "pnr": p["pnr"],
             "booking_status": "CONFIRMED"}, [st["train_id"]], [])


def _solve_cancel_without_pnr_clarification(env, p, plan):
    # no tool lists a user's bookings and every booking tool needs a PNR: ask for it, call nothing, cancel nothing
    return {"status": "needs_clarification", "selected_train_id": None, "missing": "pnr"}, None, []


def _solve_cancel_multiple_total_refund(env, p, plan):
    sts = [_status(env, x) for x in p["pnrs"]]
    if any(s["status"] != "CONFIRMED" for s in sts) or len({(s["train_id"], s["travel_class"]) for s in sts}) != 1:
        raise ValueError("design: confirmed tickets on one train and class")
    total = sum(_quote(env, x)["refund_inr"] for x in p["pnrs"])
    for x in p["pnrs"]:
        plan.add("cancel_ticket", {"pnr": x})
    return ({"status": "success", "selected_train_id": sts[0]["train_id"], "travel_class": sts[0]["travel_class"], "pnrs": p["pnrs"],
             "refund_inr": total}, [sts[0]["train_id"]], [_cancel_effect(x) for x in p["pnrs"]])


def _solve_availability_and_concession(env, p, plan):
    tid, cls = p["train_id"], p["travel_class"]
    seats = _seats(env, tid, cls)
    c = _concession(env, tid, cls, p["concession"])
    plan.add("check_availability", {"train_id": tid, "travel_class": cls})
    plan.add("get_concession_fare", {"train_id": tid, "travel_class": cls, "concession": p["concession"]})
    return ({"status": "success", "selected_train_id": tid, "travel_class": cls, "seats_available": seats,
             "concession_fare_inr": c["concession_fare_inr"]}, [tid], [])


SOLVERS_V3 = {
    "pnr_status_lookup": _solve_pnr_status_lookup, "refund_quote_no_cancel": _solve_refund_quote_no_cancel,
    "cancel_pnr": _solve_cancel_pnr, "conditional_cancel_refund_too_low": _solve_conditional_cancel_refund_too_low,
    "conditional_cancel_refund_enough": _solve_conditional_cancel_refund_enough,
    "pnr_not_found": _solve_pnr_not_found, "cancel_already_cancelled": _solve_cancel_already_cancelled,
    "cancel_after_departure": _solve_cancel_after_departure,
    "waitlist_fallback_booking": _solve_waitlist_fallback_booking, "sold_out_no_waitlist": _solve_sold_out_no_waitlist,
    "waitlist_not_needed_booking": _solve_waitlist_not_needed_booking, "live_delay": _solve_live_delay,
    "live_expected_arrival_intermediate": _solve_live_expected_arrival_intermediate,
    "live_connection_check": _solve_live_connection_check, "live_running_today": _solve_live_running_today,
    "concession_fare": _solve_concession_fare, "concession_party_total": _solve_concession_party_total,
    "concession_not_available": _solve_concession_not_available, "concession_budget_check": _solve_concession_budget_check,
    "cancel_and_rebook_class": _solve_cancel_and_rebook_class, "conditional_waitlisted_noop": _solve_conditional_waitlisted_noop,
    "conditional_waitlisted_cancel_rebook": _solve_conditional_waitlisted_cancel_rebook,
    "cancel_without_pnr_clarification": _solve_cancel_without_pnr_clarification,
    "cancel_multiple_total_refund": _solve_cancel_multiple_total_refund, "availability_and_concession": _solve_availability_and_concession,
}
SOLVERS.update(SOLVERS_V3)


# ----------------------------------------------------------------------------------------- driver
def env_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changes = {k: [before["availability"][k], after["availability"][k]]
               for k in before["availability"] if before["availability"][k] != after["availability"][k]}
    out = {"bookings": after["bookings"], "availability_changes": changes}
    for key in ("cancellations", "waitlist"):  # 3.0: only when something happened (keeps earlier gold byte-identical)
        if after.get(key):
            out[key] = after[key]
    return out


def build_task_gold(spec: SemanticTaskSpec) -> dict[str, Any]:
    env = RailwayEnv()
    env.reset()
    plan = _Plan()
    answer, allowed, effect = SOLVERS[spec.solver.kind](env, spec.solver.params, plan)
    if env.snapshot() != RailwayEnv().snapshot():
        raise AssertionError("solver mutated the environment while deriving gold")
    # Replay only the state-changing calls on a fresh baseline env to obtain the expected final env diff.
    fresh = RailwayEnv()
    fresh.reset()
    base = json.loads(json.dumps(fresh.snapshot()))
    for tool, args in effect:
        _ok(fresh, tool, args)
    diff = env_diff(base, fresh.snapshot())
    bookings = [{k: b[k] for k in ("train_id", "travel_class", "passenger")} for b in diff["bookings"]]
    if "booking_id" in answer:  # derived from the replayed booking, never typed in
        answer["booking_id"] = diff["bookings"][0]["booking_id"]
    if "booking_ids" in answer:  # multi-booking tasks: ids in the gold replay order (ids are order-dependent)
        answer["booking_ids"] = [b["booking_id"] for b in diff["bookings"]]
    gold = GoldSpec(
        semantic_task_id=spec.semantic_task_id, required_calls=plan.calls, dependency_edges=plan.edges,
        final_state=FinalStatePredicate(status=answer["status"], allowed_train_ids=allowed,
                                        travel_class=answer.get("travel_class"), expected_bookings=bookings,
                                        expected_cancellations=[c["pnr"] for c in diff.get("cancellations", [])] or None,
                                        expected_waitlist=[{k: w[k] for k in ("train_id", "travel_class", "passenger")}
                                                           for w in diff.get("waitlist", [])] or None),
        min_calls=sum(1 for c in plan.calls if not c.optional), final_answer=answer, expected_env_diff=diff,
        forbidden_tools=sorted({a.tool for a in spec.prohibited_actions if not a.match}),
        prohibited_actions=spec.prohibited_actions)
    for a in spec.prohibited_actions:  # a prohibition may never contradict the gold solution itself
        for c in plan.calls:
            if c.tool == a.tool and all(c.required_args.get(k) == v for k, v in a.match.items()):
                raise ValueError(f"{spec.semantic_task_id}: gold call {c.call_id} violates prohibition {a.tool}{a.match}")
    out = gold.model_dump(mode="json")
    for k in ("expected_cancellations", "expected_waitlist"):  # 3.0 fields: serialized only when set
        if out["final_state"][k] is None:
            del out["final_state"][k]
    for c in out["required_calls"]:  # serialize expected_error only when set (keeps earlier gold byte-identical)
        if c["expected_error"] is None:
            del c["expected_error"]
    return out


def load_specs(path: Path = SPEC_PATH) -> list[SemanticTaskSpec]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [SemanticTaskSpec(**t) for t in raw["tasks"]]


def build_all() -> dict[str, Any]:
    env = RailwayEnv()
    env.reset()
    out: dict[str, Any] = {"_meta": {
        "generator": "benchmark/build_gold.py (solver over the deterministic environment; no LLM)",
        "benchmark_version": json.loads(SPEC_PATH.read_text(encoding="utf-8"))["benchmark_version"],
        "reference_datetime": env.reference_datetime.isoformat(),
        "env_static_hash": env.static_hash, "env_baseline_state_hash": env.state_hash()}}
    for spec in load_specs():
        out[spec.semantic_task_id] = build_task_gold(spec)
    return out


def render(gold: dict[str, Any]) -> str:
    return json.dumps(gold, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    GOLD_PATH.write_text(render(build_all()), encoding="utf-8")
    print(f"wrote {GOLD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
