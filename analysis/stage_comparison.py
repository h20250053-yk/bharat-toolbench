"""Benchmark 3.0 results across the three tool stages, model by model (nothing typed in: every number comes from the run files).

    python -m analysis.stage_comparison --v2 runs/full_phase_20261124T105853Z.status.json --v3 runs/full_phase_20261125T224932Z.status.json

Stage 1 = T01-T75 with 6 tools (the 2.1.0 runs), stage 2 = T76-T100 with 12 tools, stage 3 = T101-T200 with 20 tools (the v3_new runs).
Every row is RE-SCORED with the current scorer (so all three stages are graded by the same rules); rescoring.json lists every item whose
stored run-time score differs. A model enters as soon as its v3_new run is done (status file `done`), so the report can be rebuilt after
each model. Writes analysis/results_v3/ (CSV + JSON), analysis/figures_v3/ (PNG at 2x + PDF, captions.md) and RESULTS_V3.md.

Caveat built into every output: the stages differ in their TASKS as well as in the number of tools, so a stage difference is the effect of
both. The difficulty-level table (same Easy/Medium/Hard/Very Hard rule for all 200 tasks) is the fairer comparison.
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LANGS = ["en", "hinglish", "hi", "mr", "gu"]
LANG_NAME = {"en": "English", "hinglish": "Hinglish", "hi": "Hindi", "mr": "Marathi", "gu": "Gujarati"}
STAGES = [("S1", "T01-T75", 1, 75, 6), ("S2", "T76-T100", 76, 100, 12), ("S3", "T101-T200", 101, 200, 20)]
STAGE_LABEL = {s: f"{r} ({n} tools)" for s, r, _, _, n in STAGES}
GROUPS = [("Tatkal", 101, 120), ("Berths", 121, 130), ("Boarding change", 131, 141), ("Meals", 142, 157), ("Platform & live", 158, 169),
          ("TDR", 170, 180), ("Complaints", 181, 190), ("Mixed", 191, 200)]
NEW_TOOLS = ["check_tatkal_availability", "book_tatkal_ticket", "get_berth_availability", "get_platform_info", "change_boarding_point",
             "order_meal", "file_tdr", "raise_complaint"]
STATUSES = ["completed", "output_truncated", "malformed_output", "step_limit_exceeded", "context_overflow"]
UNRELIABLE_SHARE = 0.5   # same rule as results_data: more than half of the replies unusable (malformed) => flagged, not ranked
TM_SHOW = [("tool_use_rate", "uses tools"), ("selection_recall", "selection recall"), ("selection_precision", "selection precision"),
           ("first_call_accuracy", "first call right"), ("argument_accuracy", "argument accuracy"), ("sequence_accuracy", "order respected"),
           ("unwanted_action", "unwanted state change"), ("prohibited_attempt", "forbidden action tried")]


def tnum(t: str) -> int:
    return int(t[1:])


def stage_of(t: str) -> str:
    n = tnum(t)
    return next(s for s, _, a, b, _ in STAGES if a <= n <= b)


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
    """Difference p2 - p1 with the Newcombe (Wilson hybrid) 95% interval; independent samples (different tasks)."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p2 - p1
    return d, d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2), d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def status_from_files(ts: str, split: str, root: Path) -> dict[str, Any]:
    """The status of a run rebuilt from its files (for a run still in progress, whose status file is not committed): a model is done when
    its manifest exists; its run files are the main file and the --resume copies (<stem>_resume<N>.jsonl) in order."""
    models = {}
    for key in PLAN_ORDER:
        stem = f"{key}_{split}_{ts}"
        main = root / "runs" / f"{stem}.jsonl"
        if not main.exists():
            continue
        resumes = sorted((root / "runs").glob(f"{stem}_resume*.jsonl"), key=lambda p: int(p.stem.rsplit("resume", 1)[1]))
        models[key] = {"done": (root / "runs" / f"{stem}.manifest.json").exists(),
                       "run_files": [str(p.relative_to(root)) for p in [main, *resumes]]}
    return {"ts": ts, "models": models}


def load_status(path: Path | dict[str, Any], root: Path) -> dict[str, dict[str, Any]]:
    """{model_key: {task_id: latest row}} for every model whose run is done (latest row per item over its run files, as --resume does)."""
    st = path if isinstance(path, dict) else json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for key, m in st["models"].items():
        if not m.get("done"):
            continue
        latest: dict[str, dict[str, Any]] = {}
        for f in m["run_files"]:
            for r in read_jsonl(root / f):
                latest[r["task_id"]] = r
        out[key] = latest
    return out


