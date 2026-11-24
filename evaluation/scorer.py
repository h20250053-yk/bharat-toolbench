"""Model-independent programmatic scorer for BharatToolBench trajectories (no LLM judge).

Order (plan section 15): (1) run status -> (2) structured final answer -> (3) environment state ->
(4) explicit free-text values (only where the task requires a value that has no structured field) ->
(5) tool process (required calls, allowed argument alternatives, documented equivalent observations,
dependency order, prohibitions).

task_success = outcome_success AND process_success.  Rows that never produced a model answer because of a
provider/harness failure are NOT scored (task_success = None) so they can be re-run (plan: provider_error is
re-run, never scored 0). Malformed model output and step-limit overruns ARE model failures (task_success = False).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .canonical import (canon_bool, canon_booking_id, canon_class, canon_class_set, canon_duration_minutes, canon_int,
                        canon_passenger, canon_station_name, canon_tool_args, canon_train_ids, canon_weekday_set,
                        dates_in, numbers_in, station_codes_in, times_in)
from .final_answer import parse_final_answer
from .tolerance import (clean_text, dates_in_lenient, digits_to_ascii, numbers_in_lenient, parse_final_answer_lenient, strip_thinking,
                        times_in_lenient)

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "benchmark" / "semantic_tasks.json"

NOT_SCORED_STATUSES = {"provider_error", "runner_error"}
MODEL_FAILURE_STATUSES = {"malformed_output", "step_limit_exceeded", "context_overflow", "output_truncated"}

# --------------------------------------------------------------------------------------------- explicit tables
# Free-text value checks. ONLY values that (a) the task's final_answer_requirements.must_state names and (b) the
# structured contract has no field for. Values are read from gold final_answer (never typed here).
# (Small counts and seat numbers moved to STRUCTURED_VALUE_CHECKS in audit I-11: a number in prose proves nothing.)
VALUE_CHECKS: dict[str, list[tuple[str, str]]] = {
    "T01": [("fare_inr", "number")],
    "T02": [("fare_inr", "number")],
    "T03": [("fare_inr", "number")],
    "T04": [("fare_inr", "number")],
    "T07": [("stop_arrival_time", "time")],
    "T08": [("departure", "time")],
    "T12": [("departure", "time"), ("arrival", "time")],
    "T14": [("fare_inr", "number")],
    "T17": [("segment_distance_km", "number")],
    "T31": [("departure", "time")],
    "T35": [("resolved_date", "date")],
    "T44": [("arrival", "time"), ("arrival_date", "date")],
    # batch T51-T75
    "T51": [("departure", "time")],
    "T52": [("arrival", "time")],
    "T53": [("fare_difference_inr", "number")],
    "T55": [("arrival", "time"), ("seats_available", "number")],
    "T56": [("selected_train_ids", "train_list"), ("departure_times", "time_list")],
    "T57": [("resolved_date", "date"), ("departure", "time")],
    "T59": [("fare_inr", "number")],
    "T60": [("fare_inr", "number")],
    "T62": [("fare_inr", "number")],
    "T64": [("fare_inr", "number")],
    "T65": [("departure", "time")],
    "T66": [("resolved_date", "date")],
    "T68": [("total_fare_inr", "number")],
}
# Structured value checks: requested facts the contract asks the model to copy from tool results into
# answer_values (language-neutral, and tied to selected_train, so a value can never be credited to the wrong train or
# found 'somewhere in the text'). (gold final_answer key, answer_values key, comparison kind). Each entry is a value the
# task's must_state requires; expected values are read from gold final_answer (derived from the environment).
STRUCTURED_VALUE_CHECKS: dict[str, list[tuple[str, str, str]]] = {
    "T06": [("operating_days", "operating_days", "weekday_set"), ("runs_on_requested_weekday", "runs_on_requested_day", "bool")],
    "T11": [("offered_classes", "classes", "class_set")],
    "T16": [("station_code", "station_code", "code"), ("station_name", "station_name", "station_name")],
    "T34": [("duration_minutes", "duration_minutes", "duration"), ("seats_available", "seats_available", "int")],
    # audit I-11: small integers (2, 4, 0, 17) matched any unrelated number in the prose, so they are structured now
    "T02": [("seats_available", "seats_available", "int")],
    "T26": [("seats_available", "seats_available", "int")],
    "T50": [("seats_remaining_at_end", "seats_remaining_at_end", "int")],
    "T51": [("train_count", "train_count", "int")],
    "T58": [("seats_available", "seats_available", "int")],  # asked about BTB117 CC, not about the booked train
}
_STRUCTURED_CANON = {
    "weekday_set": lambda v: canon_weekday_set(v),
    "bool": canon_bool,
    "class_set": lambda v: canon_class_set(v),
    "code": lambda v: v.strip().upper() if isinstance(v, str) and v.strip() else None,
    "station_name": canon_station_name,
    "duration": canon_duration_minutes,
    "int": canon_int,
}

# Equivalent observations documented in the task specs (final_answer_requirements.equivalent_observations).
# Each entry: alternatives for one gold call; an alternative is a list of conditions that must ALL be met by
# distinct trajectory calls. Encoded verbatim from the spec text; nothing is inferred.
EQUIVALENT_PATHS: dict[tuple[str, str], list[list[dict[str, Any]]]] = {
    # "A rejected book_ticket(BTB101, 2A) returning SOLD_OUT grounds the fallback as well as check_availability"
    ("T10", "c1"): [[{"tool": "book_ticket", "args": {"train_id": "BTB101", "travel_class": "2A"}, "error": "SOLD_OUT"}]],
    ("T22", "c4"): [[{"tool": "book_ticket", "args": {"train_id": "BTB101", "travel_class": "2A"}, "error": "SOLD_OUT"}]],
    ("T38", "c1"): [[{"tool": "book_ticket", "args": {"train_id": "BTB103", "travel_class": "3A"}, "error": "SOLD_OUT"}]],
    # "A search Ahmedabad->Jaipur on 2026-10-09 that does not list BTB107 also grounds the conflict."
    ("T21", "c1"): [[{"tool": "search_trains", "args": {"source": "ADI", "destination": "JP", "date": "2026-10-09"}, "lacks_train": "BTB107"}]],
    # "A search NDLS->LKO on 2026-10-07 that does not list BTB111 also grounds the decision."
    ("T39", "c1"): [[{"tool": "search_trains", "args": {"source": "NDLS", "destination": "LKO", "date": "2026-10-07"}, "lacks_train": "BTB111"}]],
    # "Searching NDLS->JP and NZM->JP on 2026-10-09 and finding BTB129 only from NZM resolves the station equally well."
    ("T47", "c2"): [[{"tool": "search_trains", "args": {"source": "NZM", "destination": "JP", "date": "2026-10-09"}, "has_train": "BTB129"},
                     {"tool": "search_trains", "args": {"source": "NDLS", "destination": "JP", "date": "2026-10-09"}, "lacks_train": "BTB129"}]],
    # "A rejected book_ticket(BTB101, 2A) returning SOLD_OUT grounds the fallback as well as check_availability."
    ("T73", "c1"): [[{"tool": "book_ticket", "args": {"train_id": "BTB101", "travel_class": "2A"}, "error": "SOLD_OUT"}]],
    # "A search New Delhi->Jaipur on 2026-10-09 listing BTB105 with classes ['CC'] shows the offered class as well as get_train_details."
    ("T75", "c2"): [[{"tool": "search_trains", "args": {"source": "NDLS", "destination": "JP", "date": "2026-10-09"}, "has_train": "BTB105"}]],
}


# Alternative OUTCOMES documented in the task specs (final_answer_requirements.accepted_alternative_outcomes): a second,
# complete gold final state that is also correct. Scored with exactly the same rules as the main gold; a row passes if it
# passes either one. Encoded verbatim from the spec text; nothing is inferred.
ALTERNATIVE_OUTCOMES: dict[str, dict[str, Any]] = {
    # "needs_clarification with NO booking: asking whether 'Anjali Rao' was listed twice by mistake ... is also correct."
    "T71": {"final_state": {"status": "needs_clarification", "allowed_train_ids": None, "travel_class": None, "expected_bookings": []},
            "required_calls": [], "dependency_edges": [], "final_answer": {}},
}


def _load_specs() -> dict[str, dict[str, Any]]:
    data = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    return {t["semantic_task_id"]: t for t in data["tasks"]}


_SPECS: dict[str, dict[str, Any]] | None = None


def spec_for(tid: str) -> dict[str, Any]:
    global _SPECS
    if _SPECS is None:
        _SPECS = _load_specs()
    return _SPECS[tid]


def requested_passengers(spec: dict[str, Any]) -> list[str]:
    """Passenger names given in the user's request, from the task spec parameters."""
    p = spec["solver"]["params"]
    names: list[str] = []
    if isinstance(p.get("passenger"), str):
        names.append(p["passenger"])
    names += list(p.get("passengers", []) or [])
    if isinstance(p.get("second_passenger"), str):
        names.append(p["second_passenger"])
    names += [a["passenger"] for a in p.get("assignments", []) or []]
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if canon_passenger(n) not in seen:
            seen.add(canon_passenger(n))
            out.append(n)
    return out


