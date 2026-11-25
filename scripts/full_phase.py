"""Full-run driver (MODEL_PLAN.md): for each model, in order: pre-run snapshot, the full run (`--split full`, all five languages: 500 items since benchmark 3.0, 375 in 2.x) into its own NEW run file,
`--resume` on a byte copy while items are missing or provider/runner-error rows remain, completeness check, manifest, observe_run. Run it in tmux; it never edits
tracked files. The Ollama server is restarted (same tmux session, same environment) if it is not answering.

    python scripts/full_phase.py --ts 20261124T200000Z --models local_qwen25_3b local_llama32_3b ...
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "runs"
FINAL = {"completed", "malformed_output", "step_limit_exceeded", "context_overflow", "output_truncated"}
SERVER_CMD = ("OLLAMA_MODELS=$HOME/FreeModel/models OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 "
              "ollama serve 2>&1 | tee -a $HOME/FreeModel/ollama-serve.log")


def expected_items() -> int:
    """Items of `--split full` in all five languages (3.0: 100 tasks x 5 = 500)."""
    sys.path.insert(0, str(ROOT))
    from evaluation.splits import ALL_LANGUAGES, task_ids
    return len(task_ids("full")) * len(ALL_LANGUAGES)


def completeness(files: list[Path], expected: int | None = None) -> dict:
    """Latest row per task id across the files (the rule run_pilot --resume uses); complete = `expected` items, all with a model outcome status."""
    expected = expected_items() if expected is None else expected
    latest: dict[str, dict] = {}
    for f in files:
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    latest[r["task_id"]] = r
    statuses: dict[str, int] = {}
    for r in latest.values():
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
    unresolved = sorted(t for t, r in latest.items() if r["status"] not in FINAL)
    return {"items": len(latest), "expected": expected, "unresolved": unresolved, "statuses": statuses,
            "complete": len(latest) == expected and not unresolved}


def server_up() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/version", timeout=5).read()
        return True
    except Exception:  # noqa: BLE001
        return False


def ensure_server() -> None:
    if server_up():
        return
    subprocess.run(["tmux", "kill-session", "-t", "ollama"], capture_output=True)
    subprocess.run(["tmux", "new-session", "-d", "-s", "ollama", SERVER_CMD], check=False)
    for _ in range(40):
        time.sleep(3)
        if server_up():
            return


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ts", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--max-resumes", type=int, default=3)
    args = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    from agents.registry import load_model_config
    cfg = load_model_config()
    status_file = RUNS / f"full_phase_{args.ts}.status.json"
    status: dict = {"ts": args.ts, "started": datetime.now(timezone.utc).isoformat(), "models": {}}

    def save() -> None:
        status_file.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def sh(cmd: list[str], out: Path) -> int:
        with out.open("w", encoding="utf-8") as fh:
            return subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT).returncode

    py = sys.executable
    for key in args.models:
        st = status["models"].setdefault(key, {"model": cfg[key]["model"]})
        stem = f"{key}_full_{args.ts}"
        run_file = RUNS / f"{stem}.jsonl"
        files = [run_file]
        ensure_server()
        cmd = [py, "-m", "evaluation.run_pilot", "--model", key, "--split", "full", "--max-attempts", "2", "--run-file", f"runs/{stem}.jsonl"]
        rc = sh([py, "-m", "analysis.prerun_snapshot", "--model", key, "--split", "full", "--run-file", f"runs/{stem}.jsonl", "--command", " ".join(cmd[1:])],
                RUNS / f"{stem}.prerun.console.txt")
        st["snapshot_rc"] = rc
        if rc != 0:
            st["error"] = f"pre-run snapshot refused (runs/{stem}.prerun.console.txt)"
            save()
            continue
        t0 = time.time()
        st["started"] = datetime.now(timezone.utc).isoformat()
        save()
        st["run_rc"] = sh(cmd, RUNS / f"{stem}.console.txt")
        comp = completeness(files)
        resumes = 0
        while not comp["complete"] and resumes < args.max_resumes:
            resumes += 1
            ensure_server()
            nxt = RUNS / f"{stem}_resume{resumes}.jsonl"
            prev = files[-1]
            shutil.copyfile(prev, nxt)                                   # resume only on a byte copy; the earlier file is kept
            if prev.with_suffix(".quota.json").exists():
                shutil.copyfile(prev.with_suffix(".quota.json"), nxt.with_suffix(".quota.json"))
            files.append(nxt)
            st[f"resume{resumes}_rc"] = sh(cmd[:-1] + [f"runs/{nxt.name}", "--resume"], RUNS / f"{stem}_resume{resumes}.console.txt")
            comp = completeness(files)
            save()
        st.update(seconds=round(time.time() - t0, 1), resumes=resumes, completeness=comp, run_files=[f"runs/{f.name}" for f in files])
        mcmd = [py, "-m", "analysis.run_manifest", "--prerun", f"runs/{stem}.prerun.json", "--out", f"runs/{stem}.manifest.json"]
        for f in files:
            mcmd += ["--run-file", f"runs/{f.name}"]
        sh(mcmd, RUNS / f"{stem}.manifest.console.txt")
        ocmd = [py, "-m", "analysis.observe_run", "--split", "full", "--manifest", f"runs/{stem}.manifest.json", "--out", f"analysis/results/{stem}"]
        for f in files:
            ocmd += ["--run-file", f"runs/{f.name}"]
        sh(ocmd, RUNS / f"{stem}.observe.console.txt")
        st["observe_dir"] = f"analysis/results/{stem}"
        st["done"] = bool(comp["complete"])
        save()
    status["finished"] = datetime.now(timezone.utc).isoformat()
    save()
    (RUNS / f"full_phase_{args.ts}.DONE").write_text("done\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
