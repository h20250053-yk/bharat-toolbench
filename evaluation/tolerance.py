"""Format tolerance shared by every adapter and every language (FORMAT_ROBUSTNESS.md).

Goal: judge what a model DOES (its tool calls, bookings and answer), not how it writes them. Every rule here changes only the
REPRESENTATION of something the model already said (wrapper, spelling of a status, digit script, list-vs-string, JSON quoting) and
never a decision: no rule renames an argument, repairs a value, guesses a station/train/class/status, or extracts an answer from prose.
A rule that does not apply unambiguously leaves its input untouched, so the strict result stands.

Every rule application is returned as a recovery record  {"stage", "rule", "before", "after"}  (the runner adds "turn") so the strict
and the lenient score can both be reported. Stages: "final_answer" (reading the final reply), "tool_call" (a call written as text),
"arguments" (argument formats), "final_text" (which turn's text is the final reply).

Nothing here calls a model, a tool or the network.
"""
from __future__ import annotations

import ast
import json
import re
import unicodedata
from typing import Any

from .canonical import _CLASS_SYNONYMS, canon_booking_id, canon_class, dates_in, numbers_in, times_in
from .final_answer import ANSWER_VALUE_KEYS, REQUIRED_KEYS, STATUSES

Recovery = dict[str, Any]
CONTRACT_KEYS = REQUIRED_KEYS + ("answer_values",)
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"))
from environment.railway_env import TOOL_NAMES  # noqa: E402  (all twelve tools of benchmark 3.0)


def _rec(stage: str, rule: str, before: Any = None, after: Any = None) -> Recovery:
    return {"stage": stage, "rule": rule, "before": _short(before), "after": _short(after)}


def _short(v: Any, n: int = 160) -> Any:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + "..."


# ============================================================================================ text hygiene
def clean_text(s: str) -> str:
    """NFC-normalise and drop zero-width characters (ZWJ/ZWNJ/BOM appear in Indic text and break word matching)."""
    return unicodedata.normalize("NFC", s or "").translate(_ZERO_WIDTH)


def digits_to_ascii(s: str) -> str:
    """Decimal digits of ANY script (Devanagari, Gujarati, full-width, Arabic-Indic, ...) -> ASCII digits."""
    return "".join(str(unicodedata.digit(c)) if unicodedata.category(c) == "Nd" and c not in "0123456789" else c for c in s)


_THINK_BLOCK = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.S | re.I)


def strip_thinking(text: str) -> tuple[str, list[Recovery]]:
    """Remove <think>...</think> (and a leading '...</think>' whose opening tag the template swallowed). A draft answer inside
    thinking is not an answer, and numbers inside thinking must not satisfy a value check."""
    out = _THINK_BLOCK.sub("", text or "")
    if re.search(r"</think(?:ing)?>", out, re.I) and not re.search(r"<think(?:ing)?>", out, re.I):
        out = re.split(r"</think(?:ing)?>", out, flags=re.I)[-1]
    out = re.sub(r"<think(?:ing)?>.*\Z", "", out, flags=re.S | re.I)   # unterminated thinking at the end
    return (out, [_rec("final_answer", "think_stripped", text, out)]) if out != (text or "") else (text or "", [])


# ============================================================================================ JSON repair
def _balance_closers(s: str) -> str:
    """Append the closing braces/brackets a truncated object lacks (string-aware). Never removes or alters content."""
    stack: list[str] = []
    in_str = esc = False
    for ch in s:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            stack.pop()
    return s + "".join(reversed(stack))


