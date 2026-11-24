"""Batch T26-T50 (25 semantic tasks x 4 languages = 100 DRAFT items; design phases A T26-T35, B T36-T45, C T46-T50).
Gold behaviour, environment traps, determinism, T01-T25 preservation, global duplicates, multilingual equivalence, negatives."""
import copy
import hashlib
import itertools
import json
import re
import shutil

import pytest

from benchmark import batch_t26_t50 as batch
from benchmark import build_gold as bg
from benchmark import language_checks as lc
from benchmark import semantic_overlap as so
from benchmark import validate_tasks as vt
from benchmark.build_gold import GOLD_PATH, SPEC_PATH, build_all, build_task_gold, load_specs, render
from environment import TOOL_NAMES, RailwayEnv
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


def call(e, tool, **a):
    return e.call(tool, a)


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
def test_batch_t26_t50_present_in_place():
    """Counts were 50 tasks / 200 items when this batch was the last one; later batches (T51-T75) append after it."""
    assert vt.validate() == []
    assert [s.semantic_task_id for s in load_specs()][:50] == [f"T{i:02d}" for i in range(1, 51)]
    for l in LANGS:
        assert [r["semantic_task_id"] for r in rows(l)] == vt.ALL_IDS and [r["semantic_task_id"] for r in rows(l)][25:50] == BATCH
        assert len({r["task_id"] for r in rows(l)}) == len(vt.ALL_IDS)
    assert sum(len(rows(l)) for l in LANGS) == 4 * len(vt.ALL_IDS)
    assert len(json.loads(GOLD_PATH.read_text(encoding="utf-8"))) - 1 == len(vt.ALL_IDS)  # minus _meta


def test_batch_items_review_fields_match_human_review_record():  # mr reviewed (human_review.py); en/hinglish/hi drafts
    for l in LANGS:
        for r in rows(l):
            if r["semantic_task_id"] in BATCH:
                assert (r["reviewer"], r["review_status"]) == hr.expected_review(r["language"], r["semantic_task_id"])
                assert r["review_status"] == ("reviewed" if l == "mr" else "draft")
                assert r["author"] == (batch.EN_AUTHOR if l == "en" else "Claude-generated draft")
    audit = json.loads(vt.BATCH3_AUDIT_PATH.read_text(encoding="utf-8"))["records"]
    assert len(audit) == 100 and all(a["human_review"] == a["fluency_review"] == a["equivalence_review"] == "pending_human_review" for a in audit)


def test_gold_is_deterministic_twice_and_matches_committed_file():
    assert render(build_all()) == render(build_all()) == GOLD_PATH.read_text(encoding="utf-8")


def test_t01_t25_spec_gold_language_rows_and_audits_are_frozen():
    g = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    assert vt._sha({t: g[t] for t in vt.FROZEN_T01_T25_IDS}) == vt.FROZEN_T01_T25_GOLD_SHA256
    sp = json.loads(SPEC_PATH.read_text(encoding="utf-8"))["tasks"]
    assert vt._sha([t for t in sp if t["semantic_task_id"] in vt.FROZEN_T01_T25_IDS]) == vt.FROZEN_T01_T25_SPEC_SHA256
    for l in LANGS:
        head = hr.draft_head_bytes(vt.LANG_DIR / f"{l}.jsonl", 25)  # review fields reset (benchmark/human_review.py)
        assert hashlib.sha256(head).hexdigest() == vt.FROZEN_T01_T25_LANG_SHA256[l]
    assert hashlib.sha256((vt.LANG_DIR / "batch_T16_T25_language_audit.json").read_bytes()).hexdigest() == vt.FROZEN_T16_T25_AUDIT_SHA256


@pytest.mark.parametrize("tid", BATCH)
def test_gold_replays_to_the_expected_final_state(tid):
    """Replaying ALL gold calls (optional ones included) on a fresh env must give exactly the expected bookings."""
    g, e = gold(tid), fresh()
    for c in g["required_calls"]:
        args = dict(c["required_args"])
        if any(isinstance(v, dict) for v in args.values()):
            continue  # language-specific resolve matchers are replayed by the validator
        r = e.call(c["tool"], args)
        assert r["ok"] == (not c.get("expected_error")), (tid, c, r)
    got = sorted((b["train_id"], b["travel_class"], b["passenger"]) for b in e.snapshot()["bookings"])
    assert got == sorted((b["train_id"], b["travel_class"], b["passenger"]) for b in g["final_state"]["expected_bookings"])


