"""Pilot-task tests (T01-T05): gold is programmatic, deterministic, unique and replayable."""
import json
import shutil
from pathlib import Path

import pytest

from benchmark import validate_tasks as vt
from benchmark.build_gold import GOLD_PATH, build_all, render
from environment import RailwayEnv

ROOT = Path(__file__).resolve().parent.parent
PILOT = ["T01", "T02", "T03", "T04", "T05"]


def test_validator_passes_on_committed_pilot_tasks():
    assert vt.validate() == []


def test_gold_regeneration_is_byte_identical_and_matches_committed_file():
    assert render(build_all()) == render(build_all()) == GOLD_PATH.read_text(encoding="utf-8")


def test_pilot_english_tasks_lead_the_four_language_set():
    # (was: exactly five tasks) the batch T06-T15 now follows the unchanged pilot rows
    assert sorted(p.name for p in vt.LANG_DIR.glob("*.jsonl")) == ["en.jsonl", "gu.jsonl", "hi.jsonl", "hinglish.jsonl", "mr.jsonl"]  # gu: T01-T50 so far
    rows = [json.loads(l) for l in (vt.LANG_DIR / "en.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["semantic_task_id"] for r in rows] == vt.ALL_IDS
    assert [r["category"] for r in rows[:5]] == ["single_tool", "sequential", "constraint", "booking", "recovery"]
    assert all(r["review_status"] == "draft" for r in rows)  # nothing is "accepted" without human review


def test_gold_has_no_language_key_and_no_llm_dependency():
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    assert "language" not in json.dumps(gold)
    for path in list((ROOT / "environment").glob("*.py")) + list((ROOT / "benchmark").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert not any(w in text for w in ("import openai", "import groq", "google.genai", "import anthropic")), path


def test_gold_dependency_edges_and_min_calls():
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    edges = {t: {(e["before"], e["after"]) for e in gold[t]["dependency_edges"]} for t in PILOT}
    assert edges["T01"] == set() and gold["T01"]["min_calls"] == 1
    assert edges["T02"] == {("c1", "c3"), ("c2", "c3"), ("c3", "c4"), ("c3", "c5")}
    assert ("c4", "c5") not in edges["T02"] and ("c5", "c4") not in edges["T02"]  # independent leaves: any order
    assert ("c4", "c6") in edges["T04"] and ("c5", "c6") in edges["T04"]  # booking needs the fare comparison
    assert edges["T05"] == set() and gold["T05"]["min_calls"] == 1


def test_t04_replay_mutates_state_exactly_once():
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))["T04"]
    env = RailwayEnv()
    env.reset()
    base = env.state_hash()
    book = [c for c in gold["required_calls"] if c["tool"] == "book_ticket"]
    assert len(book) == 1
    r = env.call("book_ticket", book[0]["required_args"])
    assert r["ok"] and r["data"]["booking_id"] == gold["final_answer"]["booking_id"]
    assert env.state_hash() != base
    assert gold["expected_env_diff"]["availability_changes"] == {"BTB123|SL": [41, 40]}
    env.reset()
    assert env.state_hash() == base


def test_read_only_tasks_leave_state_unchanged_and_t05_is_a_true_sold_out():
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    for t in ("T01", "T02", "T03", "T05"):
        assert gold[t]["expected_env_diff"] == {"bookings": [], "availability_changes": {}}
        assert gold[t]["final_state"]["expected_bookings"] == []
    env = RailwayEnv()
    env.reset()
    assert env.call("check_availability", {"train_id": "BTB103", "travel_class": "3A"})["data"]["status"] == "SOLD_OUT"
    h = env.state_hash()
    assert env.call("book_ticket", {"train_id": "BTB103", "travel_class": "3A", "passenger": "Vikram Singh"})["error"]["code"] == "SOLD_OUT"
    assert env.state_hash() == h  # even an (incorrect) booking attempt cannot change state


def test_t03_wording_matches_inclusive_gold_constraint():
    rows = {json.loads(l)["semantic_task_id"]: json.loads(l) for l in (vt.LANG_DIR / "en.jsonl").read_text(encoding="utf-8").splitlines()}
    assert rows["T03"]["query"] == ("I need a 3A ticket from Jaipur to Ahmedabad on 8 October 2026. I want to leave at or after 6 PM, "
                                    "pay no more than \u20b93,000, and have seats available. Which train fits? Don't book anything, just tell me the train.")
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))["T03"]
    assert gold["required_calls"][2]["required_args"]["time_window"] == {"start": "18:00", "end": "23:59"}
    assert gold["final_answer"]["selected_train_id"] == "BTB107"  # answer unchanged
    note = next(s for s in vt.load_specs() if s.semantic_task_id == "T03").playbook_note
    assert "Every constraint prunes" not in note and "excludes an over-budget candidate" in note


