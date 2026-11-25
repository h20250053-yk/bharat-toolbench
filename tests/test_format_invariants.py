"""The guarantee of the format layer, over ALL 75 tasks x 5 languages (FORMAT_ROBUSTNESS.md):

  * a FORMAT change of a correct answer            -> the lenient score passes (and any rescue is recorded as a recovery)
  * the same FORMAT change + a WRONG decision/value -> the lenient score still fails, with a decision label
  * strict is never more generous than lenient, and nothing is rescued without a recorded recovery
"""
import json
import re

import pytest

from evaluation.final_answer import CLOSE, OPEN
from evaluation.scorer import ALTERNATIVE_OUTCOMES, STRUCTURED_VALUE_CHECKS, VALUE_CHECKS, score_both
from evaluation.selfcheck import execute, final_json, gold_calls, gold_for, ideal_result

TASKS = sorted(k for k in json.load(open("benchmark/gold_labels.json", encoding="utf-8")) if not k.startswith("_"))
LANGS = ["en", "hinglish", "hi", "mr", "gu"]
DIGITS = {"hi": "०१२३४५६७८९", "mr": "०१२३४५६७८९", "gu": "૦૧૨૩૪૫૬૭૮૯"}
MONTH = {"en": "October", "hinglish": "October", "hi": "अक्टूबर", "mr": "ऑक्टोबर", "gu": "ઓક્ટોબર"}
_CACHE: dict[str, tuple[dict, dict]] = {}


def ideal(tid):
    if tid not in _CACHE:
        _CACHE[tid] = ideal_result(tid)
    return _CACHE[tid]


def script_digits(text, lang):
    return text.translate(str.maketrans("0123456789", DIGITS[lang])) if lang in DIGITS else text


# ---------------------------------------------------------------------------------------------------- natural text variants
def fmt_value(kind, value, lang, variant):
    """The gold value written in a format variant (language-sensitive digits and month words)."""
    if kind == "number":
        n = int(value)
        s = [f"₹{n:,}", f"Rs {n}/-", f"INR {n}.00", f"{n}"][variant % 4]
    elif kind == "time":
        h, m = value.split(":")
        s = [f"{value}:00", f"{value}", f"{int(h)}h{m}", f"{value} hrs"][variant % 4]
    elif kind == "date":
        y, mo, d = value.split("-")
        s = [f"{int(d)}th {MONTH[lang]} {y}", f"{MONTH[lang]} {int(d)}, {y}", f"{int(d):02d}.{mo}.{y}", f"{int(d)} {MONTH[lang]}", value][variant % 5]
    else:
        s = str(value)
    return script_digits(s, lang)


def natural_for(tid, lang, variant, wrong=False):
    fa = gold_for(tid)["final_answer"]
    parts = []
    for key, kind in VALUE_CHECKS.get(tid, []):
        v = fa[key]
        if wrong:
            if kind == "number":
                v = int(v) + 7
            elif kind == "time":
                h, m = v.split(":")
                v = f"{(int(h) + 1) % 24:02d}:{m}"
            elif kind == "date":
                y, mo, d = v.split("-")
                v = f"{y}-{mo}-{int(d) + 1:02d}"
            elif kind == "time_list":
                v = [f"{(int(t[:2]) + 1) % 24:02d}{t[2:]}" for t in v]
            elif kind == "train_list":
                v = ["BTB199"] + list(v)[1:]
        if kind in ("time_list", "train_list"):
            parts.append(f"{key}: " + ", ".join(fmt_value("time" if kind == "time_list" else "train", x, lang, variant) for x in v))
        else:
            parts.append(f"{key}: {fmt_value(kind, v, lang, variant)}")
    return "Here is the result. " + "; ".join(parts) if parts else "Here is the result."


# ---------------------------------------------------------------------------------------------------- answer format perturbations
def block(obj, natural, tags=True, **_):
    return f"{natural}\n{OPEN}\n{json.dumps(obj, ensure_ascii=False)}\n{CLOSE}" if tags else f"{natural}\n{json.dumps(obj, ensure_ascii=False)}"


def with_obj(f):
    def wrap(obj, natural, lang):
        o = json.loads(json.dumps(obj))
        return f(o, natural, lang)
    return wrap


def p_exact(o, n, l):
    return block(o, n)


def p_no_close(o, n, l):
    return block(o, n).replace(CLOSE, "")


def p_lower_tags(o, n, l):
    return block(o, n).replace(OPEN, OPEN.lower()).replace(CLOSE, CLOSE.lower())


def p_spaced_tags(o, n, l):
    return block(o, n).replace(OPEN, "< FINAL_ANSWER_JSON >").replace(CLOSE, "</ FINAL_ANSWER_JSON >")


def p_untagged(o, n, l):
    return block(o, n, tags=False)


