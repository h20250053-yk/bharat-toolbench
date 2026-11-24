"""Pilot phase driver (MODEL_PLAN.md): for each model, in order: wait for its pull, pre-run snapshot, 1-item smoke, `ollama ps` fit check,
pre-run snapshot, 25-item pilot (T01-T05 x 5 languages) into its own NEW run file, manifest, observe_run. Run it in tmux; it never edits tracked files.

    python scripts/pilot_phase.py --ts 20261124T190000Z --models local_qwen25_3b local_llama32_3b ... [--pulls ~/FreeModel/pulls]

Status goes to runs/pilot_phase_<ts>.status.json after every step. A model whose server pre-flight refuses it, or whose `ollama ps` is not
100% GPU, is NOT piloted (recorded); nothing is retried silently. No full run is ever started here.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
RESULTS = ROOT / "analysis" / "results"
LANGS = ["en", "hinglish", "hi", "mr", "gu"]


def pull_marker_name(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model) + ".done"


def ps_is_full_gpu(ps_text: str, model: str) -> bool | None:
    """True if `ollama ps` lists the model with PROCESSOR '100% GPU'; False if it lists it otherwise (CPU/GPU split or CPU); None if not listed."""
    for line in ps_text.splitlines():
        if line.split() and line.split()[0] == model:
            return "100% GPU" in line
    return None


def sh(cmd: list[str], out: Path | None = None, env: dict | None = None) -> int:
    with (out.open("w", encoding="utf-8") if out else open("/dev/null", "w")) as fh:
        return subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, env=env).returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ts", required=True, help="UTC timestamp used in every file name of this phase (YYYYMMDDTHHMMSSZ)")
    ap.add_argument("--models", nargs="+", required=True, help="model keys of config/models.yaml, in run order")
    ap.add_argument("--pulls", type=Path, default=None, help="directory with <model>.done markers written by the pull job; each model waits for its marker")
    ap.add_argument("--wait-minutes", type=int, default=180)
    args = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    from agents.registry import load_model_config
    cfg = load_model_config()
    status_file = RUNS / f"pilot_phase_{args.ts}.status.json"
    status: dict = {"ts": args.ts, "started": datetime.now(timezone.utc).isoformat(), "models": {}}

    def save() -> None:
        status_file.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    py = sys.executable
    for key in args.models:
        model = cfg[key]["model"]
        st = status["models"].setdefault(key, {"model": model})
        if args.pulls:
            marker = args.pulls / pull_marker_name(model)
            t0 = time.time()
            while not marker.exists():
                if time.time() - t0 > args.wait_minutes * 60:
                    st["error"] = f"pull marker {marker} not found after {args.wait_minutes} min"
                    break
                time.sleep(15)
            if "error" in st:
                save()
                continue
        st["pulled_at"] = datetime.now(timezone.utc).isoformat()
        save()
        for phase, extra, cap in (("smoke", ["--languages", "en", "--max-requests", "1"], "1 item"), ("pilot", [], "25 items")):
            stem = f"{key}_{phase}_{args.ts}"
            run_file = RUNS / f"{stem}.jsonl"
            cmd_run = [py, "-m", "evaluation.run_pilot", "--model", key, "--split", "pilot", *extra, "--max-attempts", "2", "--run-file", f"runs/{stem}.jsonl"]
            rc = sh([py, "-m", "analysis.prerun_snapshot", "--model", key, "--split", "pilot", "--run-file", f"runs/{stem}.jsonl",
                     "--command", " ".join(cmd_run[1:])], RUNS / f"{stem}.prerun.console.txt")
            st[f"{phase}_snapshot_rc"] = rc
            if rc != 0:
                st["error"] = f"{phase}: pre-run snapshot refused (see runs/{stem}.prerun.console.txt)"
                save()
                break
            t0 = time.time()
            rc = sh(cmd_run, RUNS / f"{stem}.console.txt")
            st[f"{phase}_run_rc"] = rc
            st[f"{phase}_seconds"] = round(time.time() - t0, 1)
            st[f"{phase}_run_file"] = f"runs/{stem}.jsonl"
            if phase == "smoke":
                ps = subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout
                (RUNS / f"{key}_ps_{args.ts}.txt").write_text(ps, encoding="utf-8")
                st["ollama_ps"] = ps.strip()
                st["full_gpu"] = ps_is_full_gpu(ps, model)
                if rc != 0 or st["full_gpu"] is not True:
                    st["error"] = (f"smoke run exit {rc}" if rc != 0 else f"`ollama ps` does not show {model} on 100% GPU ({st['full_gpu']}): not piloted")
                    save()
                    break
            else:
                sh([py, "-m", "analysis.run_manifest", "--prerun", f"runs/{stem}.prerun.json", "--run-file", f"runs/{stem}.jsonl",
                    "--out", f"runs/{stem}.manifest.json"], RUNS / f"{stem}.manifest.console.txt")
                sh([py, "-m", "analysis.observe_run", "--run-file", f"runs/{stem}.jsonl", "--split", "pilot", "--manifest", f"runs/{stem}.manifest.json",
                    "--out", f"analysis/results/{stem}"], RUNS / f"{stem}.observe.console.txt")
                st["observe_dir"] = f"analysis/results/{stem}"
            save()
        st["done"] = "error" not in st
        save()
    status["finished"] = datetime.now(timezone.utc).isoformat()
    save()
    (RUNS / f"pilot_phase_{args.ts}.DONE").write_text("done\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
