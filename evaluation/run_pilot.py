"""CLI for BharatToolBench pilot/full evaluation (resumable JSONL; one row per item and model).

Re-running with --resume skips items whose latest row is a MODEL outcome (completed, malformed_output, context_overflow,
step_limit_exceeded) and re-runs provider_error / runner_error rows (plan: provider errors are re-run, not scored).
The latest row per (task_id, model_key) is authoritative; earlier rows are kept for the audit trail.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.base import ProviderError
from agents.registry import build_adapter, load_model_config
from benchmark.build_gold import GOLD_PATH
from environment import RailwayEnv

from .quota import QuotaExceeded, QuotaTracker
from .runner import RunnerConfig, load_items, run_item
from .scorer import score_both
from .splits import ALL_LANGUAGES, SPLITS, task_ids  # noqa: F401 - task_ids re-exported for the analysis tools

ROOT = Path(__file__).resolve().parent.parent
LANG_DIR = ROOT / "benchmark" / "languages"
RUNS_DIR = ROOT / "runs"
FINAL_STATUSES = {"completed", "malformed_output", "step_limit_exceeded", "context_overflow", "output_truncated"}


def latest_rows(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[f"{r['task_id']}|{r['model_key']}"] = r
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=sorted(load_model_config()), help="a key of config/models.yaml")
    ap.add_argument("--split", default="pilot", choices=list(SPLITS))
    ap.add_argument("--languages", nargs="+", default=ALL_LANGUAGES, choices=ALL_LANGUAGES,
                    help="default: all five languages (75 tasks x 5 = 375 items for --split full); pass the four old ones for the mid-sem runs")
    ap.add_argument("--run-file", type=Path)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--max-attempts", type=int, default=5, help="attempts per item for RETRYABLE provider failures only")
    ap.add_argument("--max-requests", type=int, default=None, help="stop cleanly before an item once this many model requests were made")
    ap.add_argument("--max-total-tokens", type=int, default=None, help="stop cleanly before an item once this many tokens were used")
    args = ap.parse_args(argv)
    if args.resume and not args.run_file:
        ap.error("--resume needs --run-file pointing at the run to continue")

    if args.run_file and args.run_file.exists() and args.run_file.stat().st_size > 0 and not args.resume:
        ap.error(f"{args.run_file} already has rows: pass a NEW --run-file, or --resume to continue it (never append a fresh run to an old file)")
    items = load_items(LANG_DIR, args.languages, task_ids(args.split))
    RUNS_DIR.mkdir(exist_ok=True)
    run_file = args.run_file or (RUNS_DIR / f"{args.model}_{args.split}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl")
    run_name = run_file.stem
    quota = QuotaTracker(run_file.with_suffix(".quota.json"), max_requests=args.max_requests, max_total_tokens=args.max_total_tokens)
    existing = latest_rows(run_file) if args.resume else {}
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    env = RailwayEnv()
    cfg = RunnerConfig(max_attempts=args.max_attempts)
    print(f"Model: {args.model} | split: {args.split} | languages: {','.join(args.languages)} | items: {len(items)}")
    print(f"Run file: {run_file} | max turns per item: {cfg.max_turns}")
    preflight_done = False
    with run_file.open("a", encoding="utf-8") as fh:
        for idx, item in enumerate(items, 1):
            key = f"{item['task_id']}|{args.model}"
            if key in existing and existing[key].get("status") in FINAL_STATUSES:
                print(f"[{idx}/{len(items)}] SKIP {item['task_id']} ({existing[key]['status']})")
                continue
            try:
                quota.check()
            except QuotaExceeded as exc:
                print(f"STOP: {exc}")
                break
            if not preflight_done:
                preflight_done = True
                try:  # refuse to start a run with a model that cannot do tool calls (audit I-07); no item is attempted
                    if load_model_config()[args.model].get("provider") == "ollama":
                        probe = build_adapter(args.model)
                        info = probe.preflight()
                        print(f"Pre-flight OK: {info.get('model_digest')} capabilities={info.get('capabilities')} "
                              f"think={probe.settings().get('think_effective')}")
                except ProviderError as exc:
                    print(f"REFUSING TO RUN {args.model}: {exc}")
                    quota.save()
                    return 3
            print(f"[{idx}/{len(items)}] RUN {item['task_id']}")
            row = run_item(item, lambda: build_adapter(args.model), env, cfg, quota=quota, run_name=run_name)
            # headline = lenient (format recovery only, never prose extraction); strict = sensitivity. Both stored, see FORMAT_ROBUSTNESS.md.
            row["score"], row["score_strict"] = score_both(row, gold[item["semantic_task_id"]], row["state_snapshot"])
            row["scoring"] = {"headline": "lenient", "version": 1}
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            quota.save()
            print(f"    status={row['status']} task_success={row['score'].get('task_success')} (strict {row['score_strict'].get('task_success')}, "
                  f"recoveries {len(row['score'].get('format_recoveries', []))}) attempts={row['attempts']} "
                  f"tokens={row['usage'].get('total_tokens', 0)}")
    quota.save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