def _strip_trailing_commas(s: str) -> str:
    out, in_str, esc, i = [], False, False, 0
    while i < len(s):
        ch = s[i]
        if in_str:
            out.append(ch)
            esc = (not esc) if ch == "\\" else False
            if ch == '"' and not esc:
                in_str = False
        elif ch == '"':
            in_str = True
            out.append(ch)
        elif ch == ",":
            j = i + 1
            while j < len(s) and s[j] in " \t\r\n":
                j += 1
            if j < len(s) and s[j] in "}]":
                i += 1
                continue
            out.append(ch)
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def loads_tolerant(raw: str, allow_trailing: bool = False) -> tuple[Any, list[str]]:
    """json.loads with value-preserving fallbacks. Returns (value, [rule names used]); raises ValueError if nothing works.
    Fallbacks, in order: first complete object + ignored trailing closers/whitespace; trailing commas removed; missing closers
    appended; a pure Python literal (single quotes, None/True/False) via ast.literal_eval (never eval)."""
    body = (raw or "").strip()
    fence = re.fullmatch(r"```(?:json|JSON)?\s*(.*?)\s*```", body, re.S)
    if fence:
        body = fence.group(1).strip()
    try:
        return json.loads(body), []
    except json.JSONDecodeError:
        pass
    # first complete object, rest must be only closers / whitespace / commas (stray '}' after the object)
    try:
        obj, end = json.JSONDecoder().raw_decode(body)
        if allow_trailing or not body[end:].strip(" \t\r\n}],;"):
            return obj, ["trailing_text_ignored"]
    except json.JSONDecodeError:
        pass
    for rule, cand in (("trailing_comma_removed", _strip_trailing_commas(body)), ("closing_braces_appended", _balance_closers(body)),
                       ("trailing_comma_removed+closing_braces_appended", _balance_closers(_strip_trailing_commas(body)))):
        try:
            return json.loads(cand), [rule]
        except json.JSONDecodeError:
            continue
    try:
        lit = ast.literal_eval(body)
        if isinstance(lit, dict):
            return json.loads(json.dumps(lit)), ["python_literal"]
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        pass
    raise ValueError("not JSON")


# ============================================================================================ final answer
_OPEN_RE = re.compile(r"<\s*FINAL_ANSWER_JSON\s*>", re.I)
_CLOSE_RE = re.compile(r"<\s*/\s*FINAL_ANSWER_JSON\s*>", re.I)
_EXACT_RE = re.compile(r"<FINAL_ANSWER_JSON>(.*?)</FINAL_ANSWER_JSON>", re.S)
_KEY_ALIASES: dict[str, str] = {}
for _k in CONTRACT_KEYS + ANSWER_VALUE_KEYS:
    _KEY_ALIASES[_k.casefold()] = _k


def _canon_key(k: Any, allowed: tuple[str, ...]) -> str | None:
    if not isinstance(k, str):
        return None
    c = re.sub(r"[\s\-]+", "_", k.strip().casefold())
    return _KEY_ALIASES[c] if c in _KEY_ALIASES and _KEY_ALIASES[c] in allowed else None


def _find_block(text: str) -> tuple[str, str | None, list[Recovery]]:
    """(natural text, raw block text or None, recoveries). Order: exact tags (last block wins, as strict) -> tag variants ->
    opening tag without closing tag -> untagged JSON object that carries every contract key."""
    exact = list(_EXACT_RE.finditer(text))
    if exact:
        last = exact[-1]
        return (text[:last.start()] + text[last.end():]).strip(), last.group(1), []
    pairs = []
    for o in _OPEN_RE.finditer(text):
        c = _CLOSE_RE.search(text, o.end())
        if c:
            pairs.append((o, c))
    if pairs:
        o, c = pairs[-1]
        return (text[:o.start()] + text[c.end():]).strip(), text[o.end():c.start()], [_rec("final_answer", "tag_variant", text[o.start():o.end()], "<FINAL_ANSWER_JSON>")]
    opens = list(_OPEN_RE.finditer(text))
    if opens:
        o = opens[-1]
        return text[:o.start()].strip(), text[o.end():], [_rec("final_answer", "closing_tag_missing", text[o.start():][:60], "")]
    # untagged: the LAST top-level object (optionally fenced) that has every contract key after key normalisation
    for m in list(reversed(list(re.finditer(r"\{", text))))[:60]:
        cand = text[m.start():]
        try:
            obj, end = json.JSONDecoder().raw_decode(cand)
        except json.JSONDecodeError:
            try:
                obj, _ = loads_tolerant(_balance_closers(cand.split("```")[0]))
                end = len(cand.split("```")[0])
            except ValueError:
                continue
        if isinstance(obj, dict) and all(any(_canon_key(k, CONTRACT_KEYS) == req for k in obj) for req in REQUIRED_KEYS if req != "notes"):
            before = (text[:m.start()] + text[m.start() + end:])
            before = re.sub(r"```(?:json)?\s*```", "", before).strip()
            return before, cand[:end], [_rec("final_answer", "untagged_json", cand[:60], "")]
    return text.strip(), None, []


