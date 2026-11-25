"""Solvers for the 20-tool stage, T101-T200 (benchmark 3.0). Registered into build_gold.SOLVERS.

Same contract as every solver in build_gold.py: solver(env, params, plan) -> (final_answer, allowed_train_ids | None, effects), where
`effects` are the state-changing calls replayed on a fresh environment to obtain the expected final state. Every value is read from the
environment; each solver asserts the design situation (sold out, window not open, too late, ...) so a fixture change cannot silently
change what a task means.
"""
from __future__ import annotations

from typing import Any, Callable

from environment import RailwayEnv


def _ok(env, tool, args):  # same as build_gold._ok (kept local: build_gold imports this module at load time)
    r = env.call(tool, args)
    if not r["ok"]:
        raise ValueError(f"solver call failed: {tool}({args}) -> {r['error']}")
    return r["data"]


def _station_code(env, name):
    d = _ok(env, "resolve_station", {"name": name})
    if d["ambiguous"]:
        raise ValueError(f"spec uses ambiguous station name {name!r}: {d['candidates']}")
    return d["candidates"][0]["code"]


TODAY, TOMORROW = "2026-10-05", "2026-10-06"
SOLVERS_V4: dict[str, Callable] = {}


def k(name: str):
    def reg(fn):
        assert name not in SOLVERS_V4, name
        SOLVERS_V4[name] = fn
        return fn
    return reg


# ----------------------------------------------------------------------------------------- helpers
def _err(env, tool, args) -> str | None:
    r = env.call(tool, args)
    return None if r["ok"] else r["error"]["code"]


def _tk(env, t, c, d):
    return _ok(env, "check_tatkal_availability", {"train_id": t, "travel_class": c, "date": d})


def _st(env, pnr):
    return _ok(env, "get_booking_status", {"pnr": pnr})


def _live(env, t):
    return _ok(env, "get_live_train_status", {"train_id": t})


def _berth(env, t, c):
    return _ok(env, "get_berth_availability", {"train_id": t, "travel_class": c})


def _plat(env, t, s):
    return _ok(env, "get_platform_info", {"train_id": t, "station": s})


def _seats(env, t, c):
    return _ok(env, "check_availability", {"train_id": t, "travel_class": c})["seats_available"]


def _probe(tool, args):
    """Result of a state-changing call on a fresh environment (gold must not mutate `env`)."""
    e = RailwayEnv()
    e.reset()
    return _ok(e, tool, args)


def _stop(lv, code):
    return next(s for s in lv["stops"] if s["station"] == code)


def _hm(s: str) -> int:
    return int(s[:2]) * 60 + int(s[3:])


def _tkbook(t, c, pax, d):
    return ("book_tatkal_ticket", {"train_id": t, "travel_class": c, "passenger": pax, "date": d})


def _book(t, c, pax):
    return ("book_ticket", {"train_id": t, "travel_class": c, "passenger": pax})


def _meal(pnr, s, m, q=1):
    return ("order_meal", {"pnr": pnr, "station": s, "meal": m, "quantity": q})


def _cpl(pnr, cat):
    return ("raise_complaint", {"pnr": pnr, "category": cat})  # description is optional free text (not scored)


def _ok_status(train=None, cls=None, **kw) -> dict:
    return {"status": "success", "selected_train_id": train, **({"travel_class": cls} if cls else {}), **kw}


def _cannot(**kw) -> dict:
    return {"status": "cannot_complete", "selected_train_id": None, **kw}


# ----------------------------------------------------------------------------------------- Tatkal (T101-T120)
@k("tatkal_open_and_seats")
def _t101(env, p, plan):
    x = _tk(env, p["train_id"], p["travel_class"], p["travel_date"])
    assert x["status"] == "OPEN" and x["tatkal_seats"] > 0
    plan.add("check_tatkal_availability", {"train_id": p["train_id"], "travel_class": p["travel_class"], "date": p["travel_date"]})
    return _ok_status(p["train_id"], p["travel_class"], tatkal_status="OPEN", tatkal_seats=x["tatkal_seats"]), [p["train_id"]], []


@k("tatkal_opening_time")
def _t102(env, p, plan):
    x = _tk(env, p["train_id"], p["travel_class"], p["travel_date"])
    assert x["status"] == "NOT_YET_OPEN"
    plan.add("check_tatkal_availability", {"train_id": p["train_id"], "travel_class": p["travel_class"], "date": p["travel_date"]})
    return _ok_status(p["train_id"], p["travel_class"], tatkal_status="NOT_YET_OPEN", opens_at=x["opens_at"][11:]), [p["train_id"]], []


@k("tatkal_direct_booking")
def _t103(env, p, plan):
    x = _tk(env, p["train_id"], p["travel_class"], p["travel_date"])
    assert x["status"] == "OPEN" and x["tatkal_seats"] > 0
    if p.get("expect_general_sold_out"):
        assert _seats(env, p["train_id"], p["travel_class"]) == 0
    a = {"train_id": p["train_id"], "travel_class": p["travel_class"], "passenger": p["passenger"], "date": p["travel_date"]}
    plan.add("book_tatkal_ticket", a)
    return (_ok_status(p["train_id"], p["travel_class"], passenger=p["passenger"], tatkal_fare_inr=x["tatkal_fare_inr"], booking_id=None),
            [p["train_id"]], [_tkbook(p["train_id"], p["travel_class"], p["passenger"], p["travel_date"])])


k("tatkal_explicit_while_general_free")(lambda env, p, plan: (
    (_ for _ in ()).throw(AssertionError("general must have seats")) if _seats(env, p["train_id"], p["travel_class"]) <= 0 else _t103(env, p, plan)))


@k("tatkal_booking_not_open")
def _t104(env, p, plan):
    a = {"train_id": p["train_id"], "travel_class": p["travel_class"], "passenger": p["passenger"], "date": p["travel_date"]}
    assert _err(env, "book_tatkal_ticket", a) == "TATKAL_NOT_OPEN"
    x = _tk(env, p["train_id"], p["travel_class"], p["travel_date"])
    plan.add("book_tatkal_ticket", a, expected_error="TATKAL_NOT_OPEN")  # or the window check (scorer EQUIVALENT_PATHS)
    return _cannot(train_id=p["train_id"], opens_at=x["opens_at"][11:], reason="tatkal_not_open"), None, []


