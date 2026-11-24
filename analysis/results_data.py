"""Phase 4 data layer: everything is read from the run files, their manifests and the observe_run outputs (nothing is typed in).

Used by analysis/build_results.py (tables, statistics, RESULTS.md, LaTeX), analysis/build_figures.py (charts, diagram) and
analysis/build_media.py (examples, animated GIF). Only numpy/scipy are needed here, so it runs in the small visualisation venv
(`~/FreeModel/viz-venv`), not in the project venv.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
LANGS = ["en", "hinglish", "hi", "mr", "gu"]
LANG_NAME = {"en": "English", "hinglish": "Hinglish", "hi": "Hindi", "mr": "Marathi", "gu": "Gujarati"}
PLAN_ORDER = ["local_qwen25_3b", "local_llama32_3b", "local_llama31_8b", "local_deepseek_r1_8b", "local_qwen25_14b", "local_gpt_oss_20b",
              "local_gemma4_26b", "local_mistral_small32_24b"]
DISPLAY = {"local_qwen25_3b": "Qwen2.5-3B", "local_llama32_3b": "Llama-3.2-3B", "local_llama31_8b": "Llama-3.1-8B",
           "local_deepseek_r1_8b": "DeepSeek-R1-8B (distill)", "local_qwen25_14b": "Qwen2.5-14B", "local_gpt_oss_20b": "gpt-oss-20B",
           "local_gemma4_26b": "Gemma-4-26B-A4B", "local_mistral_small32_24b": "Mistral-Small-3.2-24B"}
FAMILY = {"local_qwen25_3b": "Qwen", "local_qwen25_14b": "Qwen", "local_llama32_3b": "Llama", "local_llama31_8b": "Llama", "local_deepseek_r1_8b": "DeepSeek",
          "local_gpt_oss_20b": "OpenAI", "local_gemma4_26b": "Google", "local_mistral_small32_24b": "Mistral"}
# one colour per model, used in EVERY chart (colour-blind-safe Okabe-Ito based)
COLOR = {"local_qwen25_3b": "#56B4E9", "local_llama32_3b": "#E69F00", "local_llama31_8b": "#D55E00", "local_deepseek_r1_8b": "#999999",
         "local_qwen25_14b": "#0072B2", "local_gpt_oss_20b": "#009E73", "local_gemma4_26b": "#CC79A7", "local_mistral_small32_24b": "#F0E442"}
# Models whose result is dominated by a serving problem: share of replies discarded by Ollama's parser above this value => "unreliable" (computed, not typed)
UNRELIABLE_SHARE = 0.5
# Language comparisons are only interpretable for models well above the 0% floor (user decision, 2026-11-24)
LANGUAGE_FOCUS = ["local_qwen25_14b", "local_gpt_oss_20b", "local_gemma4_26b"]
FLAGGED: dict[str, tuple[int, int]] = {}      # key -> (discarded replies, items); filled by mark_unreliable()
DAGGER = " \u2020"


def mark_unreliable(runs: dict[str, "Run"]) -> dict[str, tuple[int, int]]:
    """Flag models with more than UNRELIABLE_SHARE of their replies discarded by Ollama's parser: they get a dagger in every table and figure."""
    FLAGGED.clear()
    for k, r in runs.items():
        n = len(r.rows)
        d = r.summary["strict_vs_lenient"]["unparsed_model_output"]["total"]
        if n and d / n > UNRELIABLE_SHARE:
            FLAGGED[k] = (d, n)
            if not DISPLAY[k].endswith(DAGGER):
                DISPLAY[k] += DAGGER
    return dict(FLAGGED)


def footnote() -> str:
    return "; ".join(f"{DISPLAY[k].replace(DAGGER, '')}{DAGGER}: unreliable, {d}/{n} replies discarded by Ollama's parser (serving bug), excluded from ranking and size/family claims" for k, (d, n) in FLAGGED.items())


BOOTSTRAP_SEED = 20261124
BOOTSTRAP_RESAMPLES = 10000


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


