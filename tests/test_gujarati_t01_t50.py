"""Gujarati (gu), 5th language, for T01-T50: gu.jsonl + audit. The four existing language files must be untouched; every
Gujarati item must keep the shared spec/gold, the English numbers, the surface constraints and the Latin passenger names."""
import hashlib
import itertools
import json
import re
import shutil

from benchmark import batch_gujarati as gu
from benchmark import language_checks as lc
from benchmark import validate_tasks as vt
from benchmark.build_gold import GOLD_PATH, load_specs
from environment import RailwayEnv
from evaluation.canonical import dates_in, numbers_in, times_in
from evaluation.runner import load_items
from benchmark import human_review as hr

IDS = [f"T{i:02d}" for i in range(1, 51)]
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


# ------------------------------------------------------------------ coverage and preservation
def test_gujarati_covers_t01_t50_in_order_as_unreviewed_drafts():
    assert vt.validate() == []
    g = rows("gu")
    g = g[:50]  # T51-T75 follow (tests/test_gujarati_t51_t75.py)
    assert gu.GU_IDS_T01_T50 == IDS and [r["semantic_task_id"] for r in g] == IDS and [r["task_id"] for r in g] == [f"{t}_gu" for t in IDS]
    en = {r["semantic_task_id"]: r for r in rows("en")}
    for r in g:
        assert r["language"] == "gu" and r["review_status"] == "reviewed" and r["reviewer"] == hr.REVIEWER and r["author"] == "Claude-generated draft"
        e = en[r["semantic_task_id"]]
        assert (r["category"], r["allowed_tools"], r["tags"]) == (e["category"], e["allowed_tools"], [*e["tags"], "gujarati"])


def test_existing_four_languages_untouched():
    """The four existing files keep 75 rows each; their T01-T50 rows stay hash-locked and no row mentions Gujarati."""
    for l in lc.LANGS:
        rs = rows(l)
        assert len(rs) == 75 and all(r["language"] == l for r in rs)
        head = hr.draft_head_bytes(vt.LANG_DIR / f"{l}.jsonl", 50)  # review fields reset (benchmark/human_review.py)
        assert hashlib.sha256(head).hexdigest() == vt.FROZEN_T01_T50_LANG_SHA256[l]
        assert not any(re.search("[઀-૿]", r["query"]) for r in rs)
    assert "gu" not in lc.LANGS and lc.EXTRA_LANGS == ["gu"]


def test_gold_has_no_language_keys_and_one_shared_spec():
    g = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    assert not any("_gu" in k or "gujarati" in json.dumps(v) for k, v in g.items())


# ------------------------------------------------------------------ equivalence with English and with the other drafts
def test_every_gujarati_item_passes_the_same_surface_checks_as_hindi():
    specs = {s.semantic_task_id: s for s in load_specs()}
    o = vt.RawOracle()
    code_of = lambda n: next(iter(o.codes_for(n)))  # noqa: E731
    for t in IDS:
        p = specs[t].solver.params
        g, h = lc.run_checks(t, "gu", q(t), p, code_of), lc.run_checks(t, "hi", q(t, "hi"), p, code_of)
        assert all(v is not False for v in g.values()), (t, g)
        assert {k: v is True for k, v in g.items()} == {k: v is True for k, v in h.items()}, t  # same constraints checked
        assert lc.numeric_signature(q(t)) == lc.numeric_signature(q(t, "en")), t


def test_every_existing_marker_has_a_gujarati_counterpart():
    for t in IDS:
        for k, v in lc._M[t].items():
            if isinstance(v, dict):
                assert "gu" in v, (t, k)
                assert set(v) >= {"en", "hinglish", "hi", "mr"}  # the other languages' regexes are kept


def test_scripts_digits_names_and_station_endings():
    for t in IDS:
        x = q(t)
        assert re.search("[઀-૿]", x) and not re.search("[૦-૯०-९]", x)  # Gujarati text, ASCII digits only
        assert not re.search(r"BTB\d{3}[઀-૿]", x)  # suffixes never glued to train ids
    # Gujarati attaches the ablative to the station name, like Marathi: base name + 'થી'
    for t, form in [("T02", "નાગપુરથી"), ("T04", "મુંબઈથી"), ("T08", "નવી દિલ્હીથી"), ("T12", "જયપુરથી"), ("T24", "કોલકાતાથી"), ("T25", "લખનઉથી")]:
        assert form in q(t), t
    e = RailwayEnv()
    assert e.call("resolve_station", {"name": "મુંબઈથી"})["error"]["code"] == "STATION_NOT_FOUND"  # the agent must strip the ending