@k("tatkal_train_departed")
def _t111(env, p, plan):
    a = {"train_id": p["train_id"], "travel_class": p["travel_class"], "passenger": p["passenger"], "date": p["travel_date"]}
    assert _err(env, "book_tatkal_ticket", a) == "TRAIN_DEPARTED"
    plan.add("book_tatkal_ticket", a, expected_error="TRAIN_DEPARTED")
    return _cannot(train_id=p["train_id"], reason="train_departed"), None, []


@k("tatkal_not_running_on_date")
def _t112(env, p, plan):
    a = {"train_id": p["train_id"], "travel_class": p["travel_class"], "date": p["date"]}
    assert _err(env, "check_tatkal_availability", a) == "NOT_RUNNING_ON_DATE"
    plan.add("check_tatkal_availability", a, expected_error="NOT_RUNNING_ON_DATE")
    return _cannot(train_id=p["train_id"], reason="not_running_on_date"), None, []


def _general_then(env, p, plan, cap=None, strict=False, allow_waitlist=False):
    """General quota first; if sold out, Tatkal (optionally under a price cap); optionally the waitlist last."""
    t, c, pax, d = p["train_id"], p["travel_class"], p["passenger"], p["travel_date"]
    assert _seats(env, t, c) == 0, "design: general quota sold out"
    c1 = plan.add("check_availability", {"train_id": t, "travel_class": c})
    x = _tk(env, t, c, d)
    assert x["status"] == "OPEN"
    fits = x["tatkal_seats"] > 0 and (cap is None or (x["tatkal_fare_inr"] < cap if strict else x["tatkal_fare_inr"] <= cap))
    if fits:
        if cap is not None:
            plan.add("check_tatkal_availability", {"train_id": t, "travel_class": c, "date": d}, after=[c1])
        plan.add("book_tatkal_ticket", {"train_id": t, "travel_class": c, "passenger": pax, "date": d}, after=[c1])
        return (_ok_status(t, c, passenger=pax, tatkal_fare_inr=x["tatkal_fare_inr"], booking_id=None), [t], [_tkbook(t, c, pax, d)])
    c2 = plan.add("check_tatkal_availability", {"train_id": t, "travel_class": c, "date": d}, after=[c1])
    if allow_waitlist:
        plan.add("join_waitlist", {"train_id": t, "travel_class": c, "passenger": pax}, after=[c2])
        wl = _probe("join_waitlist", {"train_id": t, "travel_class": c, "passenger": pax})
        return (_ok_status(t, c, passenger=pax, booking_status="WAITLISTED", waitlist_position=wl["waitlist_position"]), [t],
                [("join_waitlist", {"train_id": t, "travel_class": c, "passenger": pax})])
    return _cannot(train_id=t, tatkal_seats=x["tatkal_seats"], tatkal_fare_inr=x["tatkal_fare_inr"],
                   reason="tatkal_over_budget" if x["tatkal_seats"] > 0 else "tatkal_sold_out"), None, []


k("general_else_tatkal")(lambda env, p, plan: _general_then(env, p, plan))
k("general_else_tatkal_no_waitlist_all_full")(lambda env, p, plan: _general_then(env, p, plan))


@k("tatkal_under_price_cap")
def _t107(env, p, plan):
    out = _general_then(env, p, plan, cap=p["max_fare_inr"])
    assert out[0]["status"] == "success"
    return out


@k("tatkal_over_price_cap")
def _t108(env, p, plan):
    out = _general_then(env, p, plan, cap=p["max_fare_inr"], strict=True)
    assert out[0]["status"] == "cannot_complete" and out[0]["reason"] == "tatkal_over_budget"
    return out


@k("chain_general_tatkal_waitlist_ends_waitlist")
def _t118(env, p, plan):
    out = _general_then(env, p, plan, allow_waitlist=True)
    assert out[0].get("booking_status") == "WAITLISTED"
    return out


@k("chain_general_tatkal_waitlist_ends_tatkal")
def _t119(env, p, plan):
    out = _general_then(env, p, plan, allow_waitlist=True)
    assert "tatkal_fare_inr" in out[0]
    return out


@k("tatkal_fare_and_seat_query")
def _t109(env, p, plan):
    x = _tk(env, p["train_id"], p["travel_class"], p["travel_date"])
    assert x["status"] == "OPEN"
    plan.add("check_tatkal_availability", {"train_id": p["train_id"], "travel_class": p["travel_class"], "date": p["travel_date"]})
    return _ok_status(p["train_id"], p["travel_class"], tatkal_fare_inr=x["tatkal_fare_inr"], tatkal_seats=x["tatkal_seats"]), [p["train_id"]], []


def _group_tatkal(env, p, plan, all_or_nothing):
    t, c, d, pax = p["train_id"], p["travel_class"], p["travel_date"], p["passengers"]
    x = _tk(env, t, c, d)
    assert x["status"] == "OPEN"
    if x["tatkal_seats"] >= len(pax):
        for n in pax:
            plan.add("book_tatkal_ticket", {"train_id": t, "travel_class": c, "passenger": n, "date": d})
        return _ok_status(t, c, booking_ids=None), [t], [_tkbook(t, c, n, d) for n in pax]
    assert all_or_nothing
    plan.add("check_tatkal_availability", {"train_id": t, "travel_class": c, "date": d})
    return _cannot(train_id=t, tatkal_seats=x["tatkal_seats"], reason="not_enough_tatkal_seats"), None, []


k("tatkal_two_passengers")(lambda env, p, plan: _group_tatkal(env, p, plan, False))
k("tatkal_group_all_or_nothing")(lambda env, p, plan: _group_tatkal(env, p, plan, True))


@k("tatkal_surcharge_difference")
def _t115(env, p, plan):
    x = _tk(env, p["train_id"], p["travel_class"], p["travel_date"])
    fare = _ok(env, "get_fare", {"train_id": p["train_id"], "travel_class": p["travel_class"]})["fare_inr"]
    plan.add("check_tatkal_availability", {"train_id": p["train_id"], "travel_class": p["travel_class"], "date": p["travel_date"]})
    plan.add("get_fare", {"train_id": p["train_id"], "travel_class": p["travel_class"]}, optional=True)  # the Tatkal reply implies it
    return _ok_status(p["train_id"], p["travel_class"], fare_difference_inr=x["tatkal_fare_inr"] - fare), [p["train_id"]], []


