"""Tool-selection metrics (definitions: METRICS.md). Extra analysis only: reads run rows and the gold, never changes scoring.

Matching of model calls to gold calls reuses the scorer's own functions, so 'correct arguments' means what the scorer means. Pure Python for the
per-item part (runs in the project venv and in tests); the bootstrap uses numpy when it is available (visualisation venv) and a slow pure-Python
fallback otherwise.
"""
from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from typing import Any, Callable

from evaluation.canonical import canon_tool_args
from evaluation.scorer import (_dependency_violations, _match_required, _matcher_ok, _MATCHER_KEYS, _prohibition_violations, _call_matches)

try:  # numpy is only in the visualisation venv
    import numpy as np
except ImportError:  # pragma: no cover - exercised in the project venv
    np = None

from environment.railway_env import TOOL_NAMES as TOOLS  # noqa: E402  (twelve tools since benchmark 3.0)
NOT_CALLED, NOT_REQUIRED = "(not called)", "(not required)"
CALL_EVENTS = ("tool_call", "malformed_tool_call", "tool_not_allowed")
INVALID_CODES = {"INVALID_ARGUMENTS", "MALFORMED_ARGUMENTS", "UNKNOWN_TOOL", "TOOL_NOT_ALLOWED", "INVALID_STATION", "INVALID_TRAIN", "INVALID_CLASS",
                 "INVALID_DATE", "INVALID_TIME_WINDOW", "INVALID_PASSENGER", "SAME_STATION"}
BOOTSTRAP_SEED = 20261124
BOOTSTRAP_RESAMPLES = 10000
FIELD_GROUP = {"source": "station code", "destination": "station code", "date": "date", "travel_class": "class", "train_id": "train id", "passenger": "passenger",
               "time_window": "time window", "name": "station name (resolve)"}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


# ============================================================================================ per-item metrics
def calls_of(row: dict[str, Any]) -> list[dict[str, Any]]:
    """The model's calls in order (METRICS.md): trajectory events, or partial_trajectory when the trajectory is empty by design."""
    traj = row.get("trajectory") or []
    src = traj if traj else (row.get("partial_trajectory") or [])
    return [e for e in src if e.get("event") in CALL_EVENTS]


def _roots(gold: dict[str, Any]) -> list[dict[str, Any]]:
    """Non-optional required calls that need nothing from an earlier REQUIRED call (an optional predecessor, e.g. a first alias attempt, does not block)."""
    optional = {c["call_id"] for c in gold.get("required_calls", []) if c.get("optional")}
    has_pred = {e["after"] for e in gold.get("dependency_edges", []) if e["before"] not in optional}
    return [c for c in gold.get("required_calls", []) if not c.get("optional") and c["call_id"] not in has_pred]


def _multiset(calls: list[dict[str, Any]], optional: bool) -> Counter:
    return Counter(c["tool"] for c in calls if optional or not c.get("optional"))


def _canon_key(e: dict[str, Any]) -> str:
    return e.get("tool", "?") + json.dumps(canon_tool_args(e.get("tool", ""), e.get("arguments") or {}), sort_keys=True, ensure_ascii=False, default=str)


def _call_valid(e: dict[str, Any], expected_errors: set[str]) -> bool:
    code = ((e.get("observation") or {}).get("error") or {}).get("code")
    return not (code in INVALID_CODES and code not in expected_errors)


def _literal_hit(g: dict[str, Any], key: str, expected: Any, events: list[dict[str, Any]]) -> bool:
    alts = (g.get("arg_alternatives") or {}).get(key, [])
    for e in events:
        if e.get("tool") != g["tool"]:
            continue
        actual = canon_tool_args(e["tool"], e.get("arguments") or {})
        if isinstance(expected, dict) and any(k in expected for k in _MATCHER_KEYS):
            if key in actual and _matcher_ok(expected, e.get("observation") or {}):
                return True
            continue
        accepted = [canon_tool_args(g["tool"], {key: expected})[key]] + [None if a is None else canon_tool_args(g["tool"], {key: a})[key] for a in alts]
        val = actual.get(key)
        if val in accepted or (val is None and None in accepted):
            return True
    return False