# ------------------------------------------------------------------ traps: the environment would NOT stop a wrong action
def test_t30_past_date_booking_would_be_accepted_by_book_ticket():
    e = fresh()
    assert call(e, "search_trains", source="PUNE", destination="NGP", date="2026-10-02")["error"]["code"] == "PAST_DATE"
    assert call(e, "book_ticket", train_id="BTB127", travel_class="SL", passenger="Rohit Pawar")["ok"]  # no date argument: the trap
    assert gold("T30")["final_state"]["expected_bookings"] == [] and gold("T30")["min_calls"] == 0


def test_t39_train_does_not_run_but_booking_would_succeed():
    e = fresh()
    assert "WED" not in call(e, "get_train_details", train_id="BTB111")["data"]["operating_days"]
    assert "BTB111" not in [t["train_id"] for t in call(e, "search_trains", source="NDLS", destination="LKO", date="2026-10-07")["data"]["trains"]]
    assert call(e, "book_ticket", train_id="BTB111", travel_class="2A", passenger="Meera Nair")["ok"]
    assert gold("T39")["forbidden_tools"] == ["book_ticket"]


def test_t37_unrequested_booking_would_succeed():
    assert call(fresh(), "book_ticket", train_id="BTB110", travel_class="2A", passenger="Rahul Verma")["ok"]
    assert gold("T37")["final_state"] == {"status": "needs_clarification", "allowed_train_ids": None, "travel_class": "2A", "expected_bookings": []}


def test_t41_booking_leg_one_first_would_leave_a_partial_itinerary():
    e = fresh()
    assert call(e, "book_ticket", train_id="BTB119", travel_class="3A", passenger="Sameer Khan")["ok"]
    assert call(e, "book_ticket", train_id="BTB121", travel_class="2A", passenger="Sameer Khan")["error"]["code"] == "SOLD_OUT"
    assert len(e.snapshot()["bookings"]) == 1  # exactly the forbidden partial state
    assert gold("T41")["final_answer"]["failing_leg"] == 2


def test_t29_and_t28_errors_and_no_cancel_tool_for_t45():
    e = fresh()
    assert call(e, "check_availability", train_id="BTB110", travel_class="1A")["error"]["code"] == "INVALID_CLASS"
    assert call(e, "get_train_details", train_id="BTB150")["error"]["code"] == "INVALID_TRAIN"
    assert not any("cancel" in t for t in TOOL_NAMES) and gold("T45")["required_calls"] == []


def test_t31_recovery_path():
    e = fresh()
    assert call(e, "resolve_station", name="Bombay Central")["error"]["code"] == "STATION_NOT_FOUND"
    assert call(e, "resolve_station", name="Mumbai Central")["data"]["candidates"][0]["code"] == "MMCT"
    c = gold("T31")["required_calls"]
    assert c[0]["optional"] and c[0]["expected_error"] == "STATION_NOT_FOUND" and ("c1", "c2") in {(x["before"], x["after"]) for x in gold("T31")["dependency_edges"]}


def test_t32_else_branch_and_t33_capacity_and_t34_budget():
    assert gold("T32")["final_answer"]["condition_fare_inr"] >= 2000 and gold("T32")["final_state"]["expected_bookings"][0]["travel_class"] == "3A"
    assert call(fresh(), "check_availability", train_id="BTB117", travel_class="CC")["data"]["seats_available"] < 3
    assert gold("T33")["expected_env_diff"]["availability_changes"] == {"BTB123|SL": [41, 38]} and gold("T33")["min_calls"] == 13
    fa = gold("T34")["final_answer"]
    assert fa["excluded_over_budget"] == ["BTB101"] and fa["selected_train_id"] == "BTB103" and fa["seats_available"] == 0


def test_t35_relative_date_resolution():
    c = [x for x in gold("T35")["required_calls"] if x["tool"] == "search_trains"][0]
    assert c["required_args"]["date"] == "2026-10-10"
    for d in ("2026-10-09", "2026-10-11"):
        assert not [t for t in call(fresh(), "search_trains", source="NDLS", destination="LKO", date=d)["data"]["trains"] if "SL" in t["classes"]]