class Run:
    """One model's complete full run: latest row per item over its run files (the rule run_pilot --resume uses) + its observations."""

    def __init__(self, key: str, status: dict[str, Any], root: Path = ROOT):
        self.key, self.status, self.root = key, status, root
        latest: dict[str, dict[str, Any]] = {}
        for f in status["run_files"]:
            for r in read_jsonl(root / f):
                latest[r["task_id"]] = r
        self.rows = latest
        stem = Path(status["run_files"][0]).stem
        self.stem = stem
        self.obs = {o["task_id"]: o for o in read_jsonl(root / status["observe_dir"] / "observations.jsonl")}
        self.summary = json.loads((root / status["observe_dir"] / "summary.json").read_text(encoding="utf-8"))
        self.prerun = json.loads((root / f"runs/{stem}.prerun.json").read_text(encoding="utf-8"))
        self.manifest = json.loads((root / f"runs/{stem}.manifest.json").read_text(encoding="utf-8"))
        s0 = next(iter(latest.values()))["adapter_settings"]
        self.settings = s0
        self.model = status["model"]
        self.params = s0.get("parameter_size")           # from Ollama (`ollama show`), recorded in every row
        self.size_b = float(str(self.params).rstrip("Bb")) if self.params else float("nan")

    # ---- item-level views
    def ok(self, task_id: str, strict: bool = False) -> bool:
        r = self.rows[task_id]
        return bool((r.get("score_strict") if strict else r["score"]).get("task_success"))

    def items(self) -> list[str]:
        return sorted(self.rows)

    def by_lang(self, lang: str) -> list[str]:
        return [t for t in self.items() if self.rows[t]["language"] == lang]

    def rate(self, ids: list[str], strict: bool = False) -> tuple[int, int]:
        return sum(self.ok(t, strict) for t in ids), len(ids)


def load_runs(status_path: Path, root: Path = ROOT) -> dict[str, Run]:
    st = json.loads(status_path.read_text(encoding="utf-8"))
    return {k: Run(k, v, root) for k, v in st["models"].items() if v.get("done") and k in PLAN_ORDER}


def ordered(runs: dict[str, Run]) -> list[Run]:
    return [runs[k] for k in PLAN_ORDER if k in runs]


def gold_tool_required(root: Path = ROOT) -> set[str]:
    g = json.loads((root / "benchmark" / "gold_labels.json").read_text(encoding="utf-8"))
    return {t for t, v in g.items() if not t.startswith("_") and any(not c.get("optional") for c in v["required_calls"])}


# ------------------------------------------------------------------------------------------------ statistics
def paired_bootstrap_gap(run: Run, lang: str, base: str = "en") -> dict[str, float]:
    """Mean success difference (lang - base) over the 75 tasks, paired by task, bootstrap over TASKS (95% percentile CI)."""
    tasks = sorted({r["semantic_task_id"] for r in run.rows.values()})
    a = np.array([int(run.ok(f"{t}_{lang}")) for t in tasks], dtype=float)
    b = np.array([int(run.ok(f"{t}_{base}")) for t in tasks], dtype=float)
    d = a - b
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    idx = rng.integers(0, len(d), size=(BOOTSTRAP_RESAMPLES, len(d)))
    boots = d[idx].mean(axis=1)
    return {"diff": float(d.mean()), "lo": float(np.percentile(boots, 2.5)), "hi": float(np.percentile(boots, 97.5)),
            "lang_rate": float(a.mean()), "base_rate": float(b.mean())}


def mcnemar_exact(a: Run, b: Run) -> dict[str, float]:
    ids = sorted(set(a.rows) & set(b.rows))
    only_a = sum(a.ok(t) and not b.ok(t) for t in ids)
    only_b = sum(b.ok(t) and not a.ok(t) for t in ids)
    n = only_a + only_b
    p = 1.0 if n == 0 else float(stats.binomtest(min(only_a, only_b), n, 0.5, alternative="two-sided").pvalue)
    return {"a": a.key, "b": b.key, "only_a": only_a, "only_b": only_b, "p": p}


def holm(pvals: list[float]) -> list[float]:
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    adj, running, m = [0.0] * len(pvals), 0.0, len(pvals)
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvals[i])
        adj[i] = min(1.0, running)
    return adj


def spearman(x: list[float], y: list[float]) -> tuple[float, float]:
    r = stats.spearmanr(x, y)
    return float(r.statistic), float(r.pvalue)


