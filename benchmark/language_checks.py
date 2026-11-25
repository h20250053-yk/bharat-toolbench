"""Automated, model-independent surface checks that the language variants (en, hinglish, hi, mr; Gujarati is checked separately in validate_tasks) of a task keep the same constraints.

IMPORTANT: these are keyword/regex presence checks written by the draft author. They catch dropped or altered
constraints (e.g. 'after' instead of 'at or after', missing 'don't book'); they are NOT a substitute for a fluent human
reviewer and never mean a variant is natural, correct or accepted. Used by build_language_audit.py and validate_tasks.py.
"""
from __future__ import annotations

import json
import re
from datetime import date as Date
from typing import Any

from environment.state import DATA_DIR, normalize_name

from .batch_t06_t15 import MARKERS as _BATCH_MARKERS
from .batch_t16_t25 import MARKERS as _BATCH2_MARKERS
from .batch_t26_t50 import MARKERS as _BATCH3_MARKERS
from .batch_t51_t75 import MARKERS as _BATCH4_MARKERS
from .batch_t76_t100 import MARKERS as _BATCH5_MARKERS
from .batch_gujarati import MARKERS as _GU_MARKERS, MONTH_WORDS as _GU_MONTHS

LANGS = ["en", "hinglish", "hi", "mr"]
EXTRA_LANGS = ["gu"]  # languages that do not (yet) cover every task; validated separately (validate_tasks.validate_gujarati)
NA = "not_applicable"
MONTH_WORD = {"en": "October", "hinglish": "October", "hi": "अक्टूबर", "mr": "ऑक्टोबर"}
CHECKS = ["intent_preserved", "route_preserved", "date_preserved", "time_preserved", "time_constraint_preserved",
          "class_preserved", "fare_constraint_preserved", "availability_constraint_preserved", "passenger_preserved",
          "booking_condition_preserved", "forbidden_action_preserved", "fallback_condition_preserved"]