@k("tatkal_fare_no_concession")
def _t116(env, p, plan):
    x = _tk(env, p["train_id"], p["travel_class"], p["travel_date"])
    assert x["status"] == "OPEN" and x["concessions_allowed"] is False
    plan.add("check_tatkal_availability", {"train_id": p["train_id"], "travel_class": p["travel_class"], "date": p["travel_date"]})
    return _ok_status(p["train_id"], p["travel_class"], tatkal_fare_inr=x["tatkal_fare_inr"]), [p["train_id"]], []


@k("waitlisted_cancel_then_tatkal")
def _t117(env, p, plan):
    st = _st(env, p["pnr"])
    assert st["status"] == "WAITLISTED" and st["passenger"] == p["booking_passenger"] and st["journey_date"] == p["travel_date"]
    t, c = st["train_id"], p["travel_class"]
    x = _tk(env, t, c, p["travel_date"])
    assert x["status"] == "OPEN" and x["tatkal_seats"] > 0
    c1 = plan.add("cancel_ticket", {"pnr": p["pnr"]})
    plan.add("book_tatkal_ticket", {"train_id": t, "travel_class": c, "passenger": st["passenger"], "date": p["travel_date"]},
             {"train_id": f"{c1}.train_id", "passenger": f"{c1}.passenger"})
    q = _ok(env, "get_cancellation_refund", {"pnr": p["pnr"]})
    return (_ok_status(t, c, refund_inr=q["refund_inr"], tatkal_fare_inr=x["tatkal_fare_inr"], booking_id=None), [t],
            [("cancel_ticket", {"pnr": p["pnr"]}), _tkbook(t, c, st["passenger"], p["travel_date"])])


@k("waitlisted_tatkal_window_for_journey_day")
def _t120(env, p, plan):
    st = _st(env, p["pnr"])
    assert st["status"] == "WAITLISTED"
    x = _tk(env, st["train_id"], st["travel_class"], st["journey_date"])
    assert x["status"] == "NOT_YET_OPEN"
    c1 = plan.add("get_booking_status", {"pnr": p["pnr"]})
    plan.add("check_tatkal_availability", {"train_id": st["train_id"], "travel_class": st["travel_class"], "date": st["journey_date"]},
             {"train_id": f"{c1}.train_id", "date": f"{c1}.journey_date"}, after=[c1])
    return _ok_status(st["train_id"], st["travel_class"], tatkal_status="NOT_YET_OPEN", opens_at=x["opens_at"][11:]), [st["train_id"]], []


# ----------------------------------------------------------------------------------------- berths (T121-T130)
@k("lower_berth_count")
def _t121(env, p, plan):
    b = _berth(env, p["train_id"], p["travel_class"])
    plan.add("get_berth_availability", {"train_id": p["train_id"], "travel_class": p["travel_class"]})
    return _ok_status(p["train_id"], p["travel_class"], lower_berths=b["lower"]), [p["train_id"]], []


def _lower_berth_booking(env, p, plan):
    from .build_gold import _verify_train_serves
    _verify_train_serves(env, p)
    t, c, pax = p["train_id"], p["travel_class"], p.get("passengers") or [p["passenger"]]
    b = _berth(env, t, c)
    c1 = plan.add("get_berth_availability", {"train_id": t, "travel_class": c})
    need = p.get("min_lower_berths", 1)
    if b["lower"] >= need and _seats(env, t, c) >= len(pax):
        for n in pax:
            plan.add("book_ticket", {"train_id": t, "travel_class": c, "passenger": n}, after=[c1])
        out = _ok_status(t, c, lower_berths=b["lower"], **({"booking_id": None} if len(pax) == 1 else {"booking_ids": None}))
        return out, [t], [_book(t, c, n) for n in pax]
    return _cannot(train_id=t, lower_berths=b["lower"], reason="no_lower_berth"), None, []


@k("senior_lower_berth_conditional_booking")
def _t122(env, p, plan):
    out = _lower_berth_booking(env, p, plan)
    assert out[0]["status"] == "success"
    return out


@k("lower_berth_condition_fails")
def _t123(env, p, plan):
    out = _lower_berth_booking(env, p, plan)
    assert out[0]["status"] == "cannot_complete"
    return out


@k("two_lower_berths_group_booking")
def _t127(env, p, plan):
    out = _lower_berth_booking(env, p, plan)
    assert out[0]["status"] == "success" and len(p["passengers"]) == 2
    return out


@k("side_lower_berth_count")
def _t124(env, p, plan):
    b = _berth(env, p["train_id"], p["travel_class"])
    plan.add("get_berth_availability", {"train_id": p["train_id"], "travel_class": p["travel_class"]})
    return _ok_status(p["train_id"], p["travel_class"], side_lower_berths=b["side_lower"]), [p["train_id"]], []


@k("berths_in_chair_car")
def _t125(env, p, plan):
    a = {"train_id": p["train_id"], "travel_class": p["travel_class"]}
    assert _err(env, "get_berth_availability", a) == "NO_BERTHS_IN_CLASS"
    plan.add("get_berth_availability", a, expected_error="NO_BERTHS_IN_CLASS")
    return _cannot(train_id=p["train_id"], reason="no_berths_in_class"), None, []


@k("compare_lower_berths_two_classes")
def _t126(env, p, plan):
    t, (a, b) = p["train_id"], p["classes"]
    la, lb = _berth(env, t, a)["lower"], _berth(env, t, b)["lower"]
    assert la != lb
    plan.add("get_berth_availability", {"train_id": t, "travel_class": a})
    plan.add("get_berth_availability", {"train_id": t, "travel_class": b})
    best = a if la > lb else b
    return _ok_status(t, best, lower_berths=max(la, lb)), [t], []


@k("lower_berth_and_senior_concession")
def _t128(env, p, plan):
    t, c = p["train_id"], p["travel_class"]
    b = _berth(env, t, c)
    cf = _ok(env, "get_concession_fare", {"train_id": t, "travel_class": c, "concession": "senior_citizen"})
    plan.add("get_berth_availability", {"train_id": t, "travel_class": c})
    plan.add("get_concession_fare", {"train_id": t, "travel_class": c, "concession": "senior_citizen"})
    return _ok_status(t, c, lower_berths=b["lower"], concession_fare_inr=cf["concession_fare_inr"]), [t], []


