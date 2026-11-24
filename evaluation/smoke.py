"""Offline smoke test (no model, no API key, no network):
  1. every non-optional gold call is executable in a fresh environment and returns the expected ok/error
  2. the scorer accepts an IDEAL trajectory + contract-conformant final answer for every task (T01-T75)
"""
from __future__ import annotations

import json

from benchmark.build_gold import GOLD_PATH
from environment import RailwayEnv

from .scorer import score
from .selfcheck import gold_call_args, gold_for, ideal_result

TASKS = sorted(k for k in json.loads(GOLD_PATH.read_text(encoding="utf-8")) if not k.startswith("_"))


def main() -> int:
    failures: list[str] = []
    for tid in TASKS:
        env = RailwayEnv()
        env.reset()
        for c in gold_for(tid)["required_calls"]:
            if c.get("optional"):
                continue
            out = env.call(c["tool"], gold_call_args(tid, c, env))
            if c.get("expected_error"):
                if (out.get("error") or {}).get("code") != c["expected_error"]:
                    failures.append(f"{tid}:{c['call_id']}: expected {c['expected_error']}, got {out}")
            elif not out.get("ok"):
                failures.append(f"{tid}:{c['call_id']} failed: {out}")
        row, snap = ideal_result(tid)
        s = score(row, gold_for(tid), snap)
        if not s["task_success"]:
            failures.append(f"{tid}: ideal trajectory not accepted by scorer: {s['failure_labels']}")
    print(f"offline smoke: {len(TASKS)} tasks, gold calls executable + scorer accepts ideal answers; failures={len(failures)}")
    for f in failures[:20]:
        print("  ", f)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
