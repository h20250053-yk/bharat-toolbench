"""Null baselines and the tool-required breakdown (audit I-10). No model, no tool call: pure scorer arithmetic.

11 of the 75 tasks need no tool call (the correct answer is a refusal or a clarification), so an agent that never calls a
tool and always answers `needs_clarification` already passes some of them. Model scores must be read against that floor,
and also on the tasks that DO require tool calls.

    python -m analysis.null_baseline [--out analysis/results/null_baseline]      # prints the table, optionally writes it
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from benchmark.build_gold import GOLD_PATH
from evaluation.final_answer import CLOSE, OPEN
from evaluation.scorer import score

STATUSES = ("needs_clarification", "cannot_complete", "success")


def _gold() -> dict[str, Any]:
    g = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in g.items() if not k.startswith("_")}


def tool_required_tasks(gold: dict[str, Any] | None = None) -> list[str]:
    """Tasks whose gold has at least one non-optional required call (the correct answer cannot be given without tools)."""
    gold = gold or _gold()
    return sorted(t for t, g in gold.items() if any(not c.get("optional") for c in g["required_calls"]))


def null_row(tid: str, status: str, language: str = "en") -> dict[str, Any]:
    """A result row of an agent that makes no tool call and answers with a constant status."""
    block = {"status": status, "selected_train": None, "selected_class": None, "booking_ids": [], "requested_passengers": [], "notes": "null baseline"}
    return {"task_id": f"{tid}_{language}", "semantic_task_id": tid, "language": language, "status": "completed", "trajectory": [],
            "final_text": f"No tools used.\n{OPEN}\n{json.dumps(block)}\n{CLOSE}", "state_snapshot": {"bookings": []}}


def null_baseline(status: str, gold: dict[str, Any] | None = None) -> list[str]:
    """Task ids passed by the no-tool, constant-status agent (identical in every language)."""
    gold = gold or _gold()
    return sorted(t for t, g in gold.items() if score(null_row(t, status), g, {"bookings": []})["task_success"])


def baseline_table(gold: dict[str, Any] | None = None) -> dict[str, Any]:
    gold = gold or _gold()
    needs_tools = set(tool_required_tasks(gold))
    out: dict[str, Any] = {"tasks": len(gold), "tool_required_tasks": len(needs_tools), "no_tool_tasks": sorted(set(gold) - needs_tools),
                           "baselines": {}}
    for st in STATUSES:
        passed = null_baseline(st, gold)
        out["baselines"][f"always_{st}_no_tools"] = {"passes": len(passed), "of": len(gold), "rate": round(len(passed) / len(gold), 4),
                                                     "passes_on_tool_required_tasks": len(set(passed) & needs_tools), "task_ids": passed}
    return out


def tool_required_breakdown(observations: list[dict[str, Any]], gold: dict[str, Any] | None = None) -> dict[str, Any]:
    """Success of a run on tool-required vs no-tool tasks (scored items only), next to the null baseline."""
    gold = gold or _gold()
    needs = set(tool_required_tasks(gold))
    base = null_baseline("needs_clarification", gold)
    res: dict[str, Any] = {}
    for name, keep in (("tool_required_tasks", lambda t: t in needs), ("no_tool_tasks", lambda t: t not in needs)):
        grp = [o for o in observations if keep(o["semantic_task_id"]) and o["scored"]]
        ok = sum(o["task_success"] is True for o in grp)
        res[name] = {"scored": len(grp), "task_success": ok, "rate": round(ok / len(grp), 4) if grp else None}
    n_items = len({o["language"] for o in observations}) or 1
    res["always_needs_clarification_baseline"] = {"task_ids": base, "passes_per_language": len(base),
                                                  "rate_all_tasks": round(len(base) / len(gold), 4), "languages_in_run": n_items}
    return res


def render_md(table: dict[str, Any]) -> str:
    L = ["# Null baselines (no tool calls, constant final status)", "",
         f"{table['tool_required_tasks']} of {table['tasks']} tasks require tool calls; no-tool tasks: {', '.join(table['no_tool_tasks'])}", "",
         "| baseline | passes | rate | on tool-required tasks |", "|---|---|---|---|"]
    for k, v in table["baselines"].items():
        L.append(f"| {k} | {v['passes']}/{v['of']} | {100 * v['rate']:.1f}% | {v['passes_on_tool_required_tasks']} |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, help="new folder to write baseline.json / baseline.md into (never overwritten)")
    args = ap.parse_args(argv)
    table = baseline_table()
    print(render_md(table))
    if args.out:
        if args.out.exists():
            ap.error(f"output directory already exists (never overwritten): {args.out}")
        args.out.mkdir(parents=True)
        (args.out / "baseline.json").write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (args.out / "baseline.md").write_text(render_md(table), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