@k("no_lower_then_upper_count")
def _t129(env, p, plan):
    b = _berth(env, p["train_id"], p["travel_class"])
    assert b["lower"] == 0
    plan.add("get_berth_availability", {"train_id": p["train_id"], "travel_class": p["travel_class"]})
    return _ok_status(p["train_id"], p["travel_class"], lower_berths=0, upper_berths=b["upper"]), [p["train_id"]], []


@k("seats_and_lower_berths")
def _t130(env, p, plan):
    t, c = p["train_id"], p["travel_class"]
    plan.add("check_availability", {"train_id": t, "travel_class": c})
    plan.add("get_berth_availability", {"train_id": t, "travel_class": c})
    return _ok_status(t, c, seats_available=_seats(env, t, c), lower_berths=_berth(env, t, c)["lower"]), [t], []


# ----------------------------------------------------------------------------------------- boarding point (T131-T140)
def _code(env, p):
    return _station_code(env, p["station_name"])


def _boarding_ok(env, p, plan, after=None, platform=False):
    s = _code(env, p)
    ch = _probe("change_boarding_point", {"pnr": p["pnr"], "station": s})
    c = plan.add("change_boarding_point", {"pnr": p["pnr"], "station": s}, after=after)
    out = _ok_status(ch["train_id"], None, boarding_station=s, boarding_time=ch["boarding_time"], boarding_date=ch["boarding_date"])
    eff = [("change_boarding_point", {"pnr": p["pnr"], "station": s})]
    if platform:
        plan.add("get_platform_info", {"train_id": ch["train_id"], "station": s}, {"train_id": f"{c}.train_id"})
        out["platform"] = _plat(env, ch["train_id"], s)["platform"]
    return out, [ch["train_id"]], eff


def _boarding_blocked(env, p, plan, code):
    s = _code(env, p)
    assert _err(env, "change_boarding_point", {"pnr": p["pnr"], "station": s}) == code
    plan.add("change_boarding_point", {"pnr": p["pnr"], "station": s}, expected_error=code)
    return _cannot(pnr=p["pnr"], reason=code.lower()), None, []


k("boarding_change_ok")(lambda env, p, plan: _boarding_ok(env, p, plan))
k("boarding_change_and_departure_time")(lambda env, p, plan: _boarding_ok(env, p, plan))
k("boarding_change_and_platform")(lambda env, p, plan: _boarding_ok(env, p, plan, platform=True))
k("boarding_change_too_late")(lambda env, p, plan: _boarding_blocked(env, p, plan, "TOO_LATE_TO_CHANGE"))
k("boarding_change_to_destination")(lambda env, p, plan: _boarding_blocked(env, p, plan, "NOT_EN_ROUTE"))
k("boarding_change_waitlisted")(lambda env, p, plan: _boarding_blocked(env, p, plan, "NOT_CONFIRMED"))
k("boarding_change_not_a_stop")(lambda env, p, plan: _boarding_blocked(env, p, plan, "NOT_A_STOP"))
k("boarding_change_cancelled_ticket")(lambda env, p, plan: _boarding_blocked(env, p, plan, "ALREADY_CANCELLED"))


@k("boarding_change_if_train_stops_there")
def _t137(env, p, plan):
    st = _st(env, p["pnr"])
    s = _code(env, p)
    stops = [x["station"] for x in _ok(env, "get_train_details", {"train_id": st["train_id"]})["stops"]]
    assert s in stops[1:-1]
    return _boarding_ok(env, p, plan)  # the change itself proves the stop; a details lookup before is optional


@k("boarding_departure_preview_no_change")
def _t138(env, p, plan):
    st = _st(env, p["pnr"])
    s = _code(env, p)
    det = _ok(env, "get_train_details", {"train_id": st["train_id"]})
    stop = next(x for x in det["stops"] if x["station"] == s)
    c1 = plan.add("get_booking_status", {"pnr": p["pnr"]})
    plan.add("get_train_details", {"train_id": st["train_id"]}, {"train_id": f"{c1}.train_id"}, after=[c1])
    return _ok_status(st["train_id"], None, boarding_time=stop["departure"]), [st["train_id"]], []


@k("cancel_unless_refund_low_then_change_boarding")
def _t200(env, p, plan):
    q = _ok(env, "get_cancellation_refund", {"pnr": p["pnr"]})
    assert q["refund_inr"] < p["min_refund_inr"]
    c1 = plan.add("get_cancellation_refund", {"pnr": p["pnr"]})
    out = _boarding_ok(env, p, plan, after=[c1])
    out[0]["refund_inr"] = q["refund_inr"]
    return out


# ----------------------------------------------------------------------------------------- meals (T141-T154)
def _meal_ok(env, p, plan, after=None):
    s = _code(env, p)
    o = _probe("order_meal", {"pnr": p["pnr"], "station": s, "meal": p["meal"], "quantity": p.get("quantity", 1)})
    plan.add("order_meal", {"pnr": p["pnr"], "station": s, "meal": p["meal"], "quantity": p.get("quantity", 1)},
             alternatives={"quantity": [None]} if p.get("quantity", 1) == 1 else None, after=after)
    st = _st(env, p["pnr"])
    return (_ok_status(st["train_id"], None, order_amount_inr=o["amount_inr"], delivery_time=o["delivery_time"]), [st["train_id"]],
            [_meal(p["pnr"], s, p["meal"], p.get("quantity", 1))])


def _meal_blocked(env, p, plan, code):
    s = _code(env, p)
    a = {"pnr": p["pnr"], "station": s, "meal": p["meal"], "quantity": p.get("quantity", 1)}
    assert _err(env, "order_meal", a) == code, (_err(env, "order_meal", a), code)
    plan.add("order_meal", a, alternatives={"quantity": [None]}, expected_error=code)
    return _cannot(pnr=p["pnr"], reason=code.lower()), None, []