def test_t40_connection_and_t48_partial_and_t50_state():
    e = fresh()
    assert call(e, "search_trains", source="LKO", destination="JP", date="2026-10-09")["data"]["count"] == 0
    fa = gold("T40")["final_answer"]
    assert (fa["first_leg_train_id"], fa["second_leg_train_id"]) == ("BTB110", "BTB101") and fa["connection_minutes"] >= 60
    assert gold("T48")["final_answer"]["booked_passengers"] == ["Leela Das"]
    e = fresh()
    assert call(e, "book_ticket", train_id="BTB117", travel_class="CC", passenger="Imran Sheikh")["ok"]
    assert call(e, "check_availability", train_id="BTB117", travel_class="CC")["data"]["seats_available"] == 1
    edges = {(x["before"], x["after"]) for x in gold("T50")["dependency_edges"]}
    assert ("c1", "c2") in edges and ("c2", "c3") in edges and gold("T50")["final_answer"]["seats_remaining_at_end"] == 0


def test_t47_ambiguity_resolved_by_the_train_not_by_asking():
    e = fresh()
    assert call(e, "resolve_station", name="Delhi")["data"]["ambiguous"]
    assert call(e, "get_train_details", train_id="BTB129")["data"]["source_station"] == "NZM"
    assert gold("T47")["final_state"]["status"] == "success" and gold("T09")["final_state"]["status"] == "needs_clarification"


def test_t42_class_bound_to_the_right_passenger():
    b = {x["passenger"]: x["travel_class"] for x in gold("T42")["final_state"]["expected_bookings"]}
    assert b == {"Ramesh Gupta": "2A", "Ajay Gupta": "3A"}


def test_solver_guards_refuse_trivialised_variants():
    s = copy.deepcopy(next(x for x in load_specs() if x.semantic_task_id == "T32"))
    s.solver.params["fare_below_inr"] = 2500  # condition would hold: no else-branch tested
    with pytest.raises(ValueError, match="else-branch"):
        build_task_gold(s)
    s = copy.deepcopy(next(x for x in load_specs() if x.semantic_task_id == "T48"))
    s.solver.params["passengers"] = ["Leela Das"]  # enough seats: policy irrelevant
    with pytest.raises(ValueError):
        build_task_gold(s)
    s = copy.deepcopy(next(x for x in load_specs() if x.semantic_task_id == "T43"))
    s.solver.params["max_fare_inr"] = 4000  # fare constraint no longer binding
    with pytest.raises(ValueError, match="prune"):
        build_task_gold(s)


# ------------------------------------------------------------------ global duplicates
def test_no_semantic_duplicates_across_all_tasks():
    specs = {s.semantic_task_id: s for s in load_specs()}
    assert so.overlap_errors(specs, json.loads(GOLD_PATH.read_text(encoding="utf-8"))) == []
    assert len({s.solver.kind for s in specs.values()}) == len(specs)


def test_overlap_rejects_a_thin_search_only_variant():
    """Regression for the redesigns of T34/T35/T42: a resolve->search info task that differs from T25 by one reasoning label
    (as the first drafts did) must be flagged."""
    specs = {s.semantic_task_id: s for s in load_specs()}
    g = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    clone = copy.deepcopy(specs["T25"])
    clone.semantic_task_id, clone.solver.kind = "T99", "first_running_date"
    clone.constraints = [c for c in clone.constraints if c["kind"] != "departure_window_cross_midnight"] + [{"kind": "first_date_search"}]
    specs["T99"], g["T99"] = clone, copy.deepcopy(g["T25"])
    assert any("T25~T99" in e or "T99" in e for e in so.overlap_errors(specs, g))


# ------------------------------------------------------------------ multilingual equivalence
def test_all_100_batch_variants_pass_surface_checks_and_share_numbers():
    specs = {s.semantic_task_id: s for s in load_specs()}
    o = vt.RawOracle()
    code_of = lambda n: next(iter(o.codes_for(n)))  # noqa: E731
    for t in BATCH:
        qs = {l: query(t, l) for l in LANGS}
        assert len({json.dumps(lc.numeric_signature(q)) for q in qs.values()}) == 1, t
        for l, q in qs.items():
            res = lc.run_checks(t, l, q, specs[t].solver.params, code_of)
            assert all(v is not False for v in res.values()), (t, l, res)
            # T45 (cancellation) has no station/class/date/passenger: its single marker covers both of its entities
            assert sum(v is True for v in res.values()) >= (1 if t == "T45" else 3), (t, l)


