"""Independent oracle for batch T101-T200 (used by validate_tasks.RawOracle). Recomputes every expected value from the RAW fixture JSON
(trains.json, account.json, live_status.json, services.json) with the service rules restated here; it imports no environment code and
no solver. If this file and the environment disagree, validation fails, which is the point.

Rules restated (benchmark 3.0, 20-tool stage):
* a run is identified by the date it leaves its origin; every stop of a run is shifted by the run's constant delay (live_status.json);
* live status shows the run in progress now, else today's run;
* Tatkal for date D opens on D-1 at 10:00 (AC) / 11:00 (SL), closes when the train leaves its origin (scheduled time); fare = fare + charge;
  no concessions; seats from services.json (missing = 0); not available on a day the train does not leave its origin;
* berths: services.json split, absent for CC; platforms per (train, station); coach position = 1-based index in coach_order (engine = 1);
* boarding change: confirmed ticket, intermediate stop only, at least 24 h before the scheduled origin departure;
* meals: confirmed ticket, stop strictly after boarding and before the destination, catering station, menu item, quantity 1-6, expected
  arrival (scheduled + delay) still ahead and >= 120 min away, inside the serving hours; amount = price * quantity;
* TDR: confirmed ticket, delay >= 180, filed before the expected departure from the boarding station; refund = fare;
* complaints: confirmed ticket, known category, AC category only in 2A/3A/CC, journey in progress (expected origin departure <= now <
  expected destination arrival);
* cancellation refund = fare - charge (class charge, or the WAITLISTED charge); no cancellation after the origin departure.
"""
from __future__ import annotations

import json
from datetime import date as Date, datetime, timedelta
from typing import Any

from environment.state import DATA_DIR

NOW = datetime(2026, 10, 5, 9, 0)
WD = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
COACH_OF = {"SL": "S1", "3A": "B1", "2A": "A1", "CC": "C1"}
AC = {"2A", "3A", "CC"}


def _hm(s: str) -> int:
    return int(s[:2]) * 60 + int(s[3:])


def _fmt(dt: datetime) -> str:
    return dt.strftime("%H:%M")


