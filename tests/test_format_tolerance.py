"""Unit tests of evaluation/tolerance.py: every rule, a counter-example per rule that must NOT be recovered, per language
where a rule is language-sensitive. (End-to-end scoring/invariant tests: tests/test_format_invariants.py.)"""
import json

import pytest

from evaluation import tolerance as T
from evaluation.final_answer import parse_final_answer

OPEN, CLOSE = "<FINAL_ANSWER_JSON>", "</FINAL_ANSWER_JSON>"
BASE = {"status": "success", "selected_train": "BTB103", "selected_class": "3A", "booking_ids": [], "requested_passengers": [], "notes": "x"}


def J(**kw):
    return json.dumps({**BASE, **kw}, ensure_ascii=False)


def parse(text):
    return T.parse_final_answer_lenient(text)


def rules(r):
    return [x["rule"] for x in r["recoveries"]]


# ------------------------------------------------------------------------------------------------ wrapper (F-01..F-06)
@pytest.mark.parametrize("text,rule", [
    (f"reply\n{OPEN}\n{J()}", "closing_tag_missing"),
    (f"reply\n{OPEN}\n{J()}\nHope this helps!", "closing_tag_missing"),
    (f"<final_answer_json>{J()}</final_answer_json>", "tag_variant"),
    (f"< FINAL_ANSWER_JSON >{J()}</ FINAL_ANSWER_JSON >", "tag_variant"),
    (J(), "untagged_json"),
    (f"Here you go:\n```json\n{J()}\n```", "untagged_json"),
    (f"{OPEN}{json.dumps({'answer': json.loads(J())})}{CLOSE}", "wrapper_object_unwrapped"),
    (f"{OPEN}{J()}}}{CLOSE}", "trailing_text_ignored"),
    (f"<think>planning {OPEN}{J(status='cannot_complete')}{CLOSE}</think>\n{OPEN}{J()}{CLOSE}", "think_stripped"),
])
def test_wrapper_rules_recover_and_record(text, rule):
    r = parse(text)
    assert r["ok"] is True and rule in rules(r) and r["answer"]["selected_train"] == "BTB103"
    assert parse_final_answer(text)["ok"] is False or rule == "think_stripped" or rule == "closing_tag_missing" and False


def test_the_strict_parser_is_untouched_for_exact_blocks():
    text = f"x\n{OPEN}\n{J()}\n{CLOSE}"
    r = parse(text)
    assert r["ok"] and r["recoveries"] == [] and parse_final_answer(text)["ok"]


@pytest.mark.parametrize("text", [
    f"<think>{OPEN}{J()}{CLOSE}</think>",                                    # a draft inside thinking is not an answer
    "The fare is 3565.",                                                     # prose only: never extracted
    f"{OPEN}{J(status='success | cannot_complete | needs_clarification')}{CLOSE}",   # echoed template
    f"{OPEN}{J(status='needs_clarity')}{CLOSE}",                              # a typo is a guess
    f"{OPEN}{J(status='maybe')}{CLOSE}",
    json.dumps({"status": "success"}),                                       # untagged JSON without the contract keys
])
def test_not_recovered(text):
    assert parse(text)["ok"] is False


# ------------------------------------------------------------------------------------------------ JSON syntax (F-05, F-07, F-08)
def test_json_repairs():
    for text, rule in ((f"{OPEN}{J()[:-1]},}}{CLOSE}", "trailing_comma_removed"),
                       (f"{OPEN}" + J().replace('"', "'") + f"{CLOSE}", "python_literal"),
                       (f"{OPEN}{J()[:-1]}{CLOSE}", "closing_braces_appended")):
        r = parse(text)
        assert r["ok"] and rule in rules(r), (text, r["error"])
    r = parse(f"{OPEN}" + J(booking_ids=None, notes=None).replace("null", "None").replace('"', "'") + f"{CLOSE}")
    assert r["ok"] and r["answer"]["booking_ids"] == []


def test_json_repair_never_evaluates_code():
    r = parse(f"{OPEN}{{'status': __import__('os').getcwd(), 'selected_train': 1}}{CLOSE}")
    assert r["ok"] is False


def test_notes_defaulted_but_decision_keys_are_not():
    d = dict(BASE)
    d.pop("notes")
    r = parse(f"{OPEN}{json.dumps(d)}{CLOSE}")
    assert r["ok"] and r["answer"]["notes"] == "" and "notes_defaulted" in rules(r)
    for key in ("status", "selected_train", "selected_class", "booking_ids", "requested_passengers"):
        d = dict(BASE)
        d.pop(key)
        r = parse(f"{OPEN}{json.dumps(d)}{CLOSE}")
        assert r["ok"] is False and r["error"] == f"missing_keys:{key}"