def _unwrap(obj: Any) -> tuple[Any, list[Recovery]]:
    if isinstance(obj, dict) and len(obj) == 1:
        (k, v), = obj.items()
        if isinstance(v, dict) and sum(1 for kk in v if _canon_key(kk, CONTRACT_KEYS)) >= len(REQUIRED_KEYS) - 1:
            return v, [_rec("final_answer", "wrapper_object_unwrapped", k, "")]
    return obj, []


_TRAIN_TOKEN = re.compile(r"BTB[0-9]{3}(?![0-9])")


def _train_from_string(v: str) -> str | None:
    s = digits_to_ascii(clean_text(v)).upper()
    compact = re.sub(r"[\s\-]", "", s.strip(" .,;:"))
    if re.fullmatch(r"BTB[0-9]{3}", compact):
        return compact
    toks = set(_TRAIN_TOKEN.findall(re.sub(r"(?<=BTB)[\s\-]+(?=\d)", "", s)))
    return toks.pop() if len(toks) == 1 else None


def _class_from_string(v: str) -> str | None:
    c = canon_class(digits_to_ascii(clean_text(v)).strip(" .,;:"))
    if c:
        return c
    toks = {t.upper() for t in re.findall(r"(?<![A-Za-z0-9])(3A|2A|SL|CC)(?![A-Za-z0-9])", digits_to_ascii(clean_text(v)), re.I)}
    return toks.pop() if len(toks) == 1 else None


_SEAT_UNITS = r"(?:seats?|trains?|सीट(?:ें|ें|ा)?|ट्रेन(?:ें)?|गाड्या|गाड़ियाँ|ગાડીઓ|ટ્રેન(?:ો)?|સીટ(?:ો)?|સીટે)"
_MINUTE_UNITS = r"(?:min(?:ute)?s?|मिनट|मिनिट(?:े|ं)?|મિનિટ)"
_RUPEE_UNITS = r"(?:rs\.?|inr|rupees?|रुपये|रुपए|रुपया|रुपयांचे|રૂપિયા)"


def _int_like(v: Any, units: str) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        m = re.fullmatch(r"\s*(\d+)(?:\.0+)?\s*(?:" + units + r")?\s*\.?\s*", digits_to_ascii(clean_text(v)), re.I)
        if m:
            return int(m.group(1))
    return None


_ABSENT = object()


