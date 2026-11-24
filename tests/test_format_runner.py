"""Runner integration of the format tolerance (shared by every adapter): text tool calls, argument formats, extra keys, final text rule,
recording of every recovery, and the tool-call invariant over all 75 tasks x 5 languages (format change -> same environment effect;
format change + wrong value -> still an error)."""
import json

import pytest

from agents.base import ToolCall
from environment import RailwayEnv
from evaluation.final_answer import CLOSE, OPEN
from evaluation.runner import RunnerConfig, execute_tool_call, run_item
from evaluation.scorer import score_both
from evaluation.selfcheck import gold_calls, gold_for, ideal_result
from test_eval_runner import FARE_CALL, FINAL, ITEM, Scripted, cfg, turn

TASKS = sorted(k for k in json.load(open("benchmark/gold_labels.json", encoding="utf-8")) if not k.startswith("_"))
LANGS = ["en", "hinglish", "hi", "mr", "gu"]
ALLOWED = ITEM["allowed_tools"]
FARE_TEXT = '{"name":"get_fare","parameters":{"train_id":"BTB103","travel_class":"2A"}}'


class Recovering(Scripted):
    SUPPORTS_TEXT_TOOL_RECOVERY = True

    def __init__(self, script, log):
        super().__init__(script, log)
        self.attached = []

    def attach_recovered_tool_calls(self, calls):
        self.attached.append([c.id for c in calls])


def make(script, cls=Recovering):
    holder = {}

    def factory():
        holder["a"] = cls(script, holder.setdefault("log", []))
        return holder["a"]
    factory.holder = holder
    return factory


def run(script, cls=Recovering):
    f = make(script, cls)
    row = run_item(ITEM, f, RailwayEnv(), cfg(), run_name="t")
    lenient, strict = score_both(row, gold_for("T01"), row["state_snapshot"])
    return row, lenient, strict, f.holder["a"]


def rules(row):
    return [r["rule"] for r in row["format_recoveries"]]


# ------------------------------------------------------------------------------------------------ text tool calls
def test_text_tool_call_is_executed_recorded_and_the_run_continues():
    row, lenient, strict, adapter = run([turn(text=FARE_TEXT), turn(text=FINAL)])
    assert row["status"] == "completed" and row["lenient_used"] and rules(row)[0] == "text_tool_call"
    ev = [e for e in row["trajectory"] if e["event"] == "tool_call"]
    assert len(ev) == 1 and ev[0]["tool"] == "get_fare" and ev[0]["tool_call_id"] == "recovered-1-1" and ev[0]["observation"]["ok"]
    assert adapter.attached == [["recovered-1-1"]]
    assert any(e["type"] == "format_recovery" and e["rule"] == "text_tool_call" for e in row["raw_log"])
    assert lenient["task_success"] is True and lenient["lenient_used"] is True
    assert strict["task_success"] is False and strict["strict_lower_bound"] and strict["failure_labels"] == ["strict:recovery_used:text_tool_call"]


def test_llama_style_text_calls_with_missing_brace_and_several_objects():
    text = ('{"name":"resolve_station","parameters":{"name":"Mumbai"}; {"name":"resolve_station","parameters":{"name":"Pune"}')
    row, *_ = run([turn(text=text), turn(text=FINAL)])
    calls = [e for e in row["trajectory"] if e["event"] == "tool_call"]
    assert [c["tool"] for c in calls] == ["resolve_station", "resolve_station"] and all(c["observation"]["ok"] for c in calls)
    assert "closing_braces_appended" in rules(row)


@pytest.mark.parametrize("text", ["I will call " + FARE_TEXT, FARE_TEXT + " and then I answer", '{"name":"get_fares","parameters":{}}',
                                  '{"name":"get-fare","parameters":{"train_id":"BTB103","travel_class":"2A"}}'])
def test_text_with_prose_or_wrong_tool_name_is_not_a_tool_call(text):
    row, *_ = run([turn(text=text)])
    assert row["status"] == "completed" and row["trajectory"] == [] and row["format_recoveries"] == [] and row["turns"] == 1


