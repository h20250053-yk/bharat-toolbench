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


TOOL_INPUT_MODELS: dict[str, type[BaseModel]] = {
    "resolve_station": ResolveStationInput,
    "search_trains": SearchTrainsInput,
    "get_train_details": TrainIdInput,
    "check_availability": TrainClassInput,
    "get_fare": TrainClassInput,
    "book_ticket": BookTicketInput,
}

TOOL_OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "resolve_station": ResolveStationOutput,
    "search_trains": SearchTrainsOutput,
    "get_train_details": TrainDetailsOutput,
    "check_availability": AvailabilityOutput,
    "get_fare": FareOutput,
    "book_ticket": BookTicketOutput,
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
}