# every regex in a list must match (case-insensitive). ("absent", rx) => rx must NOT match.
_BOOK = {"en": r"\bbook", "hinglish": r"\bbook\b|\bbooking\b", "hi": "बुक|बुकिंग", "mr": "बुक|बुकिंग", "gu": "બુક|બુકિંગ"}
_M: dict[str, dict[str, Any]] = {
    "T01": {
        "intent": {"en": [r"\bfare\b"], "hinglish": [r"\bfare\b", r"\bkitna\b"], "hi": ["किराया", "कितना"], "mr": ["भाडे", "किती"]},
        "booking": "ABSENT",
    },
    "T02": {
        "intent": {"en": [r"\bseat\b", r"\bfare\b", r"\bonly train\b"], "hinglish": [r"\bseat\b", r"\bfare\b", r"\bek hi train\b"],
                   "hi": ["सीट", "किराया", "एकमात्र ट्रेन"], "mr": ["सीट", "भाडे", "एकमेव ट्रेन"]},
        "availability": {"en": [r"\bavailable\b"], "hinglish": [r"\bavailable\b"], "hi": ["उपलब्ध"], "mr": ["उपलब्ध"]},
        "booking": "ABSENT",
    },
    "T03": {
        "intent": {"en": [r"\bwhich train\b", r"\bticket\b"], "hinglish": [r"kaun si train", r"\bticket\b"],
                   "hi": ["कौन-सी ट्रेन", "टिकट"], "mr": ["ट्रेन कोणती", "तिकीट"]},
        "time": {"en": [r"6 PM"], "hinglish": [r"shaam 6 baje"], "hi": ["शाम 6 बजे"], "mr": ["संध्याकाळी 6 वाजता"]},
        # inclusive bound: 'at or after 6 PM' (>= 18:00), never plain 'after'
        "time_constraint": {"en": [r"at or after 6 PM"], "hinglish": [r"6 baje ya uske baad"], "hi": ["6 बजे या उसके बाद"], "mr": ["6 वाजता किंवा त्यानंतर"]},
        "fare": {"en": [r"no more than ₹3,000"], "hinglish": [r"₹3,000 se zyada nahi"], "hi": ["₹3,000 से ज़्यादा नहीं"], "mr": ["₹3,000 पेक्षा जास्त नसावे"]},
        "availability": {"en": [r"have seats available"], "hinglish": [r"seats available honi chahiye"], "hi": ["सीटें उपलब्ध होनी चाहिए"], "mr": ["सीट उपलब्ध असावी"]},
        "forbidden": {"en": [r"don't book anything"], "hinglish": [r"kuch bhi book mat karna"], "hi": ["कुछ भी बुक मत कीजिए"], "mr": ["काहीही बुक करू नका"]},
    },
    "T04": {
        "intent": {"en": [r"\bbook\b", r"\bsleeper\b"], "hinglish": [r"\bbook kar do\b", r"\bsleeper\b"],
                   "hi": ["बुक कीजिए", "स्लीपर"], "mr": ["बुक करा", "स्लीपर"]},
        "fare": {"en": [r"\bcheapest\b"], "hinglish": [r"sabse sasta"], "hi": ["सबसे सस्ता"], "mr": ["सर्वात स्वस्त"]},
        "booking": {"en": [r"^book\b"], "hinglish": [r"book kar do"], "hi": ["बुक कीजिए"], "mr": ["बुक करा"]},
    },
    "T05": {
        "intent": {"en": [r"\bbook a 3A ticket\b", r"just tell me"], "hinglish": [r"3A ticket book karo", r"bas mujhe bata dena"],
                   "hi": ["3A का टिकट बुक कीजिए", "बस मुझे बता दीजिए"], "mr": ["3A", "तिकीट", "फक्त मला सांगा"]},
        "availability": {"en": [r"only if seats are available"], "hinglish": [r"sirf tab jab seats available hon"],
                         "hi": ["केवल तभी जब सीटें उपलब्ध हों"], "mr": ["फक्त सीट उपलब्ध", "तरच"]},
        "booking": {"en": [r"\bbook a 3A ticket\b", r"only if"], "hinglish": [r"book karo", r"sirf tab jab"],
                    "hi": ["बुक कीजिए", "केवल तभी"], "mr": ["बुक करा", "तरच"]},
        "forbidden": {"en": [r"don't book any other class or train"], "hinglish": [r"kisi aur class ya kisi aur train mein book mat karna"],
                      "hi": ["दूसरी क्लास या दूसरी ट्रेन में बुक मत कीजिए"],
                      "mr": ["दुसऱ्या कोणत्याही क्लासमध्ये", "दुसऱ्या ट्रेनमध्ये", "बुक करू नका"]},
        "fallback": {"en": [r"sold out", r"any other class or train"], "hinglish": [r"sold out", r"kisi aur class"],
                     "hi": ["सोल्ड आउट", "दूसरी क्लास"], "mr": ["सीट उपलब्ध नसतील", "दुसऱ्या कोणत्याही क्लासमध्ये"]},
    },
}


_M.update(_BATCH_MARKERS)  # batch T06-T15 markers live next to the batch queries (benchmark/batch_t06_t15.py)
_M.update(_BATCH2_MARKERS)  # batch T16-T25 (benchmark/batch_t16_t25.py)
_M.update(_BATCH3_MARKERS)  # batch T26-T50 (benchmark/batch_t26_t50.py)
_M.update(_BATCH4_MARKERS)  # batch T51-T75 (benchmark/batch_t51_t75.py)
_M.update(_BATCH5_MARKERS)  # batch T76-T100, benchmark 3.0 (benchmark/batch_t76_t100.py)
for _t, _keys in _GU_MARKERS.items():  # Gujarati (benchmark/batch_gujarati.py): add a 'gu' entry to each existing marker (copy, never mutate)
    for _k, _rx in _keys.items():
        if not isinstance(_M[_t].get(_k), dict):
            raise KeyError(f"Gujarati marker {_t}.{_k} has no counterpart in the other languages")
        _M[_t] = {**_M[_t], _k: {**_M[_t][_k], "gu": _rx}}


def _all(rxs: list[str], q: str) -> bool:
    return all(re.search(rx, q, re.I) for rx in rxs)


def _marker(tid: str, key: str, lang: str, q: str) -> Any:
    m = _M[tid].get(key)
    if m is None:
        return NA
    if m == "ABSENT":  # no booking verb at all
        return re.search(_BOOK[lang], q, re.I) is None
    return _all(m[lang], q)