def normalize_answer(obj: dict[str, Any]) -> tuple[dict[str, Any], list[Recovery]]:
    """Value-preserving normalisation of a parsed answer object (field shapes and spellings only)."""
    recs: list[Recovery] = []
    out: dict[str, Any] = {}
    for k, v in obj.items():
        ck = _canon_key(k, CONTRACT_KEYS)
        if ck is None or ck in out:
            out[k] = v
            continue
        if ck != k:
            recs.append(_rec("final_answer", "key_spelling", k, ck))
        out[ck] = v
    if "notes" not in out and all(k in out for k in REQUIRED_KEYS if k != "notes"):
        out["notes"] = ""
        recs.append(_rec("final_answer", "notes_defaulted", None, ""))
    st = out.get("status")
    if isinstance(st, str) and st not in STATUSES:
        c = re.sub(r"[\s\-]+", "_", st.strip().casefold()).strip("._!,;:\"'")
        if c in STATUSES:
            out["status"] = c
            recs.append(_rec("final_answer", "status_spelling", st, c))
    ids = out.get("booking_ids", _ABSENT)
    if ids is None:
        out["booking_ids"] = []
        recs.append(_rec("final_answer", "booking_ids_shape", None, []))
    elif isinstance(ids, str):
        parts = [p for p in re.split(r"[\s,;]+", ids.strip()) if p]
        if parts and all(canon_booking_id(digits_to_ascii(clean_text(p)).strip(".")) for p in parts):
            out["booking_ids"] = [canon_booking_id(digits_to_ascii(clean_text(p)).strip(".")) for p in parts]
            recs.append(_rec("final_answer", "booking_ids_shape", ids, out["booking_ids"]))
        elif ids.strip() == "":
            out["booking_ids"] = []
            recs.append(_rec("final_answer", "booking_ids_shape", ids, []))
    elif isinstance(ids, list):
        fixed = []
        for x in ids:
            c = canon_booking_id(digits_to_ascii(clean_text(x)).strip(".")) if isinstance(x, str) else None
            fixed.append(c if c and c != x else x)
        if fixed != ids:
            out["booking_ids"] = fixed
            recs.append(_rec("final_answer", "booking_ids_shape", ids, fixed))
    rp = out.get("requested_passengers", _ABSENT)
    if rp is None:
        out["requested_passengers"] = []
        recs.append(_rec("final_answer", "requested_passengers_shape", None, []))
    elif isinstance(rp, str) and rp.strip():
        out["requested_passengers"] = [rp.strip()]
        recs.append(_rec("final_answer", "requested_passengers_shape", rp, [rp.strip()]))
    elif isinstance(rp, str):
        out["requested_passengers"] = []
        recs.append(_rec("final_answer", "requested_passengers_shape", rp, []))
    sel = out.get("selected_train", _ABSENT)
    if isinstance(sel, str) and sel.strip() and not re.fullmatch(r"BTB[0-9]{3}", sel):
        t = _train_from_string(sel)
        if t:
            out["selected_train"] = t
            recs.append(_rec("final_answer", "selected_train_decoration", sel, t))
    elif isinstance(sel, list) and any(isinstance(x, str) and not re.fullmatch(r"BTB[0-9]{3}", x) for x in sel):
        fixed = [(_train_from_string(x) or x) if isinstance(x, str) else x for x in sel]
        if fixed != sel:
            out["selected_train"] = fixed
            recs.append(_rec("final_answer", "selected_train_decoration", sel, fixed))
    cls = out.get("selected_class", _ABSENT)
    if isinstance(cls, str) and cls.strip() and cls not in ("3A", "2A", "SL", "CC"):
        c = _class_from_string(cls)
        if c and c != cls:
            out["selected_class"] = c
            recs.append(_rec("final_answer", "selected_class_decoration", cls, c))
    av = out.get("answer_values")
    if isinstance(av, dict):
        fixed_av: dict[str, Any] = {}
        for k, v in av.items():
            ck = _canon_key(k, ANSWER_VALUE_KEYS)
            if ck and ck != k and ck not in av:
                recs.append(_rec("final_answer", "key_spelling", f"answer_values.{k}", ck))
                k = ck
            if k in ("seats_available", "seats_remaining_at_end", "train_count") and not (isinstance(v, int) and not isinstance(v, bool)):
                n = _int_like(v, _SEAT_UNITS)
                if n is not None:
                    recs.append(_rec("final_answer", "integer_form", v, n))
                    v = n
            elif k in ("tatkal_seats", "lower_berths", "upper_berths", "side_lower_berths", "platform", "coach_position") and isinstance(v, (float, str)):
                n = _int_like(v, _SEAT_UNITS)  # 20-tool stage: counts and numbers without a currency
                if n is not None:
                    recs.append(_rec("final_answer", "integer_form", v, n))
                    v = n
            elif k in ("waitlist_position", "refund_inr", "concession_fare_inr", "total_fare_inr",  # 3.0
                       "tatkal_fare_inr", "order_amount_inr", "fare_difference_inr", "tdr_refund_inr") and isinstance(v, (float, str)):
                n = _int_like(re.sub(r"^\s*(?:₹|rs\.?|inr)\s*", "", v.replace(",", ""), flags=re.I) if isinstance(v, str) else v, _RUPEE_UNITS)
                if n is not None:
                    recs.append(_rec("final_answer", "integer_form", v, n))
                    v = n
            elif k in ("duration_minutes", "delay_minutes") and isinstance(v, (float, str)):
                n = _int_like(v, _MINUTE_UNITS)
                if n is not None:
                    recs.append(_rec("final_answer", "integer_form", v, n))
                    v = n
            fixed_av[k] = v
        out["answer_values"] = fixed_av
    return out, recs


