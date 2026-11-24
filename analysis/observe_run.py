"""Per-item observations + diagnostic failure classification for ONE logical evaluation run (read-only on inputs).

    python -m analysis.observe_run --run-file runs/X.jsonl [--run-file runs/X_resume1.jsonl ...]
                                   --split midsem --languages en hinglish hi mr --out analysis/results/<name>
                                   [--manifest runs/X.manifest.json]

* Inputs are never modified (their SHA-256 is recorded before and after reading).
* Several files may be given in chronological order (e.g. an original run and a resume copy). Each expected
  task-language pair is counted exactly once: the LATEST row for it across the files in the given order wins (the same
  rule run_pilot --resume uses). Rows with model_key None (runner errors raised before the adapter existed) only count
  if no other row exists for that item. Duplicates, missing and unexpected items are reported.
* The official result is the scorer's `task_success` and `failure_labels`, copied verbatim. `primary_failure` and
  `secondary_tags` are DIAGNOSTIC (see analysis/FAILURE_TAXONOMY.md) and never change the official score.
* Output directory must not exist (never overwritten): observations.jsonl, summary.json, summary.md.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = ROOT / "benchmark" / "gold_labels.json"
SPEC_PATH = ROOT / "benchmark" / "semantic_tasks.json"
from analysis import null_baseline  # noqa: E402
from evaluation.splits import ALL_LANGUAGES, SPLITS, task_ids  # noqa: E402

LANGUAGES = ALL_LANGUAGES

PRIMARY_ORDER = ["success", "infra_error", "context_overflow", "output_truncated", "malformed_model_output", "step_limit", "unsafe_action",
                 "missing_booking", "tool_argument_error", "missing_required_call", "wrong_answer", "format_only", "other"]
# tool error codes that mean "the model passed bad arguments" (unless gold expects that code for the task)
ARG_ERROR_CODES = {"INVALID_TRAIN", "INVALID_STATION", "STATION_NOT_FOUND", "INVALID_ARGUMENTS", "MALFORMED_ARGUMENTS",
                   "INVALID_TIME_WINDOW", "INVALID_DATE", "INVALID_CLASS", "INVALID_PASSENGER", "SAME_STATION",
                   "PAST_DATE", "CLASS_NOT_OFFERED", "TOOL_NOT_ALLOWED", "UNKNOWN_TOOL"}
PARSE_ERRORS = ("missing_block", "malformed_json", "not_an_object", "missing_keys", "invalid_status")
TRAIN_ID_RE = re.compile(r"^BTB\d{3}$")
# a tool call written into the reply text (outside the answer block) that the serving layer did not convert
TOOL_CALL_TEXT_RE = re.compile(r'\{\s*"name"\s*:\s*"(resolve_station|search_trains|get_train_details|check_availability|get_fare|book_ticket)"')
DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
LATIN_RE = re.compile(r"[A-Za-z]")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str | None:
    import subprocess
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, capture_output=True, text=True, timeout=10)
        return (out.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")) or None
    except (OSError, subprocess.SubprocessError):
        return None


def expected_items(split: str, languages: list[str]) -> list[str]:
    """Item ids of a split: task order from evaluation.splits (pilot 5, midsem 50, full 75 tasks) x the given languages."""
    return [f"{tid}_{lang}" for tid in task_ids(split) for lang in languages]


# --------------------------------------------------------------------------------------------- loading
def load_rows(files: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, inputs = [], []
    for f in files:
        before = sha256_file(f)
        n = 0
        for lineno, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                r = json.loads(line)
                r["_source"] = {"file": f.as_posix(), "line": lineno}
                rows.append(r)
                n += 1
        after = sha256_file(f)
        if before != after:
            raise RuntimeError(f"input changed while reading: {f}")
        inputs.append({"file": f.as_posix(), "sha256": before, "rows": n, "bytes": f.stat().st_size})
    return rows, inputs


def select_latest(rows: list[dict[str, Any]], expected: list[str]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Latest row per task_id (one model per logical run). Returns (selected, integrity report)."""
    keys = {r["model_key"] for r in rows if r.get("model_key")}
    if len(keys) > 1:
        raise ValueError(f"one logical run must contain one model, found {sorted(keys)}")
    per_item: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows:
        per_item[r["task_id"]].append(r)
    selected = {}
    for tid, rs in per_item.items():
        with_model = [r for r in rs if r.get("model_key")]
        selected[tid] = (with_model or rs)[-1]
    exp = set(expected)
    report = {"rows_read": len(rows), "model_key": next(iter(keys), None), "expected_items": len(expected),
              "unique_items_selected": len(selected), "items_with_multiple_rows": sorted(t for t, rs in per_item.items() if len(rs) > 1),
              "missing_items": sorted(exp - set(selected)), "unexpected_items": sorted(set(selected) - exp)}
    report["complete"] = not report["missing_items"] and not report["unexpected_items"]
    return {t: selected[t] for t in expected if t in selected}, report