def station_aliases(lang: str) -> dict[str, list[str]]:
    st = json.loads((DATA_DIR / "stations.json").read_text(encoding="utf-8"))["stations"]
    return {s["code"]: s["aliases"][lang] for s in st}


def _codes_for(name: str) -> set[str]:
    """All station codes a surface form resolves to (same normalization as the environment; any language)."""
    key = normalize_name(name)
    st = json.loads((DATA_DIR / "stations.json").read_text(encoding="utf-8"))["stations"]
    return {s["code"] for s in st if key in {normalize_name(f) for f in [s["code"], s["name"], s["city"], *sum(s["aliases"].values(), [])]}}


def _ambiguous_route_ok(q: str, lang: str, src_name: str, dst_code: str) -> bool:
    """Ambiguous source (e.g. 'Delhi'): the variant must use an alias that is ambiguous across exactly the same
    stations, must NOT use any alias that singles one of them out (e.g. 'New Delhi'), and must put it before the destination."""
    cands = _codes_for(src_name)
    al = station_aliases(lang)
    shared = [a for a in sorted({a for c in cands for a in al[c]}) if _codes_for(a) == cands]
    specific = [a for c in cands for a in al[c] if _codes_for(a) != cands]
    ps, pd = _first_pos(q, shared), _first_pos(q, al[dst_code])
    return ps >= 0 and pd >= 0 and ps < pd and not any(a.casefold() in q.casefold() for a in specific)


def _first_pos(q: str, aliases: list[str]) -> int:
    # Marathi commonly inflects station names in route phrases (e.g. पुणे -> पुण्याहून/पुण्याला,
    # कोलकाता -> कोलकात्याहून). These are validation-time surface forms only; they do not alter
    # the frozen station aliases or benchmark text.
    forms = list(aliases)
    if aliases and any(a for a in aliases):
        expanded: list[str] = []
        for a in aliases:
            expanded.append(a)
            if not a:
                continue
            if a.endswith("े"):
                expanded.append(a[:-1] + "्या")
            if a.endswith("ा"):
                expanded.append(a[:-1] + "्या")
        forms = sorted(set(forms + expanded), key=len, reverse=True)
    pos = [q.casefold().find(a.casefold()) for a in forms if a.casefold() in q.casefold()]
    return min(pos) if pos else -1


def parse_dates(q: str, lang: str) -> list[str]:
    if lang == "gu":  # Gujarati attaches case endings to the year ('9 ઓક્ટોબર 2026ના રોજ'), so no word boundary after it
        rx = r"(?<!\d)(\d{1,2})\s+(?:" + "|".join(_GU_MONTHS) + r")\s+(\d{4})(?!\d)"
        return [Date(int(y), 10, int(d)).isoformat() for d, y in re.findall(rx, q)]
    return [Date(int(y), 10, int(d)).isoformat() for d, y in re.findall(rf"\b(\d{{1,2}})\s+{MONTH_WORD[lang]}\s+(\d{{4}})\b", q)]


def numeric_signature(q: str) -> list[str]:
    """Set of numeric values in the query (dates, train ids, class digit, times, budget). A set, not a multiset: repeating
    the class (e.g. '3A' as an explicit referent instead of a pronoun) is not a new value; a new/missing value is caught."""
    return sorted(set(re.findall(r"\d+", q.replace(",", ""))))


