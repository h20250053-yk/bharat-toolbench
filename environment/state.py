"""Environment state: immutable fixtures + mutable booking state, with deterministic reset/snapshot/hash."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .schemas import AccountBooking, Booking, Cancellation, Complaint, MealOrder, Station, TatkalBooking, TdrClaim, Train, WaitlistEntry

DATA_DIR = Path(__file__).parent / "data"


def normalize_name(text: str) -> str:
    """Deterministic surface-form normalization used for alias matching.

    NFD -> drop Devanagari nukta (so 'हज़रत' == 'हजरत') -> NFC -> casefold -> strip punctuation -> collapse spaces.
    Deliberately NOT fuzzy: only exact matches after this normalization resolve.
    """
    t = unicodedata.normalize("NFD", text).replace("\u093c", "")
    t = unicodedata.normalize("NFC", t).casefold()
    t = re.sub(r"[.,;:'\"()\-_/]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class EnvState:
    """Everything that can change during a run lives in `availability`, `bookings`, `next_booking_seq`."""

    stations: dict[str, Station]
    trains: dict[str, Train]
    alias_index: dict[str, list[str]]  # normalized surface form -> sorted station codes
    availability: dict[tuple[str, str], int] = field(default_factory=dict)  # (train_id, class) -> seats
    bookings: list[Booking] = field(default_factory=list)
    next_booking_seq: int = 1
    static_hash: str = ""
    # benchmark 3.0: the user's earlier bookings, waitlists, live running status (immutable fixtures) ...
    account_bookings: dict[str, AccountBooking] = field(default_factory=dict)  # pnr -> booking made before 'now'
    waitlist_baseline: dict[tuple[str, str], int] = field(default_factory=dict)  # (train_id, class) -> people already waiting
    cancellation_charge: dict[str, int] = field(default_factory=dict)
    concession_percent: dict[str, dict[str, int]] = field(default_factory=dict)
    live_delays: dict[tuple[str, str], int] = field(default_factory=dict)  # (train_id, run_start_date) -> delay minutes
    live_as_of: str = ""
    operations_hash: str = ""  # sha256 of account.json + live_status.json (static_hash keeps covering stations + trains only)
    # ... and their mutable part
    cancellations: list[Cancellation] = field(default_factory=list)
    waitlist: list[WaitlistEntry] = field(default_factory=list)
    next_waitlist_seq: int = 1
    # 20-tool stage: services.json (immutable) and what the eight tools change
    services: dict[str, Any] = field(default_factory=dict)
    tatkal_seats: dict[tuple[str, str], int] = field(default_factory=dict)
    tatkal_bookings: list[TatkalBooking] = field(default_factory=list)
    boarding_changes: dict[str, str] = field(default_factory=dict)  # pnr -> new boarding station
    meal_orders: list[MealOrder] = field(default_factory=list)
    tdr_claims: list[TdrClaim] = field(default_factory=list)
    complaints: list[Complaint] = field(default_factory=list)
    next_service_seq: int = 1

    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> "EnvState":
        raw_st = json.loads((data_dir / "stations.json").read_text(encoding="utf-8"))["stations"]
        raw_tr = json.loads((data_dir / "trains.json").read_text(encoding="utf-8"))["trains"]
        stations = {s["code"]: Station(**s) for s in raw_st}
        trains = {t["train_id"]: Train(**t) for t in raw_tr}
        for t in trains.values():
            for stop in t.stops:
                if stop.station not in stations:
                    raise ValueError(f"train {t.train_id} references unknown station {stop.station}")
        index: dict[str, set[str]] = {}
        for code, st in stations.items():
            forms = {code, st.name, st.city}
            for lang_forms in st.aliases.values():
                forms.update(lang_forms)
            for f in forms:
                index.setdefault(normalize_name(f), set()).add(code)
        alias_index = {k: sorted(v) for k, v in index.items()}
        acct = json.loads((data_dir / "account.json").read_text(encoding="utf-8"))
        live = json.loads((data_dir / "live_status.json").read_text(encoding="utf-8"))
        services = json.loads((data_dir / "services.json").read_text(encoding="utf-8"))
        account = {b["pnr"]: AccountBooking(**b) for b in acct["account_bookings"]}
        for b in account.values():
            if b.train_id not in trains or b.travel_class not in trains[b.train_id].classes:
                raise ValueError(f"account booking {b.pnr} references an unknown train/class")
        state = cls(stations=stations, trains=trains, alias_index=alias_index,
                    static_hash=_sha(_canonical_json({"stations": raw_st, "trains": raw_tr})),
                    operations_hash=_sha(_canonical_json({"account": acct, "live": live, "services": services})),
                    services=services,
                    account_bookings=account,
                    waitlist_baseline={tuple(k.split("|")): v for k, v in acct["waitlist_baseline"].items()},
                    cancellation_charge=dict(acct["cancellation_charge_inr"]),
                    concession_percent={k: dict(v) for k, v in acct["concession_percent"].items()},
                    live_delays={(r["train_id"], r["run_start_date"]): r["delay_minutes"] for r in live["runs"]},
                    live_as_of=live["as_of"])
        state.reset_mutable()
        return state

    def reset_mutable(self) -> None:
        """Return the mutable part to the baseline defined by the fixtures."""
        self.availability = {(t.train_id, c): info.seats for t in self.trains.values() for c, info in t.classes.items()}
        self.bookings = []
        self.next_booking_seq = 1
        self.cancellations = []
        self.waitlist = []
        self.next_waitlist_seq = 1
        self.tatkal_seats = {tuple(k.split("|")): v for k, v in self.services.get("tatkal", {}).get("seats", {}).items()}
        self.tatkal_bookings = []
        self.boarding_changes = {}
        self.meal_orders = []
        self.tdr_claims = []
        self.complaints = []
        self.next_service_seq = 1

    def snapshot(self) -> dict[str, Any]:
        """JSON-serializable view of the mutable state (for tests, debugging, gold state predicates)."""
        return {
            "availability": {f"{t}|{c}": n for (t, c), n in sorted(self.availability.items())},
            "bookings": [b.model_dump() for b in self.bookings],
            "next_booking_seq": self.next_booking_seq,
            "cancellations": [c.model_dump() for c in self.cancellations],
            "waitlist": [w.model_dump() for w in self.waitlist],
            "next_waitlist_seq": self.next_waitlist_seq,
            "tatkal_seats": {f"{t}|{c}": n for (t, c), n in sorted(self.tatkal_seats.items())},
            "tatkal_bookings": [b.model_dump() for b in self.tatkal_bookings],
            "boarding_changes": [{"pnr": p, "station": st} for p, st in sorted(self.boarding_changes.items())],
            "meal_orders": [m.model_dump() for m in self.meal_orders],
            "tdr_claims": [t.model_dump() for t in self.tdr_claims],
            "complaints": [c.model_dump() for c in self.complaints],
            "next_service_seq": self.next_service_seq,
        }

    def state_hash(self) -> str:
        return _sha(_canonical_json(self.snapshot()))
