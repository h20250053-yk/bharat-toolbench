"""Batch T51-T75 (end-sem batch: 25 semantic tasks x 4 languages = 100 DRAFT items).
Counts, freeze of T01-T50, gold behaviour, environment traps (the environment would NOT stop the wrong action), solver guards,
global duplicates, multilingual equivalence incl. the 8 language-feature tasks, negative drift tests, independent oracle,
and scorer behaviour on the new traps. No model, no network."""
import copy
import hashlib
import itertools
import json
import shutil

import pytest

from benchmark import batch_t51_t75 as batch
from benchmark import build_gold as bg
from benchmark import language_checks as lc
from benchmark import semantic_overlap as so
from benchmark import validate_tasks as vt
from benchmark.build_gold import GOLD_PATH, SPEC_PATH, build_all, build_task_gold, load_specs, render
from environment import RailwayEnv
from evaluation.scorer import score
from evaluation.selfcheck import execute, final_json, final_text, gold_calls, gold_for
from benchmark import human_review as hr

LANGS = ["en", "hinglish", "hi", "mr"]
BATCH = batch.BATCH_IDS
LANGUAGE_FEATURE_TASKS = ["T54", "T57", "T62", "T64", "T67", "T69", "T71", "T72"]
_n = itertools.count()


def gold(tid):
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))[tid]


def spec(tid):
    return next(s for s in load_specs() if s.semantic_task_id == tid)


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


def run(tid, calls, **override):
    traj, snap = execute(calls)
    obj = final_json(tid, snap, **override)
    row = {"task_id": f"{tid}_en", "semantic_task_id": tid, "language": "en", "status": "completed", "trajectory": traj,
           "final_text": final_text(tid, obj), "state_snapshot": snap}
    return score(row, gold_for(tid), snap)


# ------------------------------------------------------------------ counts, status, determinism, preservation
def test_final_counts_75_tasks_300_items_75_per_language():
    assert vt.validate() == []
    assert [s.semantic_task_id for s in load_specs()] == [f"T{i:02d}" for i in range(1, 76)] == vt.ALL_IDS
    for l in LANGS:
        assert [r["semantic_task_id"] for r in rows(l)] == vt.ALL_IDS and len({r["task_id"] for r in rows(l)}) == 75
    assert sum(len(rows(l)) for l in LANGS) == 300
    assert len(json.loads(GOLD_PATH.read_text(encoding="utf-8"))) - 1 == 75  # minus _meta


def test_batch_mix_matches_the_design():
    st = [gold(t)["final_state"]["status"] for t in BATCH]
    assert (st.count("success"), st.count("cannot_complete"), st.count("needs_clarification")) == (19, 3, 3)
    assert sum(1 for t in BATCH if gold(t)["final_state"]["expected_bookings"]) == 8
    assert set(LANGUAGE_FEATURE_TASKS) < set(BATCH)


def test_batch_items_review_fields_match_human_review_record():  # mr reviewed (human_review.py); en/hinglish/hi drafts
    for l in LANGS:
        for r in rows(l):
            if r["semantic_task_id"] in BATCH:
                assert (r["reviewer"], r["review_status"]) == hr.expected_review(r["language"], r["semantic_task_id"])
                assert r["review_status"] == ("reviewed" if l == "mr" else "draft")
                assert r["author"] == (batch.EN_AUTHOR if l == "en" else "Claude-generated draft")
    audit = json.loads(vt.BATCH4_AUDIT_PATH.read_text(encoding="utf-8"))["records"]
    assert len(audit) == 100 and all(a["human_review"] == a["fluency_review"] == a["equivalence_review"] == "pending_human_review" for a in audit)


def test_gold_is_deterministic_twice_and_matches_committed_file():
    assert render(build_all()) == render(build_all()) == GOLD_PATH.read_text(encoding="utf-8")


