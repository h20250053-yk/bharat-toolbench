"""Format-recovery analysis: could recorded final answers pass if they had followed the <FINAL_ANSWER_JSON> contract?

    python -m analysis.format_recovery --run-file runs/<stem>_resume1.jsonl --split full --out analysis/results/<new_dir>

This is an ANALYSIS of existing outputs, never an official score. Nothing is re-generated; no model or tool is called.

Candidate universe (proof in recovery_summary.json): the unchanged scorer sets task_success only when there are no
failure labels; process and state failures add labels independently of the final answer, and a run status other
than `completed` adds `run:<status>`. So only scored items whose final answer failed to parse while process_success
and state_success are true can possibly pass after a format repair. Every such item is audited.

Per candidate (deterministic rules; gold labels are NEVER read until the unchanged scorer is called at the end):
  1. run status != completed or empty final text            -> task_failure
  2. evidence checks on the verbatim final text vs the recorded trajectory / state:
       train ids not seen in the query or any tool observation, currency amounts not present in any observation,
       booking ids not in the final state, booking claims with no booking in the state,
       a final sentence that is an unfinished plan ("Let's find ...")                           -> task_failure
     truncated / degenerate output, tasks needing structured answer_values                     -> insufficient_evidence
  3. recovery
       wrapper_repair   : the text already holds an opening tag + a complete JSON object; only the closing tag is
                          appended (all values are the model's own)
       prose_extraction : the block is built ONLY from values stated explicitly in the final text and confirmed by
                          the trajectory/state: status from unambiguous cue phrases, selected_train / selected_class
                          only if exactly one distinct value is stated, booking_ids only as stated (and present in the
                          state), requested_passengers only names present in the query AND the text AND a booking
                          call; `notes` is a fixed marker (unscored). Any ambiguity -> insufficient_evidence.
  4. the recovered text (original text verbatim + block) is parsed with the unchanged parser and scored with the
     unchanged scorer on a copy of the row: pass -> format_only_recoverable; fail -> task_failure (scorer labels).
Outputs (new directory, never overwritten): recovery_candidates.jsonl, recovery_summary.json, recovery_summary.md,
recovery_diff.md.
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from analysis.observe_run import LANGUAGES, SPLITS, GOLD_PATH, SPEC_PATH, expected_items, load_rows, select_latest, sha256_file
from evaluation.final_answer import CLOSE, OPEN, parse_final_answer
from evaluation.scorer import STRUCTURED_VALUE_CHECKS, score

NOTES_MARKER = "format-recovery analysis: wrapper added to the original reply; not model output"
CATEGORIES = ("format_only_recoverable", "task_failure", "insufficient_evidence")

TRAIN_RE = re.compile(r"\bBTB\d{3}\b")
BOOKING_RE = re.compile(r"\bBK\d{4}\b")
CLASS_RE = re.compile(r"(?<![A-Za-z0-9])(1A|2A|3A|SL|CC)(?![A-Za-z0-9])")
AMOUNT_RE = re.compile(r"(?:₹|\bRs\.?|\bINR)\s*([\d,]+(?:\.\d+)?)|([\d,]+(?:\.\d+)?)\s*(?:INR\b|rupees?\b|rupaye\b|रुपये|रुपए|रुपया)", re.I)
NUM_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])")

# ---- status cue lexicons (en / hinglish / hi / mr). Clarification needs a '?' AND an information request.
CLARIFY_RE = re.compile(
    r"(please|could you|can you|kindly)\s+(please\s+)?(provide|specify|confirm|tell|share|clarify|check and provide)"
    r"|\bwhich (station|date|train|class|one)\b|\bkya aap\b|\bbata(o|iye|iyen|yein| do)\b"
    r"|कृपया|बताएं|बताइए|बताइये|स्पष्ट करें|सांगा|सांगाल|स्पष्ट करा", re.I)
CANNOT_RE = re.compile(
    r"\b(cannot|can't|could not|couldn't|unable to)\s+(complete|book|find|process|cancel|fulfil|fulfill|be completed)\b"
    r"|\bno trains?\b.{0,40}\b(available|found|run|running)\b|\bnone of the trains\b"
    r"|\bnot (be )?(possible|recognized|recognised)\b|\b(does not|doesn't) match any\b|\binvalid\b"
    r"|\b(nahi|nahin) (mil|ho) (sakti|sakta|saka|payi|paya)\b"
    r"|नहीं मिल|बुक नहीं|संभव नहीं|नहीं हो सक|मिळाली नाही|सापडल[ीे] नाही|शक्य नाही|होऊ शकले नाही", re.I)
OFFER_RE = re.compile(r"\b(would you like|shall i|do you want|should i)\b|\bkya main\b|क्या मैं|क्या आप चाहते", re.I)
UNFINISHED_RE = re.compile(
    r"\b(let's|let us|let me|i will now|i will (check|find|search|proceed|look)|next,? i will|we need to (find|check))\b"
    r"|\b(karte hain|dekhte hain|chaliye)\b|करते हैं|करेंगे|चलिए|करूया|पाहूया", re.I)
BOOK_CLAIM_RE = re.compile(r"\b(has been booked|have booked|booked successfully|successfully booked|your booking id|booking ids? (is|are))\b"
                           r"|बुक कर दिया|बुक हो गया|बुक केले|बुक झाले", re.I)
BOOK_INTENT_RE = re.compile(r"\bbook\b|बुक", re.I)
# negative claims and the observation each one needs as support
NO_TRAINS_RE = re.compile(r"\bno trains?\b(?!\s*id)|\bnone of the trains\b|\bcannot find a train\b(?!\s*id)|\bcould(?: not|n't) find (?:a|any) trains?\b(?!\s*id)"
                          r"|\bkoi train nahi\b|कोई ट्रेन नहीं|ट्रेन उपलब्ध नाही|ट्रेन सापडली नाही", re.I)
BAD_TRAIN_RE = re.compile(r"train id.{0,40}(invalid|not recogni[sz]ed|does not match|not valid|is incorrect)|(invalid|unrecogni[sz]ed) train id", re.I)
BAD_STATION_RE = re.compile(r"station.{0,60}(not (be )?found|could not be (found|resolved)|couldn't be (found|resolved))|no station with", re.I)


# --------------------------------------------------------------------------------------------- evidence helpers
def _observations(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [e.get("observation") or {} for e in row.get("trajectory", []) if e.get("event") == "tool_call"]


def _obs_numbers(row: dict[str, Any]) -> set[float]:
    nums: set[float] = set()
    for o in _observations(row):
        if o.get("ok"):
            nums |= {float(n) for n in NUM_RE.findall(json.dumps(o.get("data"), ensure_ascii=False))}
    return nums


def _amounts(text: str) -> list[float]:
    out = []
    for a, b in AMOUNT_RE.findall(text):
        v = (a or b).replace(",", "")
        try:
            out.append(float(v))
        except ValueError:
            pass
    return out


def _last_sentence(text: str) -> str:
    parts = [p.strip() for p in re.split(r"(?<=[.!?।])\s+|\n+", text) if p.strip()]
    return parts[-1] if parts else ""


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def unsupported_negative_claims(row: dict[str, Any]) -> list[str]:
    """Negative claims in the reply that no tool observation supports for USER-PROVIDED input (an error caused by the
    model's own placeholder / guessed arguments does not support a claim about the user's request)."""
    text, query = row.get("final_text") or "", row.get("query", "")
    calls = [e for e in row.get("trajectory", []) if e.get("event") == "tool_call"]

    def err(e):
        return ((e.get("observation") or {}).get("error") or {}).get("code")
    out = []
    if NO_TRAINS_RE.search(text) and not any(e.get("tool") == "search_trains" and (e.get("observation") or {}).get("ok") for e in calls):
        out.append(f"says no trains are available ({NO_TRAINS_RE.search(text).group(0)!r}) but no search_trains call succeeded")
    if BAD_TRAIN_RE.search(text):
        query_ids = set(TRAIN_RE.findall(query))
        if not any(err(e) == "INVALID_TRAIN" and (e.get("arguments") or {}).get("train_id") in query_ids for e in calls):
            out.append("says the user's train id is invalid, but no INVALID_TRAIN error was returned for a train id from the request")
    if BAD_STATION_RE.search(text):
        def user_arg(e):
            a = e.get("arguments") or {}
            return any(isinstance(a.get(k), str) and a[k].strip() and a[k].strip() in query for k in ("name", "source", "destination"))
        if not any(err(e) in ("STATION_NOT_FOUND", "INVALID_STATION") and user_arg(e) for e in calls):
            out.append("says a station could not be found, but no station error was returned for a name/code from the request")
    return out


# --------------------------------------------------------------------------------------------- audit
def audit_evidence(row: dict[str, Any]) -> tuple[str | None, str | None, dict[str, Any]]:
    """(category or None if no early decision, reason, evidence). Uses only the row (query, text, trajectory, state)."""
    text = row.get("final_text") or ""
    ev: dict[str, Any] = {}
    if row.get("status") != "completed":
        return "task_failure", f"run status `{row.get('status')}` is an official model failure (scorer adds run:{row.get('status')} regardless of format)", ev
    if not text.strip():
        return "task_failure", "no final response text: nothing to recover", ev
    seen_ids = set(TRAIN_RE.findall(row.get("query", "")))
    for o in _observations(row):
        seen_ids |= set(TRAIN_RE.findall(json.dumps(o, ensure_ascii=False)))
    text_ids = sorted(set(TRAIN_RE.findall(text)))
    ev["train_ids_in_text"] = text_ids
    unsupported = [t for t in text_ids if t not in seen_ids]
    if unsupported:
        return "task_failure", f"unsupported claim: train id(s) {unsupported} never appear in the query or any tool observation", ev
    amounts = _amounts(text)
    ev["amounts_in_text"] = amounts
    nums = _obs_numbers(row)
    bad_amounts = [a for a in amounts if a not in nums]
    if bad_amounts:
        return "task_failure", f"unsupported claim: amount(s) {bad_amounts} not present in any successful tool observation", ev
    state_ids = {b.get("booking_id") for b in (row.get("state_snapshot") or {}).get("bookings", [])}
    text_bks = sorted(set(BOOKING_RE.findall(text)))
    ev["booking_ids_in_text"], ev["booking_ids_in_state"] = text_bks, sorted(i for i in state_ids if i)
    if [b for b in text_bks if b not in state_ids]:
        return "task_failure", f"booking id(s) {[b for b in text_bks if b not in state_ids]} stated but not in the final state", ev
    if BOOK_CLAIM_RE.search(text) and not state_ids:
        return "task_failure", "claims a booking was made, but the final state has no booking", ev
    unsupported_neg = unsupported_negative_claims(row)
    ev["unsupported_negative_claims"] = unsupported_neg
    if unsupported_neg:
        return "task_failure", f"unsupported claim: {unsupported_neg[0]}", ev
    if UNFINISHED_RE.search(_last_sentence(text)):
        return "task_failure", f"final sentence is an unfinished plan, not an answer: {_last_sentence(text)[:120]!r}", ev
    resp = [x for x in row.get("raw_log", []) if x.get("type") == "model_response"]
    if resp and resp[-1].get("finish_reason") == "length":
        return "insufficient_evidence", "final reply was cut off at the output-token limit", ev
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) >= 6 and len(set(lines)) / len(lines) <= 0.5:
        return "insufficient_evidence", "degenerate repetitive output", ev
    if row["semantic_task_id"] in STRUCTURED_VALUE_CHECKS:
        return "insufficient_evidence", "task requires structured answer_values; deriving them from prose would be semantic interpretation", ev
    return None, None, ev


def decide_status(row: dict[str, Any]) -> tuple[str | None, str]:
    text, query = row.get("final_text") or "", row.get("query", "")
    clarify = "?" in text and bool(CLARIFY_RE.search(text))
    cannot = bool(CANNOT_RE.search(text))
    offer = bool(OFFER_RE.search(text))
    cues = {"clarify": clarify, "cannot": cannot, "offer": offer}
    if clarify and cannot:
        return None, f"conflicting status cues {cues}: inability statement plus a clarification request"
    if clarify:
        return "needs_clarification", f"clarification request ({CLARIFY_RE.search(text).group(0)!r} with '?')"
    if cannot:
        return "cannot_complete", f"inability statement ({CANNOT_RE.search(text).group(0)!r})"
    if offer and BOOK_INTENT_RE.search(query):
        return None, f"asks permission ({OFFER_RE.search(text).group(0)!r}) for the action the user requested"
    return "success", "no inability, clarification or permission cue; reply states an outcome"


def extract_fields(row: dict[str, Any], status: str) -> tuple[dict[str, Any] | None, str]:
    """Answer fields from explicit statements only. Returns (fields, reason) or (None, why not)."""
    text, query = row.get("final_text") or "", row.get("query", "")
    trains = sorted(set(TRAIN_RE.findall(text)))
    if len(trains) > 1:
        return None, f"several train ids stated {trains}; selected_train would need interpretation"
    classes = sorted(set(CLASS_RE.findall(text)))
    if len(classes) > 1:
        return None, f"several travel classes stated {classes}; selected_class would need interpretation"
    bookings = (row.get("state_snapshot") or {}).get("bookings", [])
    state_ids = sorted(b["booking_id"] for b in bookings)
    text_bks = sorted(set(BOOKING_RE.findall(text)))
    if set(state_ids) - set(text_bks):
        return None, f"booking id(s) {sorted(set(state_ids) - set(text_bks))} exist in the state but are not stated in the reply"
    raw = [b.get("passenger") for b in bookings] + [(e.get("arguments") or {}).get("passenger") for e in row.get("trajectory", [])
                                                    if e.get("tool") == "book_ticket"]
    # models may pass non-string arguments (e.g. a list of names); only string values can be a stated passenger name
    candidates = {c for c in raw if isinstance(c, str) and c.strip()}
    passengers = sorted(c for c in candidates if _norm(c) in _norm(query) and _norm(c) in _norm(text))
    booked_names = {_norm(b["passenger"]) for b in bookings}
    if booked_names - {_norm(p) for p in passengers}:
        return None, "a booked passenger is not named in the reply"
    return {"status": status, "selected_train": trains[0] if trains else None, "selected_class": classes[0] if classes else None,
            "booking_ids": text_bks, "requested_passengers": passengers, "notes": NOTES_MARKER}, "fields stated explicitly"


def wrapper_repair(text: str) -> str | None:
    """Append ONLY the closing tag when the reply holds an opening tag followed by a complete, valid block."""
    if OPEN in text and CLOSE not in text[text.rfind(OPEN):]:
        repaired = text.rstrip() + "\n" + CLOSE
        if parse_final_answer(repaired)["ok"]:
            return repaired
    return None


def audit_candidate(row: dict[str, Any], gold_task: dict[str, Any]) -> dict[str, Any]:
    text = row.get("final_text") or ""
    rec: dict[str, Any] = {
        "task_id": row["task_id"], "semantic_task_id": row["semantic_task_id"], "language": row["language"],
        "source_file": row["_source"]["file"], "source_line": row["_source"]["line"],
        "official": {"status": row.get("status"), "task_success": row["score"].get("task_success"),
                     "final_answer_parse": row["score"].get("final_answer_parse"), "failure_labels": row["score"].get("failure_labels"),
                     "process_success": row["score"].get("process_success"), "state_success": row["score"].get("state_success")},
        "original_final_text": text, "original_final_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "answer_block_present": OPEN in text, "recovery_method": None, "extracted_fields": None, "status_reason": None,
        "recovered_final_text": None, "recovered_parse": None, "recovered_score": None,
    }
    repaired = wrapper_repair(text) if row.get("status") == "completed" else None
    if repaired is not None:
        rec["recovery_method"], recovered = "wrapper_repair", repaired
        rec["evidence"] = {}
    else:
        category, reason, ev = audit_evidence(row)
        rec["evidence"] = ev
        if category:
            return {**rec, "classification": category, "reason": reason}
        status, why = decide_status(row)
        rec["status_reason"] = why
        if status is None:
            return {**rec, "classification": "insufficient_evidence", "reason": why}
        fields, why_f = extract_fields(row, status)
        if fields is None:
            return {**rec, "classification": "insufficient_evidence", "reason": why_f}
        rec["recovery_method"], rec["extracted_fields"] = "prose_extraction", fields
        recovered = text.rstrip() + "\n" + OPEN + "\n" + json.dumps(fields, ensure_ascii=False) + "\n" + CLOSE
    parsed = parse_final_answer(recovered)
    trial = copy.deepcopy({k: v for k, v in row.items() if k != "_source"})
    trial["final_text"] = recovered
    sc = score(trial, gold_task, trial["state_snapshot"])  # unchanged official scorer
    rec.update(recovered_final_text=recovered, recovered_parse=parsed["error"] or "ok",
               recovered_score={"task_success": sc["task_success"], "failure_labels": sc["failure_labels"]})
    if sc["task_success"] is True:
        status = (parsed.get("answer") or {}).get("status")
        rec["caveats"] = ({"needs_clarification": ["the scorer checks only the needs_clarification status, not what the reply asks for"],
                           "cannot_complete": ["the scorer checks only the cannot_complete status, not the reason the reply gives"]}
                          .get(status, []))
        return {**rec, "classification": "format_only_recoverable", "reason": f"{rec['recovery_method']}: recovered answer passes the unchanged scorer"}
    return {**rec, "classification": "task_failure", "reason": f"recovered answer still fails the unchanged scorer: {sc['failure_labels']}"}


# --------------------------------------------------------------------------------------------- run
def build(rows_selected: dict[str, dict[str, Any]], gold: dict[str, Any], categories: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sel = list(rows_selected.values())
    scored = [r for r in sel if (r.get("score") or {}).get("scored")]
    not_scored = [r for r in sel if not (r.get("score") or {}).get("scored")]
    official_success = sum(r["score"]["task_success"] is True for r in scored)
    parse_failed = [r for r in scored if r["score"].get("final_answer_parse") != "ok"]
    cands = [r for r in parse_failed if r["score"].get("process_success") and r["score"].get("state_success")]
    records = []
    for r in sorted(cands, key=lambda r: r["task_id"]):
        rec = audit_candidate(r, gold[r["semantic_task_id"]])
        rec["category"] = categories.get(r["semantic_task_id"])
        records.append(rec)
    C = collections.Counter
    recovered = [r for r in records if r["classification"] == "format_only_recoverable"]
    strict = [r for r in recovered if r["recovery_method"] == "wrapper_repair"]
    denom = len(scored)

    def breakdown(key):
        out = {}
        for k in sorted({r[key] for r in records}, key=str):
            g = [r for r in records if r[key] == k]
            out[str(k)] = dict(C(r["classification"] for r in g))
        return out

    summary = {
        "analysis": "format-recovery analysis (NOT an official score)",
        "official": {"items": len(sel), "scored_denominator": denom, "not_scored": [r["task_id"] for r in not_scored],
                     "not_scored_reasons": {r["task_id"]: r.get("error_kind") for r in not_scored},
                     "task_success": official_success, "rate": official_success / denom if denom else None,
                     "final_answer_parse_ok": sum(r["score"].get("final_answer_parse") == "ok" for r in scored)},
        "universe": {"parse_failed": len(parse_failed),
                     "excluded_process_failed": sum(not r["score"].get("process_success") for r in parse_failed),
                     "excluded_state_failed": sum(not r["score"].get("state_success") for r in parse_failed),
                     "excluded_total": len(parse_failed) - len(cands), "candidates": len(cands),
                     "why": "task_success requires zero failure labels; process/state failures add labels independently of the "
                            "final answer, so only parse-failed items with process_success and state_success can pass after repair"},
        "classification": {c: sum(r["classification"] == c for r in records) for c in CATEGORIES},
        "recovery_methods_attempted": dict(C(r["recovery_method"] for r in records if r["recovery_method"])),
        "recovered_parse_ok": sum(r["recovered_parse"] == "ok" for r in records),
        "recovered_scorer_pass": len(recovered),
        "recovered_items": [r["task_id"] for r in recovered],
        "recovered_with_caveats": {r["task_id"]: r.get("caveats") for r in recovered if r.get("caveats")},
        "format_recovery_score_strict": {"definition": "official successes + wrapper_repair passes (model-authored JSON only)",
                                         "successes": official_success + len(strict), "denominator": denom,
                                         "rate": (official_success + len(strict)) / denom if denom else None},
        "format_recovery_score_conservative": {"definition": "official successes + recovered passes without caveats (pass does not rest on a status-only check)",
                                               "successes": official_success + sum(1 for r in recovered if not r.get("caveats")), "denominator": denom,
                                               "rate": (official_success + sum(1 for r in recovered if not r.get("caveats"))) / denom if denom else None},
        "format_recovery_score_extended": {"definition": "official successes + all recovered passes (wrapper_repair + prose_extraction)",
                                           "successes": official_success + len(recovered), "denominator": denom,
                                           "rate": (official_success + len(recovered)) / denom if denom else None},
        "by_language": breakdown("language"), "by_category": breakdown("category"),
        "rejection_reasons": dict(C(_reason_family(r["reason"]) for r in records if r["classification"] != "format_only_recoverable").most_common()),
        "candidate_ids_unique": len({r["task_id"] for r in records}) == len(records),
    }
    return records, summary


def _reason_family(reason: str) -> str:
    for key in ("run status", "no final response", "unsupported claim: train id", "unsupported claim: amount",
                "unsupported claim: says no trains", "unsupported claim: says the user's train id", "unsupported claim: says a station", "booking id(s)",
                "claims a booking", "unfinished plan", "cut off", "degenerate", "structured answer_values", "conflicting status cues",
                "asks permission", "several train ids", "several travel classes", "exist in the state but are not stated",
                "booked passenger", "still fails the unchanged scorer"):
        if key in reason:
            return key
    return "other"


def render_md(records: list[dict[str, Any]], s: dict[str, Any]) -> str:
    o, u = s["official"], s["universe"]
    L = ["# Format-recovery analysis — Qwen 2.5 3B full run", "",
         "**Not an official score.** Official results are unchanged. This analysis asks whether the model's *existing* final "
         "replies would pass the unchanged scorer if only the `<FINAL_ANSWER_JSON>` contract had been followed. It does not "
         "show what the model would have generated under the contract.", "",
         "## Official result (unchanged)", "",
         f"- task_success **{o['task_success']}/{o['scored_denominator']}**; final-answer parse ok {o['final_answer_parse_ok']}/{o['scored_denominator']}",
         f"- not scored (excluded from every denominator): {o['not_scored']} ({o['not_scored_reasons']})", "",
         "## Candidate universe", "",
         f"- parse-failed scored items: {u['parse_failed']}; excluded because process failed: {u['excluded_process_failed']}, "
         f"state failed: {u['excluded_state_failed']} (overlapping), total excluded {u['excluded_total']}",
         f"- audited candidates (parse failed, process ok, state ok): **{u['candidates']}**", f"- {u['why']}", "",
         "## Classification", "", "| category | items |", "|---|---|"]
    L += [f"| {c} | {n} |" for c, n in s["classification"].items()]
    L += ["", f"- recovery attempted: {s['recovery_methods_attempted']}; recovered answers accepted by the unchanged parser: "
          f"{s['recovered_parse_ok']}; passing the unchanged scorer: **{s['recovered_scorer_pass']}** {s['recovered_items']}",
          f"- recovered items whose pass rests on a status-only check (caveat): {s['recovered_with_caveats'] or 'none'}", "",
          "## Format-recovery scores (analysis only)", "",
          f"- strict (wrapper repair of model-authored JSON only): **{s['format_recovery_score_strict']['successes']}/{s['format_recovery_score_strict']['denominator']}**",
          f"- conservative (recoveries whose pass does not rest on a status-only check): **{s['format_recovery_score_conservative']['successes']}/{s['format_recovery_score_conservative']['denominator']}**",
          f"- extended (wrapper repair + prose extraction, all scorer-accepted): **{s['format_recovery_score_extended']['successes']}/{s['format_recovery_score_extended']['denominator']}**",
          f"- official, for comparison: {o['task_success']}/{o['scored_denominator']}", "",
          "## Breakdown", "", "| language | " + " | ".join(CATEGORIES) + " |", "|---|" + "---|" * len(CATEGORIES)]
    L += [f"| {k} | " + " | ".join(str(v.get(c, 0)) for c in CATEGORIES) + " |" for k, v in s["by_language"].items()]
    L += ["", "| category | " + " | ".join(CATEGORIES) + " |", "|---|" + "---|" * len(CATEGORIES)]
    L += [f"| {k} | " + " | ".join(str(v.get(c, 0)) for c in CATEGORIES) + " |" for k, v in s["by_category"].items()]
    L += ["", "## Why candidates were not recovered", "", "| reason | items |", "|---|---|"]
    L += [f"| {k} | {n} |" for k, n in s["rejection_reasons"].items()]
    L += ["", "## Per-candidate decisions", "", "| item | classification | method | reason |", "|---|---|---|---|"]
    L += [f"| {r['task_id']} | {r['classification']} | {r['recovery_method'] or '-'} | {r['reason'].replace('|', '/')[:180]} |" for r in records]
    L += ["", "## Limitations", "",
          "- Analysis of recorded replies only; generating under the contract could change the reply itself.",
          "- Status cues are deterministic multilingual phrase lists; ambiguous replies are not recovered (conservative).",
          "- Benchmark items are drafts without human review.", ""]
    return "\n".join(L)


def render_diff(records: list[dict[str, Any]]) -> str:
    L = ["# Recovery diff (original reply vs recovered artefact)", "",
         "Only the appended block differs; the original reply is kept verbatim (sha256 recorded in recovery_candidates.jsonl).", ""]
    for r in records:
        if r["recovered_final_text"] is None:
            continue
        L += [f"## {r['task_id']} — {r['classification']} ({r['recovery_method']})", "", "**Original:**", "", "```text",
              r["original_final_text"], "```", "", "**Recovered:**", "", "```text", r["recovered_final_text"], "```", "",
              f"Parser: `{r['recovered_parse']}`; unchanged scorer: task_success={r['recovered_score']['task_success']} "
              f"labels={r['recovered_score']['failure_labels']}", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-file", type=Path, action="append", required=True)
    ap.add_argument("--split", required=True, choices=list(SPLITS))
    ap.add_argument("--languages", nargs="+", default=LANGUAGES, choices=LANGUAGES)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        ap.error(f"output directory already exists (never overwritten): {args.out}")
    rows, inputs = load_rows(args.run_file)
    selected, integrity = select_latest(rows, expected_items(args.split, args.languages))
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    categories = {t["semantic_task_id"]: t["category"] for t in json.loads(SPEC_PATH.read_text(encoding="utf-8"))["tasks"]}
    records, summary = build(selected, gold, categories)
    summary = {"inputs": inputs, "integrity": integrity, **summary}
    for i in inputs:
        if sha256_file(Path(i["file"])) != i["sha256"]:
            raise RuntimeError(f"input modified: {i['file']}")
    args.out.mkdir(parents=True)
    with (args.out / "recovery_candidates.jsonl").open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (args.out / "recovery_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.out / "recovery_summary.md").write_text(render_md(records, summary), encoding="utf-8")
    (args.out / "recovery_diff.md").write_text(render_diff(records), encoding="utf-8")
    c = summary["classification"]
    print(f"candidates={summary['universe']['candidates']} {c} recovered_pass={summary['recovered_scorer_pass']} "
          f"strict={summary['format_recovery_score_strict']['successes']}/{summary['official']['scored_denominator']} "
          f"conservative={summary['format_recovery_score_conservative']['successes']}/{summary['official']['scored_denominator']} "
          f"extended={summary['format_recovery_score_extended']['successes']}/{summary['official']['scored_denominator']} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
