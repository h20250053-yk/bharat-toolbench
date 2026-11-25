"""Semantic-duplicate check over all semantic tasks. Run:  python -m benchmark.semantic_overlap

Two tasks are SEMANTIC DUPLICATES if they test the same reasoning even though their data differ (other train,
station, passenger, date, class, fare or wording). So the comparison deliberately DROPS entity data and keeps only
reasoning features, all derived from the spec + generated gold (nothing hand-labelled):

  * solver kind             - the reasoning procedure that produces the gold (must be unique per task)
  * expected status         - success / cannot_complete / needs_clarification
  * required tools          - set of tools in the non-optional gold calls
  * mutation profile        - number of bookings expected (0, 1, 2+); since 3.0 also cancellations (1, 2+) and waitlist entries
  * expected tool errors    - e.g. CLASS_NOT_OFFERED
  * reasoning constraints   - constraint kinds with their operator / objective / condition, e.g.
                              'departure_time:>=', 'objective:latest departure', 'fallback_allowed:False'
                              (entity kinds such as route, date, train_id, travel_class, passenger are excluded)
  * explicit prohibition    - whether the user forbade an action
  * party size              - 'multi_passenger' when a task involves more than one passenger: a quantity comparison
                              (seats vs party) is a different reasoning step from reading an AVAILABLE/SOLD_OUT flag,
                              even though the passenger NAMES themselves are entity data and are ignored

Rules (each a validation error):
  1. every task has a distinct solver kind
  2. no two tasks share the same reasoning fingerprint (status, tools, mutation, errors, reasoning constraints)
  3. no pair of tasks has Jaccard similarity >= MAX_JACCARD over the full feature set

Limitation: this is a structural check. It cannot prove two tasks are different to a human; the per-task
'playbook_note' records the human-readable argument against the nearest neighbour.
"""
from __future__ import annotations

import json
from itertools import combinations
from typing import Any

ENTITY_KINDS = {"route", "date", "train_id", "travel_class", "passenger", "passengers", "boarding_station"}
VALUE_KINDS = {"objective", "condition", "fallback_allowed", "fallback_rule",  # here the VALUE is the reasoning
               "asks", "complaint_category"}  # 20-tool batch: which facts are asked for; which complaint category the text maps to
MAX_JACCARD = 0.75


def _constraint_token(c: dict[str, Any]) -> str | None:
    k = c["kind"]
    if k in ENTITY_KINDS:
        return None
    if k in VALUE_KINDS:
        return f"{k}:{c.get('value')}"
    if "op" in c:
        return f"{k}:{c['op']}"
    return k


def features(spec: Any, gold: dict[str, Any]) -> dict[str, Any]:
    req = [c for c in gold["required_calls"] if not c.get("optional")]
    n_book = len(gold["final_state"]["expected_bookings"])
    return {
        "solver": spec.solver.kind,
        "status": gold["final_state"]["status"],
        "tools": frozenset(c["tool"] for c in req),
        # 3.0: cancellations and waitlist entries are mutations too (absent for T01-T75, so their features are unchanged)
        "mutation": ("0" if n_book == 0 else ("1" if n_book == 1 else "2+"))
                    + (f"+cancel{min(len(gold['final_state'].get('expected_cancellations') or []), 2)}"
                       if gold["final_state"].get("expected_cancellations") else "")
                    + ("+waitlist" if gold["final_state"].get("expected_waitlist") else "")
                    + "".join(f"+{k}{min(len(v), 2)}" for k, v in sorted((gold["final_state"].get("expected_effects") or {}).items())),
        "errors": frozenset(c["expected_error"] for c in gold["required_calls"] if c.get("expected_error")),
        "reasoning": frozenset(t for t in (_constraint_token(c) for c in spec.constraints) if t)
                     | ({"multi_passenger"} if any(c["kind"] == "passengers" and len(c["value"]) > 1 for c in spec.constraints) else set()),
        "prohibition": bool(spec.prohibited_actions),
    }


def fingerprint(f: dict[str, Any]) -> tuple:
    return (f["status"], f["tools"], f["mutation"], f["errors"], f["reasoning"])


def tokens(f: dict[str, Any]) -> set[str]:
    return ({f"status:{f['status']}", f"mutation:{f['mutation']}", f"prohibition:{f['prohibition']}"}
            | {f"tool:{t}" for t in f["tools"]} | {f"error:{e}" for e in f["errors"]} | {f"r:{r}" for r in f["reasoning"]})


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


def analyse(specs: dict[str, Any], gold_file: dict[str, Any]) -> dict[str, Any]:
    feats = {t: features(specs[t], gold_file[t]) for t in sorted(specs)}
    pairs = sorted(((jaccard(tokens(feats[a]), tokens(feats[b])), a, b) for a, b in combinations(sorted(feats), 2)), reverse=True)
    return {"features": feats, "pairs": pairs}


def overlap_errors(specs: dict[str, Any], gold_file: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if any(t not in gold_file for t in specs):
        return ["semantic_overlap: gold missing for some task"]
    res = analyse(specs, gold_file)
    feats = res["features"]
    by_solver: dict[str, list[str]] = {}
    by_fp: dict[tuple, list[str]] = {}
    for t, f in feats.items():
        by_solver.setdefault(f["solver"], []).append(t)
        by_fp.setdefault(fingerprint(f), []).append(t)
    errors += [f"semantic duplicate: {ts} share solver kind {k!r}" for k, ts in by_solver.items() if len(ts) > 1]
    errors += [f"semantic duplicate: {ts} share the reasoning fingerprint {fp}" for fp, ts in by_fp.items() if len(ts) > 1]
    errors += [f"semantic overlap too high: {a}~{b} jaccard={j:.2f} >= {MAX_JACCARD}" for j, a, b in res["pairs"] if j >= MAX_JACCARD]
    return errors


def main() -> int:
    from .build_gold import GOLD_PATH, load_specs
    specs = {s.semantic_task_id: s for s in load_specs()}
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    res = analyse(specs, gold)
    for t, f in res["features"].items():
        print(f"{t}  {f['solver']:<34} {f['status']:<20} book={f['mutation']:<2} tools={sorted(f['tools'])} "
              f"errors={sorted(f['errors'])} reasoning={sorted(f['reasoning'])}")
    print("\nmost similar pairs (Jaccard over reasoning features, entity data excluded):")
    for j, a, b in res["pairs"][:8]:
        print(f"  {a}~{b}: {j:.2f}")
    errs = overlap_errors(specs, gold)
    for e in errs:
        print("FAIL:", e)
    print(f"{'NO DUPLICATES' if not errs else 'DUPLICATES FOUND'}: {len(specs)} tasks, {len(res['pairs'])} pairs checked, "
          f"max Jaccard {res['pairs'][0][0]:.2f} (threshold {MAX_JACCARD})")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
