"""Write a reproducibility manifest for a finished run (never overwrites).

    python -m analysis.run_manifest --prerun runs/X.prerun.json --run-file runs/X.jsonl [--run-file runs/X_resume1.jsonl]
                                    --out runs/X.manifest.json

The pre-run record (git commit, clean-tree check, CLI command, config/data/prompt hashes, Ollama version, model digest)
is captured BEFORE the run starts; this tool adds the post-run facts: SHA-256, size and row counts of every run and
quota file, unique items, statuses, time range, and whether the benchmark files still match the pre-run hashes.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_facts(path: Path) -> dict:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.suffix == ".jsonl" else None
    facts = {"file": path.as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size}
    if rows is not None:
        facts.update(rows=len(rows), unique_task_ids=len({r["task_id"] for r in rows}),
                     status=dict(collections.Counter(r["status"] for r in rows)),
                     first_started_at=min(r["started_at"] for r in rows) if rows else None,
                     last_finished_at=max(r["finished_at"] for r in rows) if rows else None)
    return facts


def build(prerun: dict, run_files: list[Path], root: Path = ROOT) -> dict:
    files = []
    for f in run_files:
        files.append(file_facts(f))
        q = f.with_suffix(".quota.json")
        if q.exists():
            files.append({**file_facts(q), "quota": json.loads(q.read_text(encoding="utf-8"))})
    now_hashes = {p: sha256_file(root / p) for p in prerun.get("file_sha256", {})}
    changed = sorted(p for p, h in now_hashes.items() if h != prerun["file_sha256"][p])
    versions: dict[str, int] = {}
    for f in run_files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                v = (json.loads(line).get("adapter_settings") or {}).get("ollama_version")
                if v:
                    versions[v] = versions.get(v, 0) + 1
    pre_v = prerun.get("ollama_version")
    return {"manifest_version": 1, "written_at": datetime.now(timezone.utc).isoformat(), "prerun": prerun, "run_files": files,
            # the Ollama server version is part of every manifest: in the pre-run record and as seen in the rows' adapter_settings
            "ollama_version": pre_v, "ollama_versions_in_rows": versions, "ollama_server_env": prerun.get("server_env"),
            "ollama_version_consistent": (set(versions) <= {pre_v}) if pre_v else None,
            "benchmark_files_unchanged_since_prerun": not changed, "changed_since_prerun": changed,
            "analysis_platform": {"python": platform.python_version(), "platform": platform.platform()}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--prerun", type=Path, required=True)
    ap.add_argument("--run-file", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        ap.error(f"manifest already exists (never overwritten): {args.out}")
    manifest = build(json.loads(args.prerun.read_text(encoding="utf-8")), args.run_file)
    args.out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"manifest -> {args.out}; benchmark files unchanged since prerun: {manifest['benchmark_files_unchanged_since_prerun']}")
    return 0 if manifest["benchmark_files_unchanged_since_prerun"] else 3


if __name__ == "__main__":
    sys.exit(main())