def test_deliberate_traps_kept_in_gujarati():
    e = RailwayEnv()
    assert "દિલ્હીથી" in q("T09") and "નવી દિલ્હી" not in q("T09") and e.call("resolve_station", {"name": "દિલ્હી"})["data"]["ambiguous"]
    assert "બૉમ્બે સેન્ટ્રલ" in q("T31") and e.call("resolve_station", {"name": "બૉમ્બે સેન્ટ્રલ"})["error"]["code"] == "STATION_NOT_FOUND"
    assert "ચેન્નઈ" in q("T18") and e.call("resolve_station", {"name": "ચેન્નઈ"})["error"]["code"] == "STATION_NOT_FOUND"
    assert "BTB150" in q("T28") and "(1A)" in q("T29") and "2 ઓક્ટોબર 2026" in q("T30") and "આ શનિવારે" in q("T35")
    assert "ત્રણ ટિકિટ" in q("T46") and "બુક" not in q("T37") and "એસી ટિકિટ" in q("T36") and "3A" not in q("T36")
    assert not re.search(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", q("T19"))  # the missing passenger stays missing
    assert "બીજી સૌથી સસ્તી" not in q("T38")  # would read as 'second-cheapest'


def test_gujarati_dates_parse_with_attached_case_endings():
    assert lc.parse_dates(q("T23"), "gu") == ["2026-10-08", "2026-10-10"]
    assert lc.parse_dates("9 ઑક્ટોબર 2026ના રોજ", "gu") == ["2026-10-09"]
    assert lc.parse_dates(q("T35"), "gu") == []


# ---- negative tests (drift in the Gujarati drafts is caught)
def test_detects_dropped_prohibition(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "T03", lambda r: r.update(query=r["query"].replace(" કંઈ પણ બુક કરશો નહીં,", "")))
    assert "T03_gu: surface check forbidden_action_preserved FAILED" in e and "T03_gu: query out of sync" in e


def test_detects_delhi_made_specific(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "T09", lambda r: r.update(query=r["query"].replace("દિલ્હીથી", "નવી દિલ્હીથી")))
    assert "T09_gu: surface check route_preserved FAILED" in e


def test_detects_changed_amount_and_gujarati_digits(tmp_path, monkeypatch):
    assert "T24_gu: numbers differ from English" in mutate(tmp_path, monkeypatch, "T24", lambda r: r.update(query=r["query"].replace("3,500", "3,000")))
    e = mutate(tmp_path, monkeypatch, "T26", lambda r: r.update(query=r["query"].replace("BTB102", "BTB૧૦૨")))
    assert "T26_gu: Gujarati/Devanagari digits are not used" in e


def test_detects_transliterated_passenger_and_wrong_status(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "T20", lambda r: r.update(query=r["query"].replace("Neha Shah", "નેહા શાહ")))
    assert "T20_gu: passenger must stay Latin and identical" in e
    assert "T20_gu: review fields must match human_review.py" in mutate(tmp_path, monkeypatch, "T20", lambda r: r.update(review_status="accepted"))


def test_detects_missing_row(tmp_path, monkeypatch):
    d = tmp_path / "langs_missing"
    shutil.copytree(vt.LANG_DIR, d)
    (d / "gu.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows("gu", d) if r["semantic_task_id"] != "T07") + "\n", encoding="utf-8")
    monkeypatch.setattr(vt, "LANG_DIR", d)
    monkeypatch.setattr(vt, "AUDIT_PATH", d / "pilot_language_audit.json")
    monkeypatch.setattr(vt, "GU_AUDIT_PATH", d / vt.GU_AUDIT_PATH.name)
    monkeypatch.setattr(vt, "GU2_AUDIT_PATH", d / vt.GU2_AUDIT_PATH.name)
    assert "gu.jsonl must hold exactly T01..T75 in order" in " | ".join(vt.validate())


def test_gujarati_audit_is_complete_and_pending():
    a = json.loads(vt.GU_AUDIT_PATH.read_text(encoding="utf-8"))["records"]
    assert [r["task_id"] for r in a] == [f"{t}_gu" for t in IDS]
    assert all(r["human_review"] == r["fluency_review"] == r["equivalence_review"] == "pending_human_review" for r in a)


# ------------------------------------------------------------------ runner and scorer can handle Gujarati
def test_runner_loads_gujarati_midsem_items():
    from evaluation.run_pilot import task_ids
    items = load_items(vt.LANG_DIR, ["gu"], task_ids("midsem"))
    assert len(items) == 50 and {i["language"] for i in items} == {"gu"}


def test_scorer_reads_gujarati_times_dates_and_digits():
    assert times_in("સાંજે 5:20 વાગ્યે, રાત્રે 11:05, સવારે 6:45, બપોરે 1:30") == {"17:20", "23:05", "06:45", "13:30"}
    assert dates_in("10 ઓક્ટોબરે પહોંચશો; 9 ઑક્ટોબર 2026") == {"2026-10-10", "2026-10-09"}
    assert numbers_in("ભાડું ₹૧,૪૬૦ છે") == {1460}
    assert times_in("रात्री 8:20") == {"20:20"} and dates_in("10 अक्टूबर") == {"2026-10-10"}  # existing languages unchanged


def test_scorer_accepts_an_ideal_gujarati_answer_for_t44():
    from evaluation.scorer import score
    from evaluation.selfcheck import execute, final_json, final_text, gold_calls, gold_for
    traj, snap = execute(gold_calls("T44"))
    fa = gold_for("T44")["final_answer"]
    h, m = map(int, fa["arrival"].split(":"))
    natural = f"ટ્રેન કોલકાતા {int(fa['arrival_date'][-2:])} ઓક્ટોબરે {'સવારે' if h < 12 else 'સાંજે'} {h if h <= 12 else h - 12}:{m:02d} વાગ્યે પહોંચશે."
    row = {"task_id": "T44_gu", "semantic_task_id": "T44", "language": "gu", "status": "completed", "trajectory": traj,
           "final_text": final_text("T44", final_json("T44", snap), natural=natural), "state_snapshot": snap}
    s = score(row, gold_for("T44"), snap)
    assert s["task_success"], s["failure_labels"]


def test_reviewed_gujarati_wording_fixes_t02_t23():
    assert "સાથે સાથે 3A નું ભાડું પણ" in q("T02") and "જવા-આવવાની ટિકિટ" in q("T23") and "આવવા-જવાની" not in q("T23")
