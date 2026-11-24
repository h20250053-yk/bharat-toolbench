"""Summarize a BharatToolBench evaluation JSONL run (latest row per item; provider/runner errors reported, not scored)."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_file", type=Path)
    args = ap.parse_args(argv)
    latest: dict[str, dict] = {}
    for line in args.run_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            latest[f"{r['task_id']}|{r['model_key']}"] = r
    rows = list(latest.values())
    print(f"items={len(rows)} statuses={dict(Counter(r['status'] for r in rows))}")
    by_lang = defaultdict(list)
    for r in rows:
        by_lang[r["language"]].append(r)
    for lang in sorted(by_lang):
        rs = by_lang[lang]
        scored = [r for r in rs if r.get("score", {}).get("scored")]
        succ = sum(bool(r["score"]["task_success"]) for r in scored)
        tok = sum(r.get("usage", {}).get("total_tokens", 0) for r in rs)
        print(f"{lang}: scored={len(scored)}/{len(rs)} success={succ} rate={(succ / len(scored)) if scored else 0:.3f} "
              f"tokens={tok} avg_tool_calls={sum(r['score'].get('observed_tool_calls', 0) for r in rs) / len(rs):.2f}")
    fails = Counter(l.split(":")[0] + ":" + l.split(":")[1] for r in rows for l in r.get("score", {}).get("failure_labels", []) if ":" in l)
    print("failure labels:", dict(fails.most_common(12)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
