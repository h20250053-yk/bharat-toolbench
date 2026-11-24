"""Structured answer-value checks for the four previously unchecked answers (T06 weekdays, T11 class list,
T16 station code + official name, T34 duration + 3A availability). Offline; real deterministic environment."""
import json

import pytest

from environment import RailwayEnv
from evaluation.scorer import STRUCTURED_VALUE_CHECKS, score
from evaluation.selfcheck import execute, final_json, final_text, gold_calls, gold_for


def run(tid, *, natural=None, values=None, drop_values=False, **json_override):
    traj, snap = execute(gold_calls(tid))
    obj = final_json(tid, snap, **json_override)
    if drop_values:
        obj.pop("answer_values", None)
    elif values is not None:
        obj["answer_values"] = {**obj["answer_values"], **values}
    row = {"task_id": f"{tid}_en", "semantic_task_id": tid, "language": "en", "status": "completed", "trajectory": traj,
           "final_text": final_text(tid, obj, natural=natural), "state_snapshot": snap}
    return score(row, gold_for(tid), snap)


def ok(s):
    return s["task_success"] is True


def failed(s, label):
    return s["task_success"] is False and any(l.startswith(label) for l in s["failure_labels"])


def env_durations(src, dst, date):
    e = RailwayEnv()
    e.reset()
    return {t["train_id"]: t["duration_minutes"] for t in e.call("search_trains", {"source": src, "destination": dst, "date": date})["data"]["trains"]}


def test_expected_values_come_from_gold_and_environment():
    st = {s.code: s for s in RailwayEnv().state.stations.values()}
    assert gold_for("T16")["final_answer"]["station_name"] == st["HWH"].name  # deterministic station record
    e = RailwayEnv()
    e.reset()
    assert gold_for("T06")["final_answer"]["operating_days"] == e.call("get_train_details", {"train_id": "BTB111"})["data"]["operating_days"]
    assert gold_for("T11")["final_answer"]["offered_classes"] == e.call("get_train_details", {"train_id": "BTB109"})["data"]["classes"]
    assert gold_for("T34")["final_answer"]["duration_minutes"] == env_durations("ADI", "MMCT", "2026-10-10")["BTB103"]
    assert set(STRUCTURED_VALUE_CHECKS) == {"T06", "T11", "T16", "T34", "T02", "T26", "T50", "T51", "T58"}


@pytest.mark.parametrize("tid", ["T06", "T11", "T16", "T34", "T02", "T26", "T50", "T51", "T58"])
def test_ideal_answers_pass_and_missing_values_fail(tid):
    assert ok(run(tid))
    assert failed(run(tid, drop_values=True), "answer_value:missing")


# ================================================================== T06 weekdays + Monday conclusion
@pytest.mark.parametrize("days", [["TUE", "WED", "SAT"], ["TUE", "THU"], ["TUE", "THU", "SAT", "MON"], ["MON", "WED", "FRI"]])
def test_t06_wrong_weekdays_fail(days):
    assert failed(run("T06", values={"operating_days": days}), "answer_value:wrong:operating_days")


def test_t06_wrong_monday_conclusion_fails():
    assert failed(run("T06", values={"runs_on_requested_day": True}), "answer_value:wrong:runs_on_requested_day")
    assert failed(run("T06", values={"runs_on_requested_day": "maybe"}), "answer_value:invalid:runs_on_requested_day")


@pytest.mark.parametrize("days,monday", [
    (["Tuesday", "Thursday", "Saturday"], False),
    (["SAT", "TUE", "THU"], "no"),                                 # order does not matter
    (["मंगलवार", "गुरुवार", "शनिवार"], "नहीं"),                       # Hindi
    ("मंगळवार, गुरुवार आणि शनिवार", "नाही"),                         # Marathi, as one string
    (["Mangalvaar", "Guruvaar", "Shanivaar"], "nahi"),              # Hinglish
    (["tue", "thu", "sat"], "false"),
])
def test_t06_correct_values_in_other_languages_and_formats_pass(days, monday):
    assert ok(run("T06", values={"operating_days": days, "runs_on_requested_day": monday}))