def test_adapter_without_the_capability_gets_no_text_recovery():
    row, *_ = run([turn(text=FARE_TEXT)], cls=Scripted)
    assert row["trajectory"] == [] and row["format_recoveries"] == []


# ------------------------------------------------------------------------------------------------ arguments
def test_argument_formats_are_normalised_recorded_and_the_original_is_kept():
    call = ToolCall(id="c1", name="Functions.Get_Fare".replace("Functions.", "functions."), arguments={"train_id": "btb 103", "travel_class": "2AC"})
    row, lenient, strict, _ = run([turn(calls=[call]), turn(text=FINAL)])
    ev = row["trajectory"][0]
    assert ev["observation"]["ok"] and ev["arguments"] == {"train_id": "BTB103", "travel_class": "2A"}
    assert ev["arguments_original"] == {"train_id": "btb 103", "travel_class": "2AC"} and ev["tool"] == "get_fare"
    assert set(rules(row)) == {"tool_name_spelling", "train_id_spelling", "class_spelling"}
    tool_req = [e for e in row["raw_log"] if e["type"] == "tool_request"][0]
    assert tool_req["arguments_original"]["train_id"] == "btb 103"
    assert lenient["task_success"] is True and strict["task_success"] is False


def test_wrong_values_are_never_repaired():
    for args in ({"train_id": "BTB1033", "travel_class": "2A"}, {"train_id": "RESERVED_BY_SEARCH", "travel_class": "2A"},
                 {"train_id": "BTB103", "travel_class": "AC"}, {"train_id": "BTB103", "travel_class": "1A"},
                 {"train_id": "BTB103", "travel_class_name": "2A"}):
        row, lenient, *_ = run([turn(calls=[ToolCall(id="c1", name="get_fare", arguments=args)]), turn(text=FINAL)])
        ev = row["trajectory"][0]
        assert ev["observation"]["ok"] is False and ev["arguments"] == args and "format_recoveries" not in ev, args
        assert lenient["task_success"] is False and lenient["lenient_used"] is False


def test_extra_keys_dropped_only_when_required_keys_are_valid_and_it_is_recorded():
    row, lenient, *_ = run([turn(calls=[ToolCall(id="c1", name="get_fare", arguments={"train_id": "BTB103", "travel_class": "2A", "date": "2026-10-05"})]),
                            turn(text=FINAL)])
    ev = row["trajectory"][0]
    assert ev["observation"]["ok"] and ev["arguments"] == {"train_id": "BTB103", "travel_class": "2A"} and rules(row) == ["extra_args_dropped"]
    row, *_ = run([turn(calls=[ToolCall(id="c1", name="get_fare", arguments={"train_id": "BTB103", "date": "2026-10-05"})]), turn(text=FINAL)])
    assert row["trajectory"][0]["observation"]["ok"] is False and row["format_recoveries"] == []        # travel_class missing: strict error stands


def test_renamed_key_is_not_repaired():
    call = ToolCall(id="c1", name="book_ticket", arguments={"train_id": "BTB103", "travel_class": "3A", "passenger_name": "Nikhil Bose"})
    row, *_ = run([turn(calls=[call]), turn(text=FINAL)])
    ev = row["trajectory"][0]
    assert ev["observation"]["error"]["code"] == "INVALID_ARGUMENTS" and row["state_snapshot"]["bookings"] == [] and row["format_recoveries"] == []


def test_native_call_with_broken_argument_json_is_repaired_value_preservingly():
    call = ToolCall(id="c1", name="get_fare", arguments={}, raw_arguments='{"train_id": "BTB103", "travel_class": "2A"', parse_ok=False, parse_error="x")
    row, lenient, *_ = run([turn(calls=[call]), turn(text=FINAL)])
    assert row["trajectory"][0]["event"] == "tool_call" and row["trajectory"][0]["observation"]["ok"]
    assert rules(row)[0].startswith("args_json_repaired")
    call = ToolCall(id="c1", name="get_fare", arguments={}, raw_arguments="not json", parse_ok=False, parse_error="x")
    row, *_ = run([turn(calls=[call]), turn(text=FINAL)])
    assert row["trajectory"][0]["event"] == "malformed_tool_call" and row["format_recoveries"] == []