# ================================================================================================ data
class Data:
    def __init__(self, v2: Path, v3: Path | dict[str, Any], root: Path = ROOT):
        from evaluation.scorer import score_both
        from analysis.observe_run import classify
        from analysis import tool_metrics as TM
        from analysis.null_baseline import null_baseline
        from benchmark.coverage_report import compute as coverage
        self.root = root
        self.gold = json.loads((root / "benchmark" / "gold_labels.json").read_text(encoding="utf-8"))
        specs = json.loads((root / "benchmark" / "semantic_tasks.json").read_text(encoding="utf-8"))["tasks"]
        self.category = {s["semantic_task_id"]: s["category"] for s in specs}
        self.level = {t: v["difficulty"] for t, v in coverage()["tasks"].items()}
        r2, r3 = load_status(v2, root), load_status(v3, root)
        self.models = [k for k in PLAN_ORDER if k in r3 and k in r2]          # a model enters once its v3_new run is done
        self.rows: dict[str, dict[str, dict[str, Any]]] = {}
        self.rescore_changes: dict[str, list[dict[str, Any]]] = {}
        self.items: dict[str, dict[str, dict[str, Any]]] = {}
        for k in self.models:
            rows = {t: r for t, r in r2[k].items() if tnum(r["semantic_task_id"]) <= 75}
            rows.update({t: r for t, r in r3[k].items() if tnum(r["semantic_task_id"]) >= 76})
            changes = []
            for t, r in rows.items():
                g = self.gold[r["semantic_task_id"]]
                if r.get("status") in ("provider_error", "runner_error"):
                    new_l, new_s = {"scored": False, "task_success": None}, {"scored": False, "task_success": None}
                else:
                    new_l, new_s = score_both(r, g, r.get("state_snapshot"))
                old = (r.get("score") or {}).get("task_success")
                if bool(old) != bool(new_l.get("task_success")):
                    changes.append({"task_id": t, "stored": old, "rescored": new_l.get("task_success"),
                                    "labels": new_l.get("failure_labels", [])})
                r["score"], r["score_strict"] = new_l, new_s
                r["_primary"] = classify(r, g)[0]
            self.rows[k], self.rescore_changes[k] = rows, changes
            self.items[k] = {t: TM.item_metrics(r, self.gold[r["semantic_task_id"]]) for t, r in rows.items()}
        self.TM = TM
        self.null_pass = set(null_baseline("needs_clarification", {t: g for t, g in self.gold.items() if not t.startswith("_")}))
        self.flagged = {k for k in self.models
                        if sum(r.get("status") == "malformed_output" for r in self.rows[k].values()) / max(1, len(self.rows[k])) > UNRELIABLE_SHARE}

    def ids(self, k: str, stage: str | None = None, lang: str | None = None, lo: int | None = None, hi: int | None = None) -> list[str]:
        out = []
        for t, r in self.rows[k].items():
            n = tnum(r["semantic_task_id"])
            if (stage is None or stage_of(r["semantic_task_id"]) == stage) and (lang is None or r["language"] == lang) \
                    and (lo is None or lo <= n <= hi):
                out.append(t)
        return sorted(out, key=lambda t: (tnum(t.split("_")[0]), LANGS.index(t.split("_", 1)[1])))

    def rate(self, k: str, ids: list[str], strict: bool = False) -> dict[str, Any]:
        n = len(ids)
        s = sum(bool((self.rows[k][t]["score_strict" if strict else "score"] or {}).get("task_success")) for t in ids)
        lo, hi = wilson(s, n)
        return {"k": s, "n": n, "rate": s / n if n else float("nan"), "lo": lo, "hi": hi}

    def name(self, k: str) -> str:
        return DISPLAY[k] + (" †" if k in self.flagged else "")


PLAN_ORDER = ["local_qwen25_3b", "local_llama32_3b", "local_llama31_8b", "local_deepseek_r1_8b", "local_qwen25_14b", "local_gpt_oss_20b",
              "local_gemma4_26b", "local_mistral_small32_24b"]
DISPLAY = {"local_qwen25_3b": "Qwen2.5-3B", "local_llama32_3b": "Llama-3.2-3B", "local_llama31_8b": "Llama-3.1-8B",
           "local_deepseek_r1_8b": "DeepSeek-R1-8B", "local_qwen25_14b": "Qwen2.5-14B", "local_gpt_oss_20b": "gpt-oss-20B",
           "local_gemma4_26b": "Gemma-4-26B-A4B", "local_mistral_small32_24b": "Mistral-Small-3.2-24B"}
COLOR = {"local_qwen25_3b": "#56B4E9", "local_llama32_3b": "#E69F00", "local_llama31_8b": "#D55E00", "local_deepseek_r1_8b": "#999999",
         "local_qwen25_14b": "#0072B2", "local_gpt_oss_20b": "#009E73", "local_gemma4_26b": "#CC79A7", "local_mistral_small32_24b": "#F0E442"}
STAGE_COLOR = {"S1": "#9ecae1", "S2": "#4292c6", "S3": "#08306b"}


