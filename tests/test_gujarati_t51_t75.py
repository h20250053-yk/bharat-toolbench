"""Gujarati for the end-sem batch T51-T75: the benchmark is now 75 tasks x 5 languages = 375 items. The language-feature
tasks must keep their feature in Gujarati, the Gujarati T01-T50 drafts are frozen, and the other four files are untouched."""
import hashlib
import itertools
import json
import shutil

from benchmark import batch_gujarati as gu
from benchmark import language_checks as lc
from benchmark import validate_tasks as vt
from benchmark.build_gold import load_specs
from environment import RailwayEnv
from evaluation.run_pilot import task_ids
from evaluation.runner import load_items
from benchmark import human_review as hr

IDS = [f"T{i}" for i in range(51, 76)]
LANGS5 = ["en", "hinglish", "hi", "mr", "gu"]
_n = itertools.count()


def rows(lang, d=None):
    return [json.loads(l) for l in ((d or vt.LANG_DIR) / f"{lang}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def q(tid, lang="gu"):
    return next(r["query"] for r in rows(lang) if r["semantic_task_id"] == tid)


def mutate(tmp_path, monkeypatch, tid, fn):
    d = tmp_path / f"languages{next(_n)}"
    shutil.copytree(vt.LANG_DIR, d)
    rs = rows("gu", d)
    for r in rs:
        if r["semantic_task_id"] == tid:
            fn(r)
    (d / "gu.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rs) + "\n", encoding="utf-8")
    monkeypatch.setattr(vt, "LANG_DIR", d)
    monkeypatch.setattr(vt, "AUDIT_PATH", d / "pilot_language_audit.json")
    monkeypatch.setattr(vt, "GU_AUDIT_PATH", d / vt.GU_AUDIT_PATH.name)
    monkeypatch.setattr(vt, "GU2_AUDIT_PATH", d / vt.GU2_AUDIT_PATH.name)
    return " | ".join(vt.validate())


def test_375_items_75_tasks_in_5_languages():
    assert vt.validate() == []
    assert gu.GU_IDS == vt.ALL_IDS and gu.GU_IDS_T51_T75 == IDS
    for l in LANGS5:
        assert [r["semantic_task_id"] for r in rows(l)] == vt.ALL_IDS
    assert sum(len(rows(l)) for l in LANGS5) == 375
    items = load_items(vt.LANG_DIR, LANGS5, task_ids("full"))
    assert len(items) == 375 and {i["language"] for i in items} == set(LANGS5)


def test_gujarati_t01_t50_rows_and_audit_are_frozen():
    head = hr.draft_head_bytes(vt.LANG_DIR / "gu.jsonl", 50)  # review fields reset (benchmark/human_review.py)
    assert hashlib.sha256(head).hexdigest() == vt.FROZEN_GU_T01_T50_LANG_SHA256
    assert hashlib.sha256(vt.GU_AUDIT_PATH.read_bytes()).hexdigest() == vt.FROZEN_GU_T01_T50_AUDIT_SHA256


def test_new_gujarati_items_are_reviewed_with_shared_fields():
    en = {r["semantic_task_id"]: r for r in rows("en")}
    for r in rows("gu")[50:]:
        e = en[r["semantic_task_id"]]
        assert r["review_status"] == "reviewed" and r["reviewer"] == hr.REVIEWER and r["author"] == "Claude-generated draft"
        assert (r["category"], r["allowed_tools"], r["tags"]) == (e["category"], e["allowed_tools"], [*e["tags"], "gujarati"])
    a = json.loads(vt.GU2_AUDIT_PATH.read_text(encoding="utf-8"))["records"]
    assert [x["task_id"] for x in a] == [f"{t}_gu" for t in IDS] and all(x["human_review"] == "pending_human_review" for x in a)


def test_same_checks_as_hindi_and_same_numbers_as_english():
    specs = {s.semantic_task_id: s for s in load_specs()}
    o = vt.RawOracle()
    code_of = lambda n: next(iter(o.codes_for(n)))  # noqa: E731
    for t in IDS:
        p = specs[t].solver.params
        g, h = lc.run_checks(t, "gu", q(t), p, code_of), lc.run_checks(t, "hi", q(t, "hi"), p, code_of)
        assert all(v is not False for v in g.values()), (t, g)
        assert {k: v is True for k, v in g.items()} == {k: v is True for k, v in h.items()}, t
        assert lc.numeric_signature(q(t)) == lc.numeric_signature(q(t, "en")), t


def test_language_features_survive_in_gujarati():
    e = RailwayEnv()
    assert "રવિ પટેલ" in q("T54") and "Ravi Patel" not in q("T54")
    assert e.call("book_ticket", {"train_id": "BTB126", "travel_class": "CC", "passenger": "રવિ પટેલ"})["error"]["code"] == "INVALID_PASSENGER"
    assert q("T57").startswith("પરમ દિવસે") and lc.parse_dates(q("T57"), "gu") == []
    assert "સવા સાત" in q("T62") and "7:15" not in q("T62")
    assert "અઢી હજાર" in q("T64") and "2,500" not in q("T64")
    assert "31 નવેમ્બર 2026" in q("T67")
    assert "હાવડાથી કોલકાતા" in q("T69")
    assert q("T71").count("Anjali Rao") == 2
    assert "BTB110 સિવાયની" in q("T72") and "BTB1O3" in q("T74")
    assert "આગલી" not in q("T73")  # 'આગલી' can mean 'previous'; the draft says 'the first train leaving after it'
    for t, form in [("T51", "મુંબઈથી"), ("T53", "કોલકાતાથી"), ("T55", "લખનઉથી"), ("T56", "પુણેથી")]:
        assert form in q(t), t


# ---- negative tests
def test_detects_romanised_name_in_t54(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "T54", lambda r: r.update(query=r["query"].replace("રવિ પટેલના", "Ravi Patel ના")))
    assert "T54_gu: surface check passenger_preserved FAILED" in e and "T54_gu: declared native-script passenger form missing" in e


def test_detects_spoken_time_and_amount_turned_into_digits(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "T62", lambda r: r.update(query=r["query"].replace("સવા સાત વાગ્યે", "7:15 વાગ્યે")))
    assert "T62_gu: numbers differ from English" in e and "T62_gu: surface check time_preserved FAILED" in e
    e = mutate(tmp_path, monkeypatch, "T64", lambda r: r.update(query=r["query"].replace("અઢી હજાર રૂપિયાથી", "₹2,500 થી")))
    assert "T64_gu: numbers differ from English" in e and "T64_gu: surface check fare_constraint_preserved FAILED" in e


def test_detects_lost_negation_fixed_typo_and_dropped_station_name(tmp_path, monkeypatch):
    assert "T72_gu: surface check forbidden_action_preserved FAILED" in mutate(
        tmp_path, monkeypatch, "T72", lambda r: r.update(query=r["query"].replace("BTB110 સિવાયની કોઈ પણ ટ્રેનમાં", "ટ્રેન BTB110 માં")))
    assert "T74_gu: surface check intent_preserved FAILED" in mutate(tmp_path, monkeypatch, "T74", lambda r: r.update(query=r["query"].replace("BTB1O3", "BTB103")))
    assert "T69_gu: surface check route_preserved FAILED" in mutate(tmp_path, monkeypatch, "T69", lambda r: r.update(query=r["query"].replace("હાવડાથી ", "")))


def test_detects_edit_to_frozen_gujarati_t01_t50_row(tmp_path, monkeypatch):
    d = tmp_path / "langs_frozen"
    shutil.copytree(vt.LANG_DIR, d)
    rs = rows("gu", d)
    rs[3]["tags"] = rs[3]["tags"] + ["x"]
    (d / "gu.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rs) + "\n", encoding="utf-8")
    monkeypatch.setattr(vt, "LANG_DIR", d)
    monkeypatch.setattr(vt, "AUDIT_PATH", d / "pilot_language_audit.json")
    monkeypatch.setattr(vt, "GU_AUDIT_PATH", d / vt.GU_AUDIT_PATH.name)
    monkeypatch.setattr(vt, "GU2_AUDIT_PATH", d / vt.GU2_AUDIT_PATH.name)
    assert "gu.jsonl rows T01-T50 changed (frozen)" in " | ".join(vt.validate())
