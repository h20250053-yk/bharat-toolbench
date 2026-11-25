"""Single source of truth for the evaluation splits and languages (used by run_pilot and the analysis tools)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALL_LANGUAGES = ["en", "hinglish", "hi", "mr", "gu"]   # 3.0: 100 tasks x 5 languages = 500 items (2.x: 75 x 5 = 375)
MIDSEM_LANGUAGES = ["en", "hinglish", "hi", "mr"]      # the four languages of the historical 200-item mid-sem runs
SPLITS = ("pilot", "midsem", "v2", "full")


def task_ids(split: str) -> list[str]:
    if split == "pilot":
        return [f"T{i:02d}" for i in range(1, 6)]
    if split == "midsem":  # the 50 tasks of the mid-sem pilot study (Qwen 2.5 3B / Llama 3.2 3B runs)
        return [f"T{i:02d}" for i in range(1, 51)]
    if split == "v2":  # the 75 tasks of benchmark 2.x (T01-T75), to compare with the 2.1.0 runs
        return [f"T{i:02d}" for i in range(1, 76)]
    if split == "full":  # every task in the spec (T01-T100 since benchmark 3.0)
        spec = json.loads((ROOT / "benchmark" / "semantic_tasks.json").read_text(encoding="utf-8"))
        return [t["semantic_task_id"] for t in spec["tasks"]]
    raise ValueError(split)