# ================================================================================================ tables
def tables(D: Data) -> dict[str, Any]:
    T: dict[str, Any] = {"models": D.models, "flagged": sorted(D.flagged), "stages": {s: {"tasks": r, "tools": n} for s, r, _, _, n in STAGES}}
    T["null_baseline"] = {s: {"pass": sum(1 for t in D.null_pass if stage_of(t) == s), "tasks": b - a + 1} for s, _, a, b, _ in STAGES}
    T["success"], T["language"], T["status"], T["failures"], T["tools"], T["groups"], T["difficulty"], T["category"] = {}, {}, {}, {}, {}, {}, {}, {}
    T["diff_vs_s1"], T["new_tools"] = {}, {}
    for k in D.models:
        T["success"][k] = {s: {"lenient": D.rate(k, D.ids(k, s)), "strict": D.rate(k, D.ids(k, s), strict=True)} for s, *_ in STAGES}
        T["success"][k]["all"] = {"lenient": D.rate(k, D.ids(k)), "strict": D.rate(k, D.ids(k), strict=True)}
        T["diff_vs_s1"][k] = {}
        for s in ("S2", "S3"):
            a, b = T["success"][k]["S1"]["lenient"], T["success"][k][s]["lenient"]
            d, lo, hi = newcombe(a["k"], a["n"], b["k"], b["n"])
            T["diff_vs_s1"][k][s] = {"diff": d, "lo": lo, "hi": hi}
        T["language"][k] = {s: {l: D.rate(k, D.ids(k, s, l)) for l in LANGS} for s, *_ in STAGES}
        T["status"][k] = {s: dict(Counter(D.rows[k][t]["status"] for t in D.ids(k, s))) for s, *_ in STAGES}
        T["failures"][k] = {s: dict(Counter(D.rows[k][t]["_primary"] for t in D.ids(k, s))) for s, *_ in STAGES}
        T["tools"][k] = {}
        for s, *_ in STAGES:
            summ = D.TM.summarize([D.items[k][t] for t in D.ids(k, s)])
            T["tools"][k][s] = {m: {x: summ[m][x] for x in ("value", "lo", "hi", "n")} for m, _ in TM_SHOW if m in summ}
        T["groups"][k] = {g: D.rate(k, D.ids(k, lo=a, hi=b)) for g, a, b in GROUPS}
        T["difficulty"][k] = {s: {lv: D.rate(k, [t for t in D.ids(k, s) if D.level[D.rows[k][t]["semantic_task_id"]] == lv])
                                  for lv in ("Easy", "Medium", "Hard", "Very Hard")} for s, *_ in STAGES}
        T["category"][k] = {s: {c: D.rate(k, [t for t in D.ids(k, s) if D.category[D.rows[k][t]["semantic_task_id"]] == c])
                                for c in sorted({D.category[D.rows[k][t]["semantic_task_id"]] for t in D.ids(k, s)})} for s, *_ in STAGES}
        # new tools (stage 3): how often a required new tool was called at all, and how often it was called when the gold does not use it
        need, hit, spurious, items_without = Counter(), Counter(), Counter(), Counter()
        for t in D.ids(k, "S3"):
            g = D.gold[D.rows[k][t]["semantic_task_id"]]
            req = {c["tool"] for c in g["required_calls"] if not c.get("optional")}
            allowed = {c["tool"] for c in g["required_calls"]}  # required or optional in the gold
            called = {e["tool"] for e in D.TM.calls_of(D.rows[k][t])}
            for tool in NEW_TOOLS:
                if tool in req:
                    need[tool] += 1
                    hit[tool] += tool in called
                elif tool not in allowed:
                    items_without[tool] += 1
                    spurious[tool] += tool in called
        T["new_tools"][k] = {tool: {"required_items": need[tool], "called_when_required": hit[tool],
                                    "recall": hit[tool] / need[tool] if need[tool] else float("nan"),
                                    "not_needed_items": items_without[tool], "called_when_not_needed": spurious[tool]} for tool in NEW_TOOLS}
    T["rescoring"] = {k: {"changed": len(v), "items": v} for k, v in D.rescore_changes.items()}
    T["lang_gap"], T["lang_tools"], T["lang_pooled"] = language_view(D)
    return T


# ================================================================================================ language view
INDIC = ["hinglish", "hi", "mr", "gu"]
STATION_ERRORS = {"INVALID_STATION", "STATION_NOT_FOUND"}
# station-error buckets (an item can be in more than one):
#   not_resolved   resolve_station -> STATION_NOT_FOUND: the model's name for the place could not be mapped (the word-ending / spelling test)
#   name_not_code  another tool -> station error with a real-looking value: a city name, a made-up or wrong code (resolve_station skipped)
#   placeholder    the value sent was empty or a placeholder / unfilled template ("next_stop", "resolve_station_result.Mumbai", "<code>")
# A call is not counted when the gold expects exactly that error from that tool (a deliberate trap).
STATION_BUCKETS = ("not_resolved", "name_not_code", "placeholder")
_PLACEHOLDER_RE = re.compile(r"[{}<>$]|^[a-z_]+\.\S|\bresult\b|_result\b|\b(next|previous|prev|current|last|first)[ _-]?(stop|station)\b"
                             r"|^(unknown|null|none|n/?a|tbd|x+|station|station[ _]?code|code|city|source|destination)$", re.I)
_STATION_KEYS = ("station", "source", "destination", "name")


def _station_value(e: dict[str, Any]) -> Any:
    """The station value behind a station error: quoted in the environment's message, else the first station-like argument."""
    msg = str(((e.get("observation") or {}).get("error") or {}).get("message") or "")
    m = re.search(r"(?:Unknown station code: |No station matches )(.+?)\.?$", msg)
    if m:
        try:
            return ast.literal_eval(m.group(1))
        except (ValueError, SyntaxError):
            pass
    args = e.get("arguments") if isinstance(e.get("arguments"), dict) else {}
    return next((args[k] for k in _STATION_KEYS if k in args), None)


def is_placeholder(value: Any) -> bool:
    return not isinstance(value, str) or not value.strip() or bool(_PLACEHOLDER_RE.search(value.strip()))


def station_error_buckets(calls: list[dict[str, Any]], gold_task: dict[str, Any], error_code) -> set[str]:
    """Which station-error buckets an item's calls fall into (see STATION_BUCKETS); traps the gold expects are not counted."""
    traps = {(c["tool"], c["expected_error"]) for c in gold_task.get("required_calls", []) if c.get("expected_error")}
    out: set[str] = set()
    for e in calls:
        code = error_code(e)
        if code not in STATION_ERRORS or (e.get("tool"), code) in traps:
            continue
        if is_placeholder(_station_value(e)):
            out.add("placeholder")
        elif e.get("tool") == "resolve_station" and code == "STATION_NOT_FOUND":
            out.add("not_resolved")
        else:
            out.add("name_not_code")
    return out


BOOT_SEED, BOOT_B = 20261126, 4000


def _boot(values_by_task: list[float]) -> tuple[float, float, float]:
    """Mean of per-task values with a 95% bootstrap interval over tasks (tasks resampled; a task's five languages stay together)."""
    import random
    n = len(values_by_task)
    if not n:
        return (float("nan"),) * 3
    rng = random.Random(BOOT_SEED)
    m = sum(values_by_task) / n
    sims = sorted(sum(values_by_task[rng.randrange(n)] for _ in range(n)) / n for _ in range(BOOT_B))
    return m, sims[int(0.025 * BOOT_B)], sims[int(0.975 * BOOT_B) - 1]