def test_t06_misspelled_weekday_is_not_guessed():
    assert failed(run("T06", values={"operating_days": ["Tuesdy", "Thursday", "Saturday"]}), "answer_value:invalid:operating_days")


def test_t06_correct_prose_does_not_rescue_wrong_structured_value():
    s = run("T06", natural="It runs on Tuesday, Thursday and Saturday, not on Monday.", values={"operating_days": ["TUE", "THU"]})
    assert failed(s, "answer_value:wrong:operating_days")


# ================================================================== T11 class list
@pytest.mark.parametrize("classes", [["2A"], ["2A", "3A", "SL"], ["SL"], ["2A", "CC"]])
def test_t11_wrong_class_list_fails(classes):
    assert failed(run("T11", values={"classes": classes}), "answer_value:wrong:classes")


@pytest.mark.parametrize("classes", [["3A", "2A"], ["AC 2 tier", "3AC"], "3A और 2A", "2A, 3A", ["2a", "3a"]])
def test_t11_class_set_order_and_format_do_not_matter(classes):
    assert ok(run("T11", values={"classes": classes}))


def test_t11_unknown_class_is_invalid():
    assert failed(run("T11", values={"classes": ["2A", "1A"]}), "answer_value:invalid:classes")


# ================================================================== T16 station code + official name
@pytest.mark.parametrize("name", ["Howrah Station", "Kolkata Junction", "Howrah", "Howrah Jn"])
def test_t16_wrong_official_name_fails(name):
    assert failed(run("T16", values={"station_name": name}), "answer_value:wrong:station_name")


@pytest.mark.parametrize("name", ["HOWRAH JUNCTION", "howrah junction.", "  Howrah   Junction ", "Howrah-Junction"])
def test_t16_case_punctuation_spacing_differences_pass(name):
    assert ok(run("T16", values={"station_name": name}))


def test_t16_name_must_be_the_station_record_not_a_transliteration():
    # the contract asks for the official name as returned by the tool; only case/punctuation/spacing are normalised
    assert failed(run("T16", values={"station_name": "हावड़ा जंक्शन"}), "answer_value:wrong:station_name")


def test_t16_wrong_code_fails_and_case_is_normalised():
    assert failed(run("T16", values={"station_code": "HWR"}), "answer_value:wrong:station_code")
    assert failed(run("T16", values={"station_code": "KOL"}), "answer_value:wrong:station_code")
    assert ok(run("T16", values={"station_code": "hwh"}))


# ================================================================== T34 train + duration + 3A availability
def test_t34_correct_train_with_wrong_duration_fails():
    other = env_durations("ADI", "MMCT", "2026-10-10")["BTB101"]  # 360: the fastest train's duration
    assert failed(run("T34", values={"duration_minutes": other}), "answer_value:wrong:duration_minutes")


def test_t34_right_duration_belonging_to_the_wrong_train_fails():
    d = env_durations("ADI", "MMCT", "2026-10-10")
    assert d["BTB125"] == d["BTB103"]  # BTB125 has the same 445 min but no 3A class, so it is not an answer
    s = run("T34", selected_train="BTB125", values={"duration_minutes": d["BTB125"]})
    assert failed(s, "final_answer:wrong_selected_train")


def test_t34_wrong_duration_with_right_number_elsewhere_in_text_fails():
    s = run("T34", natural="Among cheaper trains, the 445-minute one is best; BTB103 takes 6 hours.", values={"duration_minutes": 360})
    assert failed(s, "answer_value:wrong:duration_minutes")


@pytest.mark.parametrize("dur", [445, "445", "445 minutes", "7h 25m", "7 hours 25 minutes", "7:25", "7 hrs 25 mins",
                                 "7 घंटे 25 मिनट", "7 तास 25 मिनिटे", "७ तास २५ मिनिटे", "7 ghante 25 minute"])
def test_t34_equivalent_duration_formats_pass(dur):
    assert ok(run("T34", values={"duration_minutes": dur}))


@pytest.mark.parametrize("dur", ["about 7 hours", "7.4 hours", "7 hours", "7:52", "7.25"])
def test_t34_approximate_or_wrong_durations_fail(dur):
    s = run("T34", values={"duration_minutes": dur})
    assert s["task_success"] is False and any(l.startswith("answer_value:") and "duration_minutes" in l for l in s["failure_labels"])


