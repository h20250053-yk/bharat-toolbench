"""Deterministic simulated railway environment with twenty tools (six since benchmark 1.0, six more in 3.0, eight more for the
20-tool stage of 3.0).

No LLM, no network, no randomness, no wall-clock: all date logic uses the pinned reference datetime.
Tools never raise to the caller; they return a `ToolResult` envelope (`ok`, `data`, `error`).

Simplifications forced by the frozen tool signatures (document in the report):
  * check_availability / book_ticket take no date -> availability and bookings are per (train, class), not per date.
  * get_fare takes no source/destination -> fare is fixed per (train, class) for the train's whole journey.
Date handling lives only in search_trains (and, since 3.0, in get_live_train_status and the departed-train check of
cancel_ticket / get_cancellation_refund, which read the pinned 'now').
Benchmark 3.0 simplifications (documented): cancelling a CONFIRMED ticket returns one seat to its (train, class) pool;
waitlists are never promoted automatically and positions never move; account bookings were made before 'now' and are
already counted in the baseline seats.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date as Date
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Union

import yaml
from pydantic import BaseModel, ValidationError

from .schemas import (
    COMPLAINT_CATEGORIES, CONCESSIONS, MEALS, TOOL_DESCRIPTIONS, TOOL_INPUT_MODELS, TRAVEL_CLASSES, WEEKDAYS,
    BerthOutput, BoardingChangeOutput, Complaint, ComplaintOutput, MealOrder, MealOutput, PlatformOutput, TatkalAvailabilityOutput,
    TatkalBooking, TatkalBookOutput, TdrClaim, TdrOutput,
    AvailabilityOutput, Booking, BookingStatusOutput, BookTicketOutput, Cancellation, CancelTicketOutput, ConcessionFareOutput,
    FareOutput, JoinWaitlistOutput, LiveStatusOutput, LiveStop, RefundQuoteOutput, ResolveStationOutput, SearchTrainsOutput,
    StationCandidate, StopDetail, TimeWindow, ToolError, ToolResult, TrainDetailsOutput, TrainSummary, WaitlistEntry,
)
from .state import EnvState, normalize_name

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "benchmark.yaml"
TOOL_NAMES = tuple(TOOL_INPUT_MODELS)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]{1,59}$")
_PNR_RE = re.compile(r"^\d{10}$")


def _minutes(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:])


def _err(code: str, message: str) -> ToolResult:
    return ToolResult(ok=False, error=ToolError(code=code, message=message))


def _ok(model: BaseModel) -> ToolResult:
    return ToolResult(ok=True, data=model.model_dump(mode="json"))


def load_reference_datetime(config_path: Path = CONFIG_PATH) -> datetime:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return datetime.fromisoformat(cfg["reference_datetime"])


class RailwayEnv:
    """The environment. Construct once, call `reset()` before every benchmark run."""

    def __init__(self, state: Optional[EnvState] = None, reference_datetime: Optional[datetime] = None):
        self.state = state or EnvState.load()
        self.reference_datetime = reference_datetime or load_reference_datetime()
        # All comparisons use the naive local (IST) wall-clock of the pinned reference time.
        self._ref_naive = self.reference_datetime.replace(tzinfo=None)

    # ------------------------------------------------------------------ lifecycle / inspection
    def reset(self) -> None:
        """Restore the exact baseline state (availability, no bookings, booking counter = 1)."""
        self.state.reset_mutable()

    def snapshot(self) -> dict[str, Any]:
        return self.state.snapshot()

    def state_hash(self) -> str:
        return self.state.state_hash()

    @property
    def static_hash(self) -> str:
        return self.state.static_hash

    # ------------------------------------------------------------------ generic dispatch
    def call(self, tool_name: str, arguments: Any) -> dict[str, Any]:
        """Validate `arguments` against the tool's input schema, execute, return a plain dict.

        This is the single entry point the future runner will use (after model-adapter normalization).
        """
        model_cls = TOOL_INPUT_MODELS.get(tool_name)
        if model_cls is None:
            return _err("UNKNOWN_TOOL", f"Unknown tool: {tool_name!r}").model_dump(mode="json")
        if not isinstance(arguments, dict):
            return _err("INVALID_ARGUMENTS", "Arguments must be a JSON object.").model_dump(mode="json")
        try:
            parsed = model_cls(**arguments)
        except ValidationError as exc:
            problems = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'arguments'}: {e['msg']}" for e in exc.errors())
            return _err("INVALID_ARGUMENTS", problems).model_dump(mode="json")
        result = getattr(self, tool_name)(**{k: getattr(parsed, k) for k in type(parsed).model_fields})
        return result.model_dump(mode="json")

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _class(travel_class: str) -> Optional[str]:
        c = travel_class.strip().upper()
        return c if c in TRAVEL_CLASSES else None

    def _train_and_class(self, train_id: str, travel_class: str):
        train = self.state.trains.get(train_id.strip())
        if train is None:
            return None, None, _err("INVALID_TRAIN", f"Unknown train_id: {train_id!r}")
        cls = self._class(travel_class)
        if cls is None:
            return None, None, _err("INVALID_CLASS", f"Invalid travel class: {travel_class!r}. Valid: {', '.join(TRAVEL_CLASSES)}")
        if cls not in train.classes:
            return None, None, _err("CLASS_NOT_OFFERED", f"Train {train.train_id} does not offer class {cls}.")
        return train, cls, None

    # ------------------------------------------------------------------ tool 1
    def resolve_station(self, name: str) -> ToolResult:
        """Exact match (after deterministic normalization) of a name/alias/code. No fuzzy matching."""
        codes = self.state.alias_index.get(normalize_name(name), [])
        if not codes:
            return _err("STATION_NOT_FOUND", f"No station matches {name!r}.")
        cands = [StationCandidate(code=c, name=self.state.stations[c].name, city=self.state.stations[c].city) for c in codes]
        return _ok(ResolveStationOutput(query=name, ambiguous=len(cands) > 1, candidates=cands))

    # ------------------------------------------------------------------ tool 2
    def search_trains(self, source: str, destination: str, date: str,
                      time_window: Union[TimeWindow, dict, None] = None) -> ToolResult:
        src, dst = source.strip().upper(), destination.strip().upper()
        if src not in self.state.stations:
            return _err("INVALID_STATION", f"Unknown station code: {source!r}")
        if dst not in self.state.stations:
            return _err("INVALID_STATION", f"Unknown station code: {destination!r}")
        if src == dst:
            return _err("SAME_STATION", "Source and destination must differ.")
        if not _DATE_RE.match(date.strip()):
            return _err("INVALID_DATE", f"Date must be YYYY-MM-DD, got {date!r}")
        try:
            travel_date = Date.fromisoformat(date.strip())
        except ValueError:
            return _err("INVALID_DATE", f"Not a valid calendar date: {date!r}")
        if travel_date < self._ref_naive.date():
            return _err("PAST_DATE", f"Date {travel_date.isoformat()} is before the current date.")

        tw: Optional[TimeWindow] = None
        if time_window is not None:
            try:
                tw = time_window if isinstance(time_window, TimeWindow) else TimeWindow(**time_window)
            except (ValidationError, TypeError):
                return _err("INVALID_TIME_WINDOW", "time_window must be {start: HH:MM, end: HH:MM} or null.")
            if not (_TIME_RE.match(tw.start) and _TIME_RE.match(tw.end)):
                return _err("INVALID_TIME_WINDOW", "time_window start/end must be 24-hour HH:MM.")

        found: list[tuple[int, str, TrainSummary]] = []
        for train in self.state.trains.values():
            idx = {s.station: i for i, s in enumerate(train.stops)}
            if src not in idx or dst not in idx or idx[src] >= idx[dst]:
                continue
            board, alight = train.stops[idx[src]], train.stops[idx[dst]]
            origin_date = travel_date - timedelta(days=board.departure_day or 0)
            if WEEKDAYS[origin_date.weekday()] not in train.operating_days:
                continue
            dep_min = _minutes(board.departure)
            dep_dt = datetime.combine(travel_date, datetime.min.time()) + timedelta(minutes=dep_min)
            if dep_dt <= self._ref_naive:  # already departed (or departing right now)
                continue
            if tw is not None:
                s, e = _minutes(tw.start), _minutes(tw.end)
                inside = s <= dep_min <= e if s <= e else (dep_min >= s or dep_min <= e)
                if not inside:
                    continue
            arr_total = (alight.arrival_day or 0) * 1440 + _minutes(alight.arrival)
            dep_total = (board.departure_day or 0) * 1440 + dep_min
            found.append((dep_min, train.train_id, TrainSummary(
                train_id=train.train_id, train_name=train.train_name, source=src, destination=dst,
                departure=board.departure, arrival=alight.arrival,
                arrival_day_offset=(alight.arrival_day or 0) - (board.departure_day or 0),
                duration_minutes=arr_total - dep_total, classes=sorted(train.classes))))
        found.sort(key=lambda x: (x[0], x[1]))
        trains = [f[2] for f in found]
        return _ok(SearchTrainsOutput(source=src, destination=dst, date=travel_date.isoformat(),
                                      time_window=tw, count=len(trains), trains=trains))

    # ------------------------------------------------------------------ tool 3
    def get_train_details(self, train_id: str) -> ToolResult:
        train = self.state.trains.get(train_id.strip())
        if train is None:
            return _err("INVALID_TRAIN", f"Unknown train_id: {train_id!r}")
        return _ok(TrainDetailsOutput(
            train_id=train.train_id, train_name=train.train_name, train_type=train.train_type,
            source_station=train.source_station, destination_station=train.destination_station,
            operating_days=train.operating_days, classes=sorted(train.classes),
            total_distance_km=train.stops[-1].distance_km,
            stops=[StopDetail(station=s.station, arrival=s.arrival, departure=s.departure, distance_km=s.distance_km)
                   for s in train.stops]))

    # ------------------------------------------------------------------ tool 4
    def check_availability(self, train_id: str, travel_class: str) -> ToolResult:
        train, cls, error = self._train_and_class(train_id, travel_class)
        if error:
            return error
        seats = self.state.availability[(train.train_id, cls)]
        return _ok(AvailabilityOutput(train_id=train.train_id, travel_class=cls, seats_available=seats,
                                      status="AVAILABLE" if seats > 0 else "SOLD_OUT"))

    # ------------------------------------------------------------------ tool 5
    def get_fare(self, train_id: str, travel_class: str) -> ToolResult:
        train, cls, error = self._train_and_class(train_id, travel_class)
        if error:
            return error
        return _ok(FareOutput(train_id=train.train_id, travel_class=cls, fare_inr=train.classes[cls].fare_inr))

    # ------------------------------------------------------------------ tool 6 (STATE-CHANGING)
    def book_ticket(self, train_id: str, travel_class: str, passenger: str) -> ToolResult:
        """Validation order: train -> class -> class offered -> passenger -> duplicate -> availability.
        On any error NOTHING is mutated. On success: seats -= 1, a Booking is appended, counter += 1.
        Duplicate rule: same (train, class, passenger name, case-insensitive) is rejected with DUPLICATE_BOOKING.
        """
        train, cls, error = self._train_and_class(train_id, travel_class)
        if error:
            return error
        name = re.sub(r"\s+", " ", passenger).strip()
        if not _NAME_RE.match(name):
            return _err("INVALID_PASSENGER", "Passenger must be a full name in Latin letters (2-60 chars).")
        key = name.casefold()
        if any(b.train_id == train.train_id and b.travel_class == cls and b.passenger.casefold() == key
               for b in self.state.bookings):
            return _err("DUPLICATE_BOOKING", f"{name} already has a booking on train {train.train_id} in {cls}.")
        if self.state.availability[(train.train_id, cls)] <= 0:
            return _err("SOLD_OUT", f"No seats available on train {train.train_id} in class {cls}.")

        seq = self.state.next_booking_seq
        digest = hashlib.sha256(f"BTB|{train.train_id}|{cls}|{key}|{seq}".encode()).hexdigest()
        booking = Booking(booking_id=f"BK{seq:04d}", pnr=f"{int(digest, 16) % 10**10:010d}",
                          train_id=train.train_id, travel_class=cls, passenger=name,
                          fare_inr=train.classes[cls].fare_inr)
        self.state.availability[(train.train_id, cls)] -= 1
        self.state.bookings.append(booking)
        self.state.next_booking_seq = seq + 1
        return _ok(BookTicketOutput(**booking.model_dump()))

    # ================================================================== benchmark 3.0 tools
    def _lookup_pnr(self, pnr: str):
        """(view dict, error). A view has the booking's fields plus 'source' (account | session | waitlist) and its CURRENT status."""
        p = pnr.strip()
        if not _PNR_RE.match(p):
            return None, _err("INVALID_PNR", f"A PNR is exactly 10 digits, got {pnr!r}.")
        cancelled = {c.pnr for c in self.state.cancellations}
        for b in self.state.bookings:
            if b.pnr == p:
                return self._with_boarding({**b.model_dump(), "journey_date": None, "waitlist_position": None, "source": "session",
                                            "status": "CONFIRMED"}), None
        for b in self.state.tatkal_bookings:
            if b.pnr == p:
                return self._with_boarding({**b.model_dump(), "waitlist_position": None, "source": "tatkal", "status": "CONFIRMED"}), None
        for w in self.state.waitlist:
            if w.pnr == p:
                return {**w.model_dump(), "booking_id": w.waitlist_id, "journey_date": None, "source": "waitlist",
                        "status": "WAITLISTED"}, None
        for c in self.state.cancellations:  # a session booking / waitlist entry cancelled earlier in this conversation
            if c.pnr == p and p not in self.state.account_bookings:
                return self._with_boarding({**c.model_dump(), "fare_inr": c.refund_inr + c.cancellation_charge_inr, "journey_date": None,
                                            "waitlist_position": None, "source": "session", "status": "CANCELLED"}), None
        a = self.state.account_bookings.get(p)
        if a is None:
            return None, _err("PNR_NOT_FOUND", f"No booking with PNR {p}.")
        view = {**a.model_dump(), "source": "account"}
        if p in cancelled:
            view.update(status="CANCELLED", waitlist_position=None)
        return self._with_boarding(view), None

    def _with_boarding(self, view: dict[str, Any]) -> dict[str, Any]:
        view["boarding_station"] = self.state.boarding_changes.get(view["pnr"], self.state.trains[view["train_id"]].source_station)
        return view

    def _origin_departure(self, view: dict[str, Any]) -> Optional[datetime]:
        if not view.get("journey_date"):
            return None
        train = self.state.trains[view["train_id"]]
        d = Date.fromisoformat(view["journey_date"])
        return datetime.combine(d, datetime.min.time()) + timedelta(minutes=_minutes(train.stops[0].departure))

    def _refund_terms(self, view: dict[str, Any]):
        """(charge, refund, error) for cancelling `view` now."""
        if view["status"] == "CANCELLED":
            return None, None, _err("ALREADY_CANCELLED", f"PNR {view['pnr']} is already cancelled.")
        dep = self._origin_departure(view)
        if dep is not None and dep <= self._ref_naive:
            return None, None, _err("JOURNEY_STARTED", f"Train {view['train_id']} has already left its origin for this booking; "
                                                      "it can no longer be cancelled.")
        if view.get("quota") == "TATKAL":  # as on Indian Railways: no refund on cancelling a confirmed Tatkal ticket
            return view["fare_inr"], 0, None
        key = "WAITLISTED" if view["status"] == "WAITLISTED" else view["travel_class"]
        charge = self.state.cancellation_charge[key]
        return charge, view["fare_inr"] - charge, None

    # ------------------------------------------------------------------ tool 7
    def get_booking_status(self, pnr: str) -> ToolResult:
        view, error = self._lookup_pnr(pnr)
        if error:
            return error
        return _ok(BookingStatusOutput(
            pnr=view["pnr"], booking_id=view["booking_id"], train_id=view["train_id"],
            train_name=self.state.trains[view["train_id"]].train_name, travel_class=view["travel_class"],
            passenger=view["passenger"], journey_date=view["journey_date"], boarding_station=view["boarding_station"],
            fare_inr=view["fare_inr"], status=view["status"],
            waitlist_position=view["waitlist_position"] if view["status"] == "WAITLISTED" else None))

    # ------------------------------------------------------------------ tool 8
    def get_cancellation_refund(self, pnr: str) -> ToolResult:
        view, error = self._lookup_pnr(pnr)
        if error:
            return error
        charge, refund, error = self._refund_terms(view)
        if error:
            return error
        return _ok(RefundQuoteOutput(pnr=view["pnr"], status=view["status"], fare_inr=view["fare_inr"],
                                     cancellation_charge_inr=charge, refund_inr=refund))

    # ------------------------------------------------------------------ tool 9 (STATE-CHANGING)
    def cancel_ticket(self, pnr: str) -> ToolResult:
        """On success: the booking becomes CANCELLED (recorded in `cancellations`); a session booking / waitlist entry is removed
        from its list; a CONFIRMED ticket returns one seat to its (train, class). On any error NOTHING is mutated."""
        view, error = self._lookup_pnr(pnr)
        if error:
            return error
        charge, refund, error = self._refund_terms(view)
        if error:
            return error
        prev = view["status"]
        canc = Cancellation(pnr=view["pnr"], booking_id=view["booking_id"], train_id=view["train_id"],
                            travel_class=view["travel_class"], passenger=view["passenger"], previous_status=prev,
                            cancellation_charge_inr=charge, refund_inr=refund)
        if view["source"] == "session":
            self.state.bookings = [b for b in self.state.bookings if b.pnr != view["pnr"]]
        elif view["source"] == "tatkal":
            self.state.tatkal_bookings = [b for b in self.state.tatkal_bookings if b.pnr != view["pnr"]]
            self.state.tatkal_seats[(view["train_id"], view["travel_class"])] = self.state.tatkal_seats.get((view["train_id"], view["travel_class"]), 0) + 1
        elif view["source"] == "waitlist":
            self.state.waitlist = [w for w in self.state.waitlist if w.pnr != view["pnr"]]
        if prev == "CONFIRMED" and view["source"] != "tatkal":
            self.state.availability[(view["train_id"], view["travel_class"])] += 1
        self.state.cancellations.append(canc)
        return _ok(CancelTicketOutput(**canc.model_dump()))

    # ------------------------------------------------------------------ tool 10 (STATE-CHANGING)
    def join_waitlist(self, train_id: str, travel_class: str, passenger: str) -> ToolResult:
        """Validation order: train -> class -> class offered -> passenger -> duplicate -> seats must be SOLD OUT.
        Position = people already waiting (fixture) + entries added in this conversation + 1. On any error NOTHING is mutated."""
        train, cls, error = self._train_and_class(train_id, travel_class)
        if error:
            return error
        name = re.sub(r"\s+", " ", passenger).strip()
        if not _NAME_RE.match(name):
            return _err("INVALID_PASSENGER", "Passenger must be a full name in Latin letters (2-60 chars).")
        key = name.casefold()
        if any(x.train_id == train.train_id and x.travel_class == cls and x.passenger.casefold() == key
               for x in [*self.state.bookings, *self.state.waitlist]):
            return _err("DUPLICATE_BOOKING", f"{name} already has a booking or waitlist entry on train {train.train_id} in {cls}.")
        if self.state.availability[(train.train_id, cls)] > 0:
            return _err("SEATS_AVAILABLE", f"Train {train.train_id} has seats in class {cls}; the waitlist is only for sold-out classes.")
        seq = self.state.next_waitlist_seq
        position = (self.state.waitlist_baseline.get((train.train_id, cls), 0)
                    + sum(1 for w in self.state.waitlist if (w.train_id, w.travel_class) == (train.train_id, cls)) + 1)
        digest = hashlib.sha256(f"BTBWL|{train.train_id}|{cls}|{key}|{seq}".encode()).hexdigest()
        entry = WaitlistEntry(waitlist_id=f"WL{seq:04d}", pnr=f"{int(digest, 16) % 10**10:010d}", train_id=train.train_id,
                              travel_class=cls, passenger=name, fare_inr=train.classes[cls].fare_inr, waitlist_position=position)
        self.state.waitlist.append(entry)
        self.state.next_waitlist_seq = seq + 1
        return _ok(JoinWaitlistOutput(**entry.model_dump()))

    # ------------------------------------------------------------------ tool 11
    def _run_times(self, train, start: Date, delay: int):
        """Expected (arrival_dt, departure_dt) per stop for the run that leaves the origin on `start`."""
        base = datetime.combine(start, datetime.min.time())
        out = []
        for st in train.stops:
            arr = base + timedelta(days=st.arrival_day or 0, minutes=_minutes(st.arrival) + delay) if st.arrival else None
            dep = base + timedelta(days=st.departure_day or 0, minutes=_minutes(st.departure) + delay) if st.departure else None
            out.append((st, arr, dep))
        return out

    def get_live_train_status(self, train_id: str) -> ToolResult:
        """The run in progress now (if any), else today's run, else NOT_RUNNING_TODAY. Delay is constant over a run (fixture)."""
        train = self.state.trains.get(train_id.strip())
        if train is None:
            return _err("INVALID_TRAIN", f"Unknown train_id: {train_id!r}")
        now = self._ref_naive
        today = now.date()
        chosen = None
        max_days = max((s.arrival_day or 0) for s in train.stops)
        for back in range(max_days, -1, -1):  # older runs first; a later RUNNING run replaces an earlier one
            start = today - timedelta(days=back)
            if WEEKDAYS[start.weekday()] not in train.operating_days:
                continue
            delay = self.state.live_delays.get((train.train_id, start.isoformat()), 0)
            times = self._run_times(train, start, delay)
            first_dep, last_arr = times[0][2], times[-1][1]
            status = "NOT_STARTED" if now < first_dep else ("ARRIVED" if now >= last_arr else "RUNNING")
            if status == "RUNNING" or (back == 0 and (chosen is None or chosen[1] != "RUNNING")):
                chosen = (start, status, delay, times)
        as_of = self.reference_datetime.isoformat()
        if chosen is None:
            return _ok(LiveStatusOutput(train_id=train.train_id, train_name=train.train_name, as_of=as_of, run_start_date=None,
                                        status="NOT_RUNNING_TODAY", delay_minutes=None, last_station=None, next_station=None, stops=[]))
        start, status, delay, times = chosen
        reached = [st.station for st, arr, dep in times if (arr or dep) <= now]
        last = reached[-1] if status != "NOT_STARTED" and reached else None
        codes = [st.station for st, _, _ in times]
        nxt = codes[codes.index(last) + 1] if last and status == "RUNNING" else None
        hm = lambda dt: dt.strftime("%H:%M") if dt else None  # noqa: E731
        stops = [LiveStop(station=st.station, scheduled_arrival=st.arrival, scheduled_departure=st.departure,
                          expected_arrival=hm(arr), expected_departure=hm(dep), expected_date=(arr or dep).date().isoformat())
                 for st, arr, dep in times]
        return _ok(LiveStatusOutput(train_id=train.train_id, train_name=train.train_name, as_of=as_of,
                                    run_start_date=start.isoformat(), status=status, delay_minutes=delay,
                                    last_station=last, next_station=nxt, stops=stops))

    # ------------------------------------------------------------------ tool 12
    def get_concession_fare(self, train_id: str, travel_class: str, concession: str) -> ToolResult:
        train, cls, error = self._train_and_class(train_id, travel_class)
        if error:
            return error
        con = re.sub(r"[\s\-]+", "_", concession.strip().lower())
        if con not in CONCESSIONS:
            return _err("INVALID_CONCESSION", f"Unknown concession {concession!r}. Valid: {', '.join(CONCESSIONS)}")
        pct = self.state.concession_percent.get(con, {}).get(cls)
        if pct is None:
            return _err("CONCESSION_NOT_AVAILABLE", f"No {con} concession in class {cls}.")
        base = train.classes[cls].fare_inr
        return _ok(ConcessionFareOutput(train_id=train.train_id, travel_class=cls, concession=con, base_fare_inr=base,
                                        discount_percent=pct, concession_fare_inr=(base * (100 - pct) + 50) // 100))


    # ================================================================== benchmark 3.0, 20-tool stage
    def _seq(self, prefix: str) -> str:
        n = self.state.next_service_seq
        self.state.next_service_seq = n + 1
        return f"{prefix}{n:04d}"

    def _run(self, train, start: Date):
        """(delay, {station: (expected_arrival_dt, expected_departure_dt)}) for the run leaving the origin on `start`."""
        delay = self.state.live_delays.get((train.train_id, start.isoformat()), 0)
        return delay, {st.station: (arr, dep) for st, arr, dep in self._run_times(train, start, delay)}

    def _tatkal_window(self, train, cls: str, date: str):
        """(travel_date, status, opens_at_dt) or an error ToolResult."""
        d = date.strip()
        if not _DATE_RE.match(d):
            return None, _err("INVALID_DATE", f"Date must be YYYY-MM-DD, got {date!r}")
        try:
            travel = Date.fromisoformat(d)
        except ValueError:
            return None, _err("INVALID_DATE", f"Not a valid calendar date: {date!r}")
        if travel < self._ref_naive.date():
            return None, _err("PAST_DATE", f"Date {travel.isoformat()} is before the current date.")
        if WEEKDAYS[travel.weekday()] not in train.operating_days:
            return None, _err("NOT_RUNNING_ON_DATE", f"Train {train.train_id} does not leave its origin on {travel.isoformat()}.")
        hh = self.state.services["tatkal"]["opens_at"][cls]
        opens = datetime.combine(travel - timedelta(days=1), datetime.min.time()) + timedelta(minutes=_minutes(hh))
        departs = datetime.combine(travel, datetime.min.time()) + timedelta(minutes=_minutes(train.stops[0].departure))
        status = "DEPARTED" if self._ref_naive >= departs else ("NOT_YET_OPEN" if self._ref_naive < opens else "OPEN")
        return (travel, status, opens), None

    # ------------------------------------------------------------------ tool 13
    def check_tatkal_availability(self, train_id: str, travel_class: str, date: str) -> ToolResult:
        train, cls, error = self._train_and_class(train_id, travel_class)
        if error:
            return error
        win, error = self._tatkal_window(train, cls, date)
        if error:
            return error
        travel, status, opens = win
        tk = self.state.services["tatkal"]
        return _ok(TatkalAvailabilityOutput(
            train_id=train.train_id, travel_class=cls, date=travel.isoformat(), status=status, opens_at=opens.strftime("%Y-%m-%d %H:%M"),
            tatkal_seats=self.state.tatkal_seats.get((train.train_id, cls), 0),
            tatkal_fare_inr=train.classes[cls].fare_inr + tk["charge_inr"][cls], concessions_allowed=tk["concessions_allowed"]))

    # ------------------------------------------------------------------ tool 14 (STATE-CHANGING)
    def book_tatkal_ticket(self, train_id: str, travel_class: str, passenger: str, date: str) -> ToolResult:
        """Validation order: train -> class -> date -> window OPEN -> passenger -> duplicate -> Tatkal seats. Nothing changes on error."""
        train, cls, error = self._train_and_class(train_id, travel_class)
        if error:
            return error
        win, error = self._tatkal_window(train, cls, date)
        if error:
            return error
        travel, status, opens = win
        if status == "DEPARTED":
            return _err("TRAIN_DEPARTED", f"Train {train.train_id} has already left its origin on {travel.isoformat()}.")
        if status == "NOT_YET_OPEN":
            return _err("TATKAL_NOT_OPEN", f"Tatkal booking for {travel.isoformat()} opens at {opens.strftime('%Y-%m-%d %H:%M')}.")
        name = re.sub(r"\s+", " ", passenger).strip()
        if not _NAME_RE.match(name):
            return _err("INVALID_PASSENGER", "Passenger must be a full name in Latin letters (2-60 chars).")
        key = name.casefold()
        if any(b.train_id == train.train_id and b.travel_class == cls and b.passenger.casefold() == key
               for b in [*self.state.bookings, *self.state.tatkal_bookings]):
            return _err("DUPLICATE_BOOKING", f"{name} already has a booking on train {train.train_id} in {cls}.")
        if self.state.tatkal_seats.get((train.train_id, cls), 0) <= 0:
            return _err("TATKAL_SOLD_OUT", f"No Tatkal seats left on train {train.train_id} in class {cls}.")
        seq = self.state.next_booking_seq
        digest = hashlib.sha256(f"BTBTK|{train.train_id}|{cls}|{key}|{seq}".encode()).hexdigest()
        b = TatkalBooking(booking_id=f"BK{seq:04d}", pnr=f"{int(digest, 16) % 10**10:010d}", train_id=train.train_id, travel_class=cls,
                          passenger=name, fare_inr=train.classes[cls].fare_inr + self.state.services["tatkal"]["charge_inr"][cls],
                          journey_date=travel.isoformat())
        self.state.tatkal_seats[(train.train_id, cls)] -= 1
        self.state.tatkal_bookings.append(b)
        self.state.next_booking_seq = seq + 1
        return _ok(TatkalBookOutput(**b.model_dump()))

    # ------------------------------------------------------------------ tool 15
    def get_berth_availability(self, train_id: str, travel_class: str) -> ToolResult:
        """Berth split of the class's free seats as published (refreshed at chart preparation; bookings made in this conversation get
        their berth then, so they do not change these numbers)."""
        train, cls, error = self._train_and_class(train_id, travel_class)
        if error:
            return error
        b = self.state.services["berths"].get(f"{train.train_id}|{cls}")
        if b is None:
            return _err("NO_BERTHS_IN_CLASS", f"Class {cls} has seats, not berths.")
        return _ok(BerthOutput(train_id=train.train_id, travel_class=cls, lower=b["lower"], middle=b.get("middle"), upper=b["upper"],
                               side_lower=b["side_lower"], side_upper=b["side_upper"], total=sum(b.values())))

    # ------------------------------------------------------------------ tool 16
    def get_platform_info(self, train_id: str, station: str) -> ToolResult:
        train = self.state.trains.get(train_id.strip())
        if train is None:
            return _err("INVALID_TRAIN", f"Unknown train_id: {train_id!r}")
        code = station.strip().upper()
        if code not in self.state.stations:
            return _err("INVALID_STATION", f"Unknown station code: {station!r}")
        plat = self.state.services["platforms"].get(f"{train.train_id}|{code}")
        if plat is None:
            return _err("NOT_A_STOP", f"Train {train.train_id} does not stop at {code}.")
        return _ok(PlatformOutput(train_id=train.train_id, station=code, platform=plat, coach_order=self.state.services["coach_order"][train.train_id]))

    def _confirmed_with_date(self, pnr: str):
        view, error = self._lookup_pnr(pnr)
        if error:
            return None, error
        if view["status"] == "CANCELLED":
            return None, _err("ALREADY_CANCELLED", f"PNR {view['pnr']} is cancelled.")
        if view["status"] != "CONFIRMED":
            return None, _err("NOT_CONFIRMED", f"PNR {view['pnr']} is {view['status']}; only a confirmed ticket can use this service.")
        if not view.get("journey_date"):
            return None, _err("JOURNEY_DATE_UNKNOWN", f"PNR {view['pnr']} has no journey date on record.")
        return view, None

    # ------------------------------------------------------------------ tool 17 (STATE-CHANGING)
    def change_boarding_point(self, pnr: str, station: str) -> ToolResult:
        view, error = self._confirmed_with_date(pnr)
        if error:
            return error
        train = self.state.trains[view["train_id"]]
        code = station.strip().upper()
        if code not in self.state.stations:
            return _err("INVALID_STATION", f"Unknown station code: {station!r}")
        codes = [s.station for s in train.stops]
        if code not in codes:
            return _err("NOT_A_STOP", f"Train {train.train_id} does not stop at {code}.")
        if code in (codes[0], codes[-1]):
            return _err("NOT_EN_ROUTE", "The new boarding station must be an intermediate stop (not the origin or the destination).")
        start = Date.fromisoformat(view["journey_date"])
        departs = datetime.combine(start, datetime.min.time()) + timedelta(minutes=_minutes(train.stops[0].departure))
        if departs - self._ref_naive < timedelta(hours=self.state.services["boarding_change"]["min_hours_before_departure"]):
            return _err("TOO_LATE_TO_CHANGE", "The boarding point can be changed only until 24 hours before the train leaves its origin.")
        stop = train.stops[codes.index(code)]
        prev = view["boarding_station"]
        self.state.boarding_changes[view["pnr"]] = code
        return _ok(BoardingChangeOutput(pnr=view["pnr"], train_id=train.train_id, previous_boarding=prev, new_boarding=code,
                                        boarding_date=(start + timedelta(days=stop.departure_day or 0)).isoformat(), boarding_time=stop.departure))

    # ------------------------------------------------------------------ tool 18 (STATE-CHANGING)
    def order_meal(self, pnr: str, station: str, meal: str, quantity: int = 1) -> ToolResult:
        """Checks: confirmed ticket -> station on the route AFTER boarding and before the destination -> catering at that station -> meal
        and quantity -> expected arrival (timetable + today's delay) not passed and >= 2 h away -> meal served at that hour."""
        view, error = self._confirmed_with_date(pnr)
        if error:
            return error
        train = self.state.trains[view["train_id"]]
        cat = self.state.services["catering"]
        code = station.strip().upper()
        if code not in self.state.stations:
            return _err("INVALID_STATION", f"Unknown station code: {station!r}")
        codes = [s.station for s in train.stops]
        if code not in codes:
            return _err("NOT_A_STOP", f"Train {train.train_id} does not stop at {code}.")
        if not codes.index(view["boarding_station"]) < codes.index(code) < len(codes) - 1:
            return _err("NOT_EN_ROUTE", "Meals are delivered only at stops after your boarding station and before the destination.")
        if code not in cat["stations"]:
            return _err("CATERING_NOT_AVAILABLE", f"No e-catering at {code}.")
        m = meal.strip().lower().replace(" ", "_").replace("-", "_")
        if m not in MEALS:
            return _err("INVALID_MEAL", f"Unknown meal {meal!r}. Valid: {', '.join(MEALS)}")
        if not isinstance(quantity, int) or not 1 <= quantity <= cat["max_quantity"]:
            return _err("INVALID_QUANTITY", f"Quantity must be 1-{cat['max_quantity']}.")
        _, times = self._run(train, Date.fromisoformat(view["journey_date"]))
        arr = times[code][0]
        if arr <= self._ref_naive:
            return _err("STATION_ALREADY_PASSED", f"The train has already passed {code}.")
        if arr - self._ref_naive < timedelta(minutes=cat["min_lead_minutes"]):
            return _err("ORDER_TOO_LATE", f"The train reaches {code} at {arr.strftime('%H:%M')}; orders close 2 hours before.")
        lo, hi = cat["serving_hours"][m]
        if not _minutes(lo) <= arr.hour * 60 + arr.minute <= _minutes(hi):
            return _err("MEAL_NOT_SERVED_AT_THIS_TIME", f"{m} is served {lo}-{hi}; the train reaches {code} at {arr.strftime('%H:%M')}.")
        order = MealOrder(order_id=self._seq("ML"), pnr=view["pnr"], station=code, meal=m, quantity=quantity,
                          amount_inr=cat["menu_inr"][m] * quantity, delivery_date=arr.date().isoformat(), delivery_time=arr.strftime("%H:%M"))
        self.state.meal_orders.append(order)
        return _ok(MealOutput(**order.model_dump()))

    # ------------------------------------------------------------------ tool 19 (STATE-CHANGING)
    def file_tdr(self, pnr: str) -> ToolResult:
        view, error = self._confirmed_with_date(pnr)
        if error:
            return error
        train = self.state.trains[view["train_id"]]
        if any(t.pnr == view["pnr"] for t in self.state.tdr_claims):
            return _err("DUPLICATE_TDR", f"A TDR is already filed for PNR {view['pnr']}.")
        delay, times = self._run(train, Date.fromisoformat(view["journey_date"]))
        if delay < self.state.services["tdr"]["min_delay_minutes"]:
            return _err("TDR_NOT_ELIGIBLE", f"The train is {delay} minutes late; a TDR needs a delay of at least 180 minutes.")
        if times[view["boarding_station"]][1] <= self._ref_naive:
            return _err("TDR_WINDOW_CLOSED", "The train has already left your boarding station; a TDR had to be filed before that.")
        claim = TdrClaim(tdr_id=self._seq("TD"), pnr=view["pnr"], delay_minutes=delay, refund_inr=view["fare_inr"])
        self.state.tdr_claims.append(claim)
        return _ok(TdrOutput(**claim.model_dump()))

    # ------------------------------------------------------------------ tool 20 (STATE-CHANGING)
    def raise_complaint(self, pnr: str, category: str, description: str = "") -> ToolResult:
        view, error = self._confirmed_with_date(pnr)
        if error:
            return error
        train = self.state.trains[view["train_id"]]
        cat = category.strip().lower().replace(" ", "_").replace("-", "_")
        if cat not in COMPLAINT_CATEGORIES:
            return _err("INVALID_CATEGORY", f"Unknown category {category!r}. Valid: {', '.join(COMPLAINT_CATEGORIES)}")
        if cat in self.state.services["complaints"]["ac_classes_only"] and view["travel_class"] not in ("2A", "3A", "CC"):
            return _err("CATEGORY_NOT_APPLICABLE", f"Class {view['travel_class']} has no air conditioning.")
        _, times = self._run(train, Date.fromisoformat(view["journey_date"]))
        first, last = times[train.stops[0].station][1], times[train.stops[-1].station][0]
        if not first <= self._ref_naive < last:
            return _err("JOURNEY_NOT_IN_PROGRESS", "Complaints can be registered only while the journey is in progress.")
        c = Complaint(complaint_id=self._seq("CP"), pnr=view["pnr"], train_id=train.train_id, category=cat, description=description.strip())
        self.state.complaints.append(c)
        return _ok(ComplaintOutput(**c.model_dump()))


def tool_specs() -> list[dict[str, Any]]:
    """Provider-neutral tool specs (name, description, JSON-schema parameters) for future model adapters."""
    specs = []
    for name, model_cls in TOOL_INPUT_MODELS.items():
        schema = model_cls.model_json_schema()
        schema.pop("title", None)
        specs.append({"name": name, "description": TOOL_DESCRIPTIONS[name], "parameters": schema})
    return specs