# ------------------------------------------------------------------------------------------------ field values (F-09..F-14)
@pytest.mark.parametrize("status,expected", [("Success", "success"), (" success ", "success"), ("SUCCESS", "success"),
                                             ("needs clarification", "needs_clarification"), ("needs-clarification", "needs_clarification"),
                                             ("Cannot Complete.", "cannot_complete")])
def test_status_spelling(status, expected):
    r = parse(f"{OPEN}{J(status=status)}{CLOSE}")
    assert r["ok"] and r["answer"]["status"] == expected and "status_spelling" in rules(r)


@pytest.mark.parametrize("field,value,expected", [
    ("booking_ids", None, []), ("booking_ids", "BK0001", ["BK0001"]), ("booking_ids", "bk0001, BK0002", ["BK0001", "BK0002"]), ("booking_ids", "", []),
    ("requested_passengers", "Ananya Kulkarni", ["Ananya Kulkarni"]), ("requested_passengers", None, []),
    ("selected_train", "BTB103 (Saffron Arc)", "BTB103"), ("selected_train", "Train BTB103.", "BTB103"), ("selected_train", "btb 103", "BTB103"),
    ("selected_train", "BTB१०३", "BTB103"), ("selected_train", ["btb103", "BTB 104"], ["BTB103", "BTB104"]),
    ("selected_class", "3A (Third AC)", "3A"), ("selected_class", "3a class", "3A"), ("selected_class", "AC 2 Tier", "2A"),
])
def test_field_shapes(field, value, expected):
    r = parse(f"{OPEN}{J(**{field: value})}{CLOSE}")
    assert r["ok"] and r["answer"][field] == expected


@pytest.mark.parametrize("field,value", [
    ("selected_train", "BTB103 or BTB104"), ("selected_train", "BTB1033"), ("selected_train", "<train_id_from_search>"),
    ("selected_class", "3A or 2A"), ("selected_class", "AC"), ("selected_class", "1A"),
    ("booking_ids", "BK0001 and something else"), ("booking_ids", "Booking ID 1"),
])
def test_ambiguous_or_wrong_values_are_left_alone(field, value):
    r = parse(f"{OPEN}{J(**{field: value})}{CLOSE}")
    assert r["answer"][field] == value


def test_two_names_in_one_string_stay_one_element_and_do_not_become_two():
    r = parse(f"{OPEN}{J(requested_passengers='Priya Nair, Arjun Nair')}{CLOSE}")
    assert r["answer"]["requested_passengers"] == ["Priya Nair, Arjun Nair"]     # one (wrong) name: the scorer will not match two bookings


@pytest.mark.parametrize("key,value,expected", [
    ("seats_available", 0.0, 0), ("seats_available", "0 seats", 0), ("seats_available", "१७", 17), ("seats_available", "૧૭ સીટો", 17),
    ("seats_available", "17 सीटें", 17), ("train_count", "4 trains", 4), ("seats_remaining_at_end", 2.0, 2),
    ("duration_minutes", 445.0, 445), ("duration_minutes", "445 minutes", 445), ("duration_minutes", "445 મિનિટ", 445),
])
def test_integer_forms(key, value, expected):
    r = parse(f"{OPEN}{J(answer_values={key: value})}{CLOSE}")
    assert r["ok"] and r["answer"]["answer_values"][key] == expected


@pytest.mark.parametrize("key,value", [("seats_available", "about 17"), ("seats_available", 17.5), ("seats_available", "17 or 18"),
                                       ("duration_minutes", 7.25), ("duration_minutes", "7.25")])
def test_integer_forms_not_guessed(key, value):
    r = parse(f"{OPEN}{J(answer_values={key: value})}{CLOSE}")
    assert r["answer"]["answer_values"][key] == value


def test_key_spelling():
    obj = {"Status": "success", "Selected Train": "BTB103", "selected-class": "3A", "BOOKING_IDS": [], "Requested_Passengers": [], "NOTES": "",
           "Answer Values": {"Operating Days": ["TUE"]}}
    r = parse(f"{OPEN}{json.dumps(obj)}{CLOSE}")
    assert r["ok"] and r["answer"]["selected_train"] == "BTB103" and r["answer"]["answer_values"] == {"operating_days": ["TUE"]}
    assert "key_spelling" in rules(r)


# ------------------------------------------------------------------------------------------------ free-text readers (F-15..F-17, F-34)
@pytest.mark.parametrize("text,expected", [
    ("17:20:00", {"17:20"}), ("departs 17h20", {"17:20"}), ("17.20 hrs", {"17:20"}), ("१७:२०:००", {"17:20"}), ("17.20 बजे", {"17:20"}),
    ("૧૭.૨૦ વાગ્યે", {"17:20"}), ("17:20", {"17:20"}), ("5:20 PM", {"17:20"}),
])
def test_times_lenient(text, expected):
    assert T.times_in_lenient(text) == expected