def test_t01_t50_spec_gold_language_rows_and_audits_are_frozen():
    g = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    assert vt._sha({t: g[t] for t in vt.FROZEN_T01_T50_IDS}) == vt.FROZEN_T01_T50_GOLD_SHA256
    sp = json.loads(SPEC_PATH.read_text(encoding="utf-8"))["tasks"]
    assert vt._sha([t for t in sp if t["semantic_task_id"] in vt.FROZEN_T01_T50_IDS]) == vt.FROZEN_T01_T50_SPEC_SHA256
    for l in LANGS:
        head = hr.draft_head_bytes(vt.LANG_DIR / f"{l}.jsonl", 50)  # review fields reset (benchmark/human_review.py)
        assert hashlib.sha256(head).hexdigest() == vt.FROZEN_T01_T50_LANG_SHA256[l]
    assert hashlib.sha256((vt.LANG_DIR / "batch_T26_T50_language_audit.json").read_bytes()).hexdigest() == vt.FROZEN_T26_T50_AUDIT_SHA256


def test_gold_meta_baseline_state_hash_unchanged():
    """New tasks are spec/gold only: the mutable environment state (and so env_hash_before in existing runs) is untouched."""
    assert json.loads(GOLD_PATH.read_text(encoding="utf-8"))["_meta"]["env_baseline_state_hash"] == fresh().state_hash()


@pytest.mark.parametrize("tid", BATCH)
def test_gold_replays_to_the_expected_final_state(tid):
    g, e = gold(tid), fresh()
    for c in g["required_calls"]:
        args = dict(c["required_args"])
        if any(isinstance(v, dict) for v in args.values()):
            continue  # language-specific resolve matchers are replayed by the validator
        r = e.call(c["tool"], args)
        assert r["ok"] == (not c.get("expected_error")), (tid, c, r)
        if c.get("expected_error"):
            assert r["error"]["code"] == c["expected_error"]
    got = sorted((b["train_id"], b["travel_class"], b["passenger"]) for b in e.snapshot()["bookings"])
    assert got == sorted((b["train_id"], b["travel_class"], b["passenger"]) for b in g["final_state"]["expected_bookings"])


# ------------------------------------------------------------------ traps: the environment would NOT stop the wrong action
def test_t51_count_includes_the_cc_day_train_and_latest_is_btb124():
    tr = call(fresh(), "search_trains", source="MMCT", destination="ADI", date="2026-10-09")["data"]["trains"]
    assert len(tr) == 4 and sum("3A" in t["classes"] for t in tr) == 3  # a 3A-only count would say 3
    fa = gold("T51")["final_answer"]
    assert (fa["train_count"], fa["selected_train_id"], fa["departure"]) == (4, "BTB124", "23:50")


def test_t52_earliest_departure_is_not_earliest_arrival():
    fa = gold("T52")["final_answer"]
    assert fa["selected_train_id"] == "BTB102" and fa["arrival"] == "06:45" and fa["arrival_date"] == "2026-10-10"
    tr = [t for t in call(fresh(), "search_trains", source="ADI", destination="JP", date="2026-10-09")["data"]["trains"] if t["departure"] >= "18:00"]
    assert min(tr, key=lambda t: t["departure"])["train_id"] == "BTB108"


def test_t54_native_script_name_is_rejected_and_latin_name_books():
    e = fresh()
    for form in spec("T54").solver.params["passenger_script_forms"].values():
        assert call(e, "book_ticket", train_id="BTB126", travel_class="CC", passenger=form)["error"]["code"] == "INVALID_PASSENGER"
    assert call(e, "book_ticket", train_id="BTB126", travel_class="CC", passenger="Ravi Patel")["ok"]
    assert "रवि पटेल" in query("T54", "hi") and "रवी पटेल" in query("T54", "mr") and "Ravi Patel" not in query("T54", "hi")


def test_t55_boarding_date_differs_from_the_train_start_date():
    det = call(fresh(), "get_train_details", train_id="BTB110")["data"]
    assert det["source_station"] == "HWH" and det["stops"][1]["station"] == "LKO"
    assert gold("T55")["final_answer"]["arrival_date"] == "2026-10-10"