def language_view(D: Data) -> tuple[dict, dict, dict]:
    """Does the language matter more when there are more tools?
    gap  = per task, English success minus the mean success of the four Indian-language versions (Hinglish, Hindi, Marathi, Gujarati),
           averaged over the stage's tasks: PAIRED (same task, same gold), bootstrap 95% interval over tasks;
           spread = best minus worst language; change = stage-3 gap minus stage-1 gap (independent task sets: intervals combined).
    tools per language and stage: selection recall, argument accuracy, and the items with a station error (INVALID_STATION /
           STATION_NOT_FOUND), split into STATION_BUCKETS; only not_resolved is the word-ending / spelling problem of round one,
           and errors the gold expects (traps) are not counted.
    pooled: each language's success per stage over all models not flagged unreliable."""
    from analysis.observe_run import _error_code
    gap, tools = {}, {}
    for k in D.models:
        gap[k], tools[k] = {}, {}
        for s, *_ in STAGES:
            ids = D.ids(k, s)
            by_task: dict[str, dict[str, bool]] = defaultdict(dict)
            for t in ids:
                r = D.rows[k][t]
                by_task[r["semantic_task_id"]][r["language"]] = bool(r["score"].get("task_success"))
            diffs = [float(v["en"]) - sum(float(v[l]) for l in INDIC) / 4 for v in by_task.values() if len(v) == 5]
            m, lo, hi = _boot(diffs)
            rates = {l: D.rate(k, D.ids(k, s, l))["rate"] for l in LANGS}
            gap[k][s] = {"gap": m, "lo": lo, "hi": hi, "tasks": len(diffs), "spread": max(rates.values()) - min(rates.values()),
                         "best": max(rates, key=rates.get), "worst": min(rates, key=rates.get)}
            tools[k][s] = {}
            for l in LANGS:
                items = [D.items[k][t] for t in D.ids(k, s, l)]
                summ = D.TM.summarize(items)
                bk = [station_error_buckets(D.TM.calls_of(D.rows[k][t]), D.gold[D.rows[k][t]["semantic_task_id"]], _error_code) for t in D.ids(k, s, l)]
                tools[k][s][l] = {"selection_recall": summ["selection_recall"]["value"], "argument_accuracy": summ["argument_accuracy"]["value"],
                                  "station_error_items": sum(bool(b) for b in bk), "items": len(items),
                                  **{f"station_{b}_items": sum(b in x for x in bk) for b in STATION_BUCKETS}}
        a, b = gap[k]["S1"], gap[k]["S3"]
        half = math.sqrt(((a["hi"] - a["lo"]) / 2) ** 2 + ((b["hi"] - b["lo"]) / 2) ** 2)
        gap[k]["change_S3_vs_S1"] = {"diff": b["gap"] - a["gap"], "lo": b["gap"] - a["gap"] - half, "hi": b["gap"] - a["gap"] + half}
    reliable = [k for k in D.models if k not in D.flagged] or D.models
    pooled = {s: {l: (lambda kk, nn: {"k": kk, "n": nn, "rate": kk / nn if nn else float("nan"), "lo": wilson(kk, nn)[0], "hi": wilson(kk, nn)[1]})(
        sum(D.rate(k, D.ids(k, s, l))["k"] for k in reliable), sum(D.rate(k, D.ids(k, s, l))["n"] for k in reliable)) for l in LANGS}
        for s, *_ in STAGES}
    pooled["models"] = reliable
    return gap, tools, pooled


# ================================================================================================ files
def pc(x: float, d: int = 1) -> str:
    return "n/a" if x != x else f"{100 * x:.{d}f}"


def ci(r: dict[str, Any]) -> str:
    return "n/a" if not r["n"] else f"{pc(r['rate'])} [{pc(r['lo'])}, {pc(r['hi'])}]"


def md_table(header: list[str], rows: list[list[Any]]) -> str:
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]) + "\n"