@pytest.mark.parametrize("text", ["₹14.50", "14.50", "17:20:30", "fare 1.30", "<think>17:20</think> done"])
def test_times_lenient_does_not_invent_times(text):
    assert T.times_in_lenient(text) == set()


@pytest.mark.parametrize("text", [
    "10th October 2026", "October 10, 2026", "10-Oct-2026", "10.10.2026", "Oct 10", "10 October", "10 अक्टूबर", "१० अक्टूबर", "10 तारीख अक्टूबर",
    "10 ऑक्टोबर 2026", "१० ऑक्टोबर", "10 ઓક્ટોબર", "૧૦મી ઓક્ટોબર", "શનિવાર, 10 ઓક્ટોબર 2026",
])
def test_dates_lenient(text):
    assert T.dates_in_lenient(text) == {"2026-10-10"}


@pytest.mark.parametrize("text", ["10.09.2026", "10 September 2026", "9.10", "Oct", "<think>10 October</think>"])
def test_dates_lenient_not_invented(text):
    assert "2026-10-10" not in T.dates_in_lenient(text)


@pytest.mark.parametrize("text", ["Rs 3565/-", "₹3,565/-", "3565/- only", "३५६५/-", "૩૫૬૫/-"])
def test_numbers_lenient(text):
    assert 3565 in T.numbers_in_lenient(text)


@pytest.mark.parametrize("text", ["3.565", "3 565", "3565.50", "<think>3565</think> fare"])
def test_numbers_lenient_not_invented(text):
    assert 3565 not in T.numbers_in_lenient(text)


def test_zero_width_and_normalisation():
    assert T.clean_text("मंगळवार‍") == "मंगळवार" and T.digits_to_ascii("BTB१०३ ૧૦ ＢＴＢ１０３") == "BTB103 10 ＢＴＢ103"


# ------------------------------------------------------------------------------------------------ text tool calls (F-19, F-20, F-22)
def test_text_tool_calls_native_json_forms():
    one = '{"name":"get_fare","parameters":{"train_id":"BTB103","travel_class":"2A"}}'
    for text in (one, f"<tool_call>{one}</tool_call>", f"```json\n{one}\n```", one.replace("parameters", "arguments"),
                 json.dumps({"type": "function", "function": {"name": "get_fare", "arguments": json.dumps({"train_id": "BTB103", "travel_class": "2A"})}})):
        calls, recs = T.extract_text_tool_calls(text)
        assert calls and calls[0]["name"] == "get_fare" and calls[0]["arguments"] == {"train_id": "BTB103", "travel_class": "2A"}
        assert recs[0]["rule"] == "text_tool_call"


def test_text_tool_calls_llama_style_missing_brace_and_several_objects():
    text = ('{"name":"search_trains","parameters":{"source":"NDLS","destination":"JP","date":"2026-10-07","time_window":{"start":"09:00","end":"23:59"}}; '
            '{"name":"get_fare","parameters":{"train_id":"BTB105","travel_class":"CC"}}')
    calls, recs = T.extract_text_tool_calls(text)
    assert [c["name"] for c in calls] == ["search_trains", "get_fare"] and calls[0]["arguments"]["time_window"] == {"start": "09:00", "end": "23:59"}
    assert "closing_braces_appended" in [r["rule"] for r in recs]


@pytest.mark.parametrize("text", [
    'I will call {"name":"get_fare","parameters":{"train_id":"BTB103","travel_class":"2A"}}',      # prose around
    '{"name":"get_fares","parameters":{}}', '{"name":"get-fare","parameters":{}}', '{"name":"book","parameters":{}}',   # not an exact tool name
    '{"name":"get_fare","parameters":"BTB103"}', '{"name":"get_fare"}', '{"status":"success"}', "no json here", "",
    '{"name":"get_fare","parameters":{}} and then prose',
])
def test_text_tool_calls_not_recovered(text):
    assert T.extract_text_tool_calls(text) == (None, [])


@pytest.mark.parametrize("name,expected", [("Get_Fare", "get_fare"), ("functions.get_fare", "get_fare"), ("get_fare()", "get_fare"), (" get_fare ", "get_fare"),
                                           ("tools/get_fare", "get_fare")])
def test_tool_name_spelling(name, expected):
    assert T.normalize_tool_name(name)[0] == expected and T.normalize_tool_name(name)[1][0]["rule"] == "tool_name_spelling"


@pytest.mark.parametrize("name", ["get-fare", "getfare", "get_fares", "fare", "book", "search"])
def test_tool_name_never_fuzzy(name):
    assert T.normalize_tool_name(name) == (name, [])