def test_t34_wrong_3a_availability_fails():
    assert failed(run("T34", values={"seats_available": 18}), "answer_value:wrong:seats_available")
    assert failed(run("T34", values={"seats_available": "none"}), "answer_value:invalid:seats_available")
    assert ok(run("T34", values={"seats_available": "0"}))


def test_t34_wrong_train_fails_even_with_all_values_right():
    assert failed(run("T34", selected_train="BTB123"), "final_answer:wrong_selected_train")


def test_answer_values_not_an_object_fails():
    traj, snap = execute(gold_calls("T16"))
    obj = final_json("T16", snap)
    obj["answer_values"] = ["HWH", "Howrah Junction"]
    row = {"task_id": "T16_en", "semantic_task_id": "T16", "language": "en", "status": "completed", "trajectory": traj,
           "final_text": final_text("T16", obj), "state_snapshot": snap}
    assert failed(score(row, gold_for("T16"), snap), "answer_value:not_an_object")


# ---------------------------------------------------------------------------------------------------- audit I-02
import pytest as _pytest  # noqa: E402

from evaluation.canonical import times_in as _times_in  # noqa: E402


@_pytest.mark.parametrize("text,expected", [
    ("शाम 18:30 बजे", {"18:30"}), ("evening 18:30", {"18:30"}), ("સાંજે 18:30", {"18:30"}), ("संध्याकाळी 19:05", {"19:05"}),
    ("रात 23:30", {"23:30"}), ("रात्री 00:40", {"00:40"}), ("રાત્રે 21:15", {"21:15"}), ("night 23:50", {"23:50"}),
    ("दोपहर 14:10", {"14:10"}), ("दुपारी 13:45", {"13:45"}), ("બપોરે 15:20", {"15:20"}),
    # the existing 12-hour forms keep working
    ("रात्री 8:20", {"20:20"}), ("शाम 6:30", {"18:30"}), ("सुबह 9:05", {"09:05"}), ("evening 6:30 PM", {"18:30"}),
    ("20:20", {"20:20"}), ("8:20 PM", {"20:20"}),
    # a 24-hour hour that contradicts the day-part word is not a time
    ("सुबह 13:00", set()), ("सकाळी 18:30", set()), ("morning 19:00", set()), ("दोपहर 20:00", set()), ("शाम 13:30", set()),
])
def test_times_in_day_part_words_with_24_hour_hours(text, expected):
    assert _times_in(text) == expected


# ---------------------------------------------------------------------------------------------------- audit I-03 (Gujarati)
from evaluation.canonical import (canon_bool as _canon_bool, canon_class_set as _canon_class_set,  # noqa: E402
                                  canon_duration_minutes as _canon_dur, canon_weekday_set as _canon_wd)


@_pytest.mark.parametrize("value,expected", [
    (["સોમવાર"], {"MON"}), (["મંગળવાર", "ગુરુવાર", "શનિવાર"], {"TUE", "THU", "SAT"}), (["બુધવાર", "શુક્રવાર", "રવિવાર"], {"WED", "FRI", "SUN"}),
    ("સોમવાર, બુધવાર અને શુક્રવાર", {"MON", "WED", "FRI"}), (["સોમવારે"], {"MON"}), (["TUE", "ગુરુવાર"], {"TUE", "THU"}),
])
def test_gujarati_weekday_sets(value, expected):
    assert _canon_wd(value) == frozenset(expected)


def test_gujarati_weekday_unknown_stays_unknown():
    assert _canon_wd(["સોમવારx"]) is None and _canon_wd(["ગુજરાતી"]) is None


@_pytest.mark.parametrize("value,expected", [("હા", True), ("હાં", True), ("હોય", None), ("ના", False), ("નથી", False), ("નહીં", False),
                                             ("કદાચ", None)])
def test_gujarati_bool(value, expected):
    assert _canon_bool(value) is expected


@_pytest.mark.parametrize("value,expected", [("7 કલાક 25 મિનિટ", 445), ("7 કલાક અને 25 મિનિટ", 445), ("૭ કલાક ૨૫ મિનિટ", 445), ("7 કલાક", 420),
                                             ("445 મિનિટ", 445), ("લગભગ 7 કલાક", None), ("7.4 કલાક", None)])