def test_t03_boundary_semantics_on_real_fixture():
    """'at or after 18:00' is inclusive in the environment's own window semantics (>= start)."""
    env = RailwayEnv()
    env.reset()
    dep = env.call("search_trains", {"source": "JP", "destination": "ADI", "date": "2026-10-08"})["data"]["trains"]
    t = next(x for x in dep if x["train_id"] == "BTB101")["departure"]  # 20:20
    inc = env.call("search_trains", {"source": "JP", "destination": "ADI", "date": "2026-10-08", "time_window": {"start": t, "end": "23:59"}})
    assert "BTB101" in [x["train_id"] for x in inc["data"]["trains"]]  # a train departing exactly at `start` is included


def test_prohibited_actions_are_machine_readable_and_only_where_the_user_forbids():
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    for t in ("T01", "T02", "T04"):
        assert gold[t]["forbidden_tools"] == [] and gold[t]["prohibited_actions"] == []
    assert gold["T03"]["forbidden_tools"] == ["book_ticket"] and gold["T05"]["forbidden_tools"] == ["book_ticket"]
    assert [a["prompt_phrase"] for a in gold["T03"]["prohibited_actions"]] == ["Don't book anything"]
    assert {a["prompt_phrase"] for a in gold["T05"]["prohibited_actions"]} == {"only if seats are available", "don't book any other class or train"}
    # the prohibited tool never appears in that task's own gold solution; T04 (which books) has no prohibition
    for t in ("T03", "T05"):
        assert all(c["tool"] != "book_ticket" for c in gold[t]["required_calls"])
    assert any(c["tool"] == "book_ticket" for c in gold["T04"]["required_calls"])
    # extra harmless read-only calls are NOT prohibited anywhere
    for t in PILOT:
        assert not {"resolve_station", "search_trains", "get_train_details", "check_availability", "get_fare"} & set(gold[t]["forbidden_tools"])


def test_validator_detects_prohibition_that_contradicts_gold_or_prompt(monkeypatch):
    specs = vt.load_specs()
    t04 = next(s for s in specs if s.semantic_task_id == "T04")
    t04.prohibited_actions = [vt.GoldSpec.model_fields["prohibited_actions"].annotation.__args__[0](
        tool="book_ticket", prompt_phrase="not in the prompt", reason="x")]
    monkeypatch.setattr(vt, "load_specs", lambda: specs)
    errors = " | ".join(vt.validate())
    assert "prompt_phrase" in errors and "violates prohibition" in errors


# ---- the validator must actually catch problems (negative tests) ----
def test_validator_detects_hand_edited_gold(tmp_path, monkeypatch):
    bad = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    bad["T03"]["final_answer"]["fare_inr"] = 999
    f = tmp_path / "gold_labels.json"
    f.write_text(render(bad), encoding="utf-8")
    monkeypatch.setattr(vt, "GOLD_PATH", f)
    assert any("hand-edited or stale" in e for e in vt.validate())


def test_validator_detects_bad_prompt_and_changed_english(tmp_path, monkeypatch):
    langs = tmp_path / "languages"
    shutil.copytree(vt.LANG_DIR, langs)
    rows = [json.loads(l) for l in (langs / "en.jsonl").read_text(encoding="utf-8").splitlines()]
    rows[0]["query"] = "What is the fare for 2A class on train BTB999?"       # non-existent train
    rows[1]["query"] = "Is there a 3A seat from Nagpur to Pune tomorrow?"      # no explicit date
    (langs / "en.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(vt, "LANG_DIR", langs)
    errors = " | ".join(vt.validate())
    assert "unknown train BTB999" in errors and "no explicit date" in errors and "English query changed" in errors


@pytest.mark.parametrize("kind", ["fare_lookup", "route_availability_fare", "constrained_choice", "cheapest_booking", "conditional_booking"])
def test_every_solver_kind_is_used_by_a_pilot_task(kind):
    assert kind in {s.solver.kind for s in vt.load_specs()}
