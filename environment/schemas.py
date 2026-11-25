"""Pydantic schemas for the railway environment: fixture data, tool inputs, tool outputs.

Everything here is provider-neutral. Model adapters (a later phase) will derive provider-specific
tool schemas from `TOOL_INPUT_MODELS` and `TOOL_DESCRIPTIONS`; the environment never imports them.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

TRAVEL_CLASSES = ("3A", "2A", "SL", "CC")
WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


# ----------------------------------------------------------------------------- fixture data
class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Station(_Frozen):
    code: str
    name: str
    city: str
    state: str
    aliases: dict[str, list[str]]  # language key ("en","hinglish","hi","mr","gu") -> surface forms


class Stop(_Frozen):
    station: str
    arrival: Optional[str] = None  # HH:MM, None at the origin
    arrival_day: Optional[int] = None  # days after the train's origin departure date
    departure: Optional[str] = None  # HH:MM, None at the terminus
    departure_day: Optional[int] = None
    distance_km: int


class ClassInfo(_Frozen):
    fare_inr: int
    seats: int  # baseline seats at reset


class Train(_Frozen):
    train_id: str
    train_name: str
    train_type: str
    source_station: str
    destination_station: str
    operating_days: list[str]  # weekdays on which the train departs its ORIGIN station
    stops: list[Stop]
    classes: dict[str, ClassInfo]

    @model_validator(mode="after")
    def _consistent(self) -> "Train":
        if self.stops[0].station != self.source_station or self.stops[-1].station != self.destination_station:
            raise ValueError(f"{self.train_id}: source/destination do not match stops")
        if any(c not in TRAVEL_CLASSES for c in self.classes):
            raise ValueError(f"{self.train_id}: unknown class")
        if any(d not in WEEKDAYS for d in self.operating_days):
            raise ValueError(f"{self.train_id}: unknown weekday")
        return self


class Booking(BaseModel):
    booking_id: str
    pnr: str
    train_id: str
    travel_class: str
    passenger: str
    fare_inr: int
    status: Literal["CONFIRMED"] = "CONFIRMED"


# ----------------------------------------------------------------------------- tool envelope
class ToolError(BaseModel):
    code: str
    message: str


class ToolResult(BaseModel):
    """Every tool returns this envelope. Tools never raise to the caller."""

    ok: bool
    data: Optional[dict[str, Any]] = None
    error: Optional[ToolError] = None


# ----------------------------------------------------------------------------- tool inputs
class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResolveStationInput(_Input):
    name: str


class TimeWindow(_Input):
    start: str  # HH:MM inclusive; if start > end the window wraps past midnight
    end: str  # HH:MM inclusive


class SearchTrainsInput(_Input):
    source: str  # canonical station code
    destination: str  # canonical station code
    date: str  # YYYY-MM-DD
    time_window: Optional[TimeWindow] = None  # applies to departure time at `source`


class TrainIdInput(_Input):
    train_id: str


class TrainClassInput(_Input):
    train_id: str
    travel_class: str  # one of 3A, 2A, SL, CC


class BookTicketInput(_Input):
    train_id: str
    travel_class: str
    passenger: str  # full name, Latin script


# ----------------------------------------------------------------------------- tool outputs
class StationCandidate(BaseModel):
    code: str
    name: str
    city: str


class ResolveStationOutput(BaseModel):
    query: str
    ambiguous: bool
    candidates: list[StationCandidate]


class TrainSummary(BaseModel):
    train_id: str
    train_name: str
    source: str
    destination: str
    departure: str  # HH:MM at source
    arrival: str  # HH:MM at destination
    arrival_day_offset: int  # 0 = same day as boarding departure
    duration_minutes: int
    classes: list[str]


class SearchTrainsOutput(BaseModel):
    source: str
    destination: str
    date: str
    time_window: Optional[TimeWindow]
    count: int
    trains: list[TrainSummary]


class StopDetail(BaseModel):
    station: str
    arrival: Optional[str]
    departure: Optional[str]
    distance_km: int


class TrainDetailsOutput(BaseModel):
    train_id: str
    train_name: str
    train_type: str
    source_station: str
    destination_station: str
    operating_days: list[str]
    classes: list[str]
    total_distance_km: int
    stops: list[StopDetail]


class AvailabilityOutput(BaseModel):
    train_id: str
    travel_class: str
    seats_available: int
    status: Literal["AVAILABLE", "SOLD_OUT"]


class FareOutput(BaseModel):
    train_id: str
    travel_class: str
    fare_inr: int
    currency: Literal["INR"] = "INR"


class BookTicketOutput(BaseModel):
    booking_id: str
    pnr: str
    train_id: str
    travel_class: str
    passenger: str
    fare_inr: int
    status: Literal["CONFIRMED"]


# ----------------------------------------------------------------------------- benchmark 3.0: six more tools
BOOKING_STATUSES = ("CONFIRMED", "WAITLISTED", "CANCELLED")
CONCESSIONS = ("senior_citizen", "student")


class AccountBooking(_Frozen):
    """A booking the user made before the pinned 'now' (fixture environment/data/account.json)."""

    pnr: str
    booking_id: str
    train_id: str
    travel_class: str
    passenger: str
    journey_date: str  # YYYY-MM-DD, the date the train leaves its ORIGIN station
    fare_inr: int
    status: Literal["CONFIRMED", "WAITLISTED", "CANCELLED"]
    waitlist_position: Optional[int] = None


class WaitlistEntry(BaseModel):
    waitlist_id: str
    pnr: str
    train_id: str
    travel_class: str
    passenger: str
    fare_inr: int
    waitlist_position: int
    status: Literal["WAITLISTED"] = "WAITLISTED"


class Cancellation(BaseModel):
    pnr: str
    booking_id: str
    train_id: str
    travel_class: str
    passenger: str
    previous_status: Literal["CONFIRMED", "WAITLISTED"]
    cancellation_charge_inr: int
    refund_inr: int


class PnrInput(_Input):
    pnr: str  # 10-digit PNR


class ConcessionFareInput(_Input):
    train_id: str
    travel_class: str
    concession: str  # senior_citizen | student


class BookingStatusOutput(BaseModel):
    pnr: str
    booking_id: str
    train_id: str
    train_name: str
    travel_class: str
    passenger: str
    journey_date: Optional[str]
    fare_inr: int
    status: Literal["CONFIRMED", "WAITLISTED", "CANCELLED"]
    waitlist_position: Optional[int]


class RefundQuoteOutput(BaseModel):
    pnr: str
    status: Literal["CONFIRMED", "WAITLISTED"]
    fare_inr: int
    cancellation_charge_inr: int
    refund_inr: int


class CancelTicketOutput(BaseModel):
    pnr: str
    booking_id: str
    train_id: str
    travel_class: str
    passenger: str
    previous_status: Literal["CONFIRMED", "WAITLISTED"]
    status: Literal["CANCELLED"] = "CANCELLED"
    cancellation_charge_inr: int
    refund_inr: int


class JoinWaitlistOutput(BaseModel):
    waitlist_id: str
    pnr: str
    train_id: str
    travel_class: str
    passenger: str
    fare_inr: int
    waitlist_position: int
    status: Literal["WAITLISTED"]


class LiveStop(BaseModel):
    station: str
    scheduled_arrival: Optional[str]
    scheduled_departure: Optional[str]
    expected_arrival: Optional[str]
    expected_departure: Optional[str]
    expected_date: str  # date of the expected arrival (departure at the origin) at this stop


class LiveStatusOutput(BaseModel):
    train_id: str
    train_name: str
    as_of: str
    run_start_date: Optional[str]
    status: Literal["RUNNING", "NOT_STARTED", "ARRIVED", "NOT_RUNNING_TODAY"]
    delay_minutes: Optional[int]
    last_station: Optional[str]  # last station the train has departed (RUNNING) or reached (ARRIVED)
    next_station: Optional[str]
    stops: list[LiveStop]


class ConcessionFareOutput(BaseModel):
    train_id: str
    travel_class: str
    concession: str
    base_fare_inr: int
    discount_percent: int
    concession_fare_inr: int
    currency: Literal["INR"] = "INR"


TOOL_INPUT_MODELS: dict[str, type[BaseModel]] = {
    "resolve_station": ResolveStationInput,
    "search_trains": SearchTrainsInput,
    "get_train_details": TrainIdInput,
    "check_availability": TrainClassInput,
    "get_fare": TrainClassInput,
    "book_ticket": BookTicketInput,
    "get_booking_status": PnrInput,
    "get_cancellation_refund": PnrInput,
    "cancel_ticket": PnrInput,
    "join_waitlist": BookTicketInput,
    "get_live_train_status": TrainIdInput,
    "get_concession_fare": ConcessionFareInput,
}

TOOL_OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "resolve_station": ResolveStationOutput,
    "search_trains": SearchTrainsOutput,
    "get_train_details": TrainDetailsOutput,
    "check_availability": AvailabilityOutput,
    "get_fare": FareOutput,
    "book_ticket": BookTicketOutput,
    "get_booking_status": BookingStatusOutput,
    "get_cancellation_refund": RefundQuoteOutput,
    "cancel_ticket": CancelTicketOutput,
    "join_waitlist": JoinWaitlistOutput,
    "get_live_train_status": LiveStatusOutput,
    "get_concession_fare": ConcessionFareOutput,
}

# Model-facing descriptions. These are part of the benchmark contract: change => new benchmark version.
TOOL_DESCRIPTIONS: dict[str, str] = {
    "resolve_station": "Resolve a station or city name (any language/spelling) to canonical station code(s). "
    "Returns all matching stations; more than one candidate means the name is ambiguous.",
    "search_trains": "Search trains running from a source station to a destination station on a date (YYYY-MM-DD). "
    "Stations must be canonical station codes. Optional time_window {start, end} in 24-hour HH:MM filters by "
    "departure time at the source.",
    "get_train_details": "Get details of a train: name, type, operating days, classes, and stops with times.",
    "check_availability": "Check seat availability of a train for a travel class (3A, 2A, SL or CC).",
    "get_fare": "Get the fare in INR of a train for a travel class (3A, 2A, SL or CC).",
    "book_ticket": "Book one ticket for a passenger on a train in a travel class. Changes booking state.",
    # benchmark 3.0
    "get_booking_status": "Look up an existing booking by its 10-digit PNR: train, class, passenger, journey date, fare, "
    "and status (CONFIRMED, WAITLISTED or CANCELLED, with the waitlist position if waitlisted).",
    "get_cancellation_refund": "Quote the cancellation charge and refund in INR for a booking (10-digit PNR) WITHOUT cancelling it. "
    "Does not change anything.",
    "cancel_ticket": "Cancel a booking by its 10-digit PNR and refund the fare minus the cancellation charge. "
    "Changes booking state. A train that has already left its origin cannot be cancelled.",
    "join_waitlist": "Put a passenger on the waitlist of a train for a travel class whose seats are sold out. "
    "Only possible when no seats are available. Changes booking state.",
    "get_live_train_status": "Get today's running status of a train (as of now): whether it is running, its delay in minutes, "
    "the last station it left, and expected arrival/departure times at each stop.",
    "get_concession_fare": "Get the discounted fare in INR of a train for a travel class for a concession "
    "(senior_citizen or student), together with the normal fare and the discount percent.",
}