def test_gujarati_duration(value, expected):
    assert _canon_dur(value) == expected


def test_gujarati_class_list_separator():
    assert _canon_class_set("2A અને 3A") == frozenset({"2A", "3A"}) and _canon_class_set("3A, 2A") == frozenset({"2A", "3A"})


# ================================================================== audit I-11: small integers are structured, prose proves nothing
# gold values: T02 seats 17, T26 seats 2, T50 seats left 0, T51 trains 4, T58 seats 2
GOLD_NUMBER = {"T02": ("seats_available", 17), "T26": ("seats_available", 2), "T50": ("seats_remaining_at_end", 0),
               "T51": ("train_count", 4), "T58": ("seats_available", 2)}
PROSE_WITH_THE_GOLD_NUMBER = {  # the gold number appears elsewhere: in a count, a date, a quantity
    "T02": "I checked 17 October is not the date; 3 seats are free. Fare: {fare}.",
    "T26": "2 passengers can ask; there are 5 seats left on 2 trains.",
    "T50": "Booked 2 tickets; 0 errors; 1 seat left.",
    "T51": "I looked at 4 results pages; there are 3 trains and the last leaves at {dep}.",
    "T58": "Booked 1 ticket; searched 2 trains; 4 CC seats are left.",
}


@pytest.mark.parametrize("tid", list(GOLD_NUMBER))
def test_gold_number_elsewhere_in_prose_does_not_rescue_a_wrong_structured_value(tid):
    key, gold = GOLD_NUMBER[tid]
    fa = gold_for(tid)["final_answer"]
    prose = PROSE_WITH_THE_GOLD_NUMBER[tid].format(fare=fa.get("fare_inr"), dep=fa.get("departure"))
    wrong = gold + 3
    assert failed(run(tid, natural=prose, values={key: wrong}), f"answer_value:wrong:{key}")


@pytest.mark.parametrize("tid", list(GOLD_NUMBER))
def test_the_number_only_in_prose_is_not_enough(tid):
    key, gold = GOLD_NUMBER[tid]
    assert failed(run(tid, natural=f"The answer is {gold}.", drop_values=True), "answer_value:missing")
    traj_values = run(tid, natural=f"The answer is {gold}.", values={key: "unknown"})
    assert failed(traj_values, f"answer_value:invalid:{key}")


@pytest.mark.parametrize("tid", list(GOLD_NUMBER))
def test_correct_structured_value_passes_in_any_digit_script_and_string_form(tid):
    key, gold = GOLD_NUMBER[tid]
    assert ok(run(tid, values={key: gold})) and ok(run(tid, values={key: str(gold)}))
    assert ok(run(tid, values={key: "".join("०१२३४५६७८९"[int(d)] for d in str(gold))}))


def test_these_numbers_are_no_longer_free_text_checks():
    from evaluation.scorer import VALUE_CHECKS
    assert all(k not in {"seats_available", "seats_remaining_at_end", "train_count"} for t in GOLD_NUMBER for k, _ in VALUE_CHECKS.get(t, []))
    assert VALUE_CHECKS["T02"] == [("fare_inr", "number")] and VALUE_CHECKS["T51"] == [("departure", "time")]


def test_the_contract_prompt_names_the_new_keys():
    from evaluation.final_answer import ANSWER_VALUE_KEYS, CONTRACT_PROMPT
    for k in ("seats_remaining_at_end", "train_count", "seats_available"):
        assert k in ANSWER_VALUE_KEYS and f'"{k}"' in CONTRACT_PROMPT


# ---- "." is not a time separator unless AM/PM follows
@pytest.mark.parametrize("text,expected", [("₹14.50", set()), ("fare 14.50 INR", set()), ("10.10", set()), ("शाम 6.30", set()), ("1,460.50", set()),
                                           ("8.20 PM", {"20:20"}), ("at 9.05 am", {"09:05"}), ("6.30 p.m.", {"18:30"}), ("20:20", {"20:20"})])
def test_dot_is_a_time_separator_only_before_am_pm(text, expected):
    from evaluation.canonical import times_in
    assert times_in(text) == expected