def parse_final_answer_lenient(final_text: str) -> dict[str, Any]:
    """Like final_answer.parse_final_answer plus format tolerance. Same result shape, plus "recoveries" (list of records).
    An unambiguous block is read; anything else stays an error exactly as in the strict parser."""
    text = final_text or ""
    recs: list[Recovery] = []
    text, r = strip_thinking(text)
    recs += r
    text = clean_text(text)
    natural, raw, r = _find_block(text)
    recs += r
    res: dict[str, Any] = {"ok": False, "error": None, "answer": None, "natural_text": natural, "raw_json": raw, "recoveries": recs}
    if raw is None:
        res["error"] = "missing_block"
        return res
    try:
        obj, rules = loads_tolerant(raw, allow_trailing=any(r["rule"] == "closing_tag_missing" for r in recs))
    except ValueError:
        res["error"] = "malformed_json: not repairable"
        return res
    recs += [_rec("final_answer", rule, raw, "") for rule in rules]
    obj, r = _unwrap(obj)
    recs += r
    if not isinstance(obj, dict):
        res["error"] = "not_an_object"
        return res
    obj, r = normalize_answer(obj)
    recs += r
    missing = [k for k in REQUIRED_KEYS if k not in obj]
    if missing:
        res["error"] = "missing_keys:" + ",".join(missing)
        res["answer"] = obj
        return res
    if obj.get("status") not in STATUSES:
        res["error"] = "invalid_status"
        res["answer"] = obj
        return res
    res.update(ok=True, answer=obj)
    return res


# ============================================================================================ lenient free-text readers
_MONTH_WORDS = r"(?:october|oct|अक्टूबर|ऑक्टोबर|अक्तूबर|ઓક્ટોબર|ઑક્ટોબર)"
_DAY_MARK = r"(?:st|nd|rd|th|वीं|वा|वी|तारीख(?:\s*को)?|तारखेला|तारखे|તારીખ|તા\.|મી|લી)?"


def times_in_lenient(text: str) -> set[str]:
    t = digits_to_ascii(clean_text(strip_thinking(text)[0]))
    out = set(times_in(t))
    for h, m in re.findall(r"(?<![\d:.])(\d{1,2}):(\d{2}):00(?![\d:])", t):
        if int(h) <= 23 and int(m) <= 59:
            out.add(f"{int(h):02d}:{int(m):02d}")
    for h, m in re.findall(r"(?<![\d:.])(\d{1,2})\s?h\s?(\d{2})(?!\d)", t, re.I):
        if int(h) <= 23 and int(m) <= 59:
            out.add(f"{int(h):02d}:{int(m):02d}")
    for h, m in re.findall(r"(?<![\d:.])(\d{1,2})\.(\d{2})\s*(?:hrs?\b|hours?\b|बजे|वाजता|વાગ્યે)", t, re.I):
        if int(h) <= 23 and int(m) <= 59:
            out.add(f"{int(h):02d}:{int(m):02d}")
    return out


def dates_in_lenient(text: str, default_year: int = 2026) -> set[str]:
    t = digits_to_ascii(clean_text(strip_thinking(text)[0]))
    out = set(dates_in(t, default_year))
    months = {"october": 10, "oct": 10, "अक्टूबर": 10, "ऑक्टोबर": 10, "अक्तूबर": 10, "ઓક્ટોબર": 10, "ઑક્ટોબર": 10}
    for d, y in re.findall(r"(?<!\d)(\d{1,2})\s*" + _DAY_MARK + r"\s*(?:of\s+)?" + _MONTH_WORDS + r"\.?(?:,?\s*(\d{4}))?", t, re.I):
        if 1 <= int(d) <= 31:
            out.add(f"{int(y) if y else default_year:04d}-10-{int(d):02d}")
    for d, y in re.findall(_MONTH_WORDS + r"\.?\s*(\d{1,2})" + _DAY_MARK + r"(?:,?\s*(\d{4}))?(?!\d)", t, re.I):
        if 1 <= int(d) <= 31:
            out.add(f"{int(y) if y else default_year:04d}-10-{int(d):02d}")
    for d, y in re.findall(r"(?<!\d)(\d{1,2})[-/ ]" + _MONTH_WORDS + r"[-/ ](\d{4})", t, re.I):
        out.add(f"{int(y):04d}-10-{int(d):02d}")
    for d, y in re.findall(r"(?<![\d.])(\d{1,2})\.10\.(\d{4})(?![\d.])", t):  # dd.mm.yyyy; month 10 is the only month of the benchmark
        out.add(f"{int(y):04d}-10-{int(d):02d}")
    return {d for d in out if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)}