# ------------------------------------------------------------------------------------------------ metric tables
def overall_table(runs: dict[str, Run], tool_required: set[str]) -> list[dict[str, Any]]:
    rows = []
    for r in ordered(runs):
        ids = r.items()
        k, n = r.rate(ids)
        ks, _ = r.rate(ids, strict=True)
        lo, hi = wilson(k, n)
        tr = [t for t in ids if r.rows[t]["semantic_task_id"] in tool_required]
        ktr, ntr = r.rate(tr)
        s = r.summary
        used = [t for t in ids if r.rows[t].get("lenient_used")]
        status = Counter(r.rows[t]["status"] for t in ids)
        secs = sum(_secs(r.rows[t]) for t in ids)
        usage_in = sum(r.rows[t]["usage"].get("input_tokens", 0) for t in ids)
        usage_out = sum(r.rows[t]["usage"].get("output_tokens", 0) for t in ids)
        rows.append({"key": r.key, "model": DISPLAY[r.key], "tag": r.model, "family": FAMILY[r.key], "params": r.params, "size_b": r.size_b,
                     "n": n, "lenient": k, "lenient_rate": k / n, "ci_lo": lo, "ci_hi": hi, "strict": ks, "strict_rate": ks / n,
                     "tool_required": ktr, "tool_required_n": ntr, "tool_required_rate": ktr / ntr,
                     "null_baseline_rate": s["null_baseline"]["always_needs_clarification_baseline"]["rate_all_tasks"],
                     "items_with_recovery": len(used), "status": dict(status), "unparsed": s["strict_vs_lenient"]["unparsed_model_output"]["total"],
                     "seconds_per_item": secs / n, "wall_seconds": r.status.get("seconds"), "input_tokens": usage_in, "output_tokens": usage_out,
                     "ollama": r.settings.get("ollama_version"), "digest": r.settings.get("model_digest", "")[:12]})
    return rows


def _secs(row: dict[str, Any]) -> float:
    from datetime import datetime
    try:
        return (datetime.fromisoformat(row["finished_at"]) - datetime.fromisoformat(row["started_at"])).total_seconds()
    except (KeyError, ValueError):
        return 0.0


def language_table(runs: dict[str, Run]) -> list[dict[str, Any]]:
    out = []
    for r in ordered(runs):
        for lang in LANGS:
            ids = r.by_lang(lang)
            k, n = r.rate(ids)
            ks, _ = r.rate(ids, strict=True)
            lo, hi = wilson(k, n)
            out.append({"key": r.key, "model": DISPLAY[r.key], "lang": lang, "n": n, "lenient": k, "rate": k / n, "ci_lo": lo, "ci_hi": hi, "strict": ks})
    return out


def gap_table(runs: dict[str, Run]) -> list[dict[str, Any]]:
    out = []
    for r in ordered(runs):
        for lang in LANGS[1:]:
            g = paired_bootstrap_gap(r, lang)
            out.append({"key": r.key, "model": DISPLAY[r.key], "lang": lang, **g})
    return out


def failure_table(runs: dict[str, Run]) -> dict[str, dict[str, int]]:
    return {r.key: dict(Counter(o["primary_failure"] for o in r.obs.values())) for r in ordered(runs)}


def unsafe_table(runs: dict[str, Run]) -> list[dict[str, Any]]:
    """Unwanted bookings: items whose final state holds a booking the gold does not expect (observe_run tag `unexpected_booking`),
    the number of such extra bookings, bookings missing, and attempted prohibited actions (process label)."""
    out = []
    for r in ordered(runs):
        unexpected = [t for t, o in r.obs.items() if "unexpected_booking" in o["secondary_tags"]]
        extra = sum(len((r.obs[t].get("evidence") or {}).get("extra_bookings") or []) for t in unexpected)
        missing = sum("missing_expected_booking" in o["secondary_tags"] for o in r.obs.values())
        prohib = sum(any(l.startswith("process:prohibited_action") for l in (o.get("failure_labels") or [])) for o in r.obs.values())
        out.append({"key": r.key, "model": DISPLAY[r.key], "items_with_unwanted_booking": len(unexpected), "unwanted_bookings": extra,
                    "items_missing_expected_booking": missing, "items_with_prohibited_attempt": prohib, "n": len(r.obs)})
    return out