def test_a_fare_with_decimals_is_not_a_time_for_a_time_check():
    # T08-like check: the gold departure must be stated as a time; a price '14.50' must not satisfy a gold time of 14:50
    from evaluation.scorer import _value_found
    assert _value_found("time", "14:50", "The fare is ₹14.50.") is False and _value_found("time", "14:50", "It leaves at 14:50.") is True


# ---------------------------------------------------------------------------------------------------- Gujarati yes/no (audit follow-up)
@_pytest.mark.parametrize("value,expected", [
    ("હા", True), ("હા.", True), ("હા, સીટો ઉપલબ્ધ છે, કોઈ સમસ્યા નથી", True),           # a later નથી does not turn a leading હા into no
    ("હા, આ ટ્રેન સોમવારે ચાલે છે", True), ('"હા"', True), ("હા! બુક કરો", True),
    ("ના", False), ("ના.", False), ("ના, આ ટ્રેન સોમવારે ચાલતી નથી", False), ("ના 3A સીટ ઉપલબ્ધ નથી", False),   # ના as the first word
    ("નથી", False), ("નહીં", False), ("નહિ", False),
    # a yes/no word later in the sentence never counts (same rule as every other language)
    ("આ ટ્રેન સોમવારે ચાલતી નથી", None), ("BTB101 ના 3A માં સીટ છે, ના.", None), ("સીટ છે? ના, નથી", None), ("ટ્રેન ચાલે છે, હા", None),
    # "ના" is also the genitive "of": separate word after Latin names / numbers is NOT no
    ("BTB101 ના 3A", None), ("BTB101 ના 3A ક્લાસમાં 5 સીટ", None), ("2026 ના ઓક્ટોબર", None),
    # "હોય" means "is / if there is", not yes
    ("હોય", None), ("જો સીટ હોય તો બુક કરો", None), ("કદાચ", None), ("", None),
])
def test_gujarati_yes_no_in_replies(value, expected):
    assert _canon_bool(value) is expected


@_pytest.mark.parametrize("day", ["બુધવારે", "સોમવારે", "ગુરુવારે", "મંગળવારે", "શુક્રવારે", "શનિવારે", "રવિવારે"])
def test_gujarati_weekday_locative_forms_match(day):
    assert _canon_wd([day]) is not None and len(_canon_wd([day])) == 1


@_pytest.mark.parametrize("variant,code", [("મંગલવાર", "TUE"), ("મંગલવારે", "TUE"), ("ગુરૂવાર", "THU"), ("ગુરૂવારે", "THU"),
                                           ("બુધવારે", "WED"), ("સોમવારે", "MON"), ("ગુરુવારે", "THU")])
def test_gujarati_weekday_spelling_variants(variant, code):
    assert _canon_wd([variant]) == frozenset({code})


# ---- ONE yes/no rule for en, hinglish, hi, mr, gu: whole value, or a yes/no word as the FIRST word (before , . ! space); never later
LANG_YESNO = {
    # lang: (yes word, no word, "<yes>, ...", "<no>, ...", yes-sentence with a later negative word, sentence with the word only LATER)
    "en": ("yes", "no", "Yes, the train runs on Tuesday", "No, the train does not run on Monday",
           "Yes, the train runs and there is no problem", "The train runs on Tuesday, yes"),
    "hinglish": ("haan", "nahi", "Haan, train mangalvar ko chalti hai", "Nahi, train somvar ko nahi chalti",
                 "Haan, train chalti hai aur koi problem nahi hai", "Train mangalvar ko chalti hai, haan"),
    "hi": ("हाँ", "नहीं", "हाँ, ट्रेन मंगलवार को चलती है", "नहीं, ट्रेन सोमवार को नहीं चलती",
           "हाँ, ट्रेन चलती है और कोई समस्या नहीं है", "ट्रेन मंगलवार को चलती है, हाँ"),
    "mr": ("होय", "नाही", "होय, ट्रेन मंगळवारी धावते", "नाही, ट्रेन सोमवारी धावत नाही",
           "होय, ट्रेन धावते आणि काही अडचण नाही", "ट्रेन मंगळवारी धावते, होय"),
    "gu": ("હા", "ના", "હા, ટ્રેન મંગળવારે ચાલે છે", "ના, ટ્રેન સોમવારે ચાલતી નથી",
           "હા, ટ્રેન ચાલે છે અને કોઈ સમસ્યા નથી", "ટ્રેન મંગળવારે ચાલે છે, હા"),
}