k("meal_order_ok")(lambda env, p, plan: _meal_ok(env, p, plan))
k("meal_order_two_jain_thalis")(lambda env, p, plan: _meal_ok(env, p, plan))
k("meal_breakfast_future_journey")(lambda env, p, plan: _meal_ok(env, p, plan))
k("meal_order_too_late")(lambda env, p, plan: _meal_blocked(env, p, plan, "ORDER_TOO_LATE"))
k("meal_station_already_passed")(lambda env, p, plan: _meal_blocked(env, p, plan, "STATION_ALREADY_PASSED"))
k("meal_not_served_at_that_hour")(lambda env, p, plan: _meal_blocked(env, p, plan, "MEAL_NOT_SERVED_AT_THIS_TIME"))
k("meal_waitlisted_ticket")(lambda env, p, plan: _meal_blocked(env, p, plan, "NOT_CONFIRMED"))
k("meal_at_boarding_station")(lambda env, p, plan: _meal_blocked(env, p, plan, "NOT_EN_ROUTE"))
k("meal_station_without_catering")(lambda env, p, plan: _meal_blocked(env, p, plan, "CATERING_NOT_AVAILABLE"))
@k("meal_item_not_on_menu")
def _t151(env, p, plan):
    """The menu is in the tool description, so answering without calling is fine (the rejected call is optional)."""
    s = _code(env, p)
    a = {"pnr": p["pnr"], "station": s, "meal": p["meal"], "quantity": 1}
    assert _err(env, "order_meal", a) == "INVALID_MEAL"
    plan.add("order_meal", a, alternatives={"quantity": [None], "meal": p.get("meal_alternatives", [])}, optional=True,
             expected_error="INVALID_MEAL")
    return _cannot(pnr=p["pnr"], reason="invalid_meal"), None, []


def _expected_at(env, pnr, s):
    st = _st(env, pnr)
    lv = _live(env, st["train_id"])
    assert lv["run_start_date"] == st["journey_date"] and lv["status"] == "RUNNING"
    return st, lv, _stop(lv, s)


@k("meal_choice_by_expected_arrival")
def _t150(env, p, plan):
    s = _code(env, p)
    st, lv, stop = _expected_at(env, p["pnr"], s)
    m = p["meal_if_after"] if _hm(stop["expected_arrival"]) > _hm(p["after_time"]) else p["meal_otherwise"]
    assert m == p["meal_if_after"]
    c1 = plan.add("get_live_train_status", {"train_id": st["train_id"]})
    return _meal_ok(env, {**p, "meal": m}, plan, after=[c1])


@k("meal_if_arrival_before_deadline")
def _t151(env, p, plan):
    s = _code(env, p)
    st, lv, stop = _expected_at(env, p["pnr"], s)
    assert _hm(stop["expected_arrival"]) < _hm(p["before_time"])
    c1 = plan.add("get_live_train_status", {"train_id": st["train_id"]})
    out = _meal_ok(env, p, plan, after=[c1])
    out[0]["expected_arrival"] = stop["expected_arrival"]
    return out


@k("complaint_and_meal_order")
def _t152(env, p, plan):
    out = _meal_ok(env, p, plan)
    plan.add("raise_complaint", {"pnr": p["pnr"], "category": p["category"]})
    return out[0], out[1], [*out[2], _cpl(p["pnr"], p["category"])]  # replay in plan order (ids are sequential)


def _next_stop_meal(env, p, plan, platform=False):
    st = _st(env, p["pnr"])
    lv = _live(env, st["train_id"])
    s = lv["next_station"]
    c1 = plan.add("get_live_train_status", {"train_id": st["train_id"]})
    out = _meal_ok(env, {**p, "station_name": s}, plan, after=[c1])
    if platform:
        plan.add("get_platform_info", {"train_id": st["train_id"], "station": s})
        out[0]["platform"] = _plat(env, st["train_id"], s)["platform"]
    return out


k("meal_at_next_station")(lambda env, p, plan: _next_stop_meal(env, p, plan))
k("meal_at_next_station_and_platform")(lambda env, p, plan: _next_stop_meal(env, p, plan, platform=True))


@k("two_meal_items_total")
def _t186(env, p, plan):
    s = _code(env, p)
    total, eff = 0, []
    st = _st(env, p["pnr"])
    for m in p["meals"]:
        total += _probe("order_meal", {"pnr": p["pnr"], "station": s, "meal": m, "quantity": 1})["amount_inr"]
        plan.add("order_meal", {"pnr": p["pnr"], "station": s, "meal": m, "quantity": 1}, alternatives={"quantity": [None]})
        eff.append(_meal(p["pnr"], s, m))
    return _ok_status(st["train_id"], None, order_amount_inr=total), [st["train_id"]], eff


# ----------------------------------------------------------------------------------------- platforms and live status (T155-T162, T179-T180, T194)
@k("platform_lookup")
def _t155(env, p, plan):
    s = _code(env, p)
    plan.add("get_platform_info", {"train_id": p["train_id"], "station": s})
    return _ok_status(p["train_id"], None, platform=_plat(env, p["train_id"], s)["platform"]), [p["train_id"]], []


@k("platform_and_expected_arrival")
def _t156(env, p, plan):
    s = _code(env, p)
    lv = _live(env, p["train_id"])
    plan.add("get_platform_info", {"train_id": p["train_id"], "station": s})
    plan.add("get_live_train_status", {"train_id": p["train_id"]})
    return (_ok_status(p["train_id"], None, platform=_plat(env, p["train_id"], s)["platform"],
                       expected_arrival=_stop(lv, s)["expected_arrival"]), [p["train_id"]], [])


@k("coach_position_from_engine")
def _t157(env, p, plan):
    s = _code(env, p)
    order = _plat(env, p["train_id"], s)["coach_order"]
    first = {"SL": "S1", "3A": "B1", "2A": "A1", "CC": "C1"}[p["travel_class"]]
    plan.add("get_platform_info", {"train_id": p["train_id"], "station": s})
    return _ok_status(p["train_id"], p["travel_class"], coach_position=order.index(first) + 1), [p["train_id"]], []


@k("coach_position_for_pnr")
def _t192(env, p, plan):
    st = _st(env, p["pnr"])
    s = _code(env, p)
    order = _plat(env, st["train_id"], s)["coach_order"]
    c1 = plan.add("get_booking_status", {"pnr": p["pnr"]})
    plan.add("get_platform_info", {"train_id": st["train_id"], "station": s}, {"train_id": f"{c1}.train_id"}, after=[c1])
    first = {"SL": "S1", "3A": "B1", "2A": "A1", "CC": "C1"}[st["travel_class"]]
    return _ok_status(st["train_id"], st["travel_class"], coach_position=order.index(first) + 1), [st["train_id"]], []


