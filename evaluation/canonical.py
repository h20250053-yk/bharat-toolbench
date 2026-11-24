"""Explicit canonicalization rules for scoring (no fuzzy matching).

Every function maps a surface form to ONE canonical value (or a set of values found in a text) with
written-down rules. Nothing here repairs a wrong value: '20:20' and '8:20 PM' both become '20:20',
but '8:30 PM' stays '20:30'. Used only by the scorer, never by the environment or gold.
"""
from __future__ import annotations

import re
from typing import Any

_DEV_DIGITS = str.maketrans("०१२३४५६७८९૦૧૨૩૪૫૬૭૮૯", "01234567890123456789")  # Devanagari + Gujarati digits
TRAVEL_CLASSES = ("3A", "2A", "SL", "CC")
# Explicit class synonyms (upper-cased, spaces/hyphens/dots removed). Unknown forms stay unknown.
_CLASS_SYNONYMS = {
    "3A": "3A", "3AC": "3A", "AC3": "3A", "AC3TIER": "3A", "3TIERAC": "3A", "THIRDAC": "3A",
    "2A": "2A", "2AC": "2A", "AC2": "2A", "AC2TIER": "2A", "2TIERAC": "2A", "SECONDAC": "2A",
    "SL": "SL", "SLEEPER": "SL", "SLEEPERCLASS": "SL",
    "CC": "CC", "CHAIRCAR": "CC", "ACCHAIRCAR": "CC",
}


def ascii_digits(text: str) -> str:
    """Devanagari / Gujarati digits -> ASCII digits (Hindi/Marathi/Gujarati answers may use them)."""
    return (text or "").translate(_DEV_DIGITS)


# ------------------------------------------------------------------ scalar canonicalizers
def canon_train_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    v = re.sub(r"[\s\-]", "", value).upper()
    return v if re.fullmatch(r"BTB\d{3}", v) else None


def canon_train_ids(value: Any) -> list[str] | None:
    """A JSON string or list of strings -> ordered list of canonical train ids.
    None/''/[] -> []. Returns None if any element is not a valid train id (schema error)."""
    if value is None or value == "" or value == []:
        return []
    items = value if isinstance(value, list) else [value]
    out = []
    for x in items:
        c = canon_train_id(x)
        if c is None:
            return None
        out.append(c)
    return out