@_pytest.mark.parametrize("lang", list(LANG_YESNO))
def test_yes_no_one_rule_bare_word(lang):
    yes, no = LANG_YESNO[lang][:2]
    assert _canon_bool(yes) is True and _canon_bool(no) is False
    assert _canon_bool(yes.upper()) is True and _canon_bool(f" {no} ") is False


@_pytest.mark.parametrize("lang", list(LANG_YESNO))
def test_yes_no_one_rule_leading_word_with_comma_dot_bang_or_space(lang):
    yes, no, yes_sentence, no_sentence = LANG_YESNO[lang][:4]
    assert _canon_bool(yes_sentence) is True and _canon_bool(no_sentence) is False                      # "<yes>, ..." / "<no>, ..."
    for sep in (",", ".", "!", " "):
        assert _canon_bool(f"{yes}{sep} something follows") is True, (lang, sep)
        assert _canon_bool(f"{no}{sep} something follows") is False, (lang, sep)


@_pytest.mark.parametrize("lang", list(LANG_YESNO))
def test_yes_no_one_rule_a_later_negative_word_never_turns_a_leading_yes_into_no(lang):
    yes, no, _, _, yes_with_later_negative, _ = LANG_YESNO[lang]
    assert _canon_bool(yes_with_later_negative) is True
    assert _canon_bool(f"{no}, but also {yes}") is False                                               # and a later yes never turns a leading no


@_pytest.mark.parametrize("lang", list(LANG_YESNO))
def test_yes_no_one_rule_a_yes_no_word_only_later_in_the_sentence_is_not_read(lang):
    yes, no, _, _, _, later_only = LANG_YESNO[lang]
    assert _canon_bool(later_only) is None and _canon_bool(f"it depends, {no}") is None and _canon_bool(f"maybe. {yes}") is None


@_pytest.mark.parametrize("lang", list(LANG_YESNO))
def test_yes_no_one_rule_unknown_or_prefixed_words_are_none(lang):
    yes, no = LANG_YESNO[lang][:2]
    for text in ("", "   ", "maybe", f"{yes}x", f"x{no}", f"{yes}ish yes", "BTB101"):
        assert _canon_bool(text) is None, (lang, text)


@_pytest.mark.parametrize("value,expected", [
    ("हो", True), ("हो, चलती है", True), ("तो हो", None), ("ना", None), ("तो ना", None),               # Hindi/Marathi हो / ना: first word only; ना is no word
    ("होय", True), ("हो सकता है", True),                                                                # known consequence of the rule (leading "हो"), see AUDIT_REPORT
    ("नहीं तो", False),
    ("ha ha ha", True), ("n", False), ("y", True), ("yesterday", None), ("nahin", False),
])
def test_yes_no_ambiguous_words_count_only_as_the_first_word(value, expected):
    assert _canon_bool(value) is expected


def test_yes_no_word_lists_cover_every_language_and_gujarati_hoy_is_not_yes():
    from evaluation.canonical import NO_WORDS, YES_WORDS
    assert set(YES_WORDS) == set(NO_WORDS) == {"en", "hinglish", "hi", "mr", "gu"}
    assert "હોય" not in YES_WORDS["gu"] and "ના" in NO_WORDS["gu"]


# ---- realistic full Gujarati replies, scored end to end (T06 yes/no, T11 class list, T34 duration + seats)
def _gu_run(tid, natural, values):
    return run(tid, natural=natural, values=values)


T06_NO = ("ટ્રેન BTB111 નવી દિલ્હીથી મંગળવાર, ગુરુવાર અને શનિવારે ઊપડે છે. સોમવારે આ ટ્રેન ચાલતી નથી, એટલે સોમવારે નવી દિલ્હીથી તે મળશે નહીં.")
T06_YES = "ટ્રેન BTB111 મંગળવાર, ગુરુવાર અને શનિવારે ચાલે છે. સોમવારે પણ ચાલે છે."