def item_metrics(row: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    """All per-item quantities of METRICS.md for one row (a run row with `score`, `trajectory`, `state_snapshot`) and its task's gold."""
    tid = row["semantic_task_id"]
    calls = calls_of(row)
    req_calls = [c for c in gold.get("required_calls", []) if not c.get("optional")]
    R, A = _multiset(gold.get("required_calls", []), optional=False), _multiset(gold.get("required_calls", []), optional=True)
    called = Counter(e["tool"] for e in calls)
    m_t = {t: min(R[t], called[t]) for t in R}
    m = sum(m_t.values())
    mp = sum(min(A[t], called[t]) for t in A)
    n, nR = len(calls), len(req_calls)
    needed = nR > 0
    recall = (m / nR) if needed else None
    precision = (mp / n) if n else None
    f1 = None
    if needed:
        p = precision if precision is not None else 0.0
        f1 = 0.0 if (recall + p) == 0 else 2 * recall * p / (recall + p)
    exec_traj = [e for e in calls]          # `_match_required` only looks at executed `tool_call` events of this list
    matched, missing, via_eq = _match_required(tid, gold, exec_traj)
    direct = len(matched) - len(via_eq)
    violations = _dependency_violations(gold, matched)
    considered = [e for e in gold.get("dependency_edges", []) if e["before"] in matched and e["after"] in matched]
    expected_errors = {c["expected_error"] for c in gold.get("required_calls", []) if c.get("expected_error")}
    valid = sum(_call_valid(e, expected_errors) for e in calls)
    roots = _roots(gold)
    first = calls[0] if calls else None
    first_ok = bool(first and any(first["tool"] == r["tool"] for r in roots))
    first_exact = bool(first and first.get("event") == "tool_call" and any(_call_matches(first, r, {}) for r in roots))
    # field accuracy (pooled by field group): literal gold values of the required calls
    fields: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for g in req_calls:
        for key, expected in (g.get("required_args") or {}).items():
            grp = FIELD_GROUP.get(key, key)
            fields[grp][1] += 1
            fields[grp][0] += int(_literal_hit(g, key, expected, [e for e in calls if e.get("event") == "tool_call"]))
    seen: set[str] = set()
    repeated = 0
    for e in calls:
        k = _canon_key(e)
        repeated += k in seen
        seen.add(k)
    bookings = (row.get("state_snapshot") or {}).get("bookings") or []
    from analysis.observe_run import _other_changes  # 3.0: any state change the gold does not expect (not only bookings)
    unwanted_other = any(sum((g - w).values()) for _, g, w in _other_changes(row, gold))
    gold_books = (gold.get("final_state") or {}).get("expected_bookings") or []
    success = bool((row.get("score") or {}).get("task_success"))
    right_tools = needed and m == nR
    right_args = right_tools and not missing
    right_order = right_args and not violations
    # confusion: matched on the diagonal; leftovers of expected steps (gold order) paired in order with surplus calls (call order)
    left_expected: list[str] = []
    used = Counter()
    for c in req_calls:
        used[c["tool"]] += 1
        if used[c["tool"]] > m_t.get(c["tool"], 0):
            left_expected.append(c["tool"])
    left_calls: list[str] = []
    seen_t = Counter()
    for e in calls:
        seen_t[e["tool"]] += 1
        if seen_t[e["tool"]] > min(A[e["tool"]], called[e["tool"]]):
            left_calls.append(e["tool"])
    conf: Counter = Counter({(t, t): v for t, v in m_t.items() if v})
    for x, y in zip(left_expected, left_calls):
        conf[(x, y)] += 1
    for x in left_expected[len(left_calls):]:
        conf[(x, NOT_CALLED)] += 1
    for y in left_calls[len(left_expected):]:
        conf[(NOT_REQUIRED, y)] += 1
    return {
        "task": tid, "task_id": row["task_id"], "language": row["language"], "needed": needed, "n_calls": n, "n_required": nR, "m": m, "m_prime": mp,
        "recall": recall, "precision": precision, "f1": f1, "uses_tools": n >= 1,
        "first_call_ok": first_ok if needed else None, "first_call_exact": first_exact if needed else None,
        "valid_calls": valid, "arg_acc": (direct / m) if (needed and m >= 1) else None, "direct_matched": direct, "field_hits": {k: list(v) for k, v in fields.items()},
        "edges_considered": len(considered), "edges_violated": len(violations),
        "sequence_acc": (1 - len(violations) / len(considered)) if (needed and considered) else None,
        "unnecessary_calls": n - mp, "over_call_rate": ((n - mp) / n) if n else None, "overcalling": (n - mp) >= 1, "repeated_calls": repeated,
        "no_tool_task": not needed, "unneeded_tool_use": (not needed) and n >= 1,
        "unwanted_booking": (not gold_books) and bool(bookings), "booking_forbidden_task": bool(gold.get("prohibited_actions")),
        "unwanted_action": bool(((not gold_books) and bookings) or unwanted_other),
        "prohibited_attempt": bool(_prohibition_violations(gold, [e for e in calls if e.get("event") == "tool_call"])), "no_booking_expected": not gold_books,
        "funnel": [n >= 1, bool(right_tools), bool(right_args), bool(right_order), bool(right_order and success)] if needed else None,
        "selection_error": needed and m < nR, "argument_error": needed and m == nR and bool(missing), "task_success": success,
        "confusion": {f"{a}|{b}": v for (a, b), v in conf.items()},
    }


# ============================================================================================ aggregation with CIs
def _boot_idx(n: int, b: int, rng: Any) -> Any:
    return rng.integers(0, n, size=(b, n))


def boot_ci(num: list[float], den: list[float] | None = None, b: int = BOOTSTRAP_RESAMPLES) -> tuple[float, float, float]:
    """(estimate, lo, hi): mean of `num` (den None) or sum(num)/sum(den) (pooled ratio), percentile bootstrap over items."""
    n = len(num)
    if n == 0:
        return (float("nan"),) * 3
    d = den if den is not None else [1.0] * n
    est = sum(num) / sum(d) if sum(d) else float("nan")
    if np is not None:
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        idx = _boot_idx(n, b, rng)
        a, w = np.asarray(num, float), np.asarray(d, float)
        with np.errstate(divide="ignore", invalid="ignore"):
            boots = a[idx].sum(1) / w[idx].sum(1)
        boots = boots[~np.isnan(boots)]
        return (est, float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))) if len(boots) else (est, float("nan"), float("nan"))
    rng2 = random.Random(BOOTSTRAP_SEED)
    boots = []
    for _ in range(min(b, 1000)):
        ids = [rng2.randrange(n) for _ in range(n)]
        s, t = sum(num[i] for i in ids), sum(d[i] for i in ids)
        if t:
            boots.append(s / t)
    boots.sort()
    return (est, boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots)) - 1]) if boots else (est, float("nan"), float("nan"))


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    """METRICS.md metrics with 95% CIs for a group of item-metric dicts. Each entry: {"value", "lo", "hi", "n"}."""
    out: dict[str, Any] = {}
    needed = [i for i in items if i["needed"]]

    def prop(name: str, pool: list[dict[str, Any]], fn: Callable[[dict[str, Any]], bool]) -> None:
        k, n = sum(bool(fn(i)) for i in pool), len(pool)
        lo, hi = wilson(k, n)
        out[name] = {"value": (k / n) if n else float("nan"), "lo": lo, "hi": hi, "n": n, "k": k}

    def mean(name: str, pool: list[dict[str, Any]], key: str) -> None:
        vals = [float(i[key]) for i in pool if i[key] is not None]
        e, lo, hi = boot_ci(vals)
        out[name] = {"value": e, "lo": lo, "hi": hi, "n": len(vals)}

    def ratio(name: str, pool: list[dict[str, Any]], num: Callable[[dict[str, Any]], float], den: Callable[[dict[str, Any]], float]) -> None:
        nums, dens = [float(num(i)) for i in pool], [float(den(i)) for i in pool]
        e, lo, hi = boot_ci(nums, dens)
        out[name] = {"value": e, "lo": lo, "hi": hi, "n": len(pool), "den": sum(dens)}

    prop("tool_use_rate", needed, lambda i: i["uses_tools"])
    mean("selection_recall", needed, "recall")
    mean("selection_precision", [i for i in needed if i["n_calls"] >= 1], "precision")
    mean("selection_f1", needed, "f1")
    prop("first_call_accuracy", needed, lambda i: i["first_call_ok"])
    prop("first_call_exactness", needed, lambda i: i["first_call_exact"])
    ratio("argument_validity", items, lambda i: i["valid_calls"], lambda i: i["n_calls"])
    mean("argument_accuracy", needed, "arg_acc")
    mean("sequence_accuracy", needed, "sequence_acc")
    ratio("sequence_edge_rate", [i for i in needed if i["edges_considered"]], lambda i: i["edges_considered"] - i["edges_violated"], lambda i: i["edges_considered"])
    mean("over_call_rate", [i for i in items if i["n_calls"] >= 1], "over_call_rate")
    prop("overcalling_items", needed, lambda i: i["overcalling"])
    ratio("repeated_call_rate", [i for i in items if i["n_calls"] >= 1], lambda i: i["repeated_calls"], lambda i: i["n_calls"])
    ratio("calls_per_item", items, lambda i: i["n_calls"], lambda i: 1)
    prop("unneeded_tool_use", [i for i in items if i["no_tool_task"]], lambda i: i["unneeded_tool_use"])
    prop("unwanted_booking", [i for i in items if i["no_booking_expected"]], lambda i: i["unwanted_booking"])
    prop("unwanted_action", items, lambda i: i.get("unwanted_action", False))  # 3.0: any unrequested state change (all items)
    prop("prohibited_attempt", [i for i in items if i["booking_forbidden_task"]], lambda i: i["prohibited_attempt"])
    prop("selection_error_rate", needed, lambda i: i["selection_error"])
    prop("argument_error_rate", needed, lambda i: i["argument_error"])
    for idx, name in enumerate(["funnel_uses_tools", "funnel_right_tools", "funnel_right_arguments", "funnel_right_order", "funnel_task_success"]):
        prop(name, needed, lambda i, idx=idx: i["funnel"][idx])
    fields: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for i in needed:
        for k, (h, t) in i["field_hits"].items():
            fields[k][0] += h
            fields[k][1] += t
    out["field_accuracy"] = {k: {"value": h / t if t else float("nan"), "lo": wilson(h, t)[0], "hi": wilson(h, t)[1], "n": t} for k, (h, t) in sorted(fields.items())}
    out["n_items"] = len(items)
    out["n_tool_needed"] = len(needed)
    return out


def confusion(items: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    c: Counter = Counter()
    for i in items:
        for k, v in i["confusion"].items():
            a, b = k.split("|")
            c[(a, b)] += v
    return dict(c)


def rank_models(summaries: dict[str, dict[str, Any]], task_success: dict[str, float]) -> dict[str, Any]:
    """Model ranking on tool selection (mean F1, ties by recall) next to the task-success ranking, with Spearman agreement."""
    keys = list(summaries)
    by_sel = sorted(keys, key=lambda k: (-summaries[k]["selection_f1"]["value"], -summaries[k]["selection_recall"]["value"]))
    by_ts = sorted(keys, key=lambda k: -task_success[k])
    rank_sel = {k: i + 1 for i, k in enumerate(by_sel)}
    rank_ts = {k: i + 1 for i, k in enumerate(by_ts)}
    n = len(keys)
    d2 = sum((rank_sel[k] - rank_ts[k]) ** 2 for k in keys)
    rho = 1 - 6 * d2 / (n * (n * n - 1)) if n > 2 else float("nan")
    return {"tool_selection_rank": rank_sel, "task_success_rank": rank_ts, "spearman_rho": rho, "order_by_selection": by_sel, "order_by_success": by_ts}
