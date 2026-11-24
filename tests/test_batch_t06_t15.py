"""Batch T06-T15 (10 semantic tasks x 4 languages = 40 DRAFT items): gold behaviour, determinism, pilot preservation,
semantic-duplicate detection and multilingual equivalence. Negative tests prove the validators catch real defects."""
import copy
import hashlib
import itertools
import json
import shutil

import pytest

from benchmark import batch_t06_t15 as batch
from benchmark import language_checks as lc
from benchmark import semantic_overlap as so
from benchmark import validate_tasks as vt
from benchmark.build_gold import GOLD_PATH, SPEC_PATH, build_all, build_task_gold, load_specs, render
from environment import RailwayEnv
from benchmark import human_review as hr

LANGS = ["en", "hinglish", "hi", "mr"]
BATCH = batch.BATCH_IDS
_n = itertools.count()


def gold(tid):
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))[tid]


def rows(lang, d=None):
    return [json.loads(l) for l in ((d or vt.LANG_DIR) / f"{lang}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def fresh():
    e = RailwayEnv()
    e.reset()
    return e


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


# ------------------------------------------------------------------ counts, status, determinism, preservation
def test_counts_15_tasks_60_items_15_per_language():
    # scoped to T01-T15 (later batches append after these rows)
    assert vt.validate() == []
    assert [s.semantic_task_id for s in load_specs()][:15] == [f"T{i:02d}" for i in range(1, 16)]
    for l in LANGS:
        assert [r["semantic_task_id"] for r in rows(l)][:15] == [f"T{i:02d}" for i in range(1, 16)]
    assert sum(1 for l in LANGS for r in rows(l) if r["semantic_task_id"] in BATCH) == 40


def test_batch_items_review_fields_match_human_review_record():  # mr reviewed (human_review.py); en/hinglish/hi drafts
    for l in LANGS:
        for r in rows(l):
            if r["semantic_task_id"] in BATCH:
                assert (r["reviewer"], r["review_status"]) == hr.expected_review(r["language"], r["semantic_task_id"])
                assert r["review_status"] == ("reviewed" if l == "mr" else "draft")
                assert r["author"] == (batch.EN_AUTHOR if l == "en" else "Claude-generated draft")
    audit = json.loads(vt.BATCH_AUDIT_PATH.read_text(encoding="utf-8"))["records"]
    assert len(audit) == 40 and all(a["human_review"] == a["fluency_review"] == a["equivalence_review"] == "pending_human_review" for a in audit)


def test_gold_is_deterministic_twice_and_matches_committed_file():
    a, b = render(build_all()), render(build_all())
    assert a == b == GOLD_PATH.read_text(encoding="utf-8")


def test_pilot_t01_t05_spec_gold_and_language_rows_are_frozen():
    g = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    assert vt._sha({t: g[t] for t in vt.PILOT_IDS}) == vt.FROZEN_PILOT_GOLD_SHA256
    sp = json.loads(SPEC_PATH.read_text(encoding="utf-8"))["tasks"]
    assert vt._sha([t for t in sp if t["semantic_task_id"] in vt.PILOT_IDS]) == vt.FROZEN_PILOT_SPEC_SHA256
    for l in LANGS:
        head = hr.draft_head_bytes(vt.LANG_DIR / f"{l}.jsonl", 5)  # review fields reset (benchmark/human_review.py)
        assert hashlib.sha256(head).hexdigest() == vt.FROZEN_PILOT_LANG_SHA256[l]
    for c in itertools.chain.from_iterable(g[t]["required_calls"] for t in vt.PILOT_IDS):
        assert "expected_error" not in c  # the schema extension did not leak into pilot gold


def test_one_shared_gold_per_task_no_language_keys():
    g = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    for t in BATCH:
        assert t in g and "language" not in json.dumps(g[t]) and "query" not in g[t]
        cats = {next(r for r in rows(l) if r["semantic_task_id"] == t)["category"] for l in LANGS}
        assert cats == {batch.EN_ITEMS[t]["category"]}


# ------------------------------------------------------------------ per-task gold behaviour against the environment
def test_t06_operating_days():
    g = gold("T06")
    assert g["final_answer"]["operating_days"] == ["TUE", "THU", "SAT"] and g["final_answer"]["runs_on_requested_weekday"] is False


def test_t07_intermediate_stop_after_midnight():
    g = gold("T07")
    assert g["final_answer"]["selected_train_id"] == "BTB121" and g["final_answer"]["stop_arrival_time"] == "00:30"
    assert [c["tool"] for c in g["required_calls"] if not c["optional"]] == ["resolve_station", "resolve_station", "search_trains", "get_train_details"]


def test_t08_window_is_empty_and_fallback_is_first_after_17():
    e = fresh()
    assert e.call("search_trains", {"source": "NDLS", "destination": "LKO", "date": "2026-10-08",
                                    "time_window": {"start": "12:00", "end": "17:00"}})["data"]["count"] == 0
    assert gold("T08")["final_answer"]["selected_train_id"] == "BTB109"
    assert ("c3", "c4") in {(x["before"], x["after"]) for x in gold("T08")["dependency_edges"]}


@pytest.mark.parametrize("name", ["Delhi", "Dilli", "दिल्ली"])
def test_t09_delhi_is_ambiguous_in_every_script(name):
    r = fresh().call("resolve_station", {"name": name})["data"]
    assert r["ambiguous"] and {c["code"] for c in r["candidates"]} == {"NDLS", "NZM"}


def test_t09_clarification_gold_books_nothing():
    g = gold("T09")
    assert g["final_state"]["status"] == "needs_clarification" and g["final_state"]["expected_bookings"] == []
    assert g["min_calls"] == 0 and all(c["optional"] for c in g["required_calls"])


def test_t10_fallback_booking_mutates_exactly_the_fallback_class():
    g, e = gold("T10"), fresh()
    assert e.call("book_ticket", {"train_id": "BTB101", "travel_class": "2A", "passenger": "Sneha Patil"})["error"]["code"] == "SOLD_OUT"
    r = e.call("book_ticket", {"train_id": "BTB101", "travel_class": "3A", "passenger": "Sneha Patil"})
    assert r["ok"] and r["data"]["booking_id"] == g["final_answer"]["booking_id"] == "BK0001"
    assert g["expected_env_diff"]["availability_changes"] == {"BTB101|3A": [8, 7]}


def test_t11_expected_error_is_class_not_offered():
    g = gold("T11")
    c1 = g["required_calls"][0]
    assert c1["expected_error"] == "CLASS_NOT_OFFERED" and c1["optional"] is True
    assert fresh().call(c1["tool"], c1["required_args"])["error"]["code"] == "CLASS_NOT_OFFERED"
    assert g["final_answer"]["offered_classes"] == ["2A", "3A"] and g["final_state"]["status"] == "cannot_complete"


def test_t12_naive_latest_train_misses_the_next_day_deadline():
    trains = fresh().call("search_trains", {"source": "JP", "destination": "ADI", "date": "2026-10-09"})["data"]["trains"]
    latest = max(trains, key=lambda t: t["departure"])
    assert latest["train_id"] == "BTB107" and latest["arrival_day_offset"] == 1 and latest["arrival"] > "09:30"
    assert gold("T12")["final_answer"] == {"status": "success", "selected_train_id": "BTB101", "departure": "20:20",
                                           "arrival": "04:00", "arrival_date": "2026-10-10"}


def test_t13_two_bookings_drain_the_class_in_any_order():
    g = gold("T13")
    assert g["expected_env_diff"]["availability_changes"] == {"BTB102|3A": [2, 0]}
    for order in (["Priya Nair", "Arjun Nair"], ["Arjun Nair", "Priya Nair"]):
        e = fresh()
        for name in order:
            assert e.call("book_ticket", {"train_id": "BTB102", "travel_class": "3A", "passenger": name})["ok"]
        got = sorted((b["train_id"], b["travel_class"], b["passenger"]) for b in e.snapshot()["bookings"])
        assert got == sorted((b["train_id"], b["travel_class"], b["passenger"]) for b in g["final_state"]["expected_bookings"])
        assert e.call("check_availability", {"train_id": "BTB102", "travel_class": "3A"})["data"]["status"] == "SOLD_OUT"


def test_t14_cheapest_class_overall_is_sold_out():
    g = gold("T14")
    assert g["final_answer"]["travel_class"] == "3A" and g["final_answer"]["excluded_cheaper_sold_out"] == ["SL"]
    assert {(c["tool"], c["required_args"]["travel_class"]) for c in g["required_calls"] if not c["optional"]} == {
        ("check_availability", "3A"), ("get_fare", "3A"), ("check_availability", "SL"), ("get_fare", "2A")}


def test_t15_environment_would_accept_a_partial_booking_so_only_reasoning_prevents_it():
    e = fresh()
    h = e.state_hash()
    assert e.call("check_availability", {"train_id": "BTB130", "travel_class": "CC"})["data"] == {
        "train_id": "BTB130", "travel_class": "CC", "seats_available": 1, "status": "AVAILABLE"}
    assert e.call("book_ticket", {"train_id": "BTB130", "travel_class": "CC", "passenger": "Meera Joshi"})["ok"]  # the trap
    assert e.state_hash() != h
    g = gold("T15")
    assert g["final_state"]["expected_bookings"] == [] and g["forbidden_tools"] == ["book_ticket"]
    assert {a["prompt_phrase"] for a in g["prohibited_actions"]} == {"book only if there are seats for both of us", "otherwise don't book anything"}


def test_read_only_batch_tasks_leave_state_unchanged():
    for t in ("T06", "T07", "T08", "T09", "T11", "T12", "T14", "T15"):
        assert gold(t)["expected_env_diff"] == {"bookings": [], "availability_changes": {}}


def test_solver_rejects_fixture_change_that_would_trivialise_a_task(monkeypatch):
    """Design guards: e.g. if BTB130 had 0 seats, T15 would become a T05 duplicate -> gold generation must refuse."""
    spec = copy.deepcopy(next(s for s in load_specs() if s.semantic_task_id == "T15"))
    spec.solver.params["train_id"] = "BTB114"  # LKO->NDLS CC sold out; route check fails first, which is also a refusal
    with pytest.raises(ValueError):
        build_task_gold(spec)
    spec = copy.deepcopy(next(s for s in load_specs() if s.semantic_task_id == "T12"))
    spec.solver.params["arrive_by_time"] = "10:00"  # deadline no longer prunes BTB107
    with pytest.raises(ValueError, match="does not prune"):
        build_task_gold(spec)


# ------------------------------------------------------------------ semantic duplicates
def test_no_semantic_duplicates_across_t01_t15():
    specs = {s.semantic_task_id: s for s in load_specs()}
    g = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    assert so.overlap_errors(specs, g) == []
    assert len({s.solver.kind for s in specs.values()}) == len(specs)  # one solver kind per task (15 when written)


def _with_clone(src, new_kind=None, **param_changes):
    specs = {s.semantic_task_id: s for s in load_specs()}
    g = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    clone = copy.deepcopy(specs[src])
    clone.semantic_task_id = "T99"
    clone.solver.params.update(param_changes)
    if new_kind:
        clone.solver.kind = new_kind
    specs["T99"], g["T99"] = clone, copy.deepcopy(g[src])
    return so.overlap_errors(specs, g)


def test_overlap_detects_data_swap_duplicate():
    # same reasoning as T03, only the route/date/budget changed -> must be flagged
    e = _with_clone("T03", source_name="Mumbai", destination_name="Ahmedabad", date="2026-10-09", max_fare_inr=2600)
    assert any("T03" in x and "T99" in x for x in e)


def test_overlap_detects_renamed_solver_duplicate():
    # even when disguised under a new solver name, identical reasoning features collide
    e = _with_clone("T12", new_kind="arrival_deadline_v2")
    assert any("fingerprint" in x and "T12" in x and "T99" in x for x in e)


# ------------------------------------------------------------------ multilingual equivalence
def test_all_40_batch_variants_pass_surface_checks_and_share_numbers():
    specs = {s.semantic_task_id: s for s in load_specs()}
    o = vt.RawOracle()
    code_of = lambda n: next(iter(o.codes_for(n)))  # noqa: E731
    for t in BATCH:
        qs = {l: next(r["query"] for r in rows(l) if r["semantic_task_id"] == t) for l in LANGS}
        assert len({json.dumps(lc.numeric_signature(q)) for q in qs.values()}) == 1, t
        for l, q in qs.items():
            res = lc.run_checks(t, l, q, specs[t].solver.params, code_of)
            assert all(v is not False for v in res.values()), (t, l, res)
            assert sum(v is True for v in res.values()) >= 3, (t, l)  # checks are not vacuous


def test_t09_no_variant_names_a_specific_delhi_station():
    for l in LANGS:
        q = next(r["query"] for r in rows(l) if r["semantic_task_id"] == "T09")
        for specific in ("New Delhi", "Nai Dilli", "Nizamuddin", "नई दिल्ली", "नवी दिल्ली", "निज"):
            assert specific not in q, (l, specific)


def test_passengers_and_train_ids_stay_latin_and_identical():
    for t in BATCH:
        qs = [next(r["query"] for r in rows(l) if r["semantic_task_id"] == t) for l in LANGS]
        for token in ("Priya Nair", "Arjun Nair", "Meera Joshi", "Sameer Joshi", "Sneha Patil", "Rohan Mehta",
                      "BTB101", "BTB109", "BTB111", "BTB119", "BTB130"):
            assert len({token in q for q in qs}) == 1, (t, token)


# ---- negative tests: the validator must catch semantic drift in the batch
def test_detects_t15_dropped_group_quantity(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hi", "T15", lambda r: r.update(query=r["query"].replace("हम दोनों के लिए ", "")))
    assert "T15_hi: surface check availability_constraint_preserved FAILED" in e


def test_detects_t09_ambiguity_removed(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "mr", "T09", lambda r: r.update(query=r["query"].replace("दिल्ली", "नवी दिल्ली")))
    assert "T09_mr: surface check route_preserved FAILED" in e


def test_detects_t12_dropped_latest_objective(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hinglish", "T12", lambda r: r.update(query=r["query"].replace("jitna ho sake utni der se ", "")))
    assert "T12_hinglish: surface check time_constraint_preserved FAILED" in e


def test_detects_t10_widened_fallback(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hinglish", "T10", lambda r: r.update(query=r["query"].replace("usi train mein", "kisi bhi train mein")))
    assert "T10_hinglish: surface check fallback_condition_preserved FAILED" in e


def test_detects_t13_dropped_passenger_and_changed_time(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "en", "T13", lambda r: r.update(query=r["query"].replace(" and one for Arjun Nair", "")))
    assert "T13_en: surface check passenger_preserved FAILED" in e and "T13: passenger name not in prompt" in e
    e = mutate(tmp_path, monkeypatch, "mr", "T13", lambda r: r.update(query=r["query"].replace("संध्याकाळी 5", "संध्याकाळी 6")))
    assert "T13: numbers differ across variants" in e and "T13_mr: surface check time_preserved FAILED" in e


def test_detects_t08_dropped_fallback_rule(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "mr", "T08", lambda r: r.update(query=r["query"].split("त्या वेळेत")[0]))
    assert "T08_mr: surface check fallback_condition_preserved FAILED" in e


def test_detects_batch_review_status_and_sync_problems(tmp_path, monkeypatch):
    assert "review_status must be 'draft'" in mutate(tmp_path, monkeypatch, "hi", "T11", lambda r: r.update(review_status="accepted"))
    assert "out of sync with batch_t06_t15.py" in mutate(tmp_path, monkeypatch, "hinglish", "T06", lambda r: r.update(query=r["query"] + " "))


def test_detects_edit_to_a_frozen_pilot_row_in_a_draft_language(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hi", "T02", lambda r: r.update(tags=r["tags"] + ["x"]))
    assert "hi.jsonl pilot rows T01-T05 changed (frozen)" in e


def test_detects_hand_edited_batch_gold(tmp_path, monkeypatch):
    bad = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    bad["T12"]["final_answer"]["selected_train_id"] = "BTB107"
    f = tmp_path / "gold_labels.json"
    f.write_text(render(bad), encoding="utf-8")
    monkeypatch.setattr(vt, "GOLD_PATH", f)
    e = " | ".join(vt.validate())
    assert "hand-edited or stale" in e