def numbers_in_lenient(text: str) -> set[int]:
    t = digits_to_ascii(clean_text(strip_thinking(text)[0]))
    out = set(numbers_in(t))
    for g in re.findall(r"(?<![\w.:/-])(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:,\d{2,3})+|\d+)\s*/-", t, re.I):
        out.add(int(g.replace(",", "")))
    return out


# ============================================================================================ tool calls
def normalize_tool_name(name: Any, allowed: list[str] | tuple[str, ...] = TOOL_NAMES) -> tuple[Any, list[Recovery]]:
    """`Get_Fare`, `functions.get_fare`, ` get_fare`, `get_fare()` -> `get_fare`; anything else (get-fare, get_fares) unchanged."""
    if not isinstance(name, str) or name in allowed:
        return name, []
    c = clean_text(name).strip().casefold()
    c = re.sub(r"^(?:functions?|tools?)[./]", "", c)
    c = re.sub(r"\(\s*\)$", "", c).strip()
    if c in allowed:
        return c, [_rec("tool_call", "tool_name_spelling", name, c)]
    return name, []


def _ids_for_train(v: str) -> str | None:
    s = digits_to_ascii(clean_text(v))
    compact = re.sub(r"[\s\-]", "", s).upper()
    return compact if re.fullmatch(r"BTB[0-9]{3}", compact) else None


def _hhmm(v: Any) -> str | None:
    if not isinstance(v, str):
        return None
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*", digits_to_ascii(clean_text(v)))
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59 or (m.group(3) is not None and int(m.group(3)) > 59):
        return None
    return f"{int(m.group(1)):02d}:{m.group(2)}"


def normalize_arguments(tool: str, args: Any) -> tuple[Any, list[Recovery]]:
    """Format-only normalisation of tool arguments BEFORE env.call. Never renames a key, never repairs a value:
    train id case/space/digit script, class synonyms the scorer already knows, ISO date spelling (year first), time and
    time_window formats, a time_window given as a JSON string, trailing punctuation of a passenger name; then unknown EXTRA
    keys are dropped only if the remaining arguments are complete and valid for the tool."""
    from environment.schemas import TOOL_INPUT_MODELS
    if not isinstance(args, dict) or tool not in TOOL_INPUT_MODELS:
        return args, []
    recs: list[Recovery] = []
    out = dict(args)

    def change(key: str, new: Any, rule: str) -> None:
        if out.get(key) != new:
            recs.append(_rec("arguments", rule, out.get(key), new))
            out[key] = new

    tw = out.get("time_window")
    if isinstance(tw, str):
        try:
            parsed = json.loads(tw)
            if isinstance(parsed, dict):
                change("time_window", parsed, "args_json_string")
                tw = parsed
        except json.JSONDecodeError:
            pass
    if isinstance(tw, dict):
        fixed = dict(tw)
        for k in ("start", "end"):
            h = _hhmm(tw.get(k))
            if h is not None and h != tw.get(k):
                fixed[k] = h
        if fixed != tw:
            change("time_window", fixed, "time_format")
    if isinstance(out.get("train_id"), str):
        t = _ids_for_train(out["train_id"])
        if t and t != out["train_id"].strip():
            change("train_id", t, "train_id_spelling")
    if isinstance(out.get("travel_class"), str):
        raw = digits_to_ascii(clean_text(out["travel_class"]))
        key = re.sub(r"[\s\-_.()]", "", raw).upper()
        c = _CLASS_SYNONYMS.get(key)
        if c and c != out["travel_class"].strip().upper():
            change("travel_class", c, "class_spelling")
    if isinstance(out.get("date"), str):
        m = re.fullmatch(r"\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\s*", digits_to_ascii(clean_text(out["date"])))
        if m:
            iso = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            if iso != out["date"].strip():
                change("date", iso, "date_format")
    if isinstance(out.get("pnr"), str):                    # 3.0: '4518 203 967', '4518-203-967', native digits -> '4518203967'
        p = re.sub(r"[\s\-]", "", digits_to_ascii(clean_text(out["pnr"])))
        if re.fullmatch(r"\d{10}", p) and p != out["pnr"]:
            change("pnr", p, "pnr_format")
    elif isinstance(out.get("pnr"), int) and 0 <= out["pnr"] < 10**10:
        change("pnr", f"{out['pnr']:010d}", "pnr_format")
    if isinstance(out.get("passenger"), str):
        name = re.sub(r"\s+", " ", out["passenger"]).strip().rstrip(".,;")
        if name != re.sub(r"\s+", " ", out["passenger"]).strip():
            change("passenger", name, "passenger_punctuation")
    model = TOOL_INPUT_MODELS[tool]
    extra = [k for k in out if k not in model.model_fields]
    if extra:
        from pydantic import ValidationError
        kept = {k: v for k, v in out.items() if k in model.model_fields}
        try:
            model(**kept)
        except (ValidationError, TypeError):
            return out, recs                              # required keys missing/invalid: nothing is dropped, strict error stands
        recs.append(_rec("arguments", "extra_args_dropped", {k: out[k] for k in extra}, sorted(extra)))
        out = kept
    return out, recs