@k("platform_train_does_not_stop")
def _t158(env, p, plan):
    s = _code(env, p)
    assert _err(env, "get_platform_info", {"train_id": p["train_id"], "station": s}) == "NOT_A_STOP"
    plan.add("get_platform_info", {"train_id": p["train_id"], "station": s}, expected_error="NOT_A_STOP")
    return _cannot(train_id=p["train_id"], reason="not_a_stop"), None, []


@k("platform_for_pnr_boarding")
def _t159(env, p, plan):
    st = _st(env, p["pnr"])
    c1 = plan.add("get_booking_status", {"pnr": p["pnr"]})
    plan.add("get_platform_info", {"train_id": st["train_id"], "station": st["boarding_station"]},
             {"train_id": f"{c1}.train_id", "station": f"{c1}.boarding_station"}, after=[c1])
    return _ok_status(st["train_id"], None, platform=_plat(env, st["train_id"], st["boarding_station"])["platform"]), [st["train_id"]], []


@k("platform_and_delay")
def _t160(env, p, plan):
    s = _code(env, p)
    lv = _live(env, p["train_id"])
    assert lv["status"] == "RUNNING"
    plan.add("get_platform_info", {"train_id": p["train_id"], "station": s})
    plan.add("get_live_train_status", {"train_id": p["train_id"]})
    return _ok_status(p["train_id"], None, platform=_plat(env, p["train_id"], s)["platform"], delay_minutes=lv["delay_minutes"]), [p["train_id"]], []


@k("platform_if_delay_over_threshold")
def _t161(env, p, plan):
    s = _code(env, p)
    lv = _live(env, p["train_id"])
    assert lv["delay_minutes"] > p["min_delay_minutes"]
    c1 = plan.add("get_live_train_status", {"train_id": p["train_id"]})
    plan.add("get_platform_info", {"train_id": p["train_id"], "station": s}, after=[c1])
    return _ok_status(p["train_id"], None, platform=_plat(env, p["train_id"], s)["platform"], delay_minutes=lv["delay_minutes"]), [p["train_id"]], []


@k("arrived_yet_and_platform")
def _t162(env, p, plan):
    s = _code(env, p)
    lv = _live(env, p["train_id"])
    assert lv["status"] == "RUNNING" and _hm(_stop(lv, s)["expected_arrival"]) > 9 * 60
    plan.add("get_live_train_status", {"train_id": p["train_id"]})
    plan.add("get_platform_info", {"train_id": p["train_id"], "station": s})
    return (_ok_status(p["train_id"], None, platform=_plat(env, p["train_id"], s)["platform"], expected_arrival=_stop(lv, s)["expected_arrival"]),
            [p["train_id"]], [])


@k("timetable_arrival_not_live")
def _t179(env, p, plan):
    s = _code(env, p)
    det = _ok(env, "get_train_details", {"train_id": p["train_id"]})
    lv = _live(env, p["train_id"])
    arr = next(x for x in det["stops"] if x["station"] == s)["arrival"]
    assert lv["delay_minutes"] and _stop(lv, s)["expected_arrival"] != arr, "design: live and timetable must differ"
    plan.add("get_train_details", {"train_id": p["train_id"]})
    return _ok_status(p["train_id"], None, scheduled_arrival=arr), [p["train_id"]], []


@k("live_expected_arrival_at_destination")
def _t180(env, p, plan):
    s = _code(env, p)
    lv = _live(env, p["train_id"])
    assert lv["status"] == "RUNNING" and s == lv["stops"][-1]["station"]
    plan.add("get_live_train_status", {"train_id": p["train_id"]})
    return _ok_status(p["train_id"], None, expected_arrival=_stop(lv, s)["expected_arrival"], delay_minutes=lv["delay_minutes"]), [p["train_id"]], []


@k("live_delay_and_last_station")
def _t194(env, p, plan):
    lv = _live(env, p["train_id"])
    assert lv["status"] == "RUNNING"
    plan.add("get_live_train_status", {"train_id": p["train_id"]})
    return _ok_status(p["train_id"], None, delay_minutes=lv["delay_minutes"], station_code=lv["last_station"]), [p["train_id"]], []


# ----------------------------------------------------------------------------------------- TDR (T163-T170, T184, T187, T199)
def _tdr_view(env, pnr):
    st = _st(env, pnr)
    lv = _live(env, st["train_id"])
    assert lv["run_start_date"] == st["journey_date"]
    return st, lv


@k("tdr_file_ok")
def _t163(env, p, plan, after=None):
    st, lv = _tdr_view(env, p["pnr"])
    t = _probe("file_tdr", {"pnr": p["pnr"]})
    plan.add("file_tdr", {"pnr": p["pnr"]}, after=after)
    return _ok_status(st["train_id"], None, refund_inr=t["refund_inr"], delay_minutes=t["delay_minutes"]), [st["train_id"]], [("file_tdr", {"pnr": p["pnr"]})]


@k("best_refund_is_tdr_not_cancel")
def _t166(env, p, plan):
    q = _ok(env, "get_cancellation_refund", {"pnr": p["pnr"]})
    c1 = plan.add("get_cancellation_refund", {"pnr": p["pnr"]})  # 'whichever gives more': the cancel quote is needed to compare
    out = _t163(env, p, plan, after=[c1])
    assert out[0]["refund_inr"] > q["refund_inr"]
    out[0]["cancel_refund_inr"] = q["refund_inr"]
    return out


def _tdr_blocked(env, p, plan, code):
    assert _err(env, "file_tdr", {"pnr": p["pnr"]}) == code
    plan.add("file_tdr", {"pnr": p["pnr"]}, expected_error=code)
    return _cannot(pnr=p["pnr"], reason=code.lower()), None, []


k("tdr_not_eligible_delay_too_small")(lambda env, p, plan: _tdr_blocked(env, p, plan, "TDR_NOT_ELIGIBLE"))
k("tdr_after_train_left")(lambda env, p, plan: _tdr_blocked(env, p, plan, "TDR_WINDOW_CLOSED"))
k("tdr_cancelled_ticket")(lambda env, p, plan: _tdr_blocked(env, p, plan, "ALREADY_CANCELLED"))


@k("tdr_eligibility_without_filing")
def _t167(env, p, plan):
    st, lv = _tdr_view(env, p["pnr"])
    assert lv["delay_minutes"] >= 180 and lv["status"] == "NOT_STARTED"
    c1 = plan.add("get_booking_status", {"pnr": p["pnr"]})
    plan.add("get_live_train_status", {"train_id": st["train_id"]}, {"train_id": f"{c1}.train_id"}, after=[c1])
    return _ok_status(st["train_id"], None, tdr_eligible=True, delay_minutes=lv["delay_minutes"]), [st["train_id"]], []


