"""Multilingual pilot layer (T01-T05 x en/hinglish/hi/mr = 20 DRAFT items). Nothing here asserts human verification."""
import itertools
import json
import shutil

import pytest

from benchmark import language_checks as lc
from benchmark import validate_tasks as vt
from benchmark.build_gold import GOLD_PATH
from benchmark import human_review as hr

_n = itertools.count()
LANGS = ["en", "hinglish", "hi", "mr"]
IDS = ["T01", "T02", "T03", "T04", "T05"]


def rows(lang, d=None):
    f = (d or vt.LANG_DIR) / f"{lang}.jsonl"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def mutate(tmp_path, monkeypatch, lang, tid, fn):
    d = tmp_path / f"languages{next(_n)}"
    shutil.copytree(vt.LANG_DIR, d)
    rs = rows(lang, d)
    for r in rs:
        if r["semantic_task_id"] == tid:
            fn(r)
    (d / f"{lang}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rs) + "\n", encoding="utf-8")
    monkeypatch.setattr(vt, "LANG_DIR", d)
    monkeypatch.setattr(vt, "AUDIT_PATH", d / "pilot_language_audit.json")
    return " | ".join(vt.validate())


def test_committed_pilot_is_valid_and_has_20_items():
    assert vt.validate() == []
    assert sum(1 for l in LANGS for r in rows(l) if r["semantic_task_id"] in IDS) == 20  # pilot slice unchanged
    assert sum(len(rows(l)) for l in LANGS) == 800  # pilot 20 + T06-T15 40 + T16-T25 40 + T26-T50 100 + T51-T75 100 + T76-T100 100 + T101-T200 400


def test_every_task_has_four_variants_with_one_shared_spec_and_no_language_in_gold():
    for tid in IDS:
        got = [next(r for r in rows(l) if r["semantic_task_id"] == tid) for l in LANGS]
        assert [r["language"] for r in got] == LANGS
        assert [r["task_id"] for r in got] == [f"{tid}_{l}" for l in LANGS]
        assert len({(r["category"], tuple(r["allowed_tools"])) for r in got}) == 1
    gold = GOLD_PATH.read_text(encoding="utf-8")
    assert "hinglish" not in gold and '"language"' not in gold


def test_non_english_items_review_fields_match_human_review_record():
    for l in LANGS[1:]:
        for r in rows(l):
            assert (r["reviewer"], r["review_status"]) == hr.expected_review(r["language"], r["semantic_task_id"]) and r["author"] == "Claude-generated draft"
    audit = json.loads(vt.AUDIT_PATH.read_text(encoding="utf-8"))["records"]
    assert len(audit) == 20
    assert all(a["human_review"] == a["fluency_review"] == a["equivalence_review"] == "pending_human_review" for a in audit)


def test_english_is_unchanged():
    import hashlib
    head = b"".join((vt.LANG_DIR / "en.jsonl").read_bytes().splitlines(keepends=True)[:5])  # the 5 pilot rows, byte-exact
    assert hashlib.sha256(head).hexdigest() == vt.FROZEN_EN_SHA256
    assert {r["semantic_task_id"]: r["query"] for r in rows("en") if r["semantic_task_id"] in IDS} == vt.FROZEN_EN_QUERIES


def test_stations_use_the_frozen_aliases_and_keep_latin_names():
    for l in LANGS[1:]:
        q = {r["semantic_task_id"]: r["query"] for r in rows(l)}
        assert "Ananya Kulkarni" in q["T04"] and "Vikram Singh" in q["T05"]
        assert "BTB103" in q["T01"] and "BTB103" in q["T05"]
    assert "नागपूर" in rows("mr")[1]["query"] and "नागपुर" in rows("hi")[1]["query"] and "Nagpur" in rows("hinglish")[1]["query"]


def test_t03_is_inclusive_and_no_booking_in_every_language():
    q = {l: next(r["query"] for r in rows(l) if r["semantic_task_id"] == "T03") for l in LANGS}
    assert "at or after 6 PM" in q["en"]
    assert "6 baje ya uske baad" in q["hinglish"] and "6 बजे या उसके बाद" in q["hi"] and "6 वाजता किंवा त्यानंतर" in q["mr"]
    assert "book mat karna" in q["hinglish"] and "बुक मत कीजिए" in q["hi"] and "बुक करू नका" in q["mr"]


def test_t03_availability_is_explicit_in_every_language():
    q = {l: next(r["query"] for r in rows(l) if r["semantic_task_id"] == "T03") for l in LANGS}
    assert "have seats available" in q["en"] and "seats available honi chahiye" in q["hinglish"]
    assert "सीटें उपलब्ध होनी चाहिए" in q["hi"] and "सीट उपलब्ध असावी" in q["mr"]
    audit = json.loads(vt.AUDIT_PATH.read_text(encoding="utf-8"))["records"]
    assert all(a["checks"]["availability_constraint_preserved"] is True for a in audit if a["semantic_task_id"] == "T03")


def test_t02_only_train_meaning_in_every_language():
    q = {l: next(r["query"] for r in rows(l) if r["semantic_task_id"] == "T02") for l in LANGS}
    assert "the only train from Nagpur to Pune" in q["en"] and "ek hi train" in q["hinglish"]
    assert "एकमात्र ट्रेन" in q["hi"] and "एकमेव ट्रेन" in q["mr"]


def test_non_english_variants_are_claude_drafts_reviewed_only_per_record():
    for l in LANGS[1:]:
        for r in rows(l):
            assert r["author"] == "Claude-generated draft" and (r["reviewer"], r["review_status"]) == hr.expected_review(r["language"], r["semantic_task_id"])
            assert (r["review_status"] == "draft") == (l in ("hinglish", "hi") or int(r["semantic_task_id"][1:]) > 75)


# ---- negative tests: the validator must catch semantic drift ----
def test_detects_t03_exclusive_time(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hi", "T03", lambda r: r.update(query=r["query"].replace("या उसके बाद", "के बाद")))
    assert "T03_hi" in e and "inclusive" in e


def test_detects_t03_missing_no_booking(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "mr", "T03", lambda r: r.update(query=r["query"].replace("काहीही बुक करू नका; ", "")))
    assert "T03_mr" in e and "no-booking" in e


def test_detects_t04_dropped_booking_or_cheapest(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hinglish", "T04", lambda r: r.update(query=r["query"].replace("sabse sasta ", "")))
    assert "T04_hinglish" in e


def test_detects_t05_dropped_no_fallback(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hi", "T05", lambda r: r.update(query=r["query"].replace("या दूसरी ट्रेन", "")))
    assert "T05_hi" in e


def test_detects_changed_date_and_changed_number(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "mr", "T02", lambda r: r.update(query=r["query"].replace("7 ऑक्टोबर", "8 ऑक्टोबर")))
    assert "T02_mr" in e
    e = mutate(tmp_path, monkeypatch, "hinglish", "T03", lambda r: r.update(query=r["query"].replace("3,000", "4,000")))
    assert "T03" in e


def test_detects_wrong_status_author_and_verification_claims(tmp_path, monkeypatch):
    assert "review_status must be 'draft'" in mutate(tmp_path, monkeypatch, "hi", "T01", lambda r: r.update(review_status="accepted"))
    assert "author must be" in mutate(tmp_path, monkeypatch, "mr", "T01", lambda r: r.update(author="native speaker"))
    assert "reviewer must be null" in mutate(tmp_path, monkeypatch, "hi", "T01", lambda r: r.update(reviewer="someone"))  # mr is human-reviewed


def test_detects_changed_english_duplicate_ids_and_missing_variant(tmp_path, monkeypatch):
    assert "English query changed" in mutate(tmp_path, monkeypatch, "en", "T01", lambda r: r.update(query=r["query"] + " "))
    assert "id/language mismatch" in mutate(tmp_path, monkeypatch, "hi", "T02", lambda r: r.update(task_id="T01_hi"))
    d = tmp_path / f"languages{next(_n)}"
    shutil.copytree(vt.LANG_DIR, d)
    (d / "mr.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows("mr", d) if r["semantic_task_id"] != "T05") + "\n", encoding="utf-8")
    monkeypatch.setattr(vt, "LANG_DIR", d)
    monkeypatch.setattr(vt, "AUDIT_PATH", d / "pilot_language_audit.json")
    e = " | ".join(vt.validate())
    assert "expected exactly 800" in e and "T05: variants" in e


def test_detects_stale_audit(tmp_path, monkeypatch):
    d = tmp_path / f"languages{next(_n)}"
    shutil.copytree(vt.LANG_DIR, d)
    a = json.loads((d / "pilot_language_audit.json").read_text(encoding="utf-8"))
    a["records"][5]["human_review"] = "verified"
    (d / "pilot_language_audit.json").write_text(json.dumps(a, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(vt, "LANG_DIR", d)
    monkeypatch.setattr(vt, "AUDIT_PATH", d / "pilot_language_audit.json")
    assert "must be pending_human_review" in " | ".join(vt.validate())
