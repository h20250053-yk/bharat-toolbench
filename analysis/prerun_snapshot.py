"""Write a pre-run snapshot BEFORE an evaluation run starts (never overwrites; refuses a dirty tracked tree).

    python -m analysis.prerun_snapshot --model local_llama32_3b --split full --run-file runs/<stem>.jsonl
                                       --command "<exact CLI command>"

Writes runs/<stem>.prerun.json with: git commit + clean check, the exact command, model key and its full config
entry, Ollama version and the model's digest / quantization (read from the local server), benchmark version,
system-prompt and tool-schema hashes, SHA-256 of the task / gold / language data and of the evaluation code, the
expected item count for the split, Python / platform. The run file and its quota file must not exist yet.
Consumed by analysis/run_manifest.py. No secrets are read or written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HASHED_FILES = (["benchmark/semantic_tasks.json", "benchmark/gold_labels.json"]
                + [f"benchmark/languages/{l}.jsonl" for l in ("en", "hinglish", "hi", "mr", "gu")]
                + ["benchmark/languages/human_review.json"]
                + ["config/models.yaml", "evaluation/runner.py", "evaluation/scorer.py", "evaluation/final_answer.py",
                   "evaluation/canonical.py", "evaluation/tolerance.py", "agents/ollama_adapter.py", "evaluation/run_pilot.py"])


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30).stdout.strip()


DEFAULT_SERVER_LOG = Path.home() / "FreeModel" / "ollama-serve.log"
PLANNED_SERVER_ENV = {"OLLAMA_NUM_PARALLEL": "1", "OLLAMA_MAX_LOADED_MODELS": "1"}   # MODEL_PLAN.md: one conversation, one model on the GPU
SERVER_ENV_KEYS = ("OLLAMA_NUM_PARALLEL", "OLLAMA_MAX_LOADED_MODELS", "OLLAMA_FLASH_ATTENTION", "OLLAMA_KV_CACHE_TYPE", "OLLAMA_CONTEXT_LENGTH",
                   "OLLAMA_KEEP_ALIVE", "OLLAMA_GPU_OVERHEAD", "OLLAMA_MAX_QUEUE")


def server_env(log_path: Path | None = None) -> dict[str, Any] | None:
    """The Ollama server's own configuration as it logged it at start-up (the `server config` line of its log): the client cannot ask the
    server for its environment, so the LAST such line of the log is read. None if the log or the line is missing."""
    import re
    path = Path(log_path) if log_path else DEFAULT_SERVER_LOG
    try:
        lines = [l for l in path.read_text(encoding="utf-8", errors="replace").splitlines() if 'msg="server config"' in l]
    except OSError:
        return None
    if not lines:
        return None
    env_text = lines[-1].split('env="map[', 1)[-1]
    out: dict[str, Any] = {"log": str(path), "logged_at": lines[-1].split(" ", 1)[0].removeprefix("time=")}
    for k in SERVER_ENV_KEYS:
        m = re.search(rf"\b{k}:([^\s\]\"]*)", env_text)
        out[k] = m.group(1) if m else None
    out["planned_ok"] = all(out.get(k) == v for k, v in PLANNED_SERVER_ENV.items())
    return out


def ollama_model_info(base_url: str, model: str, client: Any = None, think: Any = None) -> dict[str, Any]:
    import httpx
    c = client or httpx.Client(timeout=30)
    version = c.get(f"{base_url}/api/version").json().get("version")
    from agents.ollama_adapter import MIN_OLLAMA_VERSION, check_min_version
    from agents.base import ProviderError
    try:  # a server older than 0.40.18 discards valid tool calls: refuse to snapshot (and so to run); the version is recorded below
        check_min_version(version)
    except ProviderError as exc:
        raise SystemExit(f"{exc}")
    entry = next((m for m in c.get(f"{base_url}/api/tags").json().get("models", []) if model in (m.get("name"), m.get("model"))), None)
    if entry is None:
        raise SystemExit(f"model {model!r} is not installed in Ollama at {base_url}")
    from agents.ollama_adapter import effective_think
    try:  # capabilities from `ollama show` (/api/show); decides the effective `think` value (audit I-05)
        shown = c.post(f"{base_url}/api/show", json={"model": model}).json()
        caps = shown.get("capabilities") if isinstance(shown, dict) else None
    except Exception:  # noqa: BLE001 - older server or transport problem: capabilities unknown, recorded as null
        caps = None
    caps = caps if isinstance(caps, list) else None
    if not caps or "tools" not in caps:  # audit I-07: refuse to snapshot (and so to run) a model without the tools capability
        raise SystemExit(f"model {model!r} does not list the 'tools' capability in `ollama show` (capabilities: {caps}); refusing")
    return {"ollama_version": version, "ollama_min_version": ".".join(map(str, MIN_OLLAMA_VERSION)), "model_digest": entry.get("digest"), "model_details": entry.get("details"),
            "capabilities": caps, "thinking_capable": bool(caps and "thinking" in caps),
            "think_config": think, "think_effective": effective_think(model, caps, think)}


def build(model_key: str, split: str, run_file: Path, command: str, client: Any = None,
          languages: list[str] | None = None, server_log: Path | None = None) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    from agents.registry import load_model_config
    from evaluation.splits import ALL_LANGUAGES, task_ids
    languages = list(languages or ALL_LANGUAGES)
    from evaluation.runner import SYSTEM_PROMPT_SHA256, TOOL_SCHEMA_SHA256, benchmark_version
    cfg = load_model_config()[model_key]
    info = ollama_model_info((cfg.get("base_url") or "http://127.0.0.1:11434").rstrip("/"), cfg["model"], client, cfg.get("think")) \
        if cfg.get("provider") == "ollama" else {}
    return {"captured_at": datetime.now(timezone.utc).isoformat(), "git_commit": _git("rev-parse", "HEAD"),
            "git_tracked_changes": _git("status", "--porcelain", "--untracked-files=no"), "command": command,
            "model_key": model_key, "model_config": cfg, **info, "split": split,
            "languages": languages, "expected_items": len(task_ids(split)) * len(languages), "run_file": run_file.as_posix(),
            "benchmark_version": benchmark_version(), "system_prompt_sha256": SYSTEM_PROMPT_SHA256,
            "tool_schema_sha256": TOOL_SCHEMA_SHA256,
            # Ollama server configuration (OLLAMA_NUM_PARALLEL=1 and OLLAMA_MAX_LOADED_MODELS=1 are part of the plan), from its own start-up log
            "server_env": server_env(server_log) if cfg.get("provider") == "ollama" else None,
            "file_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in HASHED_FILES},
            "python": platform.python_version(), "platform": platform.platform()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--split", required=True, choices=["pilot", "midsem", "v2", "full"])
    ap.add_argument("--languages", nargs="+", default=["en", "hinglish", "hi", "mr", "gu"], choices=["en", "hinglish", "hi", "mr", "gu"])
    ap.add_argument("--run-file", type=Path, required=True)
    ap.add_argument("--command", required=True)
    ap.add_argument("--server-log", type=Path, default=None, help=f"Ollama server log to read the server config from (default {DEFAULT_SERVER_LOG})")
    args = ap.parse_args(argv)
    out = args.run_file.with_suffix(".prerun.json")
    for p in (args.run_file, args.run_file.with_suffix(".quota.json"), out):
        if p.exists():
            ap.error(f"already exists (never overwritten; choose a new run file): {p}")
    snap = build(args.model, args.split, args.run_file, args.command, languages=args.languages, server_log=args.server_log)
    env = snap.get("server_env")
    if snap["model_config"].get("provider") == "ollama" and not (env and env.get("planned_ok")):
        ap.error("the Ollama server must run with OLLAMA_NUM_PARALLEL=1 and OLLAMA_MAX_LOADED_MODELS=1 (MODEL_PLAN.md); "
                 f"seen in its log: {env if env else 'no readable server log / no server config line'}")
    if snap["git_tracked_changes"]:
        ap.error(f"tracked files have uncommitted changes; commit first:\n{snap['git_tracked_changes']}")
    out.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"prerun -> {out} (commit {snap['git_commit'][:7]}, model digest {str(snap.get('model_digest'))[:12]}, "
          f"expected items {snap['expected_items']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