def recovery_table(runs: dict[str, Run]) -> list[dict[str, Any]]:
    out = []
    for r in ordered(runs):
        c = Counter()
        for t in r.items():
            for rule in sorted({x["rule"] for x in (r.rows[t]["score"].get("format_recoveries") or [])}):
                c[rule] += 1
        out.append({"key": r.key, "model": DISPLAY[r.key], "items": sum(1 for t in r.items() if r.rows[t].get("lenient_used")), "rules": dict(c.most_common())})
    return out


def category_table(runs: dict[str, Run]) -> dict[str, dict[str, tuple[int, int]]]:
    cat = {}
    for r in ordered(runs):
        by = defaultdict(list)
        for t, o in r.obs.items():
            by[o["category"]].append(t)
        cat[r.key] = {c: r.rate(sorted(ids)) for c, ids in sorted(by.items())}
    return cat


def pairwise(runs: dict[str, Run]) -> list[dict[str, Any]]:
    rs = ordered(runs)
    res = [mcnemar_exact(rs[i], rs[j]) for i in range(len(rs)) for j in range(i + 1, len(rs))]
    adj = holm([x["p"] for x in res])
    for x, p in zip(res, adj):
        x["p_holm"] = p
    return res


# ------------------------------------------------------------------------------------------------ diagnostics requested 2026-11-24
def final_block_only_table(runs: dict[str, Run]) -> list[dict[str, Any]]:
    """Per model: failed items whose ONLY recorded failure is missing keys in the final answer block (environment state and tool process are correct).
    A diagnostic count; scoring is unchanged and no defaults are applied."""
    out = []
    for r in ordered(runs):
        failed = [t for t in r.items() if not r.ok(t)]
        only, missing_any = [], 0
        for t in failed:
            sc = r.rows[t]["score"]
            if str(sc.get("final_answer_parse")).startswith("missing_keys"):
                missing_any += 1
                if set(sc.get("failure_labels") or []) <= {"final_answer:missing_keys"} and sc.get("state_success") and sc.get("process_success"):
                    only.append(t)
        keys = Counter(k for t in only for k in str(r.rows[t]["score"]["final_answer_parse"]).split(":", 1)[1].split(","))
        out.append({"key": r.key, "model": DISPLAY[r.key], "failed": len(failed), "missing_keys_any": missing_any, "only_missing_keys": len(only),
                    "share_of_failures": len(only) / len(failed) if failed else 0.0, "keys": dict(keys.most_common())})
    return out


def discard_by_language(runs: dict[str, Run]) -> dict[str, dict[str, int]]:
    return {r.key: dict(r.summary["strict_vs_lenient"]["unparsed_model_output"].get("by_language", {})) for r in ordered(runs)}


def think_audit(runs: dict[str, Run]) -> list[dict[str, Any]]:
    """What was really sent and returned: the `think` value of every recorded request and the `thinking` field / <think> text of every recorded response."""
    out = []
    for r in ordered(runs):
        sent, resp, with_think, chars, in_content = Counter(), 0, 0, 0, 0
        for row in r.rows.values():
            for e in row.get("raw_log") or []:
                if e.get("type") == "model_request":
                    sent[json.dumps(e["request"].get("think"))] += 1
                elif e.get("type") == "model_response":
                    resp += 1
                    m = (e.get("response") or {}).get("message") or {}
                    t = m.get("thinking") or ""
                    with_think += bool(t)
                    chars += len(t)
                    in_content += "<think>" in (m.get("content") or "")
        out.append({"key": r.key, "model": DISPLAY[r.key], "think_config": r.settings.get("think_config"), "think_effective": r.settings.get("think_effective"),
                    "capabilities": r.settings.get("capabilities"), "requests_by_think_value": dict(sent), "responses": resp, "responses_with_thinking_field": with_think,
                    "responses_with_think_tag_in_content": in_content, "thinking_chars_total": chars})
    return out


def call_counts(run: Run) -> dict[str, int]:
    """Executed tool calls in a run (all tools, and book_ticket alone), from the recorded trajectories."""
    total = book = 0
    for row in run.rows.values():
        for e in row.get("trajectory") or row.get("partial_trajectory") or []:
            if e.get("event") == "tool_call":
                total += 1
                book += e.get("tool") == "book_ticket"
    return {"tool_calls": total, "book_ticket_calls": book}