def test_t57_day_after_tomorrow_changes_the_answer():
    def last_sl(d):
        tr = [t for t in call(fresh(), "search_trains", source="ADI", destination="JP", date=d)["data"]["trains"] if "SL" in t["classes"]]
        return max(tr, key=lambda t: t["departure"])["train_id"]
    assert last_sl("2026-10-07") == "BTB108" and last_sl("2026-10-06") == last_sl("2026-10-08") == "BTB104"
    assert "परसों" in query("T57", "hi") and "परवा" in query("T57", "mr") and not lc.parse_dates(query("T57", "hi"), "hi")


def test_t59_and_t68_bookings_would_succeed_but_are_not_wanted():
    e = fresh()
    assert call(e, "book_ticket", train_id="BTB118", travel_class="CC", passenger="Ritu Chawla")["ok"]
    assert gold("T59")["forbidden_tools"] == ["book_ticket"] and gold("T68")["final_state"]["expected_bookings"] == []
    assert gold("T68")["prohibited_actions"] == [] and gold("T68")["final_answer"]["total_fare_inr"] == 2090 + 1460


def test_t61_one_ticket_fits_the_budget_but_the_total_does_not():
    fa = gold("T61")["final_answer"]
    assert fa["fare_inr_per_ticket"] <= 1800 < fa["total_fare_inr"] == 3 * 615
    assert call(fresh(), "check_availability", train_id="BTB127", travel_class="SL")["data"]["seats_available"] >= 3


def test_t62_spoken_time_and_t64_spoken_amount_keep_numbers_equal_across_languages():
    for t in ("T62", "T64"):
        assert len({json.dumps(lc.numeric_signature(query(t, l))) for l in LANGS}) == 1
    assert "सवा सात" in query("T62", "hi") and "7:15" not in query("T62", "hi") and "07:15" not in query("T62", "en")
    assert "ढाई हज़ार" in query("T64", "hi") and "2,500" not in query("T64", "hi") and gold("T64")["final_answer"]["fare_inr"] == 2495


def test_t63_and_t70_and_t65_seat_traps():
    e = fresh()
    assert call(e, "check_availability", train_id="BTB109", travel_class="3A")["data"]["seats_available"] == 0
    assert call(e, "check_availability", train_id="BTB104", travel_class="SL")["data"]["seats_available"] == 1  # AVAILABLE, but < 5
    assert call(e, "book_ticket", train_id="BTB104", travel_class="SL", passenger="Yash Kapoor")["ok"]  # the environment would accept it
    assert call(fresh(), "check_availability", train_id="BTB102", travel_class="3A")["data"]["seats_available"] == 2  # T65: < party of 3
    assert gold("T65")["final_answer"]["skipped_insufficient_seats"] == ["BTB102"]


def test_t66_date_comes_from_operating_days_and_booking_takes_no_date():
    assert gold("T66")["final_answer"]["resolved_date"] == "2026-10-10"
    assert "BTB111" not in [t["train_id"] for t in call(fresh(), "search_trains", source="NDLS", destination="LKO", date="2026-10-09")["data"]["trains"]]


def test_t67_impossible_date_is_invalid_and_not_parsed_as_a_date():
    assert call(fresh(), "search_trains", source="PUNE", destination="NGP", date="2026-11-31")["error"]["code"] == "INVALID_DATE"
    assert vt._parse_dates(query("T67", "en")) == [] and vt._parse_dates("on 30 November 2026") == ["2026-11-30"]


def test_t69_two_names_one_station():
    e = fresh()
    assert {c["code"] for n in ("Howrah", "Kolkata", "हावड़ा", "कोलकाता") for c in call(e, "resolve_station", name=n)["data"]["candidates"]} == {"HWH"}
    assert call(e, "search_trains", source="HWH", destination="HWH", date="2026-10-09")["error"]["code"] == "SAME_STATION"


def test_t71_second_ticket_for_the_same_name_is_refused():
    e = fresh()
    for x in ("Anjali Rao", "Sunil Rao"):
        assert call(e, "book_ticket", train_id="BTB115", travel_class="3A", passenger=x)["ok"]
    assert call(e, "book_ticket", train_id="BTB115", travel_class="3A", passenger="Anjali Rao")["error"]["code"] == "DUPLICATE_BOOKING"
    assert gold("T71")["final_answer"]["duplicate_names"] == ["Anjali Rao"] and len(gold("T71")["final_state"]["expected_bookings"]) == 2