def write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def write_tables(D: Data, T: dict[str, Any], out: Path) -> None:
    S = [s for s, *_ in STAGES]
    write_csv(out / "stage_success.csv", ["model", "stage", "tasks", "tools", "items", "successes", "rate", "ci_lo", "ci_hi", "strict_rate"],
              [[k, s, r, n, T["success"][k][s]["lenient"]["n"], T["success"][k][s]["lenient"]["k"], round(T["success"][k][s]["lenient"]["rate"], 4),
                round(T["success"][k][s]["lenient"]["lo"], 4), round(T["success"][k][s]["lenient"]["hi"], 4), round(T["success"][k][s]["strict"]["rate"], 4)]
               for k in D.models for s, r, _, _, n in STAGES])
    write_csv(out / "stage_language.csv", ["model", "stage", "language", "items", "successes", "rate"],
              [[k, s, l, x["n"], x["k"], round(x["rate"], 4)] for k in D.models for s in S for l, x in T["language"][k][s].items()])
    write_csv(out / "stage_status.csv", ["model", "stage", *STATUSES, "other"],
              [[k, s, *[T["status"][k][s].get(x, 0) for x in STATUSES], sum(v for x, v in T["status"][k][s].items() if x not in STATUSES)]
               for k in D.models for s in S])
    prim = sorted({p for k in D.models for s in S for p in T["failures"][k][s]})
    write_csv(out / "stage_failures.csv", ["model", "stage", *prim], [[k, s, *[T["failures"][k][s].get(p, 0) for p in prim]] for k in D.models for s in S])
    write_csv(out / "stage_tool_metrics.csv", ["model", "stage", "metric", "value", "ci_lo", "ci_hi", "n"],
              [[k, s, m, round(v["value"], 4) if v["value"] == v["value"] else "", round(v["lo"], 4) if v["lo"] == v["lo"] else "",
                round(v["hi"], 4) if v["hi"] == v["hi"] else "", v["n"]] for k in D.models for s in S for m, v in T["tools"][k][s].items()])
    write_csv(out / "stage3_groups.csv", ["model", "group", "items", "successes", "rate"],
              [[k, g, x["n"], x["k"], round(x["rate"], 4)] for k in D.models for g, x in T["groups"][k].items()])
    write_csv(out / "stage_difficulty.csv", ["model", "stage", "level", "items", "successes", "rate"],
              [[k, s, lv, x["n"], x["k"], round(x["rate"], 4) if x["n"] else ""] for k in D.models for s in S for lv, x in T["difficulty"][k][s].items()])
    write_csv(out / "stage3_new_tools.csv", ["model", "tool", "required_items", "called_when_required", "not_needed_items", "called_when_not_needed"],
              [[k, tool, v["required_items"], v["called_when_required"], v["not_needed_items"], v["called_when_not_needed"]]
               for k in D.models for tool, v in T["new_tools"][k].items()])
    write_csv(out / "language_gap_by_stage.csv", ["model", "stage", "tasks", "english_minus_indic_pp", "ci_lo", "ci_hi", "spread_pp", "best", "worst"],
              [[k, s, g["tasks"], round(100 * g["gap"], 2), round(100 * g["lo"], 2), round(100 * g["hi"], 2), round(100 * g["spread"], 2), g["best"], g["worst"]]
               for k in D.models for s in S for g in [T["lang_gap"][k][s]]])
    write_csv(out / "language_tools_by_stage.csv", ["model", "stage", "language", "items", "selection_recall", "argument_accuracy", "station_error_items"]
              + [f"station_{b}_items" for b in STATION_BUCKETS],
              [[k, s, l, v["items"], round(v["selection_recall"], 4) if v["selection_recall"] == v["selection_recall"] else "",
                round(v["argument_accuracy"], 4) if v["argument_accuracy"] == v["argument_accuracy"] else "", v["station_error_items"]]
               + [v[f"station_{b}_items"] for b in STATION_BUCKETS]
               for k in D.models for s in S for l, v in T["lang_tools"][k][s].items()])
    (out / "stages.json").write_text(json.dumps(T, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    (out / "rescoring.json").write_text(json.dumps(T["rescoring"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# ================================================================================================ figures
def figures(D: Data, T: dict[str, Any], out: Path) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import Patch
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 10,
                         "axes.titleweight": "bold", "figure.dpi": 100, "pdf.fonttype": 42})
    out.mkdir(parents=True, exist_ok=True)
    caps: list[str] = []
    ms = D.models
    S = [s for s, *_ in STAGES]

    def save(fig: Any, name: str, cap: str) -> None:
        fig.savefig(out / f"{name}.png", dpi=200, bbox_inches="tight", facecolor="white")
        fig.savefig(out / f"{name}.pdf", bbox_inches="tight", facecolor="white")
        plt.close(fig)
        caps.append(f"## {name}\n\n{cap}\n")

    note = "Stages differ in tasks as well as in the number of tools; error bars = 95% Wilson intervals."
    # 1. success per stage per model
    fig, ax = plt.subplots(figsize=(max(6, 1.3 * len(ms) + 2), 4.2))
    x, w = np.arange(len(ms)), 0.26
    for j, s in enumerate(S):
        vals = [T["success"][k][s]["lenient"] for k in ms]
        ax.bar(x + (j - 1) * w, [100 * v["rate"] for v in vals], w, color=STAGE_COLOR[s], edgecolor="black", lw=0.5, label=STAGE_LABEL[s])
        ax.errorbar(x + (j - 1) * w, [100 * v["rate"] for v in vals],
                    yerr=[[max(0, 100 * (v["rate"] - v["lo"])) for v in vals], [max(0, 100 * (v["hi"] - v["rate"])) for v in vals]],
                    fmt="none", color="black", capsize=2, lw=0.8)
        for i, v in enumerate(vals):
            ax.text(x[i] + (j - 1) * w, 100 * v["hi"] + 1.2, f"{100 * v['rate']:.0f}", ha="center", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels([D.name(k) for k in ms], rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("task success (%)")
    ax.set_ylim(0, 112)
    ax.set_title("Task success by tool stage", pad=22)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="lower left", bbox_to_anchor=(0, 1.0))
    save(fig, "figS1_stage_success", "Task success (lenient scorer, re-scored) of each model in the three tool stages: T01-T75 with 6 tools "
         "(2.1.0 runs), T76-T100 with 12 tools and T101-T200 with 20 tools (3.0 runs), all five languages. " + note)

    # 1b. phone version: one panel per stage, horizontal bars
    fig, axs = plt.subplots(3, 1, figsize=(5.2, 2.0 + 0.55 * len(ms) * 3), sharex=True)
    for ax, (s, r, _, _, n) in zip(axs, STAGES):
        vals = [T["success"][k][s]["lenient"] for k in ms]
        y = np.arange(len(ms))[::-1]
        ax.barh(y, [100 * v["rate"] for v in vals], color=[COLOR[k] for k in ms], edgecolor="black", lw=0.5)
        for yy, v in zip(y, vals):
            ax.text(100 * v["rate"] + 1, yy, f"{100 * v['rate']:.0f}%", va="center", fontsize=11)
        ax.set_yticks(y)
        ax.set_yticklabels([D.name(k) for k in ms], fontsize=11)
        ax.set_title(f"{r}: {n} tools", fontsize=13, loc="left")
        ax.set_xlim(0, 110)
    axs[-1].set_xlabel("task success (%)", fontsize=11)
    fig.tight_layout()
    save(fig, "figS1_blog_stage_success", "Phone-sized version of figS1: one panel per tool stage. " + note)

    # 2. selection recall / precision / unwanted actions vs number of tools
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.6))
    tools_n = [n for *_, n in STAGES]
    for ax, (m, lab) in zip(axs, [("selection_recall", "selection recall (%)"), ("selection_precision", "selection precision (%)"),
                                   ("unwanted_action", "items with an unwanted state change (%)")]):
        for k in ms:
            ys = [100 * T["tools"][k][s][m]["value"] for s in S]
            ax.plot(tools_n, ys, marker="o", color=COLOR[k], label=D.name(k), lw=1.6)
        ax.set_xticks(tools_n)
        ax.set_xticklabels([f"{n}\n({r})" for _, r, _, _, n in STAGES], fontsize=7.5)
        ax.set_xlabel("tools offered (tasks)")
        ax.set_ylabel(lab)
        ax.set_ylim(0, 100 if m != "unwanted_action" else max(10, 5 + max(100 * T["tools"][k][s][m]["value"] for k in ms for s in S)))
    fig.legend(handles=[Patch(color=COLOR[k], label=D.name(k)) for k in ms], frameon=False, fontsize=8, ncol=4, loc="lower center",
               bbox_to_anchor=(0.5, -0.12))
    fig.suptitle("Tool selection as the toolset grows", fontweight="bold")
    fig.tight_layout()
    save(fig, "figS2_selection_by_stage", "Selection recall (share of the required tools the model called), selection precision (share of its calls "
         "that the gold needs) and the share of items with any state change the user did not ask for (booking, cancellation, waitlist, Tatkal "
         "booking, boarding change, meal, TDR or complaint), for 6, 12 and 20 offered tools. " + note)

    # 3. language x stage heatmap
    fig, ax = plt.subplots(figsize=(11, 0.5 * len(ms) + 1.6))
    M = np.array([[100 * T["language"][k][s][l]["rate"] for s in S for l in LANGS] for k in ms])
    im = ax.imshow(M, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=7.5, color="white" if M[i, j] > 55 else "black")
    short = {"en": "Eng", "hinglish": "Hgl", "hi": "Hin", "mr": "Mar", "gu": "Guj"}
    ax.set_xticks(range(15))
    ax.set_xticklabels([short[l] for _ in S for l in LANGS], fontsize=7.5)
    for j, (s, r, _, _, n) in enumerate(STAGES):
        ax.text(2 + 5 * j, -0.62, f"{r} ({n} tools)", ha="center", fontsize=8.5, fontweight="bold")
        if j:
            ax.axvline(5 * j - 0.5, color="black", lw=1.2)
    ax.set_yticks(range(len(ms)))
    ax.set_yticklabels([D.name(k) for k in ms], fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.025, label="task success (%)")
    save(fig, "figS3_language_by_stage", "Task success per model, language and tool stage (75, 25 and 100 items per language in stages 1, 2 and 3). " + note)

    # 4. stage-3 task groups
    fig, ax = plt.subplots(figsize=(9, 0.5 * len(ms) + 1.6))
    G = [g for g, *_ in GROUPS]
    M = np.array([[100 * T["groups"][k][g]["rate"] for g in G] for k in ms])
    im = ax.imshow(M, cmap="Greens", vmin=0, vmax=100, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=8, color="white" if M[i, j] > 55 else "black")
    ax.set_xticks(range(len(G)))
    ax.set_xticklabels([f"{g}\n(T{a}-T{b})" for g, a, b in GROUPS], fontsize=7.5)
    ax.set_yticks(range(len(ms)))
    ax.set_yticklabels([D.name(k) for k in ms], fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.025, label="task success (%)")
    ax.set_title("20-tool stage: success by service")
    save(fig, "figS4_stage3_services", "Task success in the 20-tool stage (T101-T200, all five languages) per service group: Tatkal, berths, "
         "boarding-point change, meals, platform and live status, TDR, complaints, and mixed tasks.")

    # 5. outcome mix per stage (pooled over reliable models)
    reliable = [k for k in ms if k not in D.flagged] or ms
    order = ["success", "wrong_answer", "missing_required_call", "tool_argument_error", "missing_booking", "unsafe_action", "format_only",
             "output_truncated", "malformed_model_output", "step_limit", "context_overflow", "infra_error", "other"]
    colors = {"success": "#2E7D32", "wrong_answer": "#EF6C00", "format_only": "#F9A825", "tool_argument_error": "#C62828",
              "missing_required_call": "#AD1457", "missing_booking": "#6A1B9A", "unsafe_action": "#000000", "output_truncated": "#546E7A",
              "malformed_model_output": "#90A4AE", "step_limit": "#8D6E63", "context_overflow": "#A1887F", "infra_error": "#CFD8DC", "other": "#BDBDBD"}
    labels = {"success": "success", "wrong_answer": "wrong answer", "format_only": "only the final block failed", "tool_argument_error": "bad tool arguments",
              "missing_required_call": "required call missing", "missing_booking": "requested action missing", "unsafe_action": "unwanted / forbidden action",
              "output_truncated": "output cut at 2048 tokens", "malformed_model_output": "reply discarded / malformed", "step_limit": "step limit",
              "context_overflow": "context overflow", "infra_error": "infrastructure error", "other": "other"}
    fig, ax = plt.subplots(figsize=(7, 3.4))
    left = np.zeros(3)
    tot = [sum(sum(T["failures"][k][s].values()) for k in reliable) for s in S]
    for p in order:
        v = np.array([100 * sum(T["failures"][k][s].get(p, 0) for k in reliable) / max(1, tot[i]) for i, s in enumerate(S)])
        if v.any():
            ax.barh(range(3), v, left=left, color=colors[p], label=labels[p], edgecolor="white", lw=0.4)
            left += v
    ax.set_yticks(range(3))
    ax.set_yticklabels([STAGE_LABEL[s] for s in S])
    ax.invert_yaxis()
    ax.set_xlabel("share of items (%)")
    ax.legend(frameon=False, fontsize=7, bbox_to_anchor=(1.01, 1), loc="upper left")
    ax.set_title("What happened, by stage (all reliable models pooled)")
    save(fig, "figS5_outcomes_by_stage", "Primary outcome of every item (first matching class of analysis/observe_run.classify), pooled over the "
         f"models not flagged as unreliable ({len(reliable)} models). " + note)
    # 6. English vs Indian languages, by stage
    fig, ax = plt.subplots(figsize=(7.5, 4))
    xs = np.arange(3)
    for i, k in enumerate(ms):
        g = [T["lang_gap"][k][s] for s in S]
        off = (i - (len(ms) - 1) / 2) * 0.05
        ax.errorbar(xs + off, [100 * x["gap"] for x in g], yerr=[[max(0, 100 * (x["gap"] - x["lo"])) for x in g], [max(0, 100 * (x["hi"] - x["gap"])) for x in g]],
                    marker="o", color=COLOR[k], label=D.name(k), capsize=2, lw=1.4)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([STAGE_LABEL[s] for s in S], fontsize=8)
    ax.set_ylabel("English minus Indian-language success (pp)")
    ax.set_title("Does the language matter more with more tools?")
    ax.legend(frameon=False, fontsize=7, bbox_to_anchor=(1.01, 1), loc="upper left")
    save(fig, "figS6_language_gap_by_stage", "Per model and stage, English success minus the mean success of the Hinglish, Hindi, Marathi and Gujarati "
         "versions of the SAME tasks (paired by task), with 95% bootstrap intervals over tasks. Above zero = English does better. " + note)

    # 7. phone: each language per stage, pooled over reliable models
    P = T["lang_pooled"]
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    y = np.arange(len(LANGS))[::-1]
    for j, s in enumerate(S):
        v = [P[s][l] for l in LANGS]
        ax.barh(y + (1 - j) * 0.26, [100 * x["rate"] for x in v], 0.26, color=STAGE_COLOR[s], edgecolor="black", lw=0.4, label=f"{STAGE_LABEL[s]}")
        for yy, x in zip(y, v):
            ax.text(100 * x["rate"] + 1, yy + (1 - j) * 0.26, f"{100 * x['rate']:.0f}", va="center", fontsize=10)
    ax.set_yticks(y)
    ax.set_yticklabels([LANG_NAME[l] for l in LANGS], fontsize=12)
    ax.set_xlim(0, 105)
    ax.set_xlabel("task success (%), all reliable models", fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=1)
    save(fig, "figS7_blog_languages_by_stage", f"Each language's task success per stage, pooled over the {len(P['models'])} models not flagged unreliable "
         "(phone-sized). " + note)
    (out / "captions.md").write_text("# Captions (generated by analysis/stage_comparison.py)\n\n" + "\n".join(caps), encoding="utf-8")
    return sorted(p.name for p in out.iterdir())


# ================================================================================================ RESULTS_V3.md
def results_md(D: Data, T: dict[str, Any]) -> str:
    S = [s for s, *_ in STAGES]
    nb = T["null_baseline"]
    L = ["# BharatToolBench 3.0: results across the three tool stages", "",
         "Generated by `python -m analysis.stage_comparison` from the run files; do not edit by hand. Stage 1 = T01-T75 with 6 tools (the 2.1.0 runs), "
         "stage 2 = T76-T100 with 12 tools, stage 3 = T101-T200 with 20 tools (the 3.0 `v3_new` runs). Each item is offered only its stage's tools. "
         "All rows are re-scored with the current scorer; success = lenient scorer (format recoveries recorded), strict in brackets. "
         "Intervals: 95% Wilson. Every task appears in all five languages.", "",
         f"Models included so far: {len(D.models)} of 8 ({', '.join(D.name(k) for k in D.models)})." + (
             f" † = flagged unreliable (more than {int(100 * UNRELIABLE_SHARE)}% of replies malformed): not ranked." if D.flagged else ""), "",
         "**Read the stage differences with care:** the stages differ in their tasks (stage 2 and 3 tasks involve PNRs, refunds, waitlists, Tatkal, "
         "meals, TDRs and complaints) as well as in the number of tools, so a drop from stage 1 to stage 3 is the joint effect of harder tasks and a "
         "larger toolset. The difficulty-level table below compares like with like.", "",
         f"Do-nothing baseline (never call a tool, always ask): stage 1 {nb['S1']['pass']}/{nb['S1']['tasks']}, stage 2 {nb['S2']['pass']}/"
         f"{nb['S2']['tasks']}, stage 3 {nb['S3']['pass']}/{nb['S3']['tasks']} tasks.", "", "## 1. Task success by stage", ""]
    rows = []
    for k in D.models:
        s = T["success"][k]
        rows.append([D.name(k)] + [f"{ci(s[x]['lenient'])} ({pc(s[x]['strict']['rate'])})" for x in S]
                    + [f"{ci(s['all']['lenient'])}"] + [f"{100 * T['diff_vs_s1'][k][x]['diff']:+.1f} [{100 * T['diff_vs_s1'][k][x]['lo']:+.1f}, "
                                                        f"{100 * T['diff_vs_s1'][k][x]['hi']:+.1f}]" for x in ("S2", "S3")])
    L.append(md_table(["model"] + [STAGE_LABEL[x] for x in S] + ["all 200 tasks", "S2 - S1 (pp)", "S3 - S1 (pp)"], rows))
    L += ["", "## 2. Success by difficulty level and stage (same rule for all 200 tasks)", ""]
    rows = []
    for k in D.models:
        for lv in ("Easy", "Medium", "Hard", "Very Hard"):
            cells = [f"{pc(T['difficulty'][k][s][lv]['rate'])} (n={T['difficulty'][k][s][lv]['n']})" if T["difficulty"][k][s][lv]["n"] else "-" for s in S]
            rows.append([D.name(k), lv] + cells)
    L.append(md_table(["model", "level"] + [STAGE_LABEL[x] for x in S], rows))
    L += ["", "## 3. Success by language and stage", ""]
    rows = [[D.name(k), STAGE_LABEL[s]] + [pc(T["language"][k][s][l]["rate"]) for l in LANGS] for k in D.models for s in S]
    L.append(md_table(["model", "stage"] + [LANG_NAME[l] for l in LANGS], rows))
    L += ["", "## 4. Tool use by stage", ""]
    rows = [[D.name(k), STAGE_LABEL[s]] + [pc(T["tools"][k][s][m]["value"]) if m in T["tools"][k][s] else "n/a" for m, _ in TM_SHOW] for k in D.models for s in S]
    L.append(md_table(["model", "stage"] + [lab for _, lab in TM_SHOW], rows))
    L += ["", "## 5. Run outcomes by stage (items)", ""]
    rows = [[D.name(k), STAGE_LABEL[s]] + [T["status"][k][s].get(x, 0) for x in STATUSES] for k in D.models for s in S]
    L.append(md_table(["model", "stage"] + STATUSES, rows))
    L += ["", "## 6. 20-tool stage by service (T101-T200)", ""]
    rows = [[D.name(k)] + [f"{pc(T['groups'][k][g]['rate'])}" for g, *_ in GROUPS] for k in D.models]
    L.append(md_table(["model"] + [f"{g} (T{a}-T{b})" for g, a, b in GROUPS], rows))
    L += ["", "## 7. New tools in stage 3: called when needed / called when not needed (items)", ""]
    rows = [[D.name(k)] + [f"{v['called_when_required']}/{v['required_items']} · {v['called_when_not_needed']}/{v['not_needed_items']}"
                           for v in T["new_tools"][k].values()] for k in D.models]
    L.append(md_table(["model"] + NEW_TOOLS, rows))
    L += ["", "## 8. Language across the stages", "",
          "Gap = per task, English success minus the mean of the Hinglish, Hindi, Marathi and Gujarati versions of the same task (paired), in "
          "percentage points, with a 95% bootstrap interval over tasks. Spread = best minus worst language. Change = stage-3 gap minus stage-1 gap "
          "(different tasks, so read it with the difficulty table).", ""]
    rows = [[D.name(k)] + [f"{100 * T['lang_gap'][k][s]['gap']:+.1f} [{100 * T['lang_gap'][k][s]['lo']:+.1f}, {100 * T['lang_gap'][k][s]['hi']:+.1f}]; "
                           f"spread {100 * T['lang_gap'][k][s]['spread']:.0f} ({LANG_NAME[T['lang_gap'][k][s]['worst']]} lowest)" for s in S]
            + [f"{100 * T['lang_gap'][k]['change_S3_vs_S1']['diff']:+.1f} [{100 * T['lang_gap'][k]['change_S3_vs_S1']['lo']:+.1f}, "
               f"{100 * T['lang_gap'][k]['change_S3_vs_S1']['hi']:+.1f}]"] for k in D.models]
    L.append(md_table(["model"] + [STAGE_LABEL[s] for s in S] + ["gap change S3 - S1"], rows))
    P = T["lang_pooled"]
    L += ["", f"All reliable models pooled ({len(P['models'])}): success per language and stage.", ""]
    L.append(md_table(["stage"] + [LANG_NAME[l] for l in LANGS], [[STAGE_LABEL[s]] + [ci(P[s][l]) for l in LANGS] for s in S]))
    L += ["", "Station errors (INVALID_STATION / STATION_NOT_FOUND), items with at least one, per language, split by cause: "
          "**not resolved** = resolve_station could not map the model's name (the word-ending / spelling problem of round one); "
          "**name, not code** = another tool was given a city name or a made-up / wrong code instead of a resolved code; "
          "**placeholder** = an empty, placeholder or unfilled template value. Cell = not resolved / name, not code / placeholder "
          "(of n items); an item can count in more than one. Errors the gold expects (deliberate traps) are not counted.", ""]
    L.append(md_table(["model", "stage"] + [LANG_NAME[l] for l in LANGS],
                      [[D.name(k), STAGE_LABEL[s]] + [" / ".join(str(T['lang_tools'][k][s][l][f"station_{b}_items"]) for b in STATION_BUCKETS)
                                                      + f" (of {T['lang_tools'][k][s][l]['items']})" for l in LANGS]
                       for k in D.models for s in S]))
    L += ["", "## 9. Re-scoring check", "",
          "Stored run-time scores vs the current scorer (the 2.1.0 rows were scored by the 2.1.0 scorer when they ran):", ""]
    L.append(md_table(["model", "items whose success changed"], [[D.name(k), T["rescoring"][k]["changed"]] for k in D.models]))
    L += ["", "Figures: `analysis/figures_v3/` (captions in `captions.md`). Tables: `analysis/results_v3/`.", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--v2", default="runs/full_phase_20261124T105853Z.status.json", help="status file of the 2.1.0 runs (T01-T75, 6 tools)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--v3", help="status file of the 3.0 v3_new runs (T76-T200)")
    g.add_argument("--v3-ts", help="timestamp of a v3_new run still in progress: finished models are found from their run files + manifests")
    ap.add_argument("--out", default="analysis/results_v3")
    ap.add_argument("--figures", default="analysis/figures_v3")
    ap.add_argument("--md", default="RESULTS_V3.md")
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args(argv)
    D = Data(ROOT / a.v2, ROOT / a.v3 if a.v3 else status_from_files(a.v3_ts, "v3_new", ROOT))
    if not D.models:
        print("no model has finished its v3_new run yet")
        return 1
    T = tables(D)
    write_tables(D, T, ROOT / a.out)
    figs = [] if a.no_figures else figures(D, T, ROOT / a.figures)
    (ROOT / a.md).write_text(results_md(D, T), encoding="utf-8")
    print(f"{len(D.models)} model(s): {', '.join(D.models)}; tables -> {a.out}; {len(figs)} figure files -> {a.figures}; {a.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