# ------------------------------------------------------------------------------------------------ arguments (F-24..F-29, extra keys)
def test_argument_formats():
    args, recs = T.normalize_arguments("search_trains", {"source": "NDLS", "destination": "JP", "date": "२०२६-१०-९",
                                                         "time_window": '{"start": "9:00:00", "end": "23:59:59"}'})
    assert args == {"source": "NDLS", "destination": "JP", "date": "2026-10-09", "time_window": {"start": "09:00", "end": "23:59"}}
    assert {r["rule"] for r in recs} == {"args_json_string", "time_format", "date_format"}
    for tid in ("btb103", "BTB 103", "BTB-103", "BTB१०३", "BTB૧૦૩"):
        a, _ = T.normalize_arguments("get_fare", {"train_id": tid, "travel_class": "2A"})
        assert a["train_id"] == "BTB103", tid
    for cls, exp in (("3AC", "3A"), ("AC3", "3A"), ("Sleeper", "SL"), ("3 A", "3A"), ("३A", "3A"), ("AC 2 Tier", "2A"), ("chair car", "CC")):
        assert T.normalize_arguments("get_fare", {"train_id": "BTB103", "travel_class": cls})[0]["travel_class"] == exp, cls
    a, recs = T.normalize_arguments("book_ticket", {"train_id": "BTB103", "travel_class": "SL", "passenger": "Ananya  Kulkarni."})
    assert a["passenger"] == "Ananya Kulkarni" and recs[0]["rule"] == "passenger_punctuation"


@pytest.mark.parametrize("tool,args", [
    ("get_fare", {"train_id": "BTB1033", "travel_class": "2A"}), ("get_fare", {"train_id": "RESERVED_BY_SEARCH", "travel_class": "2A"}),
    ("get_fare", {"train_id": "<train_id_from_search>", "travel_class": "2A"}), ("get_fare", {"train_id": "BTB103", "travel_class": "AC"}),
    ("get_fare", {"train_id": "BTB103", "travel_class": "1A"}), ("search_trains", {"source": "Nagpur", "destination": "Pune", "date": "2026-10-07"}),
    ("search_trains", {"source": "NDLS", "destination": "JP", "date": "09-10-2026"}),                 # day/month ambiguity
    ("search_trains", {"source": "NDLS", "destination": "JP", "date": "2026-10-09", "time_window": {"start": "09:00", "end": "null"}}),
    ("book_ticket", {"train_id": "BTB103", "travel_class": "SL", "passenger": "Mr. Ananya Kulkarni"}),
])
def test_wrong_values_are_not_repaired(tool, args):
    out, _ = T.normalize_arguments(tool, args)
    for k, v in args.items():
        assert out[k] == v, (tool, args)


def test_extra_keys_dropped_only_when_the_rest_is_complete_and_valid_and_never_renamed():
    a, recs = T.normalize_arguments("get_train_details", {"train_id": "BTB111", "date": "2026-10-05"})
    assert a == {"train_id": "BTB111"} and recs[-1]["rule"] == "extra_args_dropped" and recs[-1]["after"] == '["date"]'
    # a renamed required key is NOT repaired and nothing is dropped
    a, recs = T.normalize_arguments("book_ticket", {"train_id": "BTB103", "travel_class": "3A", "passenger_name": "Nikhil Bose"})
    assert a == {"train_id": "BTB103", "travel_class": "3A", "passenger_name": "Nikhil Bose"} and recs == []
    # required key missing / wrong type: extras stay, strict error stands
    a, _ = T.normalize_arguments("search_trains", {"train_id": "BTB103"})
    assert a == {"train_id": "BTB103"}
    a, _ = T.normalize_arguments("book_ticket", {"train_id": "BTB103", "travel_class": "SL", "passenger": ["A B", "C D"], "x": 1})
    assert a["x"] == 1


def test_native_arguments_with_broken_json_are_repaired_value_preservingly():
    obj, recs = T.repair_arguments_json('{"train_id": "BTB103", "travel_class": "2A"')
    assert obj == {"train_id": "BTB103", "travel_class": "2A"} and recs[0]["rule"].startswith("args_json_repaired")
    assert T.repair_arguments_json("not json at all") == (None, [])
    assert T.repair_arguments_json('{"train_id": "BTB103"}') == (None, [])      # already valid: nothing to repair


# ------------------------------------------------------------------------------------------------ final text (decision 4)
def test_final_text_rule():
    assert T.final_text_from_turns([{"text": "answer", "tool_calls": False}]) == ("answer", [])
    assert T.final_text_from_turns([{"text": "let me check", "tool_calls": True}, {"text": "", "tool_calls": False}]) == ("", [])
    assert T.final_text_from_turns([{"text": "x", "tool_calls": False}, {"text": "", "tool_calls": False}])[1][0]["rule"] == "earlier_empty_turns_only"
    assert T.final_text_from_turns([{"text": "x", "tool_calls": False}, {"text": "", "tool_calls": True}, {"text": "", "tool_calls": False}])[0] == ""
    assert T.final_text_from_turns([]) == ("", [])