def test_shared_gold_per_task_and_no_language_keys():
    g = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    for t in BATCH:
        assert "language" not in json.dumps(g[t]) and "query" not in g[t]
        assert {next(r for r in rows(l) if r["semantic_task_id"] == t)["category"] for l in LANGS} == {batch.EN_ITEMS[t]["category"]}


# ---- negative tests (language drift)
def test_detects_t35_relative_date_made_explicit(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hi", "T35", lambda r: r.update(query=r["query"].replace("इस शनिवार को", "10 अक्टूबर 2026 को")))
    assert "T35_hi: surface check intent_preserved FAILED" in e


def test_detects_t41_dropped_all_or_nothing(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "mr", "T41", lambda r: r.update(query=r["query"].split(" मला दोन्ही")[0]))
    assert "T41_mr: surface check forbidden_action_preserved FAILED" in e


def test_detects_t33_dropped_group_capacity(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hinglish", "T33", lambda r: r.update(query=r["query"].replace(" jismein hum teeno ke liye seats hon", "")))
    assert "T33_hinglish: surface check availability_constraint_preserved FAILED" in e


def test_detects_t36_class_made_specific(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "en", "T36", lambda r: r.update(query=r["query"].replace("an AC ticket", "a 3A ticket")))
    assert "T36_en: surface check intent_preserved FAILED" in e


def test_detects_t42_swapped_classes(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hi", "T42", lambda r: r.update(query=r["query"].replace("के लिए 2A और", "के लिए 3A और").replace("के लिए 3A बुक", "के लिए 2A बुक")))
    assert "T42_hi: surface check intent_preserved FAILED" in e


def test_detects_t31_recovery_removed(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "mr", "T31", lambda r: r.update(query=r["query"].replace("बॉम्बे सेंट्रल", "मुंबई सेंट्रल")))
    assert "T31_mr: surface check intent_preserved FAILED" in e


def test_detects_t37_booking_verb_added(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hinglish", "T37", lambda r: r.update(query=r["query"] + " Book kar do."))
    assert "T37_hinglish: surface check booking_condition_preserved FAILED" in e


def test_detects_t29_class_changed(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hi", "T29", lambda r: r.update(query=r["query"].replace("(1A)", "(2A)")))
    assert "T29: numbers differ across variants" in e and "T29_hi: surface check class_preserved FAILED" in e


def test_detects_review_status_and_frozen_t16_t25_row(tmp_path, monkeypatch):
    assert "review_status must be 'reviewed'" in mutate(tmp_path, monkeypatch, "mr", "T44", lambda r: r.update(review_status="accepted"))
    assert "mr.jsonl rows T01-T25 changed (frozen)" in mutate(tmp_path, monkeypatch, "mr", "T22", lambda r: r.update(tags=r["tags"] + ["x"]))


# ---- negative test (oracle): a wrong solver whose gold is regenerated CONSISTENTLY must still be caught
def test_independent_oracle_catches_a_wrong_solver(tmp_path, monkeypatch):
    real = bg.SOLVERS["fastest_within_budget"]

    def wrong(env, p, plan):  # picks the cheapest instead of the fastest qualifying train
        ans, allowed, eff = real(env, p, plan)
        return {**ans, "selected_train_id": "BTB123", "duration_minutes": 525}, ["BTB123"], eff
    monkeypatch.setitem(bg.SOLVERS, "fastest_within_budget", wrong)
    f = tmp_path / "gold_labels.json"
    f.write_text(render(build_all()), encoding="utf-8")  # gold now reproducible from the (wrong) solver
    monkeypatch.setattr(vt, "GOLD_PATH", f)
    monkeypatch.setattr(vt, "build_all", build_all)
    e = " | ".join(vt.validate())
    assert "T34: oracle train {'BTB103'} != gold" in e and "T34: oracle duration_minutes=445 != gold 525" in e


# ---- coverage report is generated, deterministic and committed up to date
def test_coverage_report_is_reproducible_and_current():
    from benchmark import coverage_report as cr
    assert cr.render(cr.compute()) == cr.render(cr.compute()) == cr.OUT.read_text(encoding="utf-8")
    labelled = set().union(*cr.LABELS.values())
    assert labelled <= set(vt.ALL_IDS)  # labels only reference real tasks
