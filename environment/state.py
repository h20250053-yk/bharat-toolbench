"""Environment state: immutable fixtures + mutable booking state, with deterministic reset/snapshot/hash."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .schemas import Booking, Station, Train

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
        state = cls(stations=stations, trains=trains, alias_index=alias_index,
                    static_hash=_sha(_canonical_json({"stations": raw_st, "trains": raw_tr})))
        state.reset_mutable()
        return state

    def reset_mutable(self) -> None:
        """Return the mutable part to the baseline defined by the fixtures."""
        self.availability = {(t.train_id, c): info.seats for t in self.trains.values() for c, info in t.classes.items()}
        self.bookings = []
        self.next_booking_seq = 1

    def snapshot(self) -> dict[str, Any]:
        """JSON-serializable view of the mutable state (for tests, debugging, gold state predicates)."""
        return {
            "availability": {f"{t}|{c}": n for (t, c), n in sorted(self.availability.items())},
            "bookings": [b.model_dump() for b in self.bookings],
            "next_booking_seq": self.next_booking_seq,
        }

    def state_hash(self) -> str:
        return _sha(_canonical_json(self.snapshot()))