@_pytest.mark.parametrize("monday", ["ના, આ ટ્રેન સોમવારે ચાલતી નથી", "ના.", "નથી", "નહીં", False])
def test_t06_gujarati_no_answers_match_gold(monday):
    assert ok(_gu_run("T06", T06_NO, {"operating_days": ["મંગળવાર", "ગુરુવાર", "શનિવાર"], "runs_on_requested_day": monday}))


@_pytest.mark.parametrize("monday", ["હા", "હા, આ ટ્રેન સોમવારે ચાલે છે", "હા, કોઈ સમસ્યા નથી", True])
def test_t06_gujarati_yes_answers_are_read_as_yes_and_are_wrong(monday):
    s = _gu_run("T06", T06_YES, {"operating_days": ["મંગળવાર", "ગુરુવાર", "શનિવાર"], "runs_on_requested_day": monday})
    assert failed(s, "answer_value:wrong:runs_on_requested_day")          # parsed as yes (not "invalid"), and gold says no


@_pytest.mark.parametrize("monday", ["BTB101 ના 3A", "કદાચ"])
def test_t06_unreadable_gujarati_yes_no_is_invalid_not_guessed(monday):
    assert failed(_gu_run("T06", T06_NO, {"runs_on_requested_day": monday}), "answer_value:invalid:runs_on_requested_day")


def test_t06_gujarati_weekday_spelling_variants_and_locative_pass():
    assert ok(_gu_run("T06", T06_NO, {"operating_days": ["મંગલવારે", "ગુરૂવારે", "શનિવારે"], "runs_on_requested_day": "ના"}))
    assert failed(_gu_run("T06", T06_NO, {"operating_days": ["સોમવારે", "ગુરુવારે", "શનિવારે"]}), "answer_value:wrong:operating_days")


T11_REPLY = "ટ્રેન BTB109 માં સ્લીપર (SL) ક્લાસ નથી. આ ટ્રેનમાં 2A અને 3A ક્લાસ ઉપલબ્ધ છે."


@_pytest.mark.parametrize("classes", ["2A અને 3A", "3A અને 2A", "2A, 3A", ["2A", "3A"], ["3A", "2A"]])
def test_t11_full_gujarati_reply_with_the_right_classes_passes(classes):
    assert ok(_gu_run("T11", T11_REPLY, {"classes": classes}))


@_pytest.mark.parametrize("classes", ["2A અને SL", "SL", "2A", ["2A", "3A", "SL"]])
def test_t11_full_gujarati_reply_with_wrong_classes_fails(classes):
    assert failed(_gu_run("T11", T11_REPLY, {"classes": classes}), "answer_value:wrong:classes")


T34_REPLY = ("₹3,000 સુધીના 3A ભાડાવાળી ટ્રેનોમાં સૌથી ઓછા સમયની ટ્રેન BTB103 છે; તેની મુસાફરી 7 કલાક 25 મિનિટની છે. "
             "ના, 3A ની સીટો ઉપલબ્ધ નથી, કારણ કે તે સોલ્ડ આઉટ છે.")


@_pytest.mark.parametrize("duration", ["7 કલાક 25 મિનિટ", "7 કલાક અને 25 મિનિટ", "૭ કલાક ૨૫ મિનિટ", "445 મિનિટ", 445, "7:25"])
def test_t34_full_gujarati_reply_passes(duration):
    assert ok(_gu_run("T34", T34_REPLY, {"duration_minutes": duration, "seats_available": 0}))


@_pytest.mark.parametrize("values,label", [
    ({"duration_minutes": "7 કલાક", "seats_available": 0}, "answer_value:wrong:duration_minutes"),
    ({"duration_minutes": "લગભગ 7 કલાક", "seats_available": 0}, "answer_value:invalid:duration_minutes"),
    ({"duration_minutes": "7 કલાક 25 મિનિટ", "seats_available": 5}, "answer_value:wrong:seats_available"),
])
def test_t34_full_gujarati_reply_with_wrong_values_fails(values, label):
    assert failed(_gu_run("T34", T34_REPLY, values), label)