def run_checks(tid: str, lang: str, q: str, params: dict[str, Any], code_of: Any) -> dict[str, Any]:
    """params = spec.solver.params; code_of(name) -> station code (via the frozen English/any alias)."""
    out: dict[str, Any] = {}
    out["intent_preserved"] = _marker(tid, "intent", lang, q)
    if "station_name" in params:  # batch 2: single-station identity task (T16)
        out["route_preserved"] = _first_pos(q, station_aliases(lang)[code_of(params["station_name"])]) >= 0
    elif "source_name" in params and not _codes_for(params["source_name"]):  # batch 2: unknown source (checked via intent markers)
        out["route_preserved"] = _first_pos(q, station_aliases(lang)[code_of(params["destination_name"])]) >= 0
    elif "source_name" in params and len(_codes_for(params["source_name"])) > 1:  # batch: intentionally ambiguous source
        out["route_preserved"] = _ambiguous_route_ok(q, lang, params["source_name"], code_of(params["destination_name"]))
        if "train_id" in params:  # batch 3 (T47): ambiguous source + named train: the train id must survive too
            out["route_preserved"] = out["route_preserved"] and params["train_id"] in re.findall(r"\bBTB\d{3}\b", q)
    elif "source_name" in params:
        al, s, d = station_aliases(lang), code_of(params["source_name"]), code_of(params["destination_name"])
        ps, pd = _first_pos(q, al[s]), _first_pos(q, al[d])
        out["route_preserved"] = ps >= 0 and pd >= 0 and ps < pd
        if s == d:  # batch 4 (T69): two different names of ONE station; both names must survive (positions coincide by alias)
            out["route_preserved"] = len({a for a in al[s] if _first_pos(q, [a]) >= 0}) >= 2
        if "train_id" in params:  # batch: named train AND stated route (T10/T14/T15): both must survive
            out["route_preserved"] = out["route_preserved"] and params["train_id"] in re.findall(r"\bBTB\d{3}\b", q)
    elif "train_id" in params:  # fixed-train tasks: the 'route' entity is the explicit train id
        out["route_preserved"] = params["train_id"] in re.findall(r"\bBTB\d{3}\b", q)
    else:  # batch 3 (T45): no station or train entity at all
        out["route_preserved"] = NA
    for leg in params.get("legs", []):  # batch 3 (T41): every leg's train id must survive
        out["route_preserved"] = out["route_preserved"] and leg["train_id"] in re.findall(r"\bBTB\d{3}\b", q)
    for key in ("boarding_station_name", "stop_name", "from_name", "to_name", "via_name", "continues_to_name",
                "second_destination_name"):  # extra station entities (T06, T07, T17, T40, T41, T49, T56)
        if key in params:
            out["route_preserved"] = out["route_preserved"] and _first_pos(q, station_aliases(lang)[code_of(params[key])]) >= 0
    if "from_name" in params:  # T17: segment order must survive
        al = station_aliases(lang)
        out["route_preserved"] = out["route_preserved"] and _first_pos(q, al[code_of(params["from_name"])]) < _first_pos(q, al[code_of(params["to_name"])])
    if "return_date" in params:  # batch 2: round trip, both dates in order
        out["date_preserved"] = parse_dates(q, lang) == [params["date"], params["return_date"]]
    elif "second_date" in params:  # batch 3 (T41): two legs on two dates, in order
        out["date_preserved"] = parse_dates(q, lang) == [params["date"], params["second_date"]]
    else:
        out["date_preserved"] = (parse_dates(q, lang) == [params["date"]]) if "date" in params else NA
    out["time_preserved"] = _marker(tid, "time", lang, q)
    out["time_constraint_preserved"] = _marker(tid, "time_constraint", lang, q)
    _cls = [params[k] for k in ("travel_class", "fallback_class") if k in params]
    out["class_preserved"] = (all(re.search(rf"(?<![0-9A-Za-z]){c}(?![0-9A-Za-z])", q) is not None for c in _cls)
                              if _cls else NA)
    out["fare_constraint_preserved"] = _marker(tid, "fare", lang, q)
    av = _marker(tid, "availability", lang, q)
    out["availability_constraint_preserved"] = NA if tid in ("T01", "T04") else av
    _pax = [params["passenger"]] if "passenger" in params else list(params.get("passengers", []))
    out["passenger_preserved"] = all(x in q for x in _pax) if _pax else NA
    native = params.get("passenger_script_forms", {}).get(lang)
    if native:  # batch 4 (T54): this variant writes the name in its own script BY DESIGN; the Latin form must then be absent
        out["passenger_preserved"] = native in q and not any(x in q for x in _pax)
    if params.get("missing_slot") == "passenger":  # batch 2: no person name may appear (Latin 'First Last' pattern)
        out["passenger_preserved"] = re.search(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", q) is None
    out["booking_condition_preserved"] = _marker(tid, "booking", lang, q)
    out["forbidden_action_preserved"] = _marker(tid, "forbidden", lang, q)
    out["fallback_condition_preserved"] = _marker(tid, "fallback", lang, q)
    assert list(out) == CHECKS
    return out
