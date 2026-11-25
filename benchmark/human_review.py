"""Human review record for the non-English language items.

Single source of truth for which language items a person has reviewed. A reviewed row in benchmark/languages/<lang>.jsonl
carries reviewer=REVIEWER and review_status="reviewed"; every other row stays reviewer=None, review_status="draft".

benchmark/languages/human_review.json pins the exact query text that was reviewed (SHA-256 of the query string). If a
reviewed query is edited later, validate_tasks reports the review as stale until the record is written again on purpose:

    python -m benchmark.human_review          # rewrite human_review.json + the review fields of the language rows

The query text itself is not touched by this module, and the hash freezes in validate_tasks are computed with the review
fields reset to their draft values, so recording a review never counts as a change of frozen benchmark content.

Re-recorded for T38_mr on 2026-11-24 after the author-approved wording fix (audit I-08): the Marathi fallback now reads
"इतर ट्रेनपैकी सर्वात स्वस्त" (cheapest among the other trains); query_sha256 of T38_mr changed, nothing else.

Scope as stated by the project author on 2026-11-24: Marathi and Gujarati for all 75 tasks were checked by a human.
Hinglish and Hindi T51-T75 are not covered by this record (add them to REVIEWED once they are checked).
The benchmark 3.0 batches T76-T100 and T101-T200 are not reviewed in any language yet.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

LANG_DIR = Path(__file__).resolve().parent / "languages"
RECORD_PATH = LANG_DIR / "human_review.json"

REVIEWER = "BharatToolBench project author"  # replace with the reviewer's name if wanted, then run this module
REVIEW_DATE = "2026-11-24"
REVIEW_STATUS = "reviewed"
ALL_75 = [f"T{i:02d}" for i in range(1, 76)]
REVIEWED: dict[str, list[str]] = {"mr": ALL_75, "gu": ALL_75}
REVIEW_FIELDS = ("reviewer", "review_status")


def expected_review(lang: str, tid: str) -> tuple[str | None, str]:
    """(reviewer, review_status) a row must carry."""
    return (REVIEWER, REVIEW_STATUS) if tid in REVIEWED.get(lang, []) else (None, "draft")


def apply(row: dict[str, Any]) -> dict[str, Any]:
    reviewer, status = expected_review(row["language"], row["semantic_task_id"])
    return {**row, "reviewer": reviewer, "review_status": status}


def as_draft(row: dict[str, Any]) -> dict[str, Any]:
    """The row with its review fields reset to the draft values (used by the hash freezes)."""
    return {**row, "reviewer": None, "review_status": "draft"}


def draft_head_bytes(path: Path, n: int) -> bytes:
    """First n lines of a language file, re-serialised exactly as the builders write them, review fields reset."""
    lines = path.read_bytes().decode("utf-8").splitlines()[:n]
    return "".join(json.dumps(as_draft(json.loads(l)), ensure_ascii=False) + "\n" for l in lines).encode("utf-8")


def draft_slice_bytes(path: Path, start: int, end: int) -> bytes:
    """Lines start..end-1 (0-based, end exclusive) of a language file, re-serialised like the builders, review fields reset."""
    lines = path.read_bytes().decode("utf-8").splitlines()[start:end]
    return "".join(json.dumps(as_draft(json.loads(l)), ensure_ascii=False) + "\n" for l in lines).encode("utf-8")


def query_sha(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()


def build_record() -> dict[str, Any]:
    items = []
    for lang, ids in REVIEWED.items():
        rows = {json.loads(l)["semantic_task_id"]: json.loads(l)
                for l in (LANG_DIR / f"{lang}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
        for tid in ids:
            items.append({"task_id": f"{tid}_{lang}", "language": lang, "reviewer": REVIEWER, "review_date": REVIEW_DATE,
                          "review_status": REVIEW_STATUS, "query_sha256": query_sha(rows[tid]["query"])})
    return {"description": "Human review of non-English language items. query_sha256 pins the exact text that was reviewed; "
                           "an edit to a reviewed query makes validate_tasks report the review as stale.",
            "scope": {lang: f"{ids[0]}-{ids[-1]} ({len(ids)} items)" for lang, ids in REVIEWED.items()},
            "not_covered": "en (source text), hinglish and hi (not recorded as reviewed in this file)",
            "items": items}


def write() -> None:
    for lang in REVIEWED:
        f = LANG_DIR / f"{lang}.jsonl"
        rows = [apply(json.loads(l)) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        f.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    RECORD_PATH.write_text(json.dumps(build_record(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n = sum(len(v) for v in REVIEWED.values())
    print(f"recorded human review: {n} items ({', '.join(f'{l} {len(v)}' for l, v in REVIEWED.items())}) -> {RECORD_PATH.name}")


if __name__ == "__main__":
    write()