def accepted_passenger_forms(spec: dict[str, Any], language: str | None) -> dict[str, str]:
    """canonical passenger form written in that language's query -> canonical Latin name (spec).
    Only tasks that declare `passenger_script_forms` (T54: the user writes the name in native script) have any;
    the Latin form always stays accepted, the language's own written form is accepted additionally."""
    p = spec["solver"]["params"]
    native = (p.get("passenger_script_forms") or {}).get(language or "")
    latin = p.get("passenger")
    if native and isinstance(latin, str):
        return {canon_passenger(native): canon_passenger(latin)}
    return {}


# --------------------------------------------------------------------------------------------- process checks
def _tool_calls(trajectory: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    """(position, event) for executed tool calls; malformed / not-allowed events are excluded."""
    return [(i, e) for i, e in enumerate(trajectory) if e.get("event", "tool_call") == "tool_call"]


def _get_path(root: Any, path: str) -> Any:
    cur = root
    for piece in path.split("."):
        if piece.endswith("[*]"):
            cur = cur.get(piece[:-3], []) if isinstance(cur, dict) else []
            if not isinstance(cur, list):
                return []
        elif isinstance(cur, list):
            cur = [x[piece] for x in cur if isinstance(x, dict) and piece in x]
        elif isinstance(cur, dict):
            cur = cur.get(piece)
        else:
            return None
    return cur


def _matcher_ok(expected: dict[str, Any], obs: dict[str, Any]) -> bool:
    data = obs.get("data") or {}
    cands = sorted(c.get("code") for c in data.get("candidates", []) or [])
    if "resolves_to" in expected:
        return obs.get("ok") is True and cands == [expected["resolves_to"]]
    if "resolves_ambiguous" in expected:
        return obs.get("ok") is True and bool(data.get("ambiguous")) and cands == sorted(expected["resolves_ambiguous"])
    if "resolves_to_none" in expected:
        return (obs.get("error") or {}).get("code") == "STATION_NOT_FOUND"
    return False


_ABSENT = object()
_MATCHER_KEYS = ("resolves_to", "resolves_ambiguous", "resolves_to_none")


def _value_ok(actual: Any, accepted: list[Any]) -> bool:
    for exp in accepted:
        if exp is None and (actual is _ABSENT or actual is None):
            return True
        if exp is not None and actual is not _ABSENT and actual == exp:
            return True
    return False


def _call_matches(event: dict[str, Any], gold_call: dict[str, Any], matched_obs: dict[str, dict[str, Any]]) -> bool:
    if event.get("tool") != gold_call["tool"]:
        return False
    tool = event["tool"]
    obs = event.get("observation") or {}
    actual = canon_tool_args(tool, event.get("arguments") or {})
    alts = gold_call.get("arg_alternatives") or {}
    for key, expected in gold_call.get("required_args", {}).items():
        if isinstance(expected, dict) and any(k in expected for k in _MATCHER_KEYS):
            if key not in actual or not _matcher_ok(expected, obs):
                return False
            continue
        accepted = [canon_tool_args(tool, {key: expected})[key]]
        # allowed argument alternatives from gold (None = the argument may be omitted)
        accepted += [None if a is None else canon_tool_args(tool, {key: a})[key] for a in alts.get(key, [])]
        if not _value_ok(actual.get(key, _ABSENT), accepted):
            return False
    for arg, ref in (gold_call.get("args_from") or {}).items():
        src_id, path = ref.split(".", 1)
        if src_id not in matched_obs:
            return False
        vals = _get_path(matched_obs[src_id].get("data") or {}, path)
        vals = vals if isinstance(vals, list) else [vals]
        if actual.get(arg) not in [canon_tool_args(tool, {arg: v})[arg] for v in vals]:
            return False
    if gold_call.get("expected_error"):
        return (obs.get("error") or {}).get("code") == gold_call["expected_error"]
    return obs.get("ok") is True


def _condition_met(event: dict[str, Any], cond: dict[str, Any]) -> bool:
    if event.get("tool") != cond["tool"]:
        return False
    actual = canon_tool_args(event["tool"], event.get("arguments") or {})
    want = canon_tool_args(cond["tool"], cond["args"])
    if any(actual.get(k) != v for k, v in want.items()):
        return False
    obs = event.get("observation") or {}
    if "error" in cond:
        return (obs.get("error") or {}).get("code") == cond["error"]
    if obs.get("ok") is not True:
        return False
    ids = [t.get("train_id") for t in ((obs.get("data") or {}).get("trains") or [])]
    if "lacks_train" in cond and cond["lacks_train"] in ids:
        return False
    if "has_train" in cond and cond["has_train"] not in ids:
        return False
    return True


def _match_required(tid: str, gold: dict[str, Any], trajectory: list[dict[str, Any]]):
    calls = _tool_calls(trajectory)
    used: set[int] = set()
    matched: dict[str, int] = {}
    matched_obs: dict[str, dict[str, Any]] = {}
    via_equivalence: list[str] = []
    missing: list[str] = []
    for g in gold.get("required_calls", []):
        if g.get("optional"):
            continue
        hit = next((pos for pos, ev in calls if pos not in used and _call_matches(ev, g, matched_obs)), None)
        if hit is not None:
            used.add(hit)
            matched_obs[g["call_id"]] = trajectory[hit].get("observation") or {}
        else:
            for alt in EQUIVALENT_PATHS.get((tid, g["call_id"]), []):
                chosen: list[int] = []
                for cond in alt:
                    pos = next((p for p, ev in calls if p not in used and p not in chosen and _condition_met(ev, cond)), None)
                    if pos is None:
                        chosen = []
                        break
                    chosen.append(pos)
                if chosen:
                    used.update(chosen)
                    hit = max(chosen)
                    via_equivalence.append(g["call_id"])
                    break
        if hit is None:
            missing.append(f"{g['call_id']}:{g['tool']}")
        else:
            matched[g["call_id"]] = hit
    return matched, missing, via_equivalence


def _dependency_violations(gold: dict[str, Any], matched: dict[str, int]) -> list[str]:
    return [f"{e['before']}->{e['after']}" for e in gold.get("dependency_edges", [])
            if e["before"] in matched and e["after"] in matched and matched[e["before"]] >= matched[e["after"]]]


def _prohibition_violations(gold: dict[str, Any], trajectory: list[dict[str, Any]]) -> list[str]:
    out = []
    for p in gold.get("prohibited_actions", []):
        want = canon_tool_args(p["tool"], p.get("match") or {})
        for _, ev in _tool_calls(trajectory):
            if ev.get("tool") == p["tool"]:
                actual = canon_tool_args(ev["tool"], ev.get("arguments") or {})
                if all(actual.get(k) == v for k, v in want.items()):
                    out.append(f"{p['tool']}:{p.get('prompt_phrase', '')}")
    return out


# --------------------------------------------------------------------------------------------- outcome checks
def _booking_key(b: dict[str, Any]) -> tuple[str, str, str]:
    return (b["train_id"], b["travel_class"], canon_passenger(b["passenger"]) or "")


def _value_found(kind: str, value: Any, text: str, lenient: bool = False) -> bool:
    if lenient:  # same checks on the thinking-stripped, normalised text with the format-tolerant readers (FORMAT_ROBUSTNESS.md)
        text = digits_to_ascii(clean_text(strip_thinking(text)[0]))
        if kind == "number":
            return int(value) in numbers_in_lenient(text)
        if kind == "time":
            return value in times_in_lenient(text)
        if kind == "date":
            return value in dates_in_lenient(text)
        if kind == "time_list":
            return all(v in times_in_lenient(text) for v in value)
        if kind == "train_list":
            return set(value) <= set(re.findall(r"\bBTB[0-9]{3}\b", text.upper()))
    if kind == "number":
        return int(value) in numbers_in(text)
    if kind == "time":
        return value in times_in(text)
    if kind == "date":
        return value in dates_in(text)
    if kind == "station_code":
        return value in station_codes_in(text)
    if kind == "time_list":  # every listed time must be stated (T56)
        return all(v in times_in(text) for v in value)
    if kind == "train_list":  # every listed train id must be stated (T56)
        return set(value) <= set(re.findall(r"\bBTB\d{3}\b", text.upper()))
    raise ValueError(kind)


def _outcome(tid: str, gold: dict[str, Any], spec: dict[str, Any], final_text: str,
             snapshot: dict[str, Any], language: str | None = None, lenient: bool = False) -> tuple[dict[str, Any], list[str]]:
    fails: list[str] = []
    fs, fa = gold["final_state"], gold.get("final_answer", {})
    parsed = parse_final_answer_lenient(final_text) if lenient else parse_final_answer(final_text)
    info: dict[str, Any] = {"final_answer_parse": parsed["error"] or "ok", "natural_text_present": bool(parsed["natural_text"]),
                            "final_answer_recoveries": parsed.get("recoveries", [])}
    # environment state is authoritative and order-independent (multiset of train, class, passenger)
    actual = list(snapshot.get("bookings", []))
    info["state_success"] = Counter(map(_booking_key, actual)) == Counter(map(_booking_key, fs.get("expected_bookings", [])))
    if not info["state_success"]:
        fails.append("state:bookings_mismatch")
    if not parsed["ok"]:
        kind = parsed["error"].split(":")[0]
        fails.append(f"final_answer:{kind}")
        info["status_correct"] = False
        return info, fails
    ans = parsed["answer"]
    info["status_correct"] = ans["status"] == fs["status"]
    if not info["status_correct"]:
        fails.append(f"status:expected_{fs['status']}_got_{ans['status']}")
    # booking_ids: exactly the bookings created in the environment (mentioning an id in prose is irrelevant)
    raw_ids = ans.get("booking_ids")
    if not isinstance(raw_ids, list) or any(canon_booking_id(x) is None for x in raw_ids):
        fails.append("final_answer:booking_ids_invalid")
    elif {canon_booking_id(x) for x in raw_ids} != {b["booking_id"] for b in actual}:
        fails.append("final_answer:booking_ids_do_not_match_state")
    trains = canon_train_ids(ans.get("selected_train"))
    if trains is None:
        fails.append("final_answer:selected_train_invalid")
    if fs["status"] == "success" and info["status_correct"]:
        allowed = fs.get("allowed_train_ids")
        legs = [fa[k] for k in ("first_leg_train_id", "second_leg_train_id") if k in fa]
        round_trip = [fa[k] for k in ("outbound_train_id", "return_train_id") if k in fa]
        if trains is not None:
            if allowed and (not trains or not set(trains) <= set(allowed)):
                fails.append(f"final_answer:wrong_selected_train:{trains}")
            elif not allowed and legs and trains != legs:
                fails.append(f"final_answer:wrong_selected_trains:{trains}_expected_{legs}")
            elif not allowed and round_trip and trains != round_trip:
                fails.append(f"final_answer:wrong_selected_trains:{trains}_expected_{round_trip}")
        if fs.get("travel_class") and canon_class(ans.get("selected_class")) != fs["travel_class"]:
            fails.append(f"final_answer:wrong_selected_class:{ans.get('selected_class')}")
        if fs.get("expected_bookings"):
            req = ans.get("requested_passengers")
            want = {canon_passenger(n) for n in requested_passengers(spec)}
            forms = accepted_passenger_forms(spec, language)  # the name as written in this language's query is accepted too
            got = {forms.get(canon_passenger(x), canon_passenger(x)) for x in (req if isinstance(req, list) else []) if isinstance(x, str)}
            if not isinstance(req, list) or got != want:
                fails.append("final_answer:wrong_requested_passengers")
        for key, kind in VALUE_CHECKS.get(tid, []):
            if not _value_found(kind, fa[key], final_text or "", lenient):
                fails.append(f"value:{key}={fa[key]}_not_stated")
            elif lenient and not _value_found(kind, fa[key], final_text or "", False):   # only the format-tolerant reader found it: record it
                info["final_answer_recoveries"] = list(info["final_answer_recoveries"]) + [
                    {"stage": "final_answer", "rule": f"value_format:{kind}", "before": key, "after": str(fa[key])}]
    if info["status_correct"] and tid in STRUCTURED_VALUE_CHECKS:
        fails += _structured_value_failures(tid, fa, ans.get("answer_values"))
    return info, fails


def _structured_value_failures(tid: str, fa: dict[str, Any], values: Any) -> list[str]:
    if values is None:
        values = {}
    if not isinstance(values, dict):
        return ["answer_value:not_an_object"]
    out = []
    for gold_key, key, kind in STRUCTURED_VALUE_CHECKS[tid]:
        if key not in values:
            out.append(f"answer_value:missing:{key}")
            continue
        canon = _STRUCTURED_CANON[kind]
        got, want = canon(values[key]), canon(fa[gold_key])
        if got is None:
            out.append(f"answer_value:invalid:{key}")
        elif got != want:
            out.append(f"answer_value:wrong:{key}")
    return out


# --------------------------------------------------------------------------------------------- entry point
def score(result: dict[str, Any], gold: dict[str, Any], final_snapshot: dict[str, Any] | None = None,
          spec: dict[str, Any] | None = None, lenient: bool = False) -> dict[str, Any]:
    """Strict by default (the original scorer, byte-identical). lenient=True reads the final reply with evaluation/tolerance.py
    (format recovery only) and reports the final-answer recoveries it used in `format_recoveries`."""
    out = _score_one(result, gold, final_snapshot, spec, lenient)
    alt = ALTERNATIVE_OUTCOMES.get(result["semantic_task_id"])
    if alt and out.get("scored") and not out["task_success"]:
        alt_out = _score_one(result, {**gold, **alt, "min_calls": 0}, final_snapshot, spec, lenient)
        if alt_out["task_success"]:
            return {**alt_out, "accepted_via_alternative_outcome": alt["final_state"]["status"]}
    return out


def _score_one(result: dict[str, Any], gold: dict[str, Any], final_snapshot: dict[str, Any] | None = None,
               spec: dict[str, Any] | None = None, lenient: bool = False) -> dict[str, Any]:
    tid = result["semantic_task_id"]
    spec = spec or spec_for(tid)
    status = result.get("status", "completed")
    snapshot = final_snapshot if final_snapshot is not None else result.get("state_snapshot", {"bookings": []})
    traj = result.get("trajectory", [])
    base = {"run_status": status, "gold_status": gold["final_state"]["status"],
            "malformed_tool_calls": sum(1 for e in traj if e.get("event") == "malformed_tool_call"),
            "observed_tool_calls": len(_tool_calls(traj)),
            "required_nonoptional_calls": sum(1 for c in gold.get("required_calls", []) if not c.get("optional"))}
    if status in NOT_SCORED_STATUSES:
        return {**base, "scored": False, "task_success": None, "failure_labels": [f"not_scored:{status}"]}
    matched, missing, via_eq = _match_required(tid, gold, traj)
    deps = _dependency_violations(gold, matched)
    prohib = _prohibition_violations(gold, traj)
    disallowed = [e.get("tool") for e in traj if e.get("event") == "tool_not_allowed"]
    process_fails = ([f"process:missing_required_call:{m}" for m in missing]
                     + [f"process:dependency_violation:{d}" for d in deps]
                     + [f"process:prohibited_action:{p}" for p in prohib]
                     + [f"process:tool_not_allowed:{t}" for t in disallowed])
    info, outcome_fails = _outcome(tid, gold, spec, result.get("final_text", ""), snapshot, result.get("language"), lenient)
    if status in MODEL_FAILURE_STATUSES:
        outcome_fails = [f"run:{status}"] + outcome_fails
    labels = outcome_fails + process_fails
    return {**base, "scored": True, "task_success": not labels,
            "outcome_success": not outcome_fails, "process_success": not process_fails,
            "status_correct": info.get("status_correct", False), "state_success": info.get("state_success", False),
            "final_answer_parse": info.get("final_answer_parse"), "natural_text_present": info.get("natural_text_present", False),
            "matched_required_calls": len(matched), "satisfied_via_equivalent_observation": via_eq,
            "missing_required_calls": missing, "dependency_violations": deps, "prohibition_violations": prohib,
            "failure_labels": labels,
            **({"final_answer_recoveries": info.get("final_answer_recoveries", [])} if lenient else {})}


STRICT_LOWER_BOUND_STAGES = ("tool_call", "arguments", "final_text")


def score_both(result: dict[str, Any], gold: dict[str, Any], final_snapshot: dict[str, Any] | None = None,
               spec: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """(lenient score = the headline, strict score = sensitivity), from the same run.

    lenient: the scorer after the recorded format recoveries (run-time ones in result["format_recoveries"], final-answer ones found
    while reading the reply). strict: the original scorer on the raw reply. A recovery that happened DURING the item (a text tool call
    executed, arguments normalised, a final text taken from another turn) changed what the model saw next, which a strict harness would
    not have done; for those items the strict result is task_success AND no such recovery (a lower bound of a real strict re-run, equal to
    it whenever nothing was recovered). Final-answer-only recoveries leave the trajectory untouched, so strict is exact for them."""
    lenient = score(result, gold, final_snapshot, spec, lenient=True)
    strict = score(result, gold, final_snapshot, spec, lenient=False)
    runtime = list(result.get("format_recoveries") or [])
    final_recs = list(lenient.get("final_answer_recoveries") or [])
    lenient["format_recoveries"] = runtime + final_recs
    lenient["lenient_used"] = bool(runtime or final_recs)
    during = [r for r in runtime if r.get("stage") in STRICT_LOWER_BOUND_STAGES]
    if during and strict.get("scored") and strict.get("task_success"):
        strict = {**strict, "task_success": False, "strict_lower_bound": True,
                  "failure_labels": [f"strict:recovery_used:{r['rule']}" for r in during]}
    return lenient, strict