# ------------------------------------------------------------------------------------------------ final text rule (decision 4)
def test_text_of_a_tool_calling_turn_is_not_a_final_answer():
    row, lenient, *_ = run([turn(text=FINAL, calls=[FARE_CALL]), turn(text="")])
    assert row["final_text"] == "" and lenient["final_answer_parse"] == "missing_block" and lenient["task_success"] is False


def test_final_answer_in_the_last_turn_is_unchanged():
    row, lenient, strict, _ = run([turn(calls=[FARE_CALL]), turn(text=FINAL)])
    assert row["final_text"] == FINAL and row["format_recoveries"] == [] and row["lenient_used"] is False
    assert lenient["task_success"] and strict["task_success"] and "strict_lower_bound" not in strict


# ------------------------------------------------------------------------------------------------ row fields
def test_final_answer_stage_recoveries_are_recorded_and_strict_is_exact():
    text = f"The 2A fare on BTB103 is 3565.\n{OPEN}\n" + json.dumps({"status": "Success", "selected_train": "btb103", "selected_class": "2a",
                                                                       "booking_ids": None, "requested_passengers": None})
    row, lenient, strict, _ = run([turn(calls=[FARE_CALL]), turn(text=text)])
    assert row["final_answer"]["ok"] is False and row["final_answer_lenient"]["ok"] is True and row["lenient_used"] is True
    assert lenient["task_success"] is True and strict["task_success"] is False and "strict_lower_bound" not in strict
    got = {r["rule"] for r in lenient["format_recoveries"]}
    assert {"closing_tag_missing", "status_spelling", "booking_ids_shape", "requested_passengers_shape", "notes_defaulted"} <= got


def test_recoveries_belong_to_the_final_attempt_only():
    from agents.base import ProviderError
    f = make([turn(text=FARE_TEXT), ProviderError("rate_limit", "429", retryable=True, status_code=429)])
    scripts = [[turn(text=FARE_TEXT), ProviderError("rate_limit", "429", retryable=True, status_code=429)], [turn(calls=[FARE_CALL]), turn(text=FINAL)]]
    seq = list(scripts)
    log = []
    row = run_item(ITEM, lambda: Recovering(seq.pop(0), log), RailwayEnv(), cfg(), run_name="t")
    assert row["attempts"] == 2 and row["status"] == "completed" and row["format_recoveries"] == []


# ------------------------------------------------------------------------------------------------ invariant: tool calls, 75 tasks x 5 languages
DIG = {"hi": "०१२३४५६७८९", "mr": "०१२३४५६७८९", "gu": "૦૧૨૩૪૫૬૭૮૯"}


def sd(s, lang):
    return s.translate(str.maketrans("0123456789", DIG[lang])) if lang in DIG else s