class Oracle6:
    def __init__(self) -> None:
        load = lambda n: json.loads((DATA_DIR / n).read_text(encoding="utf-8"))  # noqa: E731
        self.T = {t["train_id"]: t for t in load("trains.json")["trains"]}
        acct = load("account.json")
        self.A = {b["pnr"]: b for b in acct["account_bookings"]}
        self.charge = acct["cancellation_charge_inr"]
        self.conc = acct["concession_percent"]
        self.wl = acct["waitlist_baseline"]
        self.delays = {(r["train_id"], r["run_start_date"]): r["delay_minutes"] for r in load("live_status.json")["runs"]}
        self.S = load("services.json")
        self.codes = {s["code"]: s for s in load("stations.json")["stations"]}

    # ----------------------------------------------------------- primitives
    def code(self, name: str) -> str:
        key = name.strip().casefold()
        hits = {c for c, s in self.codes.items() if key in {x.casefold() for x in [c, s["name"], s["city"], *sum(s["aliases"].values(), [])]}}
        assert len(hits) == 1, (name, hits)
        return hits.pop()

    def times(self, tid: str, start: Date) -> dict[str, tuple[datetime | None, datetime | None]]:
        d = self.delays.get((tid, start.isoformat()), 0)
        base = datetime.combine(start, datetime.min.time())
        out = {}
        for s in self.T[tid]["stops"]:
            arr = base + timedelta(days=s.get("arrival_day") or 0, minutes=_hm(s["arrival"]) + d) if s.get("arrival") else None
            dep = base + timedelta(days=s.get("departure_day") or 0, minutes=_hm(s["departure"]) + d) if s.get("departure") else None
            out[s["station"]] = (arr, dep)
        return out

    def runs_on(self, tid: str, d: Date) -> bool:
        return WD[d.weekday()] in self.T[tid]["operating_days"]

    def live(self, tid: str) -> dict[str, Any]:
        t = self.T[tid]
        chosen = None
        for back in range(max((s.get("arrival_day") or 0) for s in t["stops"]), -1, -1):
            start = NOW.date() - timedelta(days=back)
            if not self.runs_on(tid, start):
                continue
            tm = self.times(tid, start)
            stops = list(tm)
            first, last = tm[stops[0]][1], tm[stops[-1]][0]
            status = "NOT_STARTED" if NOW < first else ("ARRIVED" if NOW >= last else "RUNNING")
            if status == "RUNNING" or (back == 0 and (chosen is None or chosen["status"] != "RUNNING")):
                reached = [s for s in stops if (tm[s][0] or tm[s][1]) <= NOW]
                last_st = reached[-1] if status != "NOT_STARTED" and reached else None
                chosen = {"start": start, "status": status, "delay": self.delays.get((tid, start.isoformat()), 0), "times": tm,
                          "last": last_st, "next": stops[stops.index(last_st) + 1] if last_st and status == "RUNNING" else None}
        return chosen

    def tatkal(self, tid: str, cls: str, d: str) -> dict[str, Any]:
        day = Date.fromisoformat(d)
        if not self.runs_on(tid, day):
            return {"error": "NOT_RUNNING_ON_DATE"}
        opens = datetime.combine(day - timedelta(days=1), datetime.min.time()) + timedelta(minutes=_hm(self.S["tatkal"]["opens_at"][cls]))
        departs = datetime.combine(day, datetime.min.time()) + timedelta(minutes=_hm(self.T[tid]["stops"][0]["departure"]))
        status = "DEPARTED" if NOW >= departs else ("NOT_YET_OPEN" if NOW < opens else "OPEN")
        return {"status": status, "opens_at": _fmt(opens), "seats": self.S["tatkal"]["seats"].get(f"{tid}|{cls}", 0),
                "fare": self.T[tid]["classes"][cls]["fare_inr"] + self.S["tatkal"]["charge_inr"][cls]}

    def seats(self, tid: str, cls: str) -> int:
        return self.T[tid]["classes"][cls]["seats"]

    def fare(self, tid: str, cls: str) -> int:
        return self.T[tid]["classes"][cls]["fare_inr"]

    def berths(self, tid: str, cls: str) -> dict[str, int] | None:
        return self.S["berths"].get(f"{tid}|{cls}")

    def platform(self, tid: str, st: str) -> int | None:
        return self.S["platforms"].get(f"{tid}|{st}")

    def coach_pos(self, tid: str, cls: str) -> int:
        return self.S["coach_order"][tid].index(COACH_OF[cls]) + 1

    def pnr(self, pnr: str) -> dict[str, Any] | None:
        b = self.A.get(pnr)
        return None if b is None else {**b, "boarding": self.T[b["train_id"]]["stops"][0]["station"]}

    def refund(self, pnr: str) -> int:
        b = self.A[pnr]
        return b["fare_inr"] - self.charge["WAITLISTED" if b["status"] == "WAITLISTED" else b["travel_class"]]

    def service_block(self, b: dict[str, Any] | None) -> str | None:
        if b is None:
            return "PNR_NOT_FOUND"
        if b["status"] == "CANCELLED":
            return "ALREADY_CANCELLED"
        return None if b["status"] == "CONFIRMED" else "NOT_CONFIRMED"

    def boarding(self, pnr: str, st: str) -> dict[str, Any]:
        b = self.pnr(pnr)
        if self.service_block(b):
            return {"error": self.service_block(b)}
        stops = self.T[b["train_id"]]["stops"]
        codes = [s["station"] for s in stops]
        if st not in codes:
            return {"error": "NOT_A_STOP"}
        if st in (codes[0], codes[-1]):
            return {"error": "NOT_EN_ROUTE"}
        start = Date.fromisoformat(b["journey_date"])
        if datetime.combine(start, datetime.min.time()) + timedelta(minutes=_hm(stops[0]["departure"])) - NOW < timedelta(hours=24):
            return {"error": "TOO_LATE_TO_CHANGE"}
        s = stops[codes.index(st)]
        return {"train_id": b["train_id"], "time": s["departure"], "date": (start + timedelta(days=s.get("departure_day") or 0)).isoformat()}

    def meal(self, pnr: str, st: str, meal: str, qty: int = 1) -> dict[str, Any]:
        b = self.pnr(pnr)
        if self.service_block(b):
            return {"error": self.service_block(b)}
        codes = [s["station"] for s in self.T[b["train_id"]]["stops"]]
        cat = self.S["catering"]
        if st not in codes:
            return {"error": "NOT_A_STOP"}
        if not codes.index(b["boarding"]) < codes.index(st) < len(codes) - 1:
            return {"error": "NOT_EN_ROUTE"}
        if st not in cat["stations"]:
            return {"error": "CATERING_NOT_AVAILABLE"}
        if meal not in cat["menu_inr"]:
            return {"error": "INVALID_MEAL"}
        arr = self.times(b["train_id"], Date.fromisoformat(b["journey_date"]))[st][0]
        if arr <= NOW:
            return {"error": "STATION_ALREADY_PASSED"}
        if arr - NOW < timedelta(minutes=cat["min_lead_minutes"]):
            return {"error": "ORDER_TOO_LATE"}
        lo, hi = cat["serving_hours"][meal]
        if not _hm(lo) <= arr.hour * 60 + arr.minute <= _hm(hi):
            return {"error": "MEAL_NOT_SERVED_AT_THIS_TIME"}
        return {"amount": cat["menu_inr"][meal] * qty, "time": _fmt(arr), "train_id": b["train_id"]}

    def tdr(self, pnr: str) -> dict[str, Any]:
        b = self.pnr(pnr)
        if self.service_block(b):
            return {"error": self.service_block(b)}
        start = Date.fromisoformat(b["journey_date"])
        delay = self.delays.get((b["train_id"], b["journey_date"]), 0)
        if delay < self.S["tdr"]["min_delay_minutes"]:
            return {"error": "TDR_NOT_ELIGIBLE", "delay": delay}
        if self.times(b["train_id"], start)[b["boarding"]][1] <= NOW:
            return {"error": "TDR_WINDOW_CLOSED", "delay": delay}
        return {"refund": b["fare_inr"], "delay": delay, "train_id": b["train_id"]}

    def complaint(self, pnr: str, cat: str) -> dict[str, Any]:
        b = self.pnr(pnr)
        if self.service_block(b):
            return {"error": self.service_block(b)}
        if cat not in self.S["complaints"]["categories"]:
            return {"error": "INVALID_CATEGORY"}
        if cat in self.S["complaints"]["ac_classes_only"] and b["travel_class"] not in AC:
            return {"error": "CATEGORY_NOT_APPLICABLE"}
        tm = self.times(b["train_id"], Date.fromisoformat(b["journey_date"]))
        stops = list(tm)
        if not tm[stops[0]][1] <= NOW < tm[stops[-1]][0]:
            return {"error": "JOURNEY_NOT_IN_PROGRESS"}
        return {"train_id": b["train_id"]}

    def search(self, src: str, dst: str, d: str) -> list[str]:
        out = []
        for tid, t in self.T.items():
            codes = [s["station"] for s in t["stops"]]
            if src in codes and dst in codes and codes.index(src) < codes.index(dst):
                s = t["stops"][codes.index(src)]
                start = Date.fromisoformat(d) - timedelta(days=s.get("departure_day") or 0)
                if self.runs_on(tid, start) and not (d == NOW.date().isoformat() and _hm(s["departure"]) <= NOW.hour * 60 + NOW.minute):
                    out.append(tid)
        return out

    # ----------------------------------------------------------- kind -> expected answer subset
    def answer(self, kind: str, p: dict[str, Any]) -> dict[str, Any]:  # noqa: C901 (one branch per task family, on purpose)
        tid, cls = p.get("train_id"), p.get("travel_class")
        ok = lambda t, **a: {"train_ids": {t}, "answer": {"status": "success", **a}}  # noqa: E731
        no = lambda **a: {"answer": {"status": "cannot_complete", **a}}  # noqa: E731
        st = self.code(p["station_name"]) if p.get("station_name") else None
        # Tatkal
        if kind in ("tatkal_open_and_seats", "tatkal_fare_and_seat_query"):
            x = self.tatkal(tid, cls, p["travel_date"])
            assert x["status"] == "OPEN"
            return ok(tid, tatkal_seats=x["seats"], **({"tatkal_status": "OPEN"} if kind == "tatkal_open_and_seats" else {"tatkal_fare_inr": x["fare"]}))
        if kind == "tatkal_opening_time":
            x = self.tatkal(tid, cls, p["travel_date"])
            return ok(tid, tatkal_status=x["status"], opens_at=x["opens_at"])
        if kind in ("tatkal_direct_booking", "tatkal_explicit_while_general_free", "tatkal_booking_and_platform", "lower_berth_then_tatkal_booking"):
            x = self.tatkal(tid, cls, p["travel_date"])
            assert x["status"] == "OPEN" and x["seats"] > 0
            if kind == "lower_berth_then_tatkal_booking":
                assert self.berths(tid, cls)["lower"] > 0
            a = {"tatkal_fare_inr": x["fare"]}
            if kind == "tatkal_booking_and_platform":
                a["platform"] = self.platform(tid, st)
            return {**ok(tid, **a), "effects": {"tatkal_bookings": [(tid, cls, p["passenger"], p["travel_date"])]}}
        if kind in ("tatkal_booking_not_open", "tatkal_train_departed"):
            x = self.tatkal(tid, cls, p["travel_date"])
            want = {"tatkal_booking_not_open": "NOT_YET_OPEN", "tatkal_train_departed": "DEPARTED"}[kind]
            assert x["status"] == want
            return no(reason="tatkal_not_open" if want == "NOT_YET_OPEN" else "train_departed",
                      **({"opens_at": x["opens_at"]} if want == "NOT_YET_OPEN" else {}))
        if kind == "tatkal_not_running_on_date":
            assert self.tatkal(tid, cls, p["date"]).get("error") == "NOT_RUNNING_ON_DATE"
            return no(reason="not_running_on_date")
        if kind.startswith("general_else_tatkal") or kind.startswith("chain_general") or kind in ("tatkal_under_price_cap", "tatkal_over_price_cap"):
            assert self.seats(tid, cls) == 0
            x = self.tatkal(tid, cls, p["travel_date"])
            cap = p.get("max_fare_inr")
            fits = x["seats"] > 0 and (cap is None or (x["fare"] < cap if kind == "tatkal_over_price_cap" else x["fare"] <= cap))
            if fits:
                return {**ok(tid, tatkal_fare_inr=x["fare"]), "effects": {"tatkal_bookings": [(tid, cls, p["passenger"], p["travel_date"])]}}
            if kind.startswith("chain_general"):
                return {**ok(tid, booking_status="WAITLISTED", waitlist_position=self.wl.get(f"{tid}|{cls}", 0) + 1),
                        "waitlist": [(tid, cls, p["passenger"])]}
            return no(tatkal_seats=x["seats"], tatkal_fare_inr=x["fare"], reason="tatkal_over_budget" if x["seats"] else "tatkal_sold_out")
        if kind in ("tatkal_two_passengers", "tatkal_group_all_or_nothing"):
            x = self.tatkal(tid, cls, p["travel_date"])
            if x["seats"] >= len(p["passengers"]):
                return {"train_ids": {tid}, "answer": {"status": "success"},
                        "effects": {"tatkal_bookings": [(tid, cls, n, p["travel_date"]) for n in p["passengers"]]}}
            return no(tatkal_seats=x["seats"], reason="not_enough_tatkal_seats")
        if kind == "tatkal_surcharge_difference":
            return ok(tid, fare_difference_inr=self.tatkal(tid, cls, p["travel_date"])["fare"] - self.fare(tid, cls))
        if kind == "tatkal_fare_no_concession":
            assert self.S["tatkal"]["concessions_allowed"] is False
            return ok(tid, tatkal_fare_inr=self.tatkal(tid, cls, p["travel_date"])["fare"])
        if kind == "waitlisted_cancel_then_tatkal":
            b = self.pnr(p["pnr"])
            assert b["status"] == "WAITLISTED"
            x = self.tatkal(b["train_id"], cls, p["travel_date"])
            return {**ok(b["train_id"], refund_inr=self.refund(p["pnr"]), tatkal_fare_inr=x["fare"]), "cancellations": [p["pnr"]],
                    "effects": {"tatkal_bookings": [(b["train_id"], cls, b["passenger"], p["travel_date"])]}}
        if kind in ("waitlisted_tatkal_window_for_journey_day", "waitlisted_then_tatkal_fare_no_booking"):
            b = self.pnr(p["pnr"])
            assert b["status"] == "WAITLISTED"
            x = self.tatkal(b["train_id"], b["travel_class"], b["journey_date"])
            if kind == "waitlisted_tatkal_window_for_journey_day":
                return ok(b["train_id"], tatkal_status=x["status"], opens_at=x["opens_at"])
            return ok(b["train_id"], booking_status="WAITLISTED", tatkal_status=x["status"], tatkal_fare_inr=x["fare"])
        # berths
        if kind in ("lower_berth_count", "side_lower_berth_count", "no_lower_then_upper_count"):
            b = self.berths(tid, cls)
            return ok(tid, **{"lower_berth_count": {"lower_berths": b["lower"]}, "side_lower_berth_count": {"side_lower_berths": b["side_lower"]},
                              "no_lower_then_upper_count": {"lower_berths": b["lower"], "upper_berths": b["upper"]}}[kind])
        if kind in ("senior_lower_berth_conditional_booking", "lower_berth_condition_fails", "two_lower_berths_group_booking"):
            assert tid in self.search(self.code(p["source_name"]), self.code(p["destination_name"]), p["date"])
            pax = p.get("passengers") or [p["passenger"]]
            lower = self.berths(tid, cls)["lower"]
            if lower >= p.get("min_lower_berths", 1) and self.seats(tid, cls) >= len(pax):
                return {**ok(tid, lower_berths=lower), "bookings": [(tid, cls, n) for n in pax]}
            return {**no(lower_berths=lower, reason="no_lower_berth"), "bookings": []}
        if kind == "berths_in_chair_car":
            assert self.berths(tid, cls) is None
            return no(reason="no_berths_in_class")
        if kind == "compare_lower_berths_two_classes":
            ls = {c: self.berths(tid, c)["lower"] for c in p["classes"]}
            best = max(ls, key=ls.get)
            return ok(tid, travel_class=best, lower_berths=ls[best])
        if kind == "lower_berth_and_senior_concession":
            pct = self.conc["senior_citizen"][cls]
            return ok(tid, lower_berths=self.berths(tid, cls)["lower"], concession_fare_inr=(self.fare(tid, cls) * (100 - pct) + 50) // 100)
        if kind == "seats_and_lower_berths":
            return ok(tid, seats_available=self.seats(tid, cls), lower_berths=self.berths(tid, cls)["lower"])
        if kind == "lower_berth_fallback_other_class_booking":
            assert self.berths(tid, cls)["lower"] == 0
            fb = p["fallback_class"]
            return {**ok(tid, travel_class=fb, lower_berths=self.berths(tid, fb)["lower"]), "bookings": [(tid, fb, p["passenger"])]}
        # boarding point
        if kind.startswith("boarding_change") or kind == "cancel_unless_refund_low_then_change_boarding":
            x = self.boarding(p["pnr"], st)
            if "error" in x:
                return no(reason=x["error"].lower())
            a = {"boarding_station": st, "boarding_time": x["time"], "boarding_date": x["date"]}
            if kind == "boarding_change_and_platform":
                a["platform"] = self.platform(x["train_id"], st)
            if kind == "cancel_unless_refund_low_then_change_boarding":
                assert self.refund(p["pnr"]) < p["min_refund_inr"]
                a["refund_inr"] = self.refund(p["pnr"])
            return {**ok(x["train_id"], **a), "effects": {"boarding_changes": [(p["pnr"], st)]}}
        if kind == "boarding_departure_preview_no_change":
            b = self.pnr(p["pnr"])
            return ok(b["train_id"], boarding_time=next(s["departure"] for s in self.T[b["train_id"]]["stops"] if s["station"] == st))
        # meals
        if kind.startswith("meal_") or kind in ("complaint_and_meal_order", "two_meal_items_total"):
            b = self.pnr(p["pnr"])
            if kind in ("meal_at_next_station", "meal_at_next_station_and_platform"):
                st = self.live(b["train_id"])["next"]
            meals = p.get("meals") or [p.get("meal")]
            if kind == "meal_choice_by_expected_arrival":
                arr = self.times(b["train_id"], Date.fromisoformat(b["journey_date"]))[st][0]
                meals = [p["meal_if_after"] if arr.hour * 60 + arr.minute > _hm(p["after_time"]) else p["meal_otherwise"]]
            res = [self.meal(p["pnr"], st, m, p.get("quantity", 1)) for m in meals]
            if "error" in res[0]:
                return no(reason=res[0]["error"].lower())
            a: dict[str, Any] = {"order_amount_inr": sum(r["amount"] for r in res)}
            if kind != "two_meal_items_total":
                a["delivery_time"] = res[0]["time"]
            if kind == "meal_if_arrival_before_deadline":
                assert _hm(res[0]["time"]) < _hm(p["before_time"])
                a["expected_arrival"] = res[0]["time"]
            if kind == "meal_at_next_station_and_platform":
                a["platform"] = self.platform(b["train_id"], st)
            eff = {"meal_orders": [(p["pnr"], st, m, p.get("quantity", 1)) for m in meals]}
            if kind == "complaint_and_meal_order":
                assert "error" not in self.complaint(p["pnr"], p["category"])
                eff["complaints"] = [(p["pnr"], p["category"])]
            return {**ok(b["train_id"], **a), "effects": eff}
        # platforms / live
        if kind == "platform_lookup":
            return ok(tid, platform=self.platform(tid, st))
        if kind in ("platform_and_expected_arrival", "arrived_yet_and_platform"):
            lv = self.live(tid)
            return ok(tid, platform=self.platform(tid, st), expected_arrival=_fmt(lv["times"][st][0]))
        if kind == "coach_position_from_engine":
            return ok(tid, travel_class=cls, coach_position=self.coach_pos(tid, cls))
        if kind == "coach_position_for_pnr":
            b = self.pnr(p["pnr"])
            return ok(b["train_id"], travel_class=b["travel_class"], coach_position=self.coach_pos(b["train_id"], b["travel_class"]))
        if kind == "platform_train_does_not_stop":
            assert self.platform(tid, st) is None
            return no(reason="not_a_stop")
        if kind == "platform_for_pnr_boarding":
            b = self.pnr(p["pnr"])
            return ok(b["train_id"], platform=self.platform(b["train_id"], b["boarding"]))
        if kind in ("platform_and_delay", "platform_if_delay_over_threshold"):
            lv = self.live(tid)
            assert lv["delay"] > p.get("min_delay_minutes", -1)
            return ok(tid, platform=self.platform(tid, st), delay_minutes=lv["delay"])
        if kind == "timetable_arrival_not_live":
            return ok(tid, scheduled_arrival=next(s["arrival"] for s in self.T[tid]["stops"] if s["station"] == st))
        if kind == "live_expected_arrival_at_destination":
            lv = self.live(tid)
            return ok(tid, expected_arrival=_fmt(lv["times"][st][0]), delay_minutes=lv["delay"])
        if kind == "live_delay_and_last_station":
            lv = self.live(tid)
            return ok(tid, delay_minutes=lv["delay"], station_code=lv["last"])
        # TDR
        if kind in ("tdr_file_ok", "best_refund_is_tdr_not_cancel"):
            x = self.tdr(p["pnr"])
            a = {"refund_inr": x["refund"], "delay_minutes": x["delay"]}
            if kind == "best_refund_is_tdr_not_cancel":
                assert x["refund"] > self.refund(p["pnr"])
                a["cancel_refund_inr"] = self.refund(p["pnr"])
            return {**ok(x["train_id"], **a), "effects": {"tdr_claims": [(p["pnr"],)]}}
        if kind in ("tdr_not_eligible_delay_too_small", "tdr_after_train_left", "tdr_cancelled_ticket"):
            return no(reason=self.tdr(p["pnr"])["error"].lower())
        if kind in ("tdr_eligibility_without_filing", "cancel_refund_vs_tdr_quote"):
            x = self.tdr(p["pnr"])
            assert "error" not in x
            if kind == "tdr_eligibility_without_filing":
                return ok(x["train_id"], tdr_eligible=True, delay_minutes=x["delay"])
            return ok(x["train_id"], refund_inr=self.refund(p["pnr"]), tdr_refund_inr=x["refund"], tdr_eligible=True)
        if kind == "cancel_else_tdr_both_blocked":
            b = self.pnr(p["pnr"])
            assert self.times(b["train_id"], Date.fromisoformat(b["journey_date"]))[b["boarding"]][1] - timedelta(
                minutes=self.delays.get((b["train_id"], b["journey_date"]), 0)) <= NOW  # left its origin: no cancellation
            assert self.tdr(p["pnr"]).get("error") == "TDR_WINDOW_CLOSED"
            return no(reason="cancel_and_tdr_not_possible")
        if kind == "train_delay_tdr_threshold_check":
            lv = self.live(tid)
            return ok(tid, tdr_eligible=lv["delay"] >= self.S["tdr"]["min_delay_minutes"], delay_minutes=lv["delay"])
        if kind == "tdr_else_punctuality_complaint":
            assert self.tdr(p["pnr"]).get("error") == "TDR_WINDOW_CLOSED"
            x = self.complaint(p["pnr"], "punctuality")
            return {**ok(x["train_id"]), "effects": {"complaints": [(p["pnr"], "punctuality")]}}
        if kind == "tdr_if_late_then_book_other_train":
            x = self.tdr(p["pnr"])
            assert x["delay"] > 180 and p["new_train_id"] in self.search(self.code(p["source_name"]), self.code(p["destination_name"]), p["travel_date"])
            return {**ok(p["new_train_id"], travel_class=cls, refund_inr=x["refund"]), "bookings": [(p["new_train_id"], cls, p["passenger"])],
                    "effects": {"tdr_claims": [(p["pnr"],)]}}
        # complaints
        if kind.startswith("complaint_") and kind not in ("complaint_without_pnr", "complaint_if_delay_over_an_hour"):
            x = self.complaint(p["pnr"], p["category"])
            if "error" in x:
                return no(reason=x["error"].lower())
            return {**ok(x["train_id"]), "effects": {"complaints": [(p["pnr"], p["category"])]}}
        if kind == "complaint_without_pnr":
            return {"answer": {"status": "needs_clarification", "missing": "pnr"}}
        if kind == "complaint_if_delay_over_an_hour":
            lv = self.live(tid)
            assert lv["delay"] > p["min_delay_minutes"] and "error" not in self.complaint(p["pnr"], p["category"])
            return {**ok(tid, delay_minutes=lv["delay"]), "effects": {"complaints": [(p["pnr"], p["category"])]}}
        # mixed
        if kind == "platform_only_if_confirmed":
            b = self.pnr(p["pnr"])
            return ok(b["train_id"], booking_status=b["status"])
        if kind == "search_today_seat_and_platform":
            src, dst = self.code(p["source_name"]), self.code(p["destination_name"])
            t = [x for x in self.search(src, dst, p["travel_date"]) if self.T[x]["stops"][[s["station"] for s in self.T[x]["stops"]].index(src)]["departure"] == p["departure_time"]]
            assert len(t) == 1
            return ok(t[0], seats_available=self.seats(t[0], cls), platform=self.platform(t[0], src))
        if kind == "tatkal_open_and_lower_berths":
            return ok(tid, tatkal_status=self.tatkal(tid, cls, p["travel_date"])["status"], lower_berths=self.berths(tid, cls)["lower"])
        if kind == "which_of_two_pnrs_confirmed":
            conf = [x for x in p["pnrs"] if self.A[x]["status"] == "CONFIRMED"]
            assert len(conf) == 1
            return ok(self.A[conf[0]]["train_id"], confirmed_pnr=conf[0])
        if kind == "search_today_then_tatkal_booking":
            t = [x for x in self.search(self.code(p["source_name"]), self.code(p["destination_name"]), p["travel_date"]) if cls in self.T[x]["classes"]]
            assert len(t) == 1
            x = self.tatkal(t[0], cls, p["travel_date"])
            return {**ok(t[0], tatkal_fare_inr=x["fare"]), "effects": {"tatkal_bookings": [(t[0], cls, p["passenger"], p["travel_date"])]}}
        if kind == "tatkal_opening_times_two_classes":
            return ok(tid, opens_at_by_class={c: self.tatkal(tid, c, p["travel_date"])["opens_at"] for c in p["classes"]})
        raise KeyError(kind)