def test_t72_excluded_train_is_first_and_bookable():
    tr = call(fresh(), "search_trains", source="HWH", destination="NDLS", date="2026-10-09")["data"]["trains"]
    assert tr[0]["train_id"] == "BTB110" and call(fresh(), "book_ticket", train_id="BTB110", travel_class="3A", passenger="Arjun Sen")["ok"]
    assert gold("T72")["prohibited_actions"][0]["match"] == {"train_id": "BTB110"}


def test_t74_typo_is_invalid_and_the_lookalike_would_book():
    e = fresh()
    assert call(e, "get_train_details", train_id="BTB1O3")["error"]["code"] == "INVALID_TRAIN"
    assert call(e, "book_ticket", train_id="BTB103", travel_class="2A", passenger="Ravi Shankar")["ok"]
    assert all("BTB1O3" in query("T74", l) for l in LANGS)


def test_t73_and_t75_recovery_paths():
    assert gold("T73")["final_answer"]["selected_train_id"] == "BTB103" and gold("T73")["final_answer"]["requested_status"] == "SOLD_OUT"
    e = fresh()
    assert call(e, "book_ticket", train_id="BTB105", travel_class="SL", passenger="Sonal Bhatia")["error"]["code"] == "CLASS_NOT_OFFERED"
    assert gold("T75")["final_state"]["travel_class"] == "CC" and gold("T11")["final_state"]["status"] == "cannot_complete"


def test_solver_guards_refuse_trivialised_variants():
    cases = [("T61", {"max_total_fare_inr": 2000}, "TOTAL"),           # total fits: nothing to test
             ("T64", {"max_fare_exclusive_inr": 4000}, "over budget"),  # earliest train no longer excluded
             ("T70", {"min_seats": 1}, "below the threshold"),          # threshold met
             ("T57", {"travel_class": "3A"}, "one day off"),            # 3A: daily BTB102 is always last, the day would not matter
             ("T62", {"departure_time": "06:00"}, "class"),             # BTB115 has no CC
             ("T73", {"train_id": "BTB103"}, "sold out")]
    for tid, change, msg in cases:
        s = copy.deepcopy(spec(tid))
        s.solver.params.update(change)
        with pytest.raises(ValueError, match=msg):
            build_task_gold(s)


# ------------------------------------------------------------------ global duplicates
def test_no_semantic_duplicates_across_t01_t75():
    specs = {s.semantic_task_id: s for s in load_specs()}
    assert so.overlap_errors(specs, json.loads(GOLD_PATH.read_text(encoding="utf-8"))) == []
    assert len({s.solver.kind for s in specs.values()}) == 75
    res = so.analyse(specs, json.loads(GOLD_PATH.read_text(encoding="utf-8")))
    assert res["pairs"][0][0] < so.MAX_JACCARD


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
            assert sum(v is True for v in res.values()) >= 3, (t, l)
            assert res["route_preserved"] is True, (t, l)


def test_marathi_variants_use_case_endings_on_station_names():
    """Group A design: Marathi attaches the ablative to the source name (मुंबईहून, पुण्याहून, कोलकात्याहून ...)."""
    for t in ("T51", "T52", "T53", "T55", "T56"):
        assert "हून" in query(t, "mr"), t