def perturb(tool, args, lang, i):
    """A FORMAT variant of a correct call (same meaning)."""
    a = json.loads(json.dumps(args))
    name = [tool, f"functions.{tool}", tool.upper(), f"{tool}()", f" {tool} "][i % 5]
    if "train_id" in a:
        a["train_id"] = [sd(a["train_id"], lang), a["train_id"].lower(), a["train_id"][:3] + " " + a["train_id"][3:], a["train_id"][:3] + "-" + a["train_id"][3:], a["train_id"]][i % 5]
    if a.get("travel_class") in ("3A", "2A", "SL", "CC"):
        a["travel_class"] = {"3A": ["3AC", "AC3", "3a", "3 A", "3A"], "2A": ["2AC", "AC 2 Tier", "2a", "2 A", "2A"], "SL": ["Sleeper", "sl", "SL", " sl ", "SL"],
                             "CC": ["Chair Car", "cc", "CC", "chair car", "CC"]}[a["travel_class"]][i % 5]
    if "date" in a:
        y, m, d = a["date"].split("-")
        a["date"] = [sd(a["date"], lang), f"{y}-{int(m)}-{int(d)}", f"{y}/{m}/{d}", f"{y}.{m}.{d}", a["date"]][i % 5]
    if isinstance(a.get("time_window"), dict):
        tw = a["time_window"]
        a["time_window"] = [json.dumps({"start": tw["start"] + ":00", "end": tw["end"] + ":59"}), {"start": f"{int(tw['start'][:2])}{tw['start'][2:]}", "end": tw["end"]},
                            {"start": sd(tw["start"], lang), "end": sd(tw["end"], lang)}, tw, json.dumps(tw)][i % 5]
    if "passenger" in a:
        a["passenger"] = [a["passenger"] + ".", a["passenger"], a["passenger"].replace(" ", "  "), a["passenger"] + " ,", a["passenger"]][i % 5]
    if i % 2 == 0 and tool in ("get_train_details", "get_fare", "check_availability"):
        a["date"] = "2026-10-05"            # an unknown extra key on a call whose required keys are valid
    return name, a


def replay(tid, make_call):
    env = RailwayEnv()
    env.reset()
    recs, obs_ok, effects = [], [], []
    for n, (tool, args) in enumerate(gold_calls(tid), 1):
        name, a = make_call(tool, args)
        call = ToolCall(id=f"c{n}", name=name, arguments=a)
        if tool == "resolve_station":
            env_name = env.state.stations[args["name"]["resolves_to"]].name if isinstance(args.get("name"), dict) else args["name"]
        obs, ev = execute_tool_call(env, call, ALLOWED, n, [], 1, recs)
        obs_ok.append(obs["ok"])
    return env.snapshot(), obs_ok, recs


@pytest.mark.parametrize("tid", TASKS)
def test_tool_call_format_changes_have_the_same_effect_in_every_language(tid):
    base_snap, base_ok, _ = replay(tid, lambda t, a: (t, a))
    for lang in LANGS:
        for i in range(5):
            snap, ok, recs = replay(tid, lambda t, a: perturb(t, a, lang, i))
            assert snap == base_snap and ok == base_ok, (tid, lang, i)
            assert all(r["stage"] in ("arguments", "tool_call") and r["rule"] for r in recs)


WRONG = [
    ("wrong train", lambda t, a: (t, {**a, "train_id": "BTB1033"}) if "train_id" in a else None),
    ("placeholder train", lambda t, a: (t, {**a, "train_id": "<train_id_from_search>"}) if "train_id" in a else None),
    ("class AC", lambda t, a: (t, {**a, "travel_class": "AC"}) if "travel_class" in a else None),
    ("renamed passenger key", lambda t, a: (t, {k if k != "passenger" else "passenger_name": v for k, v in a.items()}) if "passenger" in a else None),
    ("ambiguous date", lambda t, a: (t, {**a, "date": "09-10-2026"}) if "date" in a else None),
    ("unknown tool", lambda t, a: ("get_fares", a)),
]


@pytest.mark.parametrize("tid", TASKS)
def test_tool_call_format_change_plus_wrong_value_is_still_an_error(tid):
    for label, wrong in WRONG:
        for lang in LANGS:
            env = RailwayEnv()
            env.reset()
            hit = False
            for n, (tool, args) in enumerate(gold_calls(tid), 1):
                w = wrong(tool, args)
                if w is None:
                    continue
                name, a = w
                name, a = perturb(name if name in ALLOWED else tool, a, lang, 1)     # + a format variant
                if label == "unknown tool":
                    name = "get_fares"
                recs: list = []
                obs, _ = execute_tool_call(env, ToolCall(id=f"c{n}", name=name, arguments=a), ALLOWED, n, [], 1, recs)
                assert obs["ok"] is False, (tid, label, lang, tool, a)
                hit = True
                break
            if label == "unknown tool" and gold_calls(tid):
                assert hit