def p_fenced(o, n, l):
    return f"{n}\n```json\n{json.dumps(o, ensure_ascii=False)}\n```"


def p_trailing_comma(o, n, l):
    return block(o, n).replace("}\n" + CLOSE, ",}\n" + CLOSE, 1) if False else f"{n}\n{OPEN}\n{json.dumps(o, ensure_ascii=False)[:-1]},}}\n{CLOSE}"


def p_python_literal(o, n, l):
    return f"{n}\n{OPEN}\n{repr(o)}\n{CLOSE}"


def p_extra_brace_and_prose(o, n, l):
    return f"{n}\n{OPEN}\n{json.dumps(o, ensure_ascii=False)}}}\n{CLOSE}\nHope this helps!"


def p_status_case(o, n, l):
    o["status"] = o["status"].upper().replace("_", " ") if o["status"] != "success" else "Success"
    return block(o, n)


def p_shapes(o, n, l):
    if o.get("booking_ids"):
        o["booking_ids"] = ", ".join(x.lower() for x in o["booking_ids"])
    else:
        o["booking_ids"] = None
    if len(o.get("requested_passengers") or []) == 1:
        o["requested_passengers"] = o["requested_passengers"][0]
    elif not o.get("requested_passengers"):
        o["requested_passengers"] = None
    return block(o, n)


def p_decorated(o, n, l):
    if isinstance(o.get("selected_train"), str):
        o["selected_train"] = f"{o['selected_train'].lower()} (train)"
    elif isinstance(o.get("selected_train"), list):
        o["selected_train"] = [f"{t} ." for t in o["selected_train"]]
    if o.get("selected_class"):
        o["selected_class"] = f"{o['selected_class'].lower()} class"
    return block(o, n)


def p_keys(o, n, l):
    o = {k.upper(): v for k, v in o.items()}
    if isinstance(o.get("ANSWER_VALUES"), dict):
        o["ANSWER_VALUES"] = {k.upper(): v for k, v in o["ANSWER_VALUES"].items()}
    return block(o, n)


def p_notes_missing(o, n, l):
    o.pop("notes", None)
    return block(o, n)


def p_think_prefix(o, n, l):
    wrong = dict(o, status="cannot_complete" if o["status"] != "cannot_complete" else "success")
    return f"<think>draft: {OPEN}{json.dumps(wrong)}{CLOSE} and the fare might be 99999</think>\n" + block(o, n)


def p_bom_crlf(o, n, l):
    return "﻿" + block(o, n).replace("\n", "\r\n")


def p_wrapper(o, n, l):
    return f"{n}\n{OPEN}\n{json.dumps({'answer': o}, ensure_ascii=False)}\n{CLOSE}"


def p_int_forms(o, n, l):
    av = o.get("answer_values")
    if isinstance(av, dict):
        for k, v in list(av.items()):
            if isinstance(v, int) and not isinstance(v, bool) and k != "duration_minutes":
                av[k] = f"{v} seats" if k.startswith("seats") else float(v)
            elif k == "duration_minutes" and isinstance(v, int):
                av[k] = float(v)
    return block(o, n)


def p_script_digits_in_ids(o, n, l):
    if isinstance(o.get("selected_train"), str):
        o["selected_train"] = script_digits(o["selected_train"], l)
    if o.get("booking_ids"):
        o["booking_ids"] = [script_digits(b, l) for b in o["booking_ids"]]
    return block(o, n)


FORMATS = [p_exact, p_no_close, p_lower_tags, p_spaced_tags, p_untagged, p_fenced, p_trailing_comma, p_python_literal, p_extra_brace_and_prose,
           p_status_case, p_shapes, p_decorated, p_keys, p_notes_missing, p_think_prefix, p_bom_crlf, p_wrapper, p_int_forms, p_script_digits_in_ids]


def score_text(tid, lang, text):
    row, snap = ideal(tid)
    r = {**row, "language": lang, "task_id": f"{tid}_{lang}", "final_text": text}
    return score_both(r, gold_for(tid), snap)


def correct_obj(tid):
    row, snap = ideal(tid)
    return final_json(tid, snap)