@k("cancel_else_tdr_both_blocked")
def _t168(env, p, plan):
    assert _err(env, "cancel_ticket", {"pnr": p["pnr"]}) == "JOURNEY_STARTED"
    assert _err(env, "file_tdr", {"pnr": p["pnr"]}) == "TDR_WINDOW_CLOSED"
    c1 = plan.add("cancel_ticket", {"pnr": p["pnr"]}, expected_error="JOURNEY_STARTED")
    plan.add("file_tdr", {"pnr": p["pnr"]}, after=[c1], expected_error="TDR_WINDOW_CLOSED")
    return _cannot(pnr=p["pnr"], reason="cancel_and_tdr_not_possible"), None, []


@k("train_delay_tdr_threshold_check")
def _t170(env, p, plan):
    lv = _live(env, p["train_id"])
    assert lv["run_start_date"] == TODAY and 0 < lv["delay_minutes"] < 180
    plan.add("get_live_train_status", {"train_id": p["train_id"]})
    return _ok_status(p["train_id"], None, tdr_eligible=False, delay_minutes=lv["delay_minutes"]), [p["train_id"]], []


@k("cancel_refund_vs_tdr_quote")
def _t184(env, p, plan):
    st, lv = _tdr_view(env, p["pnr"])
    q = _ok(env, "get_cancellation_refund", {"pnr": p["pnr"]})
    assert lv["delay_minutes"] >= 180 and lv["status"] == "NOT_STARTED"
    c1 = plan.add("get_cancellation_refund", {"pnr": p["pnr"]})
    plan.add("get_booking_status", {"pnr": p["pnr"]}, optional=True)
    plan.add("get_live_train_status", {"train_id": st["train_id"]})
    return _ok_status(st["train_id"], None, refund_inr=q["refund_inr"], tdr_refund_inr=st["fare_inr"], tdr_eligible=True), [st["train_id"]], []


@k("tdr_else_punctuality_complaint")
def _t187(env, p, plan):
    assert _err(env, "file_tdr", {"pnr": p["pnr"]}) == "TDR_WINDOW_CLOSED"
    c1 = plan.add("file_tdr", {"pnr": p["pnr"]}, expected_error="TDR_WINDOW_CLOSED")
    plan.add("raise_complaint", {"pnr": p["pnr"], "category": "punctuality"}, after=[c1])
    st = _st(env, p["pnr"])
    return _ok_status(st["train_id"], None), [st["train_id"]], [_cpl(p["pnr"], "punctuality")]


@k("tdr_if_late_then_book_other_train")
def _t199(env, p, plan):
    from .build_gold import _verify_train_serves
    _verify_train_serves(env, {**p, "train_id": p["new_train_id"], "date": p["travel_date"]})
    st, lv = _tdr_view(env, p["pnr"])
    assert lv["delay_minutes"] > 180 and _seats(env, p["new_train_id"], p["travel_class"]) > 0
    c1 = plan.add("file_tdr", {"pnr": p["pnr"]})
    plan.add("book_ticket", {"train_id": p["new_train_id"], "travel_class": p["travel_class"], "passenger": p["passenger"]}, after=[c1])
    return (_ok_status(p["new_train_id"], p["travel_class"], refund_inr=st["fare_inr"], booking_id=None), [p["new_train_id"]],
            [("file_tdr", {"pnr": p["pnr"]}), _book(p["new_train_id"], p["travel_class"], p["passenger"])])


# ----------------------------------------------------------------------------------------- complaints (T171-T178, T189, T195)
def _complaint_ok(env, p, plan, after=None):
    st = _st(env, p["pnr"])
    _probe("raise_complaint", {"pnr": p["pnr"], "category": p["category"]})
    plan.add("raise_complaint", {"pnr": p["pnr"], "category": p["category"]}, after=after)
    return _ok_status(st["train_id"], None), [st["train_id"]], [_cpl(p["pnr"], p["category"])]


def _complaint_blocked(env, p, plan, code):
    assert _err(env, "raise_complaint", {"pnr": p["pnr"], "category": p["category"]}) == code
    plan.add("raise_complaint", {"pnr": p["pnr"], "category": p["category"]}, expected_error=code)
    return _cannot(pnr=p["pnr"], reason=code.lower()), None, []


k("complaint_ac_not_working")(lambda env, p, plan: _complaint_ok(env, p, plan))
k("complaint_water_shortage")(lambda env, p, plan: _complaint_ok(env, p, plan))
k("complaint_cleanliness_running")(lambda env, p, plan: _complaint_ok(env, p, plan))
k("complaint_security")(lambda env, p, plan: _complaint_ok(env, p, plan))
k("complaint_punctuality")(lambda env, p, plan: _complaint_ok(env, p, plan))
k("complaint_catering")(lambda env, p, plan: _complaint_ok(env, p, plan))
k("complaint_ac_in_non_ac_class")(lambda env, p, plan: _complaint_blocked(env, p, plan, "CATEGORY_NOT_APPLICABLE"))
k("complaint_journey_not_started")(lambda env, p, plan: _complaint_blocked(env, p, plan, "JOURNEY_NOT_IN_PROGRESS"))


@k("complaint_without_pnr")
def _t176(env, p, plan):
    return {"status": "needs_clarification", "selected_train_id": None, "missing": "pnr"}, None, []


@k("complaint_if_delay_over_an_hour")
def _t189(env, p, plan):
    lv = _live(env, p["train_id"])
    assert lv["delay_minutes"] > p["min_delay_minutes"]
    c1 = plan.add("get_live_train_status", {"train_id": p["train_id"]})
    out = _complaint_ok(env, p, plan, after=[c1])
    out[0]["delay_minutes"] = lv["delay_minutes"]
    return out


# ----------------------------------------------------------------------------------------- mixed (T181-T198)
@k("platform_only_if_confirmed")
def _t181(env, p, plan):
    st = _st(env, p["pnr"])
    assert st["status"] != "CONFIRMED"
    plan.add("get_booking_status", {"pnr": p["pnr"]})
    return _ok_status(st["train_id"], None, booking_status=st["status"]), [st["train_id"]], []