def canon_class(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    key = re.sub(r"[\s\-_.()]", "", value).upper()
    return _CLASS_SYNONYMS.get(key)


def canon_passenger(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return " ".join(value.split()).casefold()


def canon_booking_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.strip().upper()
    return v if re.fullmatch(r"BK\d{4}", v) else None


def canon_hhmm(value: Any) -> str | None:
    """'8:05' / '08:05' -> '08:05' (24-hour input only; used for tool arguments)."""
    if not isinstance(value, str):
        return None
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", ascii_digits(value))
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        return None
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def canon_tool_args(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Canonical form of MODEL tool arguments for comparison with gold required_args.
    Only formatting is normalised (case, whitespace, HH:MM padding); values are never repaired."""
    out: dict[str, Any] = {}
    for k, v in (args or {}).items():
        if k == "train_id":
            out[k] = canon_train_id(v) or v
        elif k == "travel_class":
            out[k] = canon_class(v) or v
        elif k == "passenger":
            out[k] = canon_passenger(v) or v
        elif k in ("source", "destination") and isinstance(v, str):
            out[k] = v.strip().upper()
        elif k == "date" and isinstance(v, str):
            out[k] = v.strip()
        elif k == "time_window":
            if isinstance(v, dict):
                out[k] = {"start": canon_hhmm(v.get("start")) or v.get("start"), "end": canon_hhmm(v.get("end")) or v.get("end")}
            else:
                out[k] = v
        else:
            out[k] = v
    return out


# ------------------------------------------------------------------ value extraction from free text
_NUM_RE = re.compile(r"(?<![\w.:/-])(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(\d+))?(?![\w:/])", re.I)


def numbers_in(text: str) -> set[int]:
    """Standalone integers in a text. Handles '1460', '1,460', '₹1,460', 'Rs 1460', 'INR 1,460.00', Indian
    grouping '1,00,000' and Devanagari digits. Tokens glued to letters (BTB102, 3A, BK0001) are NOT numbers."""
    out: set[int] = set()
    for m in _NUM_RE.finditer(ascii_digits(text)):
        frac = m.group(2)
        if frac and int(frac) != 0:
            continue  # a non-integer amount is not an integer value
        out.add(int(m.group(1).replace(",", "")))
    return out


# day-part words (en / Hinglish / Hindi / Marathi / Gujarati) -> how to read the hour
_MORNING = r"(?:morning|subah|सुबह|सकाळी|सकाळ|સવારે|સવાર)"
_NOON = r"(?:afternoon|noon|dopahar|दोपहर|दुपारी|दुपार|બપોરે|બપોર)"
_EVENING = r"(?:evening|shaam|sham|शाम|संध्याकाळी|संध्याकाळ|સાંજે|સાંજ)"
_NIGHT = r"(?:night|raat|रात|रात्री|रात्रि|રાત્રે|રાતે|રાત)"
_TIME_RE = re.compile(
    r"(?:(?P<part>" + "|".join([_MORNING, _NOON, _EVENING, _NIGHT]) + r")\s*(?:को|ला|ko|of|at)?\s*)?"
    r"(?<![\d:])(?P<h>\d{1,2})(?::(?P<m>\d{2})|\.(?P<m2>\d{2})(?=\s*[ap]\.?\s?m))?\s*(?P<ampm>a\.?\s?m\.?|p\.?\s?m\.?)?(?![\d:])(?!\.\d)", re.I)


def _apply_part(h: int, part: str) -> int | None:
    """Hour (0-23) for a clock hour written after a day-part word, or None if the combination is not a valid time.
    12-hour readings first; a 24-hour hour (0 or 13-23) is accepted only when it lies inside that part of the day
    ('शाम 18:30' = 18:30, but 'सुबह 13:00' is rejected)."""
    p = part.casefold()
    if re.fullmatch(_MORNING, p, re.I):
        return 0 if h == 12 else h if h <= 11 else None
    if re.fullmatch(_NOON, p, re.I):
        return 12 if h == 12 else h + 12 if 1 <= h <= 6 else h if 13 <= h <= 16 else None
    if re.fullmatch(_EVENING, p, re.I):
        return h + 12 if 1 <= h <= 11 else h if 16 <= h <= 23 else None
    if re.fullmatch(_NIGHT, p, re.I):
        return h + 12 if 6 <= h <= 11 else 0 if h in (0, 12) else h if h <= 5 or 18 <= h <= 23 else None
    return None


def times_in(text: str) -> set[str]:
    """Clock times in a text as canonical 24-hour 'HH:MM'. Rules (explicit, in order):
      1. 'h[:mm] AM/PM' -> 12-hour conversion ('8:20 PM' -> 20:20, '12:30 AM' -> 00:30);
      2. a day-part word before the time (सुबह/सकाळी/morning = AM, दोपहर/दुपारी = afternoon, शाम/संध्याकाळी/evening = PM,
         रात/रात्री/night = PM for 6-11, AM for 1-5) -> converted ('रात्री 8:20' -> 20:20); a 24-hour hour that fits the
         part of the day is kept ('शाम 18:30' -> 18:30), one that contradicts it is not a time ('सुबह 13:00');
      3. otherwise 'H:MM' is read as 24-hour ('20:20', '04:00', '8:20' -> 08:20).
    The separator is ':'; '.' counts only when AM/PM follows ('8.20 PM'), so '₹14.50' or '10.10' are not times.
    A bare number without ':' and without AM/PM or a day-part word is NOT a time."""
    out: set[str] = set()
    for m in _TIME_RE.finditer(ascii_digits(text)):
        h, mm, ampm, part = int(m.group("h")), m.group("m") or m.group("m2"), m.group("ampm"), m.group("part")
        if mm is None and not ampm and not part:
            continue
        minute = int(mm) if mm else 0
        if minute > 59:
            continue
        if ampm:
            if not 1 <= h <= 12:
                continue
            pm = ampm.lower().startswith("p")
            h = (0 if h == 12 else h) + (12 if pm else 0)
        elif part:
            conv = _apply_part(h, part)
            if conv is None:
                continue
            h = conv
        elif h > 23:
            continue
        out.add(f"{h:02d}:{minute:02d}")
    return out


_MONTHS = {"october": 10, "oct": 10, "अक्टूबर": 10, "ऑक्टोबर": 10, "अक्तूबर": 10, "ઓક્ટોબર": 10, "ઑક્ટોબર": 10}


def dates_in(text: str, default_year: int = 2026) -> set[str]:
    """Dates in a text as ISO 'YYYY-MM-DD': '2026-10-10', '10/10/2026', '10-10-2026', '10 October [2026]',
    '10 Oct', '10 अक्टूबर', '10 ऑक्टोबर'. Only October month names are needed by the benchmark (all dates are Oct 2026)."""
    t = ascii_digits(text)
    out: set[str] = set()
    for y, mo, d in re.findall(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t):
        out.add(f"{int(y):04d}-{int(mo):02d}-{int(d):02d}")
    for d, mo, y in re.findall(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", t):
        out.add(f"{int(y):04d}-{int(mo):02d}-{int(d):02d}")
    names = "|".join(sorted(map(re.escape, _MONTHS), key=len, reverse=True))
    for d, name, y in re.findall(r"(?<!\d)(\d{1,2})\s*(" + names + r")\.?(?:,?\s*(\d{4}))?", t, re.I):
        out.add(f"{int(y) if y else default_year:04d}-{_MONTHS[name.casefold()]:02d}-{int(d):02d}")
    return out


def station_codes_in(text: str) -> set[str]:
    return set(re.findall(r"\b[A-Z]{2,4}\b", text or ""))


# ------------------------------------------------------------------ structured answer values (answer_values)
# Explicit tables; anything not listed is NOT recognised (returns None -> 'invalid'), never guessed.
_WEEKDAYS = {
    "MON": ["mon", "monday", "somvar", "somvaar", "somwar", "सोमवार", "सोमवारी", "સોમવાર", "સોમવારે"],
    "TUE": ["tue", "tues", "tuesday", "mangalvar", "mangalvaar", "mangalwar", "मंगलवार", "मंगळवार", "मंगळवारी", "મંગળવાર", "મંગળવારે", "મંગલવાર", "મંગલવારે"],
    "WED": ["wed", "wednesday", "budhvar", "budhvaar", "budhwar", "बुधवार", "बुधवारी", "બુધવાર", "બુધવારે"],
    "THU": ["thu", "thur", "thurs", "thursday", "guruvar", "guruvaar", "guruwar", "brihaspativar", "गुरुवार", "गुरुवारी", "बृहस्पतिवार", "ગુરુવાર", "ગુરુવારે", "ગુરૂવાર", "ગુરૂવારે"],
    "FRI": ["fri", "friday", "shukravar", "shukravaar", "shukrawar", "शुक्रवार", "शुक्रवारी", "શુક્રવાર", "શુક્રવારે"],
    "SAT": ["sat", "saturday", "shanivar", "shanivaar", "shaniwar", "शनिवार", "शनिवारी", "શનિવાર", "શનિવારે"],
    "SUN": ["sun", "sunday", "ravivar", "ravivaar", "raviwar", "रविवार", "रविवारी", "રવિવાર", "રવિવારે"],
}
_WEEKDAY_LOOKUP = {form: code for code, forms in _WEEKDAYS.items() for form in forms}
# Yes/no words per language (one rule for ALL of them, see canon_bool). Ambiguous words (Hindi/Marathi "हो", Gujarati "ના" = also the
# genitive "of", "હોય" = "is / if there is" is NOT yes) are safe only because they count solely as the first word.
YES_WORDS = {"en": {"true", "yes", "y"}, "hinglish": {"haan", "han", "ha"}, "hi": {"हाँ", "हां"}, "mr": {"होय", "हो"}, "gu": {"હા", "હાં"}}
NO_WORDS = {"en": {"false", "no", "n"}, "hinglish": {"nahi", "nahin"}, "hi": {"नहीं", "नही"}, "mr": {"नाही"}, "gu": {"ના", "નથી", "નહીં", "નહિ"}}
_TRUE = set().union(*YES_WORDS.values())
_FALSE = set().union(*NO_WORDS.values())
# the first word of a reply: optional opening quote/bracket, then the word up to a space, "," "." "!", a closing quote or the end of the value
_FIRST_WORD = re.compile(r"[\"'“”‘’(]*([^\s,.!\"'“”‘’()]+)(?=$|[\s,.!\"'“”‘’)])")


def canon_weekday(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return _WEEKDAY_LOOKUP.get(re.sub(r"[\s.]", "", value).casefold())


def canon_weekday_set(value: Any) -> frozenset[str] | None:
    """List (or comma/slash/'and'-separated string) of weekdays -> set of codes; None if any element is unknown."""
    items = _split_list(value)
    if items is None:
        return None
    codes = [canon_weekday(x) for x in items]
    return None if any(c is None for c in codes) else frozenset(codes)


def canon_class_set(value: Any) -> frozenset[str] | None:
    """List (or comma/slash/'and'-separated string) of travel classes -> set; order never matters."""
    items = _split_list(value)
    if items is None:
        return None
    codes = [canon_class(x) for x in items]
    return None if any(c is None for c in codes) else frozenset(codes)


def _split_list(value: Any) -> list[str] | None:
    if isinstance(value, list):
        return value if all(isinstance(x, str) for x in value) else None
    if isinstance(value, str):
        parts = [p.strip() for p in re.split(r",|/|;|\band\b|\baur\b|और|आणि|અને", value) if p.strip()]
        return parts or None
    return None


def canon_bool(value: Any) -> bool | None:
    """Yes/no of a value, with ONE rule for en, hinglish, hi, mr and gu: the whole value is a yes/no word, or a yes/no word is the
    FIRST word, followed by ',' '.' '!' or a space. A leading yes/no word decides ("Yes, there is no problem" is yes; "हा, कोई समस्या नथी"
    style replies likewise). A yes/no word later in the sentence never counts ("it runs, yes" is unknown). Anything else is None."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        m = _FIRST_WORD.match(value.strip().casefold())
        if m:
            w = m.group(1)
            return True if w in _TRUE else False if w in _FALSE else None
    return None


def canon_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        m = re.fullmatch(r"\s*(\d+)\s*", ascii_digits(value))
        return int(m.group(1)) if m else None
    return None


def canon_station_name(value: Any) -> str | None:
    """Harmless differences only: case, surrounding/repeated whitespace, punctuation (. , - ' ")."""
    if not isinstance(value, str) or not value.strip():
        return None
    return " ".join(re.sub(r"[.,\-'\"()]", " ", value).split()).casefold()


_H = r"(?:h|hr|hrs|hour|hours|ghanta|ghante|घंटा|घंटे|तास|કલાક|કલાકે)"
_M = r"(?:m|min|mins|minute|minutes|minit|minat|मिनट|मिनिट|मिनिटे|मिनिटं|મિનિટ|મિનિટે)"


def canon_duration_minutes(value: Any) -> int | None:
    """A journey DURATION -> whole minutes. Accepted (explicit) forms only:
       445 | "445" | "445 min(utes)" | "7h 25m" | "7 h 25 min" | "7 hours 25 minutes" | "7 hours" | "7:25" (h:mm)
       | "7 घंटे 25 मिनट" | "7 तास 25 मिनिटे" | "7 ghante 25 minute"; Devanagari digits allowed.
    Rejected (None): approximations ("about 7 hours"), decimals ("7.4 hours"), minutes >= 60 in h:mm, anything else."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if not isinstance(value, str):
        return None
    v = " ".join(ascii_digits(value).casefold().split())
    if re.fullmatch(r"\d+", v):
        return int(v)
    m = re.fullmatch(r"(\d+)\s*" + _M, v)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"(\d+):([0-5]\d)(?:\s*" + _H + r")?", v)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.fullmatch(r"(\d+)\s*" + _H + r"(?:\s*(?:and|aur|और|आणि|અને)?\s*(\d+)\s*" + _M + r")?", v)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2) or 0)
    return None