# ---------------------------------------------------------------------------------------------------- wrong decisions
def wrong_variants(tid):
    """(label, obj mutator, expected label prefix) wrong DECISIONS for this task."""
    g = gold_for(tid)
    wrong_status = "cannot_complete" if g["final_state"]["status"] != "cannot_complete" else "success"
    alt = ALTERNATIVE_OUTCOMES.get(tid, {}).get("final_state", {}).get("status")
    # a status that the spec accepts as an alternative outcome (T82: 'already cancelled' as success) is not a wrong decision
    out = [] if wrong_status == alt else [("status", lambda o: o.update(status=wrong_status), "status:")]
    if g["final_state"]["status"] == "success":
        if g["final_state"].get("allowed_train_ids") or any(k in g["final_answer"] for k in ("first_leg_train_id", "outbound_train_id")):
            out.append(("train", lambda o: o.update(selected_train="BTB199"), "final_answer:"))
        if g["final_state"].get("travel_class"):
            out.append(("class", lambda o: o.update(selected_class="SL" if g["final_state"]["travel_class"] != "SL" else "CC"), "final_answer:wrong_selected_class"))
        if g["final_state"].get("expected_bookings"):
            out.append(("booking", lambda o: o.update(booking_ids=["BK9999"]), "final_answer:booking_ids"))
    for gold_key, key, kind in STRUCTURED_VALUE_CHECKS.get(tid, []):
        def mut(o, key=key):
            v = o["answer_values"][key]
            o["answer_values"][key] = (not v) if isinstance(v, bool) else v + 3 if isinstance(v, int) else (["MON"] if "TUE" in str(v) else ["XX"]) if isinstance(v, list) else str(v) + "x"
        out.append((f"value:{key}", mut, "answer_value:"))
    return out


@pytest.mark.parametrize("tid", TASKS)
def test_format_changes_of_a_correct_answer_pass_and_every_rescue_is_recorded(tid):
    for lang in LANGS:
        for i, fmt in enumerate(FORMATS):
            natural = natural_for(tid, lang, variant=i)
            lenient, strict = score_text(tid, lang, fmt(json.loads(json.dumps(correct_obj(tid))), natural, lang))
            assert lenient["task_success"] is True, (tid, lang, fmt.__name__, lenient["failure_labels"])
            if strict["task_success"] is not True:        # a rescue must be recorded; nothing is rescued silently
                assert lenient["lenient_used"] and lenient["format_recoveries"], (tid, lang, fmt.__name__)
            else:
                assert strict["task_success"] is True


@pytest.mark.parametrize("tid", TASKS)
def test_format_change_plus_wrong_decision_still_fails(tid):
    for label, mutate, prefix in wrong_variants(tid):
        for lang in LANGS:
            for i, fmt in enumerate(FORMATS):
                obj = json.loads(json.dumps(correct_obj(tid)))
                mutate(obj)
                lenient, strict = score_text(tid, lang, fmt(obj, natural_for(tid, lang, variant=i), lang))
                assert lenient["task_success"] is False, (tid, lang, label, fmt.__name__)
                assert any(l.startswith(prefix) for l in lenient["failure_labels"]), (tid, lang, label, fmt.__name__, lenient["failure_labels"])
                assert strict["task_success"] is False


@pytest.mark.parametrize("tid", [t for t in TASKS if VALUE_CHECKS.get(t)])
def test_free_text_value_formats_pass_and_wrong_values_fail_in_every_language(tid):
    obj = correct_obj(tid)
    for lang in LANGS:
        for variant in range(5):
            ok_l, _ = score_text(tid, lang, block(json.loads(json.dumps(obj)), natural_for(tid, lang, variant), tags=True))
            assert ok_l["task_success"] is True, (tid, lang, variant, ok_l["failure_labels"])
            bad_l, bad_s = score_text(tid, lang, block(json.loads(json.dumps(obj)), natural_for(tid, lang, variant, wrong=True)))
            assert bad_l["task_success"] is False and any(l.startswith("value:") for l in bad_l["failure_labels"]), (tid, lang, variant)
            assert bad_s["task_success"] is False


def test_thinking_text_does_not_satisfy_a_value_check_or_supply_an_answer():
    tid = "T01"
    fa = gold_for(tid)["final_answer"]
    obj = correct_obj(tid)
    lenient, strict = score_text(tid, "en", f"<think>the fare is {fa['fare_inr']}</think>\n" + block(obj, "Done."))
    assert lenient["task_success"] is False and any(l.startswith("value:") for l in lenient["failure_labels"])
    lenient, _ = score_text(tid, "en", f"<think>{OPEN}{json.dumps(obj)}{CLOSE}</think>")
    assert lenient["task_success"] is False and "final_answer:missing_block" in lenient["failure_labels"]


def test_a_strict_exact_answer_has_no_recovery_and_equal_scores():
    for tid in TASKS[:10]:
        lenient, strict = score_text(tid, "en", block(correct_obj(tid), natural_for(tid, "en", 3)))
        assert lenient["task_success"] and strict["task_success"] and not lenient["lenient_used"] and lenient["format_recoveries"] == []


def test_strict_score_equals_the_original_scorer():
    from evaluation.scorer import score
    for tid in TASKS:
        row, snap = ideal(tid)
        bad = {**row, "final_text": row["final_text"].replace(CLOSE, "")}
        _, strict = score_both(bad, gold_for(tid), snap)
        assert strict["task_success"] == score(bad, gold_for(tid), snap)["task_success"] is False
