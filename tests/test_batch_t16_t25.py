"""Batch T16-T25 (10 semantic tasks x 4 languages = 40 DRAFT items): gold behaviour, referential integrity, state changes,
determinism, T01-T15 preservation, duplicates, multilingual equivalence, and negative tests."""
import copy
import hashlib
import itertools
import json
import shutil

import pytest

from benchmark import batch_t16_t25 as batch
from benchmark import language_checks as lc
from benchmark import semantic_overlap as so
from benchmark import validate_tasks as vt
from benchmark.build_gold import GOLD_PATH, SPEC_PATH, build_all, build_task_gold, load_specs, render
from environment import RailwayEnv
from environment.schemas import TRAVEL_CLASSES
from benchmark import human_review as hr

LANGS = ["en", "hinglish", "hi", "mr"]
BATCH = batch.BATCH_IDS
_n = itertools.count()


def gold(tid):
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))[tid]


def rows(lang, d=None):
    return [json.loads(l) for l in ((d or vt.LANG_DIR) / f"{lang}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def query(tid, lang):
    return next(r["query"] for r in rows(lang) if r["semantic_task_id"] == tid)


def fresh():
    e = RailwayEnv()
    e.reset()
    return e


def mutate(tmp_path, monkeypatch, lang, tid, fn, fname=None):
    d = tmp_path / f"languages{next(_n)}"
    shutil.copytree(vt.LANG_DIR, d)
    if fname:  # mutate a non-jsonl file (e.g. an audit)
        fn(d / fname)
    else:
        rs = rows(lang, d)
        for r in rs:
            if r["semantic_task_id"] == tid:
                fn(r)
        (d / f"{lang}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rs) + "\n", encoding="utf-8")
    monkeypatch.setattr(vt, "LANG_DIR", d)
    monkeypatch.setattr(vt, "AUDIT_PATH", d / "pilot_language_audit.json")
    return " | ".join(vt.validate())


# ------------------------------------------------------------------ counts, status, determinism, preservation
def test_counts_25_tasks_100_items_25_per_language():
    # scoped to T01-T25 (later batches append after these rows)
    assert vt.validate() == []
    assert [s.semantic_task_id for s in load_specs()][:25] == [f"T{i:02d}" for i in range(1, 26)]
    for l in LANGS:
        assert [r["semantic_task_id"] for r in rows(l)][:25] == [f"T{i:02d}" for i in range(1, 26)]
    assert sum(1 for l in LANGS for r in rows(l) if r["semantic_task_id"] in BATCH) == 40


def test_batch_items_review_fields_match_human_review_record():  # mr reviewed (human_review.py); en/hinglish/hi drafts
    for l in LANGS:
        for r in rows(l):
            if r["semantic_task_id"] in BATCH:
                assert (r["reviewer"], r["review_status"]) == hr.expected_review(r["language"], r["semantic_task_id"])
                assert r["review_status"] == ("reviewed" if l == "mr" else "draft")
                assert r["author"] == (batch.EN_AUTHOR if l == "en" else "Claude-generated draft")
    audit = json.loads(vt.BATCH2_AUDIT_PATH.read_text(encoding="utf-8"))["records"]
    assert len(audit) == 40 and all(a["human_review"] == a["fluency_review"] == a["equivalence_review"] == "pending_human_review" for a in audit)


def test_gold_is_deterministic_twice_and_matches_committed_file():
    assert render(build_all()) == render(build_all()) == GOLD_PATH.read_text(encoding="utf-8")


def test_t01_t15_spec_gold_language_rows_and_audit_are_frozen():
    g = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    assert vt._sha({t: g[t] for t in vt.FROZEN_T01_T15_IDS}) == vt.FROZEN_T01_T15_GOLD_SHA256
    sp = json.loads(SPEC_PATH.read_text(encoding="utf-8"))["tasks"]
    assert vt._sha([t for t in sp if t["semantic_task_id"] in vt.FROZEN_T01_T15_IDS]) == vt.FROZEN_T01_T15_SPEC_SHA256
    for l in LANGS:
        head = hr.draft_head_bytes(vt.LANG_DIR / f"{l}.jsonl", 15)  # review fields reset (benchmark/human_review.py)
        assert hashlib.sha256(head).hexdigest() == vt.FROZEN_T01_T15_LANG_SHA256[l]
    assert hashlib.sha256((vt.LANG_DIR / "batch_T06_T15_language_audit.json").read_bytes()).hexdigest() == vt.FROZEN_T06_T15_AUDIT_SHA256


def test_every_referenced_train_station_and_class_exists():
    import re
    e = fresh()
    trains = set(e.state.trains)
    # every DELIBERATELY invalid entity is listed here by task kind; anything else must exist and be unambiguous
    invalid_train = {"invalid_train_id"}                                   # T28 (BTB150)
    invalid_class = {"unsupported_class"}                                  # T29 (1A)
    unknown_source = {"unknown_station", "alias_retry_earliest"}           # T18 (Chennai), T31 (Bombay Central)
    ambiguous_source = {"ambiguous_station_clarification", "disambiguation_by_train"}  # T09, T47 ('Delhi')
    for s in load_specs():
        p, k = s.solver.params, s.solver.kind
        for leg in p.get("legs", []):  # nested multi-leg entities (T41)
            assert leg["train_id"] in trains and leg["travel_class"] in e.state.trains[leg["train_id"]].classes
        for a in p.get("assignments", []):  # per-passenger classes (T42)
            assert a["travel_class"] in e.state.trains[p["train_id"]].classes
        for key, v in p.items():
            if key == "train_id":
                assert (v in trains) != (k in invalid_train), (s.semantic_task_id, v)
            if key in ("travel_class", "fallback_class"):
                assert (v in TRAVEL_CLASSES) != (k in invalid_class), (s.semantic_task_id, v)
            if key.endswith("_name") or key == "recovered_station":
                r = e.call("resolve_station", {"name": v})
                if k in unknown_source and key == "source_name":
                    assert r["error"]["code"] == "STATION_NOT_FOUND"
                elif k in ambiguous_source and key == "source_name":
                    assert r["data"]["ambiguous"]
                else:
                    assert r["ok"] and not r["data"]["ambiguous"], (s.semantic_task_id, v)
        if "train_id" in p and "travel_class" in p and k not in ("class_not_offered", "unsupported_class",
                                                                   "class_not_offered_take_offered"):  # T11, T29, T75 intentional
            assert p["travel_class"] in e.state.trains[p["train_id"]].classes, s.semantic_task_id
        for q in (query(s.semantic_task_id, l) for l in LANGS):
            ids = set(re.findall(r"\bBTB\d{3}\b", q))
            assert ids <= trains or (k in invalid_train and ids - trains == {p["train_id"]})


# ------------------------------------------------------------------ per-task gold behaviour against the environment
@pytest.mark.parametrize("lang", LANGS)
def test_t16_every_language_alias_resolves_to_howrah(lang):
    al = lc.station_aliases(lang)["HWH"]
    used = [a for a in al if a in query("T16", lang)]
    assert used and fresh().call("resolve_station", {"name": used[0]})["data"]["candidates"][0]["code"] == "HWH"
    assert gold("T16")["final_answer"]["station_code"] == "HWH" and gold("T16")["final_answer"]["station_name"] == "Howrah Junction"


def test_t17_segment_distance_is_not_the_cumulative_distance():
    fa = gold("T17")["final_answer"]
    assert fa["segment_distance_km"] == 838 and fa["naive_cumulative_km_at_destination"] == 1030


@pytest.mark.parametrize("name", ["Chennai", "चेन्नई"])
def test_t18_unknown_station_in_every_script(name):
    assert fresh().call("resolve_station", {"name": name})["error"]["code"] == "STATION_NOT_FOUND"
    c1 = gold("T18")["required_calls"][0]
    assert c1["expected_error"] == "STATION_NOT_FOUND" and c1["required_args"]["name"] == {"resolves_to_none": True}


def test_t19_only_the_passenger_name_is_missing():
    g = gold("T19")
    assert g["final_state"]["status"] == "needs_clarification" and g["min_calls"] == 0 and g["final_state"]["expected_bookings"] == []
    assert fresh().call("check_availability", {"train_id": "BTB116", "travel_class": "3A"})["data"]["seats_available"] == 41
    import re
    for l in LANGS:
        assert re.search(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", query("T19", l)) is None, l


def test_t20_route_is_empty_on_every_day():
    e = fresh()
    assert all(e.call("search_trains", {"source": "LKO", "destination": "PUNE", "date": f"2026-10-{d:02d}"})["data"]["count"] == 0 for d in range(5, 12))
    assert gold("T20")["final_answer"]["reason"] == "no_direct_train" and gold("T20")["expected_env_diff"]["bookings"] == []


def test_t21_named_train_runs_the_other_way():
    d = fresh().call("get_train_details", {"train_id": "BTB107"})["data"]
    assert (d["source_station"], d["destination_station"]) == ("JP", "ADI")
    g = gold("T21")
    assert g["final_answer"]["requested"] == ["ADI", "JP"] and g["final_state"]["expected_bookings"] == []


def test_t22_skips_sold_out_earliest_and_mutates_only_the_winner():
    g, e = gold("T22"), fresh()
    assert e.call("book_ticket", {"train_id": "BTB101", "travel_class": "2A", "passenger": "Karan Malhotra"})["error"]["code"] == "SOLD_OUT"
    r = e.call("book_ticket", {"train_id": "BTB103", "travel_class": "2A", "passenger": "Karan Malhotra"})
    assert r["ok"] and r["data"]["booking_id"] == g["final_answer"]["booking_id"]
    assert g["expected_env_diff"]["availability_changes"] == {"BTB103|2A": [35, 34]}
    assert ("c4", "c5") in {(x["before"], x["after"]) for x in g["dependency_edges"]}  # booking depends on the sold-out observation


def test_t23_round_trip_books_both_legs_in_any_order():
    g = gold("T23")
    assert g["expected_env_diff"]["availability_changes"] == {"BTB127|SL": [33, 32], "BTB128|SL": [40, 39]}
    want = sorted((b["train_id"], b["travel_class"], b["passenger"]) for b in g["final_state"]["expected_bookings"])
    for order in (["BTB127", "BTB128"], ["BTB128", "BTB127"]):
        e = fresh()
        for t in order:
            assert e.call("book_ticket", {"train_id": t, "travel_class": "SL", "passenger": "Ishaan Desai"})["ok"]
        assert sorted((b["train_id"], b["travel_class"], b["passenger"]) for b in e.snapshot()["bookings"]) == want


def test_t24_every_candidate_exceeds_the_budget():
    e = fresh()
    fares = [e.call("get_fare", {"train_id": t, "travel_class": "2A"})["data"]["fare_inr"] for t in ("BTB110", "BTB112")]
    assert min(fares) > 3500 and gold("T24")["final_answer"]["cheapest_fare_found"] == min(fares)


def test_t25_naive_same_date_wrap_search_gives_the_wrong_answer():
    naive = fresh().call("search_trains", {"source": "LKO", "destination": "HWH", "date": "2026-10-09",
                                           "time_window": {"start": "23:00", "end": "05:00"}})["data"]["trains"]
    assert {t["train_id"] for t in naive} == {"BTB109", "BTB111"}  # BTB111 at 03:55 on the 9th: before the window
    assert gold("T25")["final_answer"]["departures"] == [{"train_id": "BTB109", "departure_date": "2026-10-09", "departure": "23:40"}]


def test_read_only_batch_tasks_leave_state_unchanged():
    for t in ("T16", "T17", "T18", "T19", "T20", "T21", "T24", "T25"):
        assert gold(t)["expected_env_diff"] == {"bookings": [], "availability_changes": {}}


def test_solver_guards_refuse_trivialised_variants():
    spec = copy.deepcopy(next(s for s in load_specs() if s.semantic_task_id == "T24"))
    spec.solver.params["max_fare_inr"] = 4000  # BTB112 would fit: no longer infeasible
    with pytest.raises(ValueError, match="feasible"):
        build_task_gold(spec)
    spec = copy.deepcopy(next(s for s in load_specs() if s.semantic_task_id == "T17"))
    spec.solver.params["from_name"] = "Mumbai"  # segment from the origin: naive answer would be right
    with pytest.raises(ValueError, match="origin"):
        build_task_gold(spec)


# ------------------------------------------------------------------ duplicates
def test_no_semantic_duplicates_across_t01_t25():
    specs = {s.semantic_task_id: s for s in load_specs()}
    assert so.overlap_errors(specs, json.loads(GOLD_PATH.read_text(encoding="utf-8"))) == []
    assert len({s.solver.kind for s in specs.values()}) == len(specs)  # one solver kind per task (25 when written)


def test_overlap_flags_a_second_missing_slot_clarification():
    """Regression for the batch design: a 'missing date' clarification next to T19 ('missing passenger') was flagged
    as the same reasoning pattern and replaced by T20 (no trains on route). A clone like that must keep failing."""
    specs = {s.semantic_task_id: s for s in load_specs()}
    g = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    clone = copy.deepcopy(specs["T19"])
    clone.semantic_task_id, clone.solver.kind = "T99", "missing_date_clarification"
    clone.constraints = [c if c["kind"] != "missing_slot" else {"kind": "missing_slot", "value": "date"} for c in clone.constraints]
    specs["T99"], g["T99"] = clone, copy.deepcopy(g["T19"])
    assert any("fingerprint" in e and "T19" in e and "T99" in e for e in so.overlap_errors(specs, g))


# ------------------------------------------------------------------ multilingual equivalence
def test_all_40_batch_variants_pass_surface_checks_and_share_numbers():
    specs = {s.semantic_task_id: s for s in load_specs()}
    o = vt.RawOracle()
    code_of = lambda n: next(iter(o.codes_for(n)))  # noqa: E731
    for t in BATCH:
        qs = {l: query(t, l) for l in LANGS}
        assert len({json.dumps(lc.numeric_signature(q)) for q in qs.values()}) == 1, t
        for l, q in qs.items():
            res = lc.run_checks(t, l, q, specs[t].solver.params, code_of)
            assert all(v is not False for v in res.values()), (t, l, res)
            assert sum(v is True for v in res.values()) >= 3, (t, l)


def test_one_shared_gold_per_task_no_language_keys():
    g = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    for t in BATCH:
        assert "language" not in json.dumps(g[t]) and "query" not in g[t]
        assert {next(r for r in rows(l) if r["semantic_task_id"] == t)["category"] for l in LANGS} == {batch.EN_ITEMS[t]["category"]}


# ---- negative tests
def test_detects_t22_dropped_scope_of_earliest(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hi", "T22", lambda r: r.update(query=r["query"].replace("उन ट्रेनों में से जिनमें अभी भी 2A की सीटें उपलब्ध हैं, ", "")))
    assert "T22_hi: surface check time_constraint_preserved FAILED" in e


def test_detects_t25_dropped_second_date(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "mr", "T25", lambda r: r.update(query=r["query"].replace("10 ऑक्टोबर रोजी ", "")))
    assert "T25: numbers differ across variants" in e and "T25_mr: surface check time_constraint_preserved FAILED" in e


def test_detects_t19_name_added(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hinglish", "T19", lambda r: r.update(query=r["query"] + " Naam: Ravi Kumar."))
    assert "T19_hinglish: surface check passenger_preserved FAILED" in e


def test_detects_t17_reversed_segment(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "en", "T17", lambda r: r.update(query="On train BTB115, how many kilometres is it from Bengaluru to Pune?"))
    assert "T17_en: surface check route_preserved FAILED" in e


def test_detects_t18_unknown_station_replaced(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hi", "T18", lambda r: r.update(query=r["query"].replace("चेन्नई", "मुंबई")))
    assert "T18_hi: surface check intent_preserved FAILED" in e


def test_detects_t23_dropped_return_date(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hinglish", "T23", lambda r: r.update(query=r["query"].replace(", aur 10 October 2026 ko Nagpur se Pune wapas", "")))
    assert "T23_hinglish: surface check date_preserved FAILED" in e


def test_detects_review_status_and_sync_problems(tmp_path, monkeypatch):
    assert "review_status must be 'reviewed'" in mutate(tmp_path, monkeypatch, "mr", "T24", lambda r: r.update(review_status="accepted"))
    assert "out of sync with batch_t16_t25.py" in mutate(tmp_path, monkeypatch, "hi", "T16", lambda r: r.update(query=r["query"] + " "))


def test_detects_edit_to_a_frozen_t06_t15_row_and_audit(tmp_path, monkeypatch):
    assert "mr.jsonl rows T01-T15 changed (frozen)" in mutate(tmp_path, monkeypatch, "mr", "T12", lambda r: r.update(tags=r["tags"] + ["x"]))

    def bump(f):
        a = json.loads(f.read_text(encoding="utf-8"))
        a["_meta"]["note"] += " "
        f.write_text(json.dumps(a, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert "T06-T15 audit file changed (frozen)" in mutate(tmp_path, monkeypatch, None, None, bump, fname="batch_T06_T15_language_audit.json")


def test_detects_hand_edited_t06_t15_gold(tmp_path, monkeypatch):
    bad = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    bad["T13"]["min_calls"] = 4
    f = tmp_path / "gold_labels.json"
    f.write_text(render(bad), encoding="utf-8")
    monkeypatch.setattr(vt, "GOLD_PATH", f)
    e = " | ".join(vt.validate())
    assert "T01-T15 gold changed (frozen)" in e
