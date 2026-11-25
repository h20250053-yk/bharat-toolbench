"""Human review record (benchmark/human_review.py + languages/human_review.json): Marathi and Gujarati T01-T75 reviewed,
English / Hinglish / Hindi untouched drafts, the hash freezes still protect the text, and an edit to a reviewed query is
reported as a stale review."""
import itertools
import json
import shutil

from benchmark import human_review as hr
from benchmark import validate_tasks as vt

_n = itertools.count()
ALL = [f"T{i:02d}" for i in range(1, 76)]


def rows(lang, d=None):
    return [json.loads(l) for l in ((d or vt.LANG_DIR) / f"{lang}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def mutate(tmp_path, monkeypatch, lang, tid, fn, record_fn=None):
    d = tmp_path / f"languages{next(_n)}"
    shutil.copytree(vt.LANG_DIR, d)
    rs = rows(lang, d)
    for r in rs:
        if r["semantic_task_id"] == tid:
            fn(r)
    (d / f"{lang}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rs) + "\n", encoding="utf-8")
    if record_fn:
        rec = json.loads((d / hr.RECORD_PATH.name).read_text(encoding="utf-8"))
        record_fn(rec)
        (d / hr.RECORD_PATH.name).write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(vt, "LANG_DIR", d)
    monkeypatch.setattr(vt, "AUDIT_PATH", d / "pilot_language_audit.json")
    monkeypatch.setattr(vt, "GU_AUDIT_PATH", d / vt.GU_AUDIT_PATH.name)
    monkeypatch.setattr(vt, "GU2_AUDIT_PATH", d / vt.GU2_AUDIT_PATH.name)
    monkeypatch.setattr(hr, "RECORD_PATH", d / hr.RECORD_PATH.name)
    return " | ".join(vt.validate())


def test_scope_is_marathi_and_gujarati_all_75():
    assert hr.REVIEWED == {"mr": ALL, "gu": ALL}
    for lang in ("mr", "gu"):  # T01-T75 reviewed; the 3.0 batch T76-T100 is still a draft in every language
        assert all((r["review_status"] == "reviewed" and r["reviewer"] == hr.REVIEWER) == (r["semantic_task_id"] in ALL) for r in rows(lang))
    for lang in ("en", "hinglish", "hi"):
        assert all(r["review_status"] == "draft" and r["reviewer"] is None for r in rows(lang))


def test_record_pins_current_query_text():
    rec = json.loads(hr.RECORD_PATH.read_text(encoding="utf-8"))
    assert [i["task_id"] for i in rec["items"]] == [f"{t}_mr" for t in ALL] + [f"{t}_gu" for t in ALL]
    q = {r["task_id"]: r["query"] for lang in ("mr", "gu") for r in rows(lang)}
    assert all(i["query_sha256"] == hr.query_sha(q[i["task_id"]]) and i["review_date"] == hr.REVIEW_DATE for i in rec["items"])


def test_freeze_hashes_ignore_review_fields_only():
    # the normalised heads equal the frozen draft-era hashes, so the text freeze is unchanged by recording the review
    import hashlib
    for lang in ("mr",):
        assert hashlib.sha256(hr.draft_head_bytes(vt.LANG_DIR / f"{lang}.jsonl", 50)).hexdigest() == vt.FROZEN_T01_T50_LANG_SHA256[lang]
    assert hashlib.sha256(hr.draft_head_bytes(vt.LANG_DIR / "gu.jsonl", 50)).hexdigest() == vt.FROZEN_GU_T01_T50_LANG_SHA256


def test_validator_passes_and_reports_review():
    assert vt.validate() == []
    assert "150 human-reviewed" in vt._review_summary()


def test_detects_stale_review_after_query_edit(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "mr", "T60", lambda r: r.update(query=r["query"] + " "))
    assert "T60_mr: query changed after human review (stale review" in e
    e = mutate(tmp_path, monkeypatch, "gu", "T70", lambda r: r.update(query=r["query"] + " "))
    assert "T70_gu: query changed after human review (stale review" in e


def test_detects_review_field_drift(tmp_path, monkeypatch):
    assert "T10_mr: reviewer must be" in mutate(tmp_path, monkeypatch, "mr", "T10", lambda r: r.update(reviewer=None))
    assert "T10_hi: reviewer must be null before human review" in mutate(tmp_path, monkeypatch, "hi", "T10", lambda r: r.update(reviewer="someone"))
    assert "T55_hinglish: review_status must be 'draft'" in mutate(tmp_path, monkeypatch, "hinglish", "T55", lambda r: r.update(review_status="reviewed"))
    e = mutate(tmp_path, monkeypatch, "mr", "T01", lambda r: None, record_fn=lambda rec: rec["items"].pop())
    assert "items differ from human_review.REVIEWED" in e
