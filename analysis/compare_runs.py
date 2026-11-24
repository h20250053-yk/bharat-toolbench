"""Compare two or more observe_run result directories (e.g. Qwen 2.5 3B vs 7B vs Llama) on identical items.

    python -m analysis.compare_runs analysis/results/A analysis/results/B [...] --out analysis/results/comparison_A_vs_B

Refuses (exit 2) unless all runs share: the same item set, benchmark_version, system-prompt hash, tool-schema hash, and
(when recorded in both) dataset hashes; every run must be complete (no missing items). Unscored items (e.g. a
context_overflow) are listed, excluded from that run's denominator and from paired comparisons. Warns when decoding settings
differ (temperature / seed / num_ctx / max_tokens). Only the official `task_success` is used for success numbers;
diagnostic categories are reported separately. Output directory is never overwritten.
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from pathlib import Path
from typing import Any

BOOTSTRAP_SEED = 20261014
BOOTSTRAP_RESAMPLES = 10000
DECODING_KEYS = ("temperature", "seed", "num_ctx", "max_tokens")


def load(d: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    summary = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    obs = {}
    for line in (d / "observations.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            o = json.loads(line)
            obs[o["task_id"]] = o
    return summary, obs


def check_comparable(runs: list[tuple[str, dict[str, Any], dict[str, dict[str, Any]]]]) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    name0, s0, o0 = runs[0]
    for name, s, o in runs:
        if not s["integrity"]["complete"]:
            errors.append(f"{name}: run is incomplete (missing {len(s['integrity']['missing_items'])} items)")
        unscored = sorted(t for t, x in o.items() if not x["scored"])
        if unscored:
            warnings.append(f"{name}: {len(unscored)} item(s) not scored {unscored}; excluded from that run's denominator "
                            f"and from all paired comparisons")
    for name, s, o in runs[1:]:
        if set(o) != set(o0):
            errors.append(f"{name}: item set differs from {name0} ({len(set(o) ^ set(o0))} items differ)")
        for key in ("benchmark_version", "system_prompt_sha256", "tool_schema_sha256"):
            if s[key] != s0[key]:
                errors.append(f"{name}: {key} differs from {name0}: {s[key]} vs {s0[key]}")
        if s.get("dataset_sha256") and s0.get("dataset_sha256"):
            data_keys = [k for k in s0["dataset_sha256"] if k.startswith("benchmark/")]
            diff = [k for k in data_keys if s["dataset_sha256"].get(k) != s0["dataset_sha256"].get(k)]
            if diff:
                errors.append(f"{name}: dataset files differ from {name0}: {diff}")
        else:
            warnings.append(f"{name} or {name0}: dataset hashes not recorded (pass --manifest to observe_run); not verified")
    for name, s, _ in runs:
        if len(s["decoding_settings"]) != 1:
            warnings.append(f"{name}: settings vary within the run: {s['decoding_settings']}")
    dec = {name: tuple((s["decoding_settings"][0] if s["decoding_settings"] else {}).get(k) for k in DECODING_KEYS) for name, s, _ in runs}
    if len(set(dec.values())) > 1:
        warnings.append(f"decoding settings differ {DECODING_KEYS}: {dec}")
    return errors, warnings


def paired(a: dict[str, dict[str, Any]], b: dict[str, dict[str, Any]]) -> dict[str, Any]:
    items = sorted(t for t in a if a[t]["scored"] and b.get(t, {}).get("scored"))  # items scored in BOTH runs
    x = [1 if a[t]["task_success"] else 0 for t in items]
    y = [1 if b[t]["task_success"] else 0 for t in items]
    counts = {"both_success": sum(i and j for i, j in zip(x, y)), "only_a": sum(i and not j for i, j in zip(x, y)),
              "only_b": sum(j and not i for i, j in zip(x, y)), "both_fail": sum(not i and not j for i, j in zip(x, y))}
    n = len(items)
    rng = random.Random(BOOTSTRAP_SEED)
    diffs = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append((sum(y[i] for i in idx) - sum(x[i] for i in idx)) / n)
    diffs.sort()
    return {**counts, "items": n, "success_rate_a": sum(x) / n, "success_rate_b": sum(y) / n, "diff_b_minus_a": (sum(y) - sum(x)) / n,
            "bootstrap_95ci_diff": [diffs[int(0.025 * BOOTSTRAP_RESAMPLES)], diffs[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]],
            "bootstrap": {"seed": BOOTSTRAP_SEED, "resamples": BOOTSTRAP_RESAMPLES, "unit": "item (paired resampling)"}}


def compare(runs: list[tuple[str, dict[str, Any], dict[str, dict[str, Any]]]]) -> dict[str, Any]:
    table = {}
    for name, s, o in runs:
        sc = [x for x in o.values() if x["scored"]]
        table[name] = {"model_key": s["model_key"], "items": len(o), "scored": len(sc),
                       "not_scored": sorted(t for t, x in o.items() if not x["scored"]),
                       "task_success": sum(x["task_success"] is True for x in sc),
                       "task_success_strict": sum(x.get("task_success_strict", x["task_success"]) is True for x in o.values() if x.get("scored_strict", x["scored"])),
                       "items_with_recovery": sum(bool(x.get("lenient_used")) for x in o.values()),
                       "parse_ok": s["rates"]["parse_ok"], "process_success": s["rates"]["process_success"],
                       "state_success": s["rates"]["state_success"], "tool_calls_ok": s["rates"]["tool_calls_ok"],
                       "tool_calls": s["rates"]["tool_calls"], "input_tokens": s["cost"]["input_tokens"],
                       "output_tokens": s["cost"]["output_tokens"], "wall_seconds": s["cost"]["wall_seconds_first_start_to_last_finish"],
                       "by_language": {k: v["task_success"] for k, v in s["by_language"].items()},
                       "by_category": {k: v["task_success"] for k, v in s["by_category"].items()},
                       "primary_failure": s["diagnostic"]["primary_failure"]}
    tasks = sorted({o2["semantic_task_id"] for _, _, o in runs for o2 in o.values()})
    per_task = {t: {name: sum(1 for x in o.values() if x["semantic_task_id"] == t and x["task_success"] is True) for name, _, o in runs}
                for t in tasks}
    pairs = {f"{runs[i][0]} vs {runs[j][0]}": paired(runs[i][2], runs[j][2])
             for i in range(len(runs)) for j in range(i + 1, len(runs))}
    return {"runs": table, "per_task_success": per_task, "paired": pairs}


def render_md(result: dict[str, Any], warnings: list[str]) -> str:
    names = list(result["runs"])
    L = ["# Model comparison", "", "Success = scorer `task_success`: headline = lenient (format recovery only), `task_success_strict` = sensitivity. Primary failures are diagnostic.", ""]
    if warnings:
        L += ["**Warnings:**", ""] + [f"- {w}" for w in warnings] + [""]
    L += ["| metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for metric in ("model_key", "items", "scored", "not_scored", "task_success", "task_success_strict", "items_with_recovery", "parse_ok", "process_success", "state_success", "tool_calls_ok",
                   "tool_calls", "input_tokens", "output_tokens", "wall_seconds"):
        L.append(f"| {metric} | " + " | ".join(str(result["runs"][n][metric]) for n in names) + " |")
    for group in ("by_language", "by_category"):
        keys = sorted({k for n in names for k in result["runs"][n][group]})
        L += ["", f"## Success {group.replace('_', ' ')}", "", "| | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
        L += [f"| {k} | " + " | ".join(str(result["runs"][n][group].get(k, "-")) for n in names) + " |" for k in keys]
    L += ["", "## Paired item-level comparison", ""]
    for pair, p in result["paired"].items():
        L.append(f"- **{pair}** ({p['items']} items scored in both): both {p['both_success']}, only A {p['only_a']}, only B {p['only_b']}, neither {p['both_fail']}; "
                 f"diff (B-A) {p['diff_b_minus_a']:+.3f}, 95% bootstrap CI [{p['bootstrap_95ci_diff'][0]:+.3f}, {p['bootstrap_95ci_diff'][1]:+.3f}]")
    L += ["", "## Primary failure distribution (diagnostic)", ""] + [f"- {n}: {result['runs'][n]['primary_failure']}" for n in names]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("result_dirs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if len(args.result_dirs) < 2:
        ap.error("need at least two result directories")
    if args.out.exists():
        ap.error(f"output directory already exists (never overwritten): {args.out}")
    runs = [(d.name, *load(d)) for d in args.result_dirs]
    errors, warnings = check_comparable(runs)
    for w in warnings:
        print("WARNING:", w)
    if errors:
        for e in errors:
            print("REFUSED:", e)
        return 2
    result = compare(runs)
    args.out.mkdir(parents=True)
    (args.out / "comparison.json").write_text(json.dumps({"warnings": warnings, **result}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.out / "comparison.md").write_text(render_md(result, warnings), encoding="utf-8")
    print(f"compared {len(runs)} runs -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