@k("search_today_seat_and_platform")
def _t182(env, p, plan):
    from .build_gold import _resolve_calls, _trains
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    tr = [t for t in _trains(env, src, dst, p["travel_date"]) if t["departure"] == p["departure_time"]]
    assert len(tr) == 1 and p["travel_class"] in tr[0]["classes"]
    t = tr[0]["train_id"]
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["travel_date"]}, after=resolves)
    plan.add("check_availability", {"train_id": t, "travel_class": p["travel_class"]}, {"train_id": f"{c3}.trains[*].train_id"}, after=[c3])
    plan.add("get_platform_info", {"train_id": t, "station": src}, {"train_id": f"{c3}.trains[*].train_id"}, after=[c3])
    return (_ok_status(t, p["travel_class"], seats_available=_seats(env, t, p["travel_class"]), platform=_plat(env, t, src)["platform"]),
            [t], [])


@k("tatkal_open_and_lower_berths")
def _t183(env, p, plan):
    t, c = p["train_id"], p["travel_class"]
    x = _tk(env, t, c, p["travel_date"])
    plan.add("check_tatkal_availability", {"train_id": t, "travel_class": c, "date": p["travel_date"]})
    plan.add("get_berth_availability", {"train_id": t, "travel_class": c})
    return _ok_status(t, c, tatkal_status=x["status"], lower_berths=_berth(env, t, c)["lower"]), [t], []


@k("which_of_two_pnrs_confirmed")
def _t185(env, p, plan):
    sts = [_st(env, x) for x in p["pnrs"]]
    conf = [s for s in sts if s["status"] == "CONFIRMED"]
    assert len(conf) == 1
    for x in p["pnrs"]:
        plan.add("get_booking_status", {"pnr": x})
    return _ok_status(conf[0]["train_id"], None, confirmed_pnr=conf[0]["pnr"]), [conf[0]["train_id"]], []


@k("lower_berth_then_tatkal_booking")
def _t188(env, p, plan):
    t, c = p["train_id"], p["travel_class"]
    assert _berth(env, t, c)["lower"] > 0
    x = _tk(env, t, c, p["travel_date"])
    assert x["status"] == "OPEN" and x["tatkal_seats"] > 0
    c1 = plan.add("get_berth_availability", {"train_id": t, "travel_class": c})
    plan.add("book_tatkal_ticket", {"train_id": t, "travel_class": c, "passenger": p["passenger"], "date": p["travel_date"]}, after=[c1])
    return (_ok_status(t, c, tatkal_fare_inr=x["tatkal_fare_inr"], booking_id=None), [t],
            [_tkbook(t, c, p["passenger"], p["travel_date"])])


@k("waitlisted_then_tatkal_fare_no_booking")
def _t190(env, p, plan):
    st = _st(env, p["pnr"])
    assert st["status"] == "WAITLISTED"
    x = _tk(env, st["train_id"], st["travel_class"], st["journey_date"])
    assert x["status"] == "OPEN"
    c1 = plan.add("get_booking_status", {"pnr": p["pnr"]})
    plan.add("check_tatkal_availability", {"train_id": st["train_id"], "travel_class": st["travel_class"], "date": st["journey_date"]},
             {"train_id": f"{c1}.train_id", "date": f"{c1}.journey_date"}, after=[c1])
    return (_ok_status(st["train_id"], st["travel_class"], booking_status="WAITLISTED", tatkal_status="OPEN",
                       tatkal_fare_inr=x["tatkal_fare_inr"]), [st["train_id"]], [])


@k("search_today_then_tatkal_booking")
def _t191(env, p, plan):
    from .build_gold import _resolve_calls, _trains
    src, dst, resolves = _resolve_calls(env, plan, p["source_name"], p["destination_name"])
    tr = [t for t in _trains(env, src, dst, p["travel_date"]) if p["travel_class"] in t["classes"]]
    assert len(tr) == 1
    t = tr[0]["train_id"]
    x = _tk(env, t, p["travel_class"], p["travel_date"])
    assert x["status"] == "OPEN" and x["tatkal_seats"] > 0
    c3 = plan.add("search_trains", {"source": src, "destination": dst, "date": p["travel_date"]}, after=resolves)
    plan.add("book_tatkal_ticket", {"train_id": t, "travel_class": p["travel_class"], "passenger": p["passenger"], "date": p["travel_date"]},
             {"train_id": f"{c3}.trains[*].train_id"}, after=[c3])
    return (_ok_status(t, p["travel_class"], tatkal_fare_inr=x["tatkal_fare_inr"], booking_id=None), [t],
            [_tkbook(t, p["travel_class"], p["passenger"], p["travel_date"])])


@k("tatkal_booking_and_platform")
def _t193(env, p, plan):
    out = _t103(env, p, plan)
    s = _code(env, p)
    plan.add("get_platform_info", {"train_id": p["train_id"], "station": s})
    out[0]["platform"] = _plat(env, p["train_id"], s)["platform"]
    return out


@k("tatkal_opening_times_two_classes")
def _t196(env, p, plan):
    t, d = p["train_id"], p["travel_date"]
    times = {}
    for c in p["classes"]:
        x = _tk(env, t, c, d)
        assert x["status"] == "NOT_YET_OPEN"
        plan.add("check_tatkal_availability", {"train_id": t, "travel_class": c, "date": d})
        times[c] = x["opens_at"][11:]
    assert len(set(times.values())) == 2
    return _ok_status(t, None, opens_at_by_class=times), [t], []


@k("lower_berth_fallback_other_class_booking")
def _t197(env, p, plan):
    from .build_gold import _verify_train_serves
    _verify_train_serves(env, p)
    t, c, fb, pax = p["train_id"], p["travel_class"], p["fallback_class"], p["passenger"]
    assert _berth(env, t, c)["lower"] == 0 and _berth(env, t, fb)["lower"] > 0 and _seats(env, t, fb) > 0
    c1 = plan.add("get_berth_availability", {"train_id": t, "travel_class": c})
    c2 = plan.add("get_berth_availability", {"train_id": t, "travel_class": fb}, after=[c1])
    plan.add("book_ticket", {"train_id": t, "travel_class": fb, "passenger": pax}, after=[c2])
    return _ok_status(t, fb, lower_berths=_berth(env, t, fb)["lower"], booking_id=None), [t], [_book(t, fb, pax)]