_SEGMENT_SPLIT = re.compile(r"(?<=[}\]\"\w])\s*;\s*(?=\{)|(?<=\})\s*\n\s*(?=\{)")


def extract_text_tool_calls(text: str, allowed: list[str] | tuple[str, ...] = TOOL_NAMES) -> tuple[list[dict[str, Any]] | None, list[Recovery]]:
    """If the WHOLE reply is one or more tool-call objects (`{"name": ..., "parameters"|"arguments": {...}}`, also OpenAI
    `{"function": {...}}`, optionally in <tool_call> tags or a code fence, separated by whitespace / ';'), return them
    [{"name", "arguments", "raw"}]. Prose around them, an unknown tool name or non-object arguments -> (None, []) (not recovered)."""
    t = clean_text(strip_thinking(text)[0]).strip()
    if not t:
        return None, []
    recs: list[Recovery] = []
    for pat in (r"<tool_call>(.*?)</tool_call>", r"```(?:json)?(.*?)```"):
        if re.search(pat, t, re.S):
            t = re.sub(pat, lambda m: m.group(1) + "\n", t, flags=re.S).strip()
    t = re.sub(r"</?tool_call>", "\n", t).strip()
    if not t.startswith("{"):
        return None, []
    segments = [s.strip() for s in _SEGMENT_SPLIT.split(t) if s.strip()]
    calls: list[dict[str, Any]] = []
    for seg in segments:
        try:
            obj, rules = loads_tolerant(seg)
        except ValueError:
            return None, []
        if not isinstance(obj, dict):
            return None, []
        fn = obj.get("function") if isinstance(obj.get("function"), dict) else obj
        name, args = fn.get("name"), fn.get("parameters", fn.get("arguments"))
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                return None, []
        name, nrecs = normalize_tool_name(name, allowed)
        if name not in allowed or not isinstance(args, dict):
            return None, []
        recs += [_rec("tool_call", r, seg, "") for r in rules] + nrecs
        calls.append({"name": name, "arguments": args, "raw": seg})
    if not calls:
        return None, []
    recs.insert(0, _rec("tool_call", "text_tool_call", text, [c["name"] for c in calls]))
    return calls, recs


def repair_arguments_json(raw: str) -> tuple[dict[str, Any] | None, list[Recovery]]:
    """A native call whose `arguments` string is not valid JSON: value-preserving repair (closers, trailing commas, literals)."""
    try:
        obj, rules = loads_tolerant(raw)
    except ValueError:
        return None, []
    if isinstance(obj, dict) and rules:
        return obj, [_rec("arguments", "args_json_repaired:" + "+".join(rules), raw, obj)]
    return None, []


# ============================================================================================ which text is the final reply
def final_text_from_turns(turns: list[dict[str, Any]]) -> tuple[str, list[Recovery]]:
    """The final reply is the LAST turn's text. An earlier turn's text is used only when every later turn was empty (no text, no
    tool call) - never when a tool call came after it. Each turn: {"text": str, "tool_calls": bool}."""
    if not turns:
        return "", []
    if turns[-1].get("text"):
        return turns[-1]["text"], []
    for i in range(len(turns) - 2, -1, -1):
        t = turns[i]
        if t.get("tool_calls"):
            return "", []                      # a tool call came after that text: it was not a final reply
        if t.get("text"):
            return t["text"], [_rec("final_text", "earlier_empty_turns_only", t["text"], "")]
    return "", []