# ---- negative tests (language drift in the new language-feature tasks)
def test_detects_t54_name_romanised_in_hindi(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hi", "T54", lambda r: r.update(query=r["query"].replace("रवि पटेल", "Ravi Patel")))
    assert "T54_hi: surface check passenger_preserved FAILED" in e and "T54_hi: declared native-script passenger form missing" in e


def test_detects_t62_spoken_time_turned_into_digits(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "mr", "T62", lambda r: r.update(query=r["query"].replace("सव्वा सात", "7:15")))
    assert "T62: numbers differ across variants" in e and "T62_mr: surface check time_preserved FAILED" in e


def test_detects_t64_amount_turned_into_digits(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hinglish", "T64", lambda r: r.update(query=r["query"].replace("dhai hazaar rupaye", "₹2,500")))
    assert "T64: numbers differ across variants" in e and "T64_hinglish: surface check fare_constraint_preserved FAILED" in e


def test_detects_t57_relative_day_made_explicit(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hi", "T57", lambda r: r.update(query=r["query"].replace("परसों", "7 अक्टूबर 2026 को")))
    assert "T57_hi: surface check intent_preserved FAILED" in e


def test_detects_t69_second_station_name_dropped(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "mr", "T69", lambda r: r.update(query=r["query"].replace("हावड्याहून ", "")))
    assert "T69_mr: surface check route_preserved FAILED" in e


def test_detects_t71_duplicate_removed(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hinglish", "T71", lambda r: r.update(query=r["query"].replace(", Anjali Rao.", ".")))
    assert "T71_hinglish: surface check intent_preserved FAILED" in e


def test_detects_t72_negation_lost(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hi", "T72", lambda r: r.update(query=r["query"].replace("BTB110 को छोड़कर किसी भी ट्रेन में", "ट्रेन BTB110 में")))
    assert "T72_hi: surface check forbidden_action_preserved FAILED" in e


def test_detects_t74_typo_corrected_and_t67_date_fixed(tmp_path, monkeypatch):
    assert "T74_mr: surface check intent_preserved FAILED" in mutate(tmp_path, monkeypatch, "mr", "T74", lambda r: r.update(query=r["query"].replace("BTB1O3", "BTB103")))
    assert "T67_hi: surface check intent_preserved FAILED" in mutate(tmp_path, monkeypatch, "hi", "T67", lambda r: r.update(query=r["query"].replace("31 नवंबर", "30 नवंबर")))


def test_detects_t59_retraction_dropped_and_frozen_t26_t50_row(tmp_path, monkeypatch):
    e = mutate(tmp_path, monkeypatch, "hinglish", "T59", lambda r: r.update(query=r["query"].split(" — ")[0]))
    assert "T59_hinglish: surface check forbidden_action_preserved FAILED" in e
    assert "hi.jsonl rows T01-T50 changed (frozen)" in mutate(tmp_path, monkeypatch, "hi", "T40", lambda r: r.update(tags=r["tags"] + ["x"]))


# ---- negative test (oracle): a wrong solver whose gold is regenerated CONSISTENTLY must still be caught
def test_independent_oracle_catches_a_wrong_solver(tmp_path, monkeypatch):
    real = bg.SOLVERS["earliest_arrival_after_time"]

    def wrong(env, p, plan):  # picks the earliest DEPARTURE instead of the earliest arrival
        ans, allowed, eff = real(env, p, plan)
        return {**ans, "selected_train_id": "BTB108", "arrival": "09:00"}, ["BTB108"], eff
    monkeypatch.setitem(bg.SOLVERS, "earliest_arrival_after_time", wrong)
    f = tmp_path / "gold_labels.json"
    f.write_text(render(build_all()), encoding="utf-8")
    monkeypatch.setattr(vt, "GOLD_PATH", f)
    monkeypatch.setattr(vt, "build_all", build_all)
    e = " | ".join(vt.validate())
    assert "T52: oracle train {'BTB102'} != gold" in e and "T52: oracle arrival='06:45' != gold '09:00'" in e


# ------------------------------------------------------------------ scorer on the new traps
def test_scorer_t54_failed_native_attempt_then_latin_booking_passes_but_wrong_spelling_fails():
    c = gold_calls("T54")
    assert run("T54", [("book_ticket", {"train_id": "BTB126", "travel_class": "CC", "passenger": "रवि पटेल"})] + c)["task_success"]
    bad = [x if x[0] != "book_ticket" else ("book_ticket", {**x[1], "passenger": "Ravee Patel"}) for x in c]
    s = run("T54", bad)
    assert not s["task_success"] and "state:bookings_mismatch" in s["failure_labels"]


def test_scorer_t59_and_t72_prohibitions():
    s = run("T59", gold_calls("T59") + [("book_ticket", {"train_id": "BTB118", "travel_class": "CC", "passenger": "Ritu Chawla"})])
    assert not s["task_success"] and any(l.startswith("process:prohibited_action:book_ticket") for l in s["failure_labels"])
    c = [x if x[0] != "book_ticket" else ("book_ticket", {**x[1], "train_id": "BTB110"}) for x in gold_calls("T72")]
    s = run("T72", c, selected_train="BTB110")
    assert not s["task_success"] and any("prohibited_action" in l for l in s["failure_labels"])


def test_scorer_t71_harmless_duplicate_attempt_and_t73_sold_out_booking_equivalence():
    c = gold_calls("T71") + [("book_ticket", {"train_id": "BTB115", "travel_class": "3A", "passenger": "Anjali Rao"})]
    assert run("T71", c)["task_success"]
    c = [("book_ticket", {"train_id": "BTB101", "travel_class": "2A", "passenger": "Varun Bhatt"})] + gold_calls("T73")[1:]
    s = run("T73", c)
    assert s["task_success"] and s["satisfied_via_equivalent_observation"] == ["c1"]


def test_scorer_t56_requires_every_listed_train_and_time():
    traj, snap = execute(gold_calls("T56"))
    obj = final_json("T56", snap)
    row = {"task_id": "T56_en", "semantic_task_id": "T56", "language": "en", "status": "completed", "trajectory": traj, "state_snapshot": snap,
           "final_text": final_text("T56", obj, natural="BTB127 at 18:15 and BTB116 at 18:25.")}
    s = score(row, gold_for("T56"), snap)
    assert not s["task_success"] and any(l.startswith("value:selected_train_ids") for l in s["failure_labels"])
    row["final_text"] = final_text("T56", obj, natural="BTB127 (18:15, to Nagpur), BTB116 (6:25 PM) and BTB124 (8:20 PM), both to Mumbai.")
    assert score(row, gold_for("T56"), snap)["task_success"]


def test_scorer_t75_offered_class_seen_in_search_is_equivalent():
    c = [("search_trains", {"source": "NDLS", "destination": "JP", "date": "2026-10-09"}),
         ("book_ticket", {"train_id": "BTB105", "travel_class": "CC", "passenger": "Sonal Bhatia"})]
    s = run("T75", c)
    assert s["task_success"] and s["satisfied_via_equivalent_observation"] == ["c2"]


def test_run_pilot_splits():
    from evaluation import run_pilot as rp
    assert rp.task_ids("midsem") == [f"T{i:02d}" for i in range(1, 51)] and rp.task_ids("full") == vt.ALL_IDS and len(rp.task_ids("pilot")) == 5


# ---- T71: a clarifying question (no booking) is an accepted alternative outcome
def test_t71_clarification_without_booking_is_accepted_but_not_with_a_booking():
    from evaluation.scorer import ALTERNATIVE_OUTCOMES
    assert "accepted_alternative_outcomes" in spec("T71").final_answer_requirements and set(ALTERNATIVE_OUTCOMES) == {"T71"}
    s = run("T71", [], status="needs_clarification", selected_train=None, selected_class=None, requested_passengers=[])
    assert s["task_success"] and s["accepted_via_alternative_outcome"] == "needs_clarification"
    one = [("book_ticket", {"train_id": "BTB115", "travel_class": "3A", "passenger": "Sunil Rao"})]
    s = run("T71", one, status="needs_clarification", selected_train=None, selected_class=None)
    assert not s["task_success"]  # asking AND booking is neither outcome
    assert run("T71", gold_calls("T71"))["task_success"]  # the main outcome still passes, without the alternative flag
    assert "accepted_via_alternative_outcome" not in run("T71", gold_calls("T71"))
    assert not run("T71", [], status="cannot_complete", selected_train=None, selected_class=None)["task_success"]


def test_alternative_outcome_applies_only_to_t71():
    s = run("T70", [("check_availability", {"train_id": "BTB104", "travel_class": "SL"})], status="needs_clarification", selected_train=None)
    assert not s["task_success"]