# --------------------------------------------------------------------------------------------- classification
def _booking_key(b: dict[str, Any]) -> tuple[str, str, str]:
    return (str(b.get("train_id", "")).upper(), str(b.get("travel_class", "")).upper(), " ".join(str(b.get("passenger", "")).lower().split()))


def _gold_expected_errors(gold_task: dict[str, Any]) -> set[str]:
    return {c["expected_error"] for c in gold_task.get("required_calls", []) if c.get("expected_error")}


def _tool_events(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [e for e in row.get("trajectory", []) if e.get("event") in ("tool_call", "malformed_tool_call", "tool_not_allowed")]


def _error_code(e: dict[str, Any]) -> str | None:
    if e.get("event") == "malformed_tool_call":
        return "MALFORMED_ARGUMENTS"
    if e.get("event") == "tool_not_allowed":
        return "TOOL_NOT_ALLOWED"
    obs = e.get("observation") or {}
    return None if obs.get("ok") else (obs.get("error") or {}).get("code")


def _last_done_reason(row: dict[str, Any]) -> str | None:
    resps = [x for x in row.get("raw_log", []) if x.get("type") == "model_response"]
    return resps[-1].get("finish_reason") if resps else None


def _script(text: str) -> str:
    dev, lat = len(DEVANAGARI_RE.findall(text)), len(LATIN_RE.findall(text))
    if dev + lat == 0:
        return "none"
    share = dev / (dev + lat)
    return "devanagari" if share >= 0.6 else "latin" if share <= 0.2 else "mixed"


def _repetitive(text: str) -> bool:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return len(lines) >= 6 and len(set(lines)) / len(lines) <= 0.5


def classify(row: dict[str, Any], gold_task: dict[str, Any]) -> tuple[str, list[str], dict[str, Any]]:
    """(primary_failure, secondary_tags, evidence). Deterministic; priority order = PRIMARY_ORDER."""
    status, sc = row.get("status"), row.get("score") or {}
    labels = list(sc.get("failure_labels") or [])
    events = _tool_events(row)
    expected_err = _gold_expected_errors(gold_task)
    arg_errors = [(e.get("tool"), _error_code(e)) for e in events if _error_code(e) in ARG_ERROR_CODES and _error_code(e) not in expected_err]
    actual = collections.Counter(map(_booking_key, (row.get("state_snapshot") or {}).get("bookings", [])))
    wanted = collections.Counter(map(_booking_key, gold_task["final_state"].get("expected_bookings", [])))
    extra, missing = actual - wanted, wanted - actual
    evidence = {"argument_errors": arg_errors, "extra_bookings": sorted(extra.elements()), "missing_bookings": sorted(missing.elements())}

    # ---- secondary tags (heuristic, independent of primary)
    tags: list[str] = []
    seen_ids: set[str] = set(re.findall(r"BTB\d{3}", row.get("query", "").upper()))
    bad_ids, ungrounded, parallel = False, False, False
    by_turn: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for e in events:
        by_turn[e.get("turn", 0)].append(e)
    for turn in sorted(by_turn):
        turn_ungrounded = False
        for e in by_turn[turn]:
            tid = (e.get("arguments") or {}).get("train_id")
            if isinstance(tid, str):
                if not TRAIN_ID_RE.match(tid.strip().upper()):
                    bad_ids = True
                elif tid.strip().upper() not in seen_ids:
                    ungrounded = turn_ungrounded = True
        if turn_ungrounded and len(by_turn[turn]) > 1:
            parallel = True
        for e in by_turn[turn]:  # ids become known only after this turn's observations
            seen_ids |= set(re.findall(r"BTB\d{3}", json.dumps(e.get("observation") or {}).upper()))
    if bad_ids:
        tags.append("invalid_train_id_format")
    if ungrounded:
        tags.append("ungrounded_train_id")
    if parallel:
        tags.append("parallel_dependent_calls")
    if any(code == "INVALID_STATION" for _, code in arg_errors):
        tags.append("guessed_station_code")
    if any(code == "STATION_NOT_FOUND" for _, code in arg_errors):
        tags.append("unresolvable_station_name")
    final_text = row.get("final_text") or ""
    if not final_text.strip():
        tags.append("empty_final_text")
    elif _last_done_reason(row) == "length" or _repetitive(final_text):
        tags.append("repetition_or_truncation")
    from evaluation.final_answer import split_answer
    if TOOL_CALL_TEXT_RE.search(split_answer(final_text)[0]):
        tags.append("tool_call_as_text")
    if final_text.strip():
        script = _script(final_text)
        want = "latin" if row.get("language") in ("en", "hinglish") else "devanagari"
        if script not in (want, "none"):
            tags.append("reply_language_mismatch")
    if extra:  # visible even when a higher-priority primary (e.g. step_limit, context_overflow) masks unsafe_action
        tags.append("unexpected_booking")
    if missing:
        tags.append("missing_expected_booking")
    if sc.get("final_answer_parse") == "missing_block":
        tags.append("no_final_block")
    if (row.get("attempts") or 1) > 1:
        tags.append("retried")

    # ---- primary (first match wins)
    if sc.get("task_success") is True:
        return "success", tags, evidence
    if status in ("provider_error", "runner_error"):
        return ("context_overflow" if row.get("error_kind") == "context_overflow" else "infra_error"), tags, evidence
    if status == "context_overflow":  # scored model failure since audit I-04 (older runs: provider_error + error_kind)
        return "context_overflow", tags, evidence
    if status == "output_truncated":  # cut off by the max_tokens limit; kept apart from malformed output (audit I-05)
        return "output_truncated", tags, evidence
    if status == "malformed_output":
        return "malformed_model_output", tags + [f"kind:{row.get('error_kind')}"], evidence
    if status == "step_limit_exceeded":
        return "step_limit", tags, evidence
    if any(l.startswith(("process:prohibited_action", "process:tool_not_allowed")) for l in labels) or extra:
        return "unsafe_action", tags, evidence
    if missing:
        return "missing_booking", tags, evidence
    process_fail = any(l.startswith(("process:missing_required_call", "process:dependency_violation")) for l in labels)
    if process_fail and arg_errors:
        return "tool_argument_error", tags, evidence
    if process_fail:
        return "missing_required_call", tags, evidence
    parse_ok = sc.get("final_answer_parse") == "ok"
    if parse_ok and labels:
        return "wrong_answer", tags, evidence
    if not parse_ok and all(l.startswith("final_answer:") and l.split(":")[1].split(" ")[0] in PARSE_ERRORS for l in labels):
        return "format_only", tags, evidence
    return "other", tags, evidence


# --------------------------------------------------------------------------------------------- observations
def observation(row: dict[str, Any], gold: dict[str, Any], categories: dict[str, str]) -> dict[str, Any]:
    gold_task = gold[row["semantic_task_id"]]
    primary, tags, evidence = classify(row, gold_task)
    sc = row.get("score") or {}
    events = _tool_events(row)
    codes = [c for c in map(_error_code, events) if c]
    usage = row.get("usage") or {}
    try:
        secs = (datetime.fromisoformat(row["finished_at"]) - datetime.fromisoformat(row["started_at"])).total_seconds()
    except (KeyError, ValueError):
        secs = None
    n_ok = sum(1 for e in events if e.get("event") == "tool_call" and (e.get("observation") or {}).get("ok"))
    tools = ",".join(e.get("tool") or "?" for e in events) or "none"
    text = row.get("final_text") or ""
    obs_line = (f"{row.get('status')}; {n_ok}/{len(events)} tool calls ok [{tools}]; answer parse={sc.get('final_answer_parse')}; "
                f"state={'ok' if sc.get('state_success') else 'mismatch'}; process={'ok' if sc.get('process_success') else 'fail'}"
                + (f"; argument errors={collections.Counter(c for _, c in evidence['argument_errors'])}" if evidence["argument_errors"] else "")
                + (f"; extra bookings={evidence['extra_bookings']}" if evidence["extra_bookings"] else "")
                + (f"; missing bookings={evidence['missing_bookings']}" if evidence["missing_bookings"] else ""))
    settings = row.get("adapter_settings") or {}
    strict = row.get("score_strict") or sc          # runs written before benchmark 2.1.0 carry only the (strict) score
    rec_rules = [r.get("rule") for r in (sc.get("format_recoveries") or [])]
    return {
        "task_id": row["task_id"], "semantic_task_id": row["semantic_task_id"], "language": row["language"],
        "category": categories.get(row["semantic_task_id"]), "model_key": row.get("model_key"),
        "model_digest": settings.get("model_digest"), "source_file": row["_source"]["file"], "source_line": row["_source"]["line"],
        # official (verbatim from the scorer)
        "status": row.get("status"), "error_kind": row.get("error_kind"), "task_success": sc.get("task_success"),
        "task_success_strict": strict.get("task_success"), "scored_strict": strict.get("scored"), "has_strict_score": "score_strict" in row,
        "lenient_used": bool(sc.get("lenient_used")), "format_recoveries": rec_rules,
        "transport_unparsed": row.get("error_kind") == "unparsed_model_output",
        "scored": sc.get("scored"), "outcome_success": sc.get("outcome_success"), "process_success": sc.get("process_success"),
        "state_success": sc.get("state_success"), "status_correct": sc.get("status_correct"),
        "final_answer_parse": sc.get("final_answer_parse"), "failure_labels": sc.get("failure_labels"),
        # diagnostic
        "primary_failure": primary, "secondary_tags": tags, "evidence": evidence,
        "tool_calls": len(events), "tool_calls_ok": n_ok, "tool_error_codes": dict(collections.Counter(codes)),
        "malformed_tool_calls": sum(1 for e in events if e.get("event") == "malformed_tool_call"),
        "turns": row.get("turns"), "attempts": row.get("attempts"), "last_done_reason": _last_done_reason(row),
        "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
        "cached_input_tokens": usage.get("cached_input_tokens", 0), "duration_s": secs,
        "final_text_excerpt": text[:300], "final_text_script": _script(text) if text.strip() else "none",
        "observation": obs_line,
    }


# --------------------------------------------------------------------------------------------- summary
def _rate(num: int, den: int) -> str:
    return f"{num}/{den}" + (f" ({100 * num / den:.1f}%)" if den else "")


def _group(obs: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for k in sorted({o[key] for o in obs}, key=str):
        g = [o for o in obs if o[key] == k]
        scored = [o for o in g if o["scored"]]
        out[str(k)] = {"items": len(g), "scored": len(scored), "task_success": sum(o["task_success"] is True for o in scored),
                       "parse_ok": sum(o["final_answer_parse"] == "ok" for o in scored),
                       "process_success": sum(bool(o["process_success"]) for o in scored),
                       "state_success": sum(bool(o["state_success"]) for o in scored),
                       "primary_failure": dict(collections.Counter(o["primary_failure"] for o in g))}
    return out


def strict_vs_lenient(obs: list[dict[str, Any]]) -> dict[str, Any]:
    """Headline (lenient: format recovery only, never prose extraction) next to the strict sensitivity score, the recoveries used
    (per rule and per language) and the transport category (reply discarded by the serving layer). See FORMAT_ROBUSTNESS.md."""
    sc_len = [o for o in obs if o["scored"]]
    sc_str = [o for o in obs if o.get("scored_strict", o["scored"])]
    used = [o for o in obs if o.get("lenient_used")]
    unp = [o for o in obs if o.get("transport_unparsed")]
    return {"definition": "lenient = scorer after recorded format recoveries (headline); strict = original scorer, lower bound when a run-time recovery was used",
            "has_strict_scores": any(o.get("has_strict_score") for o in obs),
            "lenient": {"scored": len(sc_len), "task_success": sum(o["task_success"] is True for o in sc_len)},
            "strict": {"scored": len(sc_str), "task_success": sum(o.get("task_success_strict") is True for o in sc_str)},
            "items_with_recovery": len(used),
            "recovery_rules": dict(collections.Counter(r for o in used for r in set(o["format_recoveries"])).most_common()),
            "items_with_recovery_by_language": dict(collections.Counter(o["language"] for o in used)),
            "unparsed_model_output": {"total": len(unp), "by_language": dict(collections.Counter(o["language"] for o in unp))}}


def summarize(obs: list[dict[str, Any]], rows: dict[str, dict[str, Any]], integrity: dict[str, Any], inputs: list[dict[str, Any]],
              manifest: dict[str, Any] | None) -> dict[str, Any]:
    scored = [o for o in obs if o["scored"]]
    sel = list(rows.values())
    starts = [datetime.fromisoformat(r["started_at"]) for r in sel if r.get("started_at")]
    ends = [datetime.fromisoformat(r["finished_at"]) for r in sel if r.get("finished_at")]
    codes: collections.Counter = collections.Counter()
    for o in obs:
        codes.update(o["tool_error_codes"])
    settings = {json.dumps({k: (r.get("adapter_settings") or {}).get(k) for k in ("temperature", "seed", "num_ctx", "max_tokens", "model_digest")},
                           sort_keys=True) for r in sel}
    return {
        "generated_by": "analysis/observe_run.py", "analysis_git_commit": _git_head(), "inputs": inputs, "integrity": integrity,
        "ollama_versions": sorted({(r.get("adapter_settings") or {}).get("ollama_version") for r in sel} - {None}),
        "model_key": integrity["model_key"], "decoding_settings": [json.loads(s) for s in sorted(settings)],
        "benchmark_version": sorted({r.get("benchmark_version") for r in sel}),
        "system_prompt_sha256": sorted({r.get("system_prompt_sha256") for r in sel}),
        "tool_schema_sha256": sorted({r.get("tool_schema_sha256") for r in sel}),
        # run_manifest.py nests the pre-run record under "prerun"; a bare pre-run record has it at top level
        "dataset_sha256": (manifest or {}).get("file_sha256") or ((manifest or {}).get("prerun") or {}).get("file_sha256"),
        "official": {"items": len(obs), "scored": len(scored), "not_scored": len(obs) - len(scored),
                     "task_success": sum(o["task_success"] is True for o in scored),
                     "status": dict(collections.Counter(o["status"] for o in obs)),
                     "failure_label_families": dict(collections.Counter(l.split(":")[0] + ":" + l.split(":")[1] if ":" in l else l
                                                                        for o in obs for l in (o["failure_labels"] or [])).most_common())},
        "rates": {"parse_ok": sum(o["final_answer_parse"] == "ok" for o in scored),
                  "process_success": sum(bool(o["process_success"]) for o in scored),
                  "state_success": sum(bool(o["state_success"]) for o in scored),
                  "tool_calls": sum(o["tool_calls"] for o in obs), "tool_calls_ok": sum(o["tool_calls_ok"] for o in obs),
                  "top_tool_error_codes": dict(codes.most_common(10))},
        "null_baseline": null_baseline.tool_required_breakdown(obs),
        "strict_vs_lenient": strict_vs_lenient(obs),
        "by_language": _group(obs, "language"), "by_task": _group(obs, "semantic_task_id"), "by_category": _group(obs, "category"),
        "diagnostic": {"primary_failure": {k: v for k, v in ((p, sum(o["primary_failure"] == p for o in obs)) for p in PRIMARY_ORDER) if v},
                       "secondary_tags": dict(collections.Counter(t for o in obs for t in o["secondary_tags"]).most_common()),
                       "format_only_items": sorted(o["task_id"] for o in obs if o["primary_failure"] == "format_only")},
        "cost": {"input_tokens": sum(o["input_tokens"] for o in obs), "output_tokens": sum(o["output_tokens"] for o in obs),
                 "cached_input_tokens": sum(o["cached_input_tokens"] for o in obs),
                 "attempts_gt_1": sum((o["attempts"] or 1) > 1 for o in obs),
                 "sum_item_seconds": round(sum(o["duration_s"] or 0 for o in obs), 1),
                 "wall_seconds_first_start_to_last_finish": round((max(ends) - min(starts)).total_seconds(), 1) if starts and ends else None},
    }


def render_md(s: dict[str, Any]) -> str:
    o, r = s["official"], s["rates"]
    L = [f"# Run summary: {s['model_key']}", "",
         "Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC "
         "(analysis/FAILURE_TAXONOMY.md).", "",
         "## Integrity", "", f"- inputs: " + "; ".join(f"`{i['file']}` ({i['rows']} rows, sha256 {i['sha256'][:12]}...)" for i in s["inputs"]),
         f"- expected items {s['integrity']['expected_items']}, selected {s['integrity']['unique_items_selected']}, "
         f"missing {len(s['integrity']['missing_items'])}, unexpected {len(s['integrity']['unexpected_items'])}, "
         f"items with >1 row {len(s['integrity']['items_with_multiple_rows'])}, complete={s['integrity']['complete']}", "",
         "## Official result", "",
         f"- task_success: **{_rate(o['task_success'], o['scored'])}** (not scored: {o['not_scored']})",
         f"- status: {o['status']}",
         f"- final-answer parse ok: {_rate(r['parse_ok'], o['scored'])}; process ok: {_rate(r['process_success'], o['scored'])}; "
         f"state ok: {_rate(r['state_success'], o['scored'])}",
         f"- tool calls ok: {_rate(r['tool_calls_ok'], r['tool_calls'])}; top error codes: {r['top_tool_error_codes']}",
         f"- failure label families: {o['failure_label_families']}", "",
         "## Lenient (headline) and strict (sensitivity)", "",
         f"- lenient task_success: **{_rate(s['strict_vs_lenient']['lenient']['task_success'], s['strict_vs_lenient']['lenient']['scored'])}**; "
         f"strict: {_rate(s['strict_vs_lenient']['strict']['task_success'], s['strict_vs_lenient']['strict']['scored'])}"
         + ("" if s['strict_vs_lenient']['has_strict_scores'] else " (this run predates benchmark 2.1.0: only the strict score exists, lenient = strict)"),
         f"- items that needed a format recovery: {s['strict_vs_lenient']['items_with_recovery']}; by rule {s['strict_vs_lenient']['recovery_rules']}; "
         f"by language {s['strict_vs_lenient']['items_with_recovery_by_language']}",
         f"- reply discarded by the serving layer (`unparsed_model_output`, transport category): {s['strict_vs_lenient']['unparsed_model_output']}", "",
         "## Read against the null baseline (audit I-10)", "",
         f"- tool-required tasks: {_rate(s['null_baseline']['tool_required_tasks']['task_success'], s['null_baseline']['tool_required_tasks']['scored'])}; "
         f"no-tool tasks: {_rate(s['null_baseline']['no_tool_tasks']['task_success'], s['null_baseline']['no_tool_tasks']['scored'])}",
         f"- baseline 'always needs_clarification, no tool calls' passes {s['null_baseline']['always_needs_clarification_baseline']['passes_per_language']} "
         f"of {len(__import__('analysis.null_baseline', fromlist=['x'])._gold())} tasks "
         f"({100 * s['null_baseline']['always_needs_clarification_baseline']['rate_all_tasks']:.1f}%)", "",
         "## By language", "", "| language | success | parse ok | process ok | state ok | primary failures |", "|---|---|---|---|---|---|"]
    for k, g in s["by_language"].items():
        L.append(f"| {k} | {_rate(g['task_success'], g['scored'])} | {g['parse_ok']} | {g['process_success']} | {g['state_success']} | {g['primary_failure']} |")
    L += ["", "## By task category", "", "| category | items | success | parse ok | process ok | state ok |", "|---|---|---|---|---|---|"]
    for k, g in s["by_category"].items():
        L.append(f"| {k} | {g['items']} | {g['task_success']} | {g['parse_ok']} | {g['process_success']} | {g['state_success']} |")
    L += ["", "## By task", "", "| task | success | parse ok | process ok | state ok | primary failures |", "|---|---|---|---|---|---|"]
    for k, g in s["by_task"].items():
        L.append(f"| {k} | {g['task_success']}/{g['scored']} | {g['parse_ok']} | {g['process_success']} | {g['state_success']} | {g['primary_failure']} |")
    d, c = s["diagnostic"], s["cost"]
    L += ["", "## Diagnostic classification (not an official score)", "", f"- primary_failure: {d['primary_failure']}",
          f"- secondary tags: {d['secondary_tags']}",
          f"- format_only (tool process and booking state correct, only the final-answer block failed): {len(d['format_only_items'])} items",
          "", "## Cost", "", f"- tokens: input {c['input_tokens']}, output {c['output_tokens']}, cached input {c['cached_input_tokens']}",
          f"- items retried: {c['attempts_gt_1']}; wall time {c['wall_seconds_first_start_to_last_finish']} s "
          f"(sum of item times {c['sum_item_seconds']} s)",
          f"- decoding settings: {s['decoding_settings']}", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-file", type=Path, action="append", required=True, help="repeat, in chronological order")
    ap.add_argument("--split", required=True, choices=list(SPLITS))
    ap.add_argument("--languages", nargs="+", default=LANGUAGES, choices=LANGUAGES)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--manifest", type=Path)
    args = ap.parse_args(argv)
    if args.out.exists():
        ap.error(f"output directory already exists (never overwritten): {args.out}")
    rows, inputs = load_rows(args.run_file)
    expected = expected_items(args.split, args.languages)
    selected, integrity = select_latest(rows, expected)
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    categories = {t["semantic_task_id"]: t["category"] for t in json.loads(SPEC_PATH.read_text(encoding="utf-8"))["tasks"]}
    obs = [observation(r, gold, categories) for r in selected.values()]
    manifest = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest else None
    summary = summarize(obs, selected, integrity, inputs, manifest)
    for i in inputs:  # inputs must be unchanged after the analysis
        if sha256_file(Path(i["file"])) != i["sha256"]:
            raise RuntimeError(f"input modified: {i['file']}")
    args.out.mkdir(parents=True)
    with (args.out / "observations.jsonl").open("w", encoding="utf-8") as fh:
        for o in obs:
            fh.write(json.dumps(o, ensure_ascii=False) + "\n")
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.out / "summary.md").write_text(render_md(summary), encoding="utf-8")
    o = summary["official"]
    print(f"items={o['items']} (expected {integrity['expected_items']}, complete={integrity['complete']}) "
          f"task_success={o['task_success']}/{o['scored']} parse_ok={summary['rates']['parse_ok']} -> {args.out}")
    return 0 if integrity["complete"] else 2


if __name__ == "__main__":
    sys.exit(main())
