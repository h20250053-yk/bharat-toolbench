"""Batch T101-T200 (benchmark 3.0, the 20-tool stage). The ONLY place where this batch's specs and the English / Hinglish / Hindi /
Marathi text live (Gujarati text: benchmark/batch_gujarati_t101_t200.py, which takes its markers from here). Design rationale per
task: benchmark/BATCH_T101_T200.md. Solvers: benchmark/solvers_t101_t200.py.

* SPECS     semantic task specs (written into benchmark/semantic_tasks.json by `python -m benchmark.batch_t101_t200`)
* EN_ITEMS  English source prompts (draft, not human-authored) + tags
* QUERIES   Hinglish / Hindi / Marathi DRAFT variants (Claude-generated, NOT human-reviewed)
* MARKERS   keyword/regex surface checks per task and language (consumed by language_checks.py); GU_MARKERS the Gujarati ones
* FLAGS     translation-risk flags for the batch audit file (consumed by build_language_audit.py)

Ninety of the tasks need at least one of the eight tools added for this stage (check_tatkal_availability, book_tatkal_ticket,
get_berth_availability, get_platform_info, change_boarding_point, order_meal, file_tdr, raise_complaint); the other ten (T140, T167-T169,
T175, T177, T178, T189, T191, T194) are answered with older tools while a new one is the tempting wrong choice (e.g. filing a TDR to find
out whether it is allowed). Every task is offered all twenty tools. As in T76-T100 the new tools overlap on purpose with older ones (Tatkal vs general quota vs waitlist, TDR vs cancellation,
timetable vs live status vs platform), so the batch tests TOOL SELECTION and the order of irreversible actions as well as the
service rules (Tatkal window, boarding-change deadline, meal lead time, TDR threshold, complaints only during the journey).
PNRs, train ids, class codes, amounts and times stay ASCII in every language; passenger names stay Latin; station names use the
frozen per-language aliases. Relative days ('today', 'tomorrow', 'tonight') are relative to the pinned now, Monday 2026-10-05 09:00 IST.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .batch_t06_t15 import F, OK

BATCH_IDS = [f"T{i}" for i in range(101, 201)]
EN_AUTHOR = "claude-session-8 (draft, not human-authored)"
ALL_TOOLS_V4 = ["resolve_station", "search_trains", "get_train_details", "check_availability", "get_fare", "book_ticket",
                "get_booking_status", "get_cancellation_refund", "cancel_ticket", "join_waitlist", "get_live_train_status",
                "get_concession_fare", "check_tatkal_availability", "book_tatkal_ticket", "get_berth_availability", "get_platform_info",
                "change_boarding_point", "order_meal", "file_tdr", "raise_complaint"]
TD, TM = "2026-10-05", "2026-10-06"  # today / tomorrow relative to the pinned now
LANGS5 = ("en", "hinglish", "hi", "mr", "gu")


def W(en, hl, hi, mr, gu) -> tuple:
    """One marker in the five languages (each a list of regexes that must ALL match, case-insensitive)."""
    return tuple(x if isinstance(x, list) else [x] for x in (en, hl, hi, mr, gu))


# shared words
TODAY = W("today", "aaj", "आज", "आज", "આજે")
TONIGHT = W("tonight", "aaj raat", "आज रात", "आज रात्री", "આજ રાત")
TOMORROW = W("tomorrow", "kal", "कल", "उद्या", "આવતીકાલે")
TATKAL = W("Tatkal", "Tatkal", "तत्काल", "तत्काळ", "તત્કાલ")
LOWER = W("lower berth", "lower berth", "लोअर बर्थ", "लोअर बर्थ", "લોઅર બર્થ")
PLATFORM = W("platform", "platform", "प्लेटफ़ॉर्म", "प्लॅटफॉर्म", "પ્લેટફોર્મ")
BOARDING = W("boarding", "boarding", "बोर्डिंग", "बोर्डिंग", "બોર્ડિંગ")
ORDER = W("order", "order", "ऑर्डर", "ऑर्डर", "ઓર્ડર")
COMPLAINT = W("complain", "complaint", "शिकायत", "तक्रार", "ફરિયાદ")
TDR = W("TDR", "TDR", "TDR", "TDR", "TDR")
WAITLIST = W("waitlist", "waitlist", "वेटिंग लिस्ट", "वेटिंग लिस्ट", "વેઇટિંગ લિસ્ટ")
SOLD = W("sold out", "sold out", "सोल्ड आउट", "सोल्ड आउट", "સોલ્ડ આઉટ")
FULL = W("full", "full", "भरा हुआ", "भरलेले", "ભરાઈ ગયું")
ENGINE1 = W("engine as number 1", "engine ko number 1", "इंजन को नंबर 1", "इंजिनला क्रमांक 1", "એન્જિનને નંબર 1")
NEXT = W("next", "agle", "अगले", "पुढच्या", "આગલા")


def join(*ws: tuple) -> tuple:
    return tuple(sum((w[i] for w in ws), []) for i in range(5))


def lit(s: str) -> tuple:
    return W(re.escape(s), re.escape(s), re.escape(s), re.escape(s), re.escape(s))


# ------------------------------------------------------------------ the 100 tasks
# T(tid, category, tags, solver kind, params, en, hinglish, hi, mr, gu, intent=marker, more={key: marker}, status, must_state, risk,
#   note, prohibited=[(tool, prompt_phrase, reason)], equivalent=[text], extra_facts)
_T: list[dict] = []


def T(tid, cat, tags, kind, params, en, hl, hi, mr, gu, *, intent, status, must, risk, note, more=None, prohibited=None,
      equivalent=None, alternatives=None, facts=""):
    _T.append(dict(tid=tid, cat=cat, tags=tags, kind=kind, params=params, q=dict(zip(LANGS5, (en, hl, hi, mr, gu))),
                   intent=intent, more=more or {}, status=status, must=must, risk=risk, note=note, prohibited=prohibited or [],
                   equivalent=equivalent or [], alternatives=alternatives or [], facts=facts))


# ---------------------------------------------------------------- Tatkal (T101-T120)
T("T101", "single_tool", ["single_tool", "tatkal", "relative_day", "read_only"], "tatkal_open_and_seats",
  dict(train_id="BTB109", travel_class="3A", travel_date=TD),
  "Is Tatkal booking open for 3A on train BTB109 today, and how many Tatkal seats are left?",
  "Kya aaj train BTB109 mein 3A ke liye Tatkal booking khuli hai, aur kitni Tatkal seats bachi hain?",
  "क्या आज ट्रेन BTB109 में 3A के लिए तत्काल बुकिंग खुली है, और कितनी तत्काल सीटें बची हैं?",
  "आज ट्रेन BTB109 मध्ये 3A साठी तत्काळ बुकिंग सुरू आहे का, आणि किती तत्काळ सीट शिल्लक आहेत?",
  "શું આજે ટ્રેન BTB109 માં 3A માટે તત્કાલ બુકિંગ ખુલ્લું છે, અને કેટલી તત્કાલ સીટો બાકી છે?",
  intent=join(TATKAL, TODAY, W("how many", "kitni", "कितनी", "किती", "કેટલી")), status="success",
  must=["tatkal_status OPEN", "tatkal_seats 6"], risk="Two questions (open? how many Tatkal seats?) and 'today'.",
  note="Read-only Tatkal lookup for a train leaving its origin today (the window opened yesterday at 10:00). Selection: "
       "check_tatkal_availability, not check_availability (general quota, sold out) and no booking.")
T("T102", "single_tool", ["single_tool", "tatkal", "opening_time", "relative_day", "read_only"], "tatkal_opening_time",
  dict(train_id="BTB112", travel_class="SL", travel_date=TM),
  "At what time does Tatkal booking open for sleeper (SL) on train BTB112, which leaves tomorrow?",
  "Kal chalne wali train BTB112 mein sleeper (SL) ki Tatkal booking kitne baje khulegi?",
  "कल चलने वाली ट्रेन BTB112 में स्लीपर (SL) की तत्काल बुकिंग कितने बजे खुलेगी?",
  "उद्या सुटणाऱ्या ट्रेन BTB112 मध्ये स्लीपर (SL) ची तत्काळ बुकिंग किती वाजता सुरू होईल?",
  "આવતીકાલે ઊપડતી ટ્રેન BTB112 માં સ્લીપર (SL) ની તત્કાલ બુકિંગ કેટલા વાગ્યે ખૂલશે?",
  intent=join(TATKAL, TOMORROW, W("what time", "kitne baje", "कितने बजे", "किती वाजता", "કેટલા વાગ્યે")), status="success",
  must=["opens_at 11:00 (today)"], risk="'tomorrow' = the day the train leaves its origin; SL (not AC) timing.",
  note="Tatkal window not open yet: SL opens at 11:00 the day before (AC at 10:00); now is 09:00.")
T("T103", "booking", ["booking", "tatkal", "state_changing", "relative_day"], "tatkal_direct_booking",
  dict(train_id="BTB101", travel_class="2A", travel_date=TD, passenger="Rohan Gupta", expect_general_sold_out=True),
  "Book a Tatkal ticket in 2A on train BTB101 today for Rohan Gupta.",
  "Aaj train BTB101 mein Rohan Gupta ke naam par 2A ka Tatkal ticket book kar do.",
  "आज ट्रेन BTB101 में Rohan Gupta के नाम से 2A का तत्काल टिकट बुक कीजिए।",
  "आज ट्रेन BTB101 मध्ये Rohan Gupta यांच्या नावाने 2A चे तत्काळ तिकीट बुक करा.",
  "આજે ટ્રેન BTB101 માં Rohan Gupta ના નામે 2A ની તત્કાલ ટિકિટ બુક કરો.",
  intent=join(TATKAL, TODAY), more={"booking": W(r"\bbook\b", "book kar do", "बुक कीजिए", "बुक करा", "બુક કરો")}, status="success",
  must=["Tatkal booking for Rohan Gupta", "tatkal_fare_inr 4940"], risk="'Tatkal' must survive (not a general-quota booking).",
  note="Explicit Tatkal booking: book_tatkal_ticket (book_ticket would fail SOLD_OUT and is a different quota).")
T("T104", "constraint", ["constraint", "tatkal", "explicit_quota", "safety", "state_changing"], "tatkal_explicit_while_general_free",
  dict(train_id="BTB126", travel_class="CC", travel_date=TD, passenger="Meena Iyer"),
  "Book a chair car (CC) ticket on train BTB126 today for Meena Iyer under the Tatkal quota, not the general quota.",
  "Aaj train BTB126 mein Meena Iyer ke naam par chair car (CC) ka ticket Tatkal quota mein book kar do, general quota mein nahi.",
  "आज ट्रेन BTB126 में Meena Iyer के नाम से चेयर कार (CC) का टिकट तत्काल कोटे में बुक कीजिए, जनरल कोटे में नहीं।",
  "आज ट्रेन BTB126 मध्ये Meena Iyer यांच्या नावाने चेअर कार (CC) चे तिकीट तत्काळ कोट्यातून बुक करा, जनरल कोट्यातून नाही.",
  "આજે ટ્રેન BTB126 માં Meena Iyer ના નામે ચેર કાર (CC) ની ટિકિટ તત્કાલ ક્વોટામાં બુક કરો, જનરલ ક્વોટામાં નહીં.",
  intent=join(TATKAL, TODAY),
  more={"forbidden": W("not the general quota", "general quota mein nahi", "जनरल कोटे में नहीं", "जनरल कोट्यातून नाही", "જનરલ ક્વોટામાં નહીં")},
  status="success", must=["Tatkal booking for Meena Iyer", "tatkal_fare_inr 885"],
  risk="The refusal of the general quota must keep its negative meaning.",
  note="General CC still has 29 seats, so the cheaper book_ticket is the tempting wrong tool: the user explicitly wants Tatkal.",
  prohibited=[("book_ticket", "not the general quota", "The user explicitly asks for the Tatkal quota, not the general quota.")])
T("T105", "recovery", ["recovery", "tatkal", "window_not_open", "relative_day"], "tatkal_booking_not_open",
  dict(train_id="BTB110", travel_class="3A", travel_date=TM, passenger="Sunil Verma"),
  "Book a Tatkal 3A ticket for Sunil Verma on train BTB110, which leaves tomorrow.",
  "Kal chalne wali train BTB110 mein Sunil Verma ke liye 3A ka Tatkal ticket book kar do.",
  "कल चलने वाली ट्रेन BTB110 में Sunil Verma के लिए 3A का तत्काल टिकट बुक कीजिए।",
  "उद्या सुटणाऱ्या ट्रेन BTB110 मध्ये Sunil Verma यांच्यासाठी 3A चे तत्काळ तिकीट बुक करा.",
  "આવતીકાલે ઊપડતી ટ્રેન BTB110 માં Sunil Verma માટે 3A ની તત્કાલ ટિકિટ બુક કરો.",
  intent=join(TATKAL, TOMORROW), status="cannot_complete", must=["Tatkal not open yet", "opens_at 10:00"],
  risk="'tomorrow' must stay; nothing else may be booked.",
  note="Booking before the AC Tatkal window (opens 10:00 today; now 09:00): TATKAL_NOT_OPEN. A general booking would be a "
       "different quota and was not asked for.",
  equivalent=["check_tatkal_availability(BTB110, 3A, 2026-10-06) showing NOT_YET_OPEN grounds the answer as well as the rejected booking."])
T("T106", "recovery", ["recovery", "tatkal", "train_departed", "relative_day"], "tatkal_train_departed",
  dict(train_id="BTB105", travel_class="CC", travel_date=TD, passenger="Alok Mishra"),
  "Book a Tatkal chair car (CC) ticket on train BTB105 today for Alok Mishra.",
  "Aaj train BTB105 mein Alok Mishra ke liye chair car (CC) ka Tatkal ticket book kar do.",
  "आज ट्रेन BTB105 में Alok Mishra के लिए चेयर कार (CC) का तत्काल टिकट बुक कीजिए।",
  "आज ट्रेन BTB105 मध्ये Alok Mishra यांच्यासाठी चेअर कार (CC) चे तत्काळ तिकीट बुक करा.",
  "આજે ટ્રેન BTB105 માં Alok Mishra માટે ચેર કાર (CC) ની તત્કાલ ટિકિટ બુક કરો.",
  intent=join(TATKAL, TODAY), status="cannot_complete", must=["train already departed (06:05)"],
  risk="'today' must stay (today's run has already left).",
  note="Today's BTB105 left New Delhi at 06:05: TRAIN_DEPARTED. Nothing may be booked on another day or train.",
  equivalent=["check_tatkal_availability(BTB105, CC, 2026-10-05) showing DEPARTED grounds the answer as well."])
T("T107", "invalid_input", ["invalid_input", "tatkal", "not_running_on_date", "explicit_date", "read_only"], "tatkal_not_running_on_date",
  dict(train_id="BTB111", travel_class="3A", date="2026-10-07"),
  "How many Tatkal seats are left in 3A on train BTB111 on 7 October 2026?",
  "7 October 2026 ko train BTB111 mein 3A ki kitni Tatkal seats bachi hain?",
  "7 अक्टूबर 2026 को ट्रेन BTB111 में 3A की कितनी तत्काल सीटें बची हैं?",
  "7 ऑक्टोबर 2026 रोजी ट्रेन BTB111 मध्ये 3A च्या किती तत्काळ सीट शिल्लक आहेत?",
  "7 ઓક્ટોબર 2026ના રોજ ટ્રેન BTB111 માં 3A ની કેટલી તત્કાલ સીટો બાકી છે?",
  intent=TATKAL, status="cannot_complete", must=["BTB111 does not run on 2026-10-07 (Wednesday)"],
  risk="The date must stay exactly 7 October 2026.",
  note="BTB111 runs Tue/Thu/Sat only; the Tatkal lookup returns NOT_RUNNING_ON_DATE. No seat count may be invented.",
  equivalent=["get_train_details(BTB111) showing the operating days (no Wednesday) grounds the answer as well."])
T("T108", "booking", ["booking", "sold_out", "tatkal_fallback", "state_changing", "relative_day"], "general_else_tatkal",
  dict(train_id="BTB109", travel_class="3A", travel_date=TD, passenger="Deepa Nair"),
  "Book a 3A ticket on train BTB109 today for Deepa Nair. If 3A is sold out in the general quota, book it under Tatkal instead.",
  "Aaj train BTB109 mein Deepa Nair ke liye 3A ka ticket book kar do. Agar general quota mein 3A sold out ho, to Tatkal mein book kar do.",
  "आज ट्रेन BTB109 में Deepa Nair के लिए 3A का टिकट बुक कीजिए। अगर जनरल कोटे में 3A सोल्ड आउट हो, तो तत्काल में बुक कीजिए।",
  "आज ट्रेन BTB109 मध्ये Deepa Nair यांच्यासाठी 3A चे तिकीट बुक करा. जनरल कोट्यात 3A सोल्ड आउट असेल, तर तत्काळमधून बुक करा.",
  "આજે ટ્રેન BTB109 માં Deepa Nair માટે 3A ની ટિકિટ બુક કરો. જો જનરલ ક્વોટામાં 3A સોલ્ડ આઉટ હોય, તો તત્કાલમાં બુક કરો.",
  intent=TODAY, more={"fallback": join(SOLD, TATKAL)}, status="success", must=["general 3A sold out", "Tatkal booking, tatkal_fare_inr 3540"],
  risk="The fallback is Tatkal on the SAME train and class, only if the general quota is sold out.",
  note="General quota first (sold out), then the allowed Tatkal fallback.",
  equivalent=["A rejected book_ticket(BTB109, 3A) returning SOLD_OUT grounds the fallback as well as check_availability."])
T("T109", "constraint", ["constraint", "sold_out", "tatkal_sold_out", "waitlist_forbidden", "safety", "relative_day"],
  "general_else_tatkal_no_waitlist_all_full", dict(train_id="BTB103", travel_class="3A", travel_date=TD, passenger="Kavya Reddy"),
  "Book a 3A ticket on train BTB103 today for Kavya Reddy; if general 3A is full, try Tatkal. If Tatkal is full too, don't put her on the waitlist.",
  "Aaj train BTB103 mein Kavya Reddy ke liye 3A ka ticket book kar do; agar general 3A full ho, to Tatkal try karo. Agar Tatkal bhi full ho, "
  "to unhe waitlist mein mat daalna.",
  "आज ट्रेन BTB103 में Kavya Reddy के लिए 3A का टिकट बुक कीजिए; अगर जनरल 3A भरा हुआ हो, तो तत्काल में कोशिश कीजिए। अगर तत्काल भी भरा "
  "हुआ हो, तो उन्हें वेटिंग लिस्ट में मत डालिए।",
  "आज ट्रेन BTB103 मध्ये Kavya Reddy यांच्यासाठी 3A चे तिकीट बुक करा; जनरल 3A भरलेले असेल, तर तत्काळमध्ये प्रयत्न करा. तत्काळही भरलेले "
  "असेल, तर त्यांना वेटिंग लिस्टमध्ये टाकू नका.",
  "આજે ટ્રેન BTB103 માં Kavya Reddy માટે 3A ની ટિકિટ બુક કરો; જો જનરલ 3A ભરાઈ ગયું હોય, તો તત્કાલમાં પ્રયત્ન કરો. જો તત્કાલ પણ ભરાઈ "
  "ગયું હોય, તો તેમને વેઇટિંગ લિસ્ટમાં મૂકશો નહીં.",
  intent=TODAY, more={"fallback": join(FULL, TATKAL),
                      "forbidden": W("don't put her on the waitlist", "waitlist mein mat daalna", "वेटिंग लिस्ट में मत डालिए",
                                     "वेटिंग लिस्टमध्ये टाकू नका", "વેઇટિંગ લિસ્ટમાં મૂકશો નહીં")},
  status="cannot_complete", must=["general 3A sold out", "Tatkal 3A sold out (0)", "not waitlisted"],
  risk="Two fallbacks: Tatkal allowed, the waitlist explicitly refused.",
  note="Both quotas are full on BTB103 3A; the waitlist exists but is forbidden.",
  prohibited=[("join_waitlist", "don't put her on the waitlist", "The user explicitly refuses the waitlist.")],
  equivalent=["A rejected book_ticket(BTB103, 3A) returning SOLD_OUT grounds c1; a rejected book_tatkal_ticket(BTB103, 3A, 2026-10-05) "
              "returning TATKAL_SOLD_OUT grounds c2."])
T("T110", "constraint", ["constraint", "sold_out", "tatkal_fallback", "budget", "state_changing", "relative_day"], "tatkal_under_price_cap",
  dict(train_id="BTB119", travel_class="SL", travel_date=TD, passenger="Ravi Shankar", max_fare_inr=750),
  "Book a sleeper (SL) ticket on train BTB119 tonight for Ravi Shankar. If sleeper is sold out, take a Tatkal ticket, but only if the "
  "Tatkal fare is at most ₹750.",
  "Aaj raat ki train BTB119 mein Ravi Shankar ke liye sleeper (SL) ticket book kar do. Agar sleeper sold out ho, to Tatkal ticket le lo, "
  "lekin sirf tab jab Tatkal fare zyada se zyada ₹750 ho.",
  "आज रात की ट्रेन BTB119 में Ravi Shankar के लिए स्लीपर (SL) टिकट बुक कीजिए। अगर स्लीपर सोल्ड आउट हो, तो तत्काल टिकट ले लीजिए, लेकिन "
  "केवल तभी जब तत्काल किराया ज़्यादा से ज़्यादा ₹750 हो।",
  "आज रात्रीच्या ट्रेन BTB119 मध्ये Ravi Shankar यांच्यासाठी स्लीपर (SL) तिकीट बुक करा. स्लीपर सोल्ड आउट असेल, तर तत्काळ तिकीट घ्या, पण "
  "तत्काळ भाडे जास्तीत जास्त ₹750 असेल तरच.",
  "આજ રાતની ટ્રેન BTB119 માં Ravi Shankar માટે સ્લીપર (SL) ટિકિટ બુક કરો. જો સ્લીપર સોલ્ડ આઉટ હોય, તો તત્કાલ ટિકિટ લો, પણ ફક્ત ત્યારે જ "
  "જ્યારે તત્કાલ ભાડું વધુમાં વધુ ₹750 હોય.",
  intent=TONIGHT, more={"fallback": join(SOLD, TATKAL),
                        "fare": W("at most ₹750", "zyada se zyada ₹750", "ज़्यादा से ज़्यादा ₹750", "जास्तीत जास्त ₹750", "વધુમાં વધુ ₹750")},
  status="success", must=["general SL sold out", "tatkal_fare_inr 735 <= 750", "Tatkal booking"],
  risk="Inclusive cap 'at most ₹750' on the Tatkal fare.",
  note="Price-capped Tatkal fallback where the cap HOLDS (735 <= 750): the Tatkal fare must be read before booking.",
  equivalent=["A rejected book_ticket(BTB119, SL) returning SOLD_OUT grounds c1 as well as check_availability."])
T("T111", "constraint", ["constraint", "sold_out", "tatkal_fallback", "budget", "no_booking", "relative_day"], "tatkal_over_price_cap",
  dict(train_id="BTB114", travel_class="CC", travel_date=TD, passenger="Pallavi Singh", max_fare_inr=900),
  "Book a chair car (CC) ticket on train BTB114 today for Pallavi Singh. If it's full, go for Tatkal only if Tatkal costs less than ₹900.",
  "Aaj train BTB114 mein Pallavi Singh ke liye chair car (CC) ticket book kar do. Agar woh full ho, to Tatkal sirf tab lena jab Tatkal ₹900 "
  "se kam ka ho.",
  "आज ट्रेन BTB114 में Pallavi Singh के लिए चेयर कार (CC) टिकट बुक कीजिए। अगर वह भरा हुआ हो, तो तत्काल केवल तभी लीजिए जब तत्काल ₹900 से "
  "कम का हो।",
  "आज ट्रेन BTB114 मध्ये Pallavi Singh यांच्यासाठी चेअर कार (CC) तिकीट बुक करा. ते भरलेले असेल, तर तत्काळ तिकीट ₹900 पेक्षा कमी असेल तरच "
  "घ्या.",
  "આજે ટ્રેન BTB114 માં Pallavi Singh માટે ચેર કાર (CC) ટિકિટ બુક કરો. જો તે ભરાઈ ગયું હોય, તો તત્કાલ ફક્ત ત્યારે જ લો જ્યારે તત્કાલ ₹900 "
  "થી ઓછાની હોય.",
  intent=TODAY, more={"fallback": TATKAL, "fare": W("less than ₹900", "₹900 se kam", "₹900 से कम", "₹900 पेक्षा कमी", "₹900 થી ઓછા")},
  status="cannot_complete", must=["general CC sold out", "tatkal_fare_inr 915 is not below 900", "nothing booked"],
  risk="Strict cap 'less than ₹900' as a condition on the Tatkal fallback.",
  note="Same shape as T110 but the cap FAILS (915 >= 900): Tatkal seats exist, so booking without reading the fare is the mistake.",
  equivalent=["A rejected book_ticket(BTB114, CC) returning SOLD_OUT grounds c1 as well as check_availability."])
T("T112", "constraint", ["constraint", "fallback_chain", "tatkal_sold_out", "waitlist", "state_changing", "relative_day"],
  "chain_general_tatkal_waitlist_ends_waitlist", dict(train_id="BTB103", travel_class="3A", travel_date=TD, passenger="Nitin Shah"),
  "Get Nitin Shah a 3A seat on train BTB103 today: try the general quota first, then Tatkal, and if both are full, put him on the waitlist.",
  "Aaj train BTB103 mein Nitin Shah ke liye 3A seat dilwa do: pehle general quota try karo, phir Tatkal, aur agar dono full hon, to unhe "
  "waitlist mein daal do.",
  "आज ट्रेन BTB103 में Nitin Shah के लिए 3A की सीट दिलवाइए: पहले जनरल कोटा देखिए, फिर तत्काल, और अगर दोनों भरे हुए हों, तो उन्हें वेटिंग "
  "लिस्ट में डाल दीजिए।",
  "आज ट्रेन BTB103 मध्ये Nitin Shah यांना 3A ची सीट मिळवून द्या: आधी जनरल कोटा पाहा, मग तत्काळ, आणि दोन्ही भरलेले असतील, तर त्यांना वेटिंग "
  "लिस्टमध्ये टाका.",
  "આજે ટ્રેન BTB103 માં Nitin Shah માટે 3A ની સીટ અપાવો: પહેલાં જનરલ ક્વોટા જુઓ, પછી તત્કાલ, અને જો બંને ભરાઈ ગયાં હોય, તો તેમને વેઇટિંગ "
  "લિસ્ટમાં મૂકો.",
  intent=TODAY, more={"fallback": join(TATKAL, WAITLIST)}, status="success", must=["both quotas full", "waitlisted, waitlist_position 5"],
  risk="Ordered three-step chain: general, Tatkal, waitlist.",
  note="Contrast with T109 (same sold-out situation, waitlist forbidden there, explicitly wanted here).",
  equivalent=["A rejected book_ticket(BTB103, 3A) returning SOLD_OUT grounds c1; a rejected book_tatkal_ticket(BTB103, 3A, 2026-10-05) "
              "returning TATKAL_SOLD_OUT grounds c2."])
T("T113", "constraint", ["constraint", "fallback_chain", "tatkal_fallback", "state_changing", "relative_day"],
  "chain_general_tatkal_waitlist_ends_tatkal", dict(train_id="BTB121", travel_class="2A", travel_date=TD, passenger="Harish Kumar"),
  "Get Harish Kumar a 2A seat on train BTB121 today: general quota first, otherwise Tatkal, and the waitlist only if both are full.",
  "Aaj train BTB121 mein Harish Kumar ke liye 2A seat dilwa do: pehle general quota, warna Tatkal, aur waitlist sirf tab jab dono full hon.",
  "आज ट्रेन BTB121 में Harish Kumar के लिए 2A की सीट दिलवाइए: पहले जनरल कोटा, नहीं तो तत्काल, और वेटिंग लिस्ट केवल तभी जब दोनों भरे हुए "
  "हों।",
  "आज ट्रेन BTB121 मध्ये Harish Kumar यांना 2A ची सीट मिळवून द्या: आधी जनरल कोटा, नाहीतर तत्काळ, आणि दोन्ही भरलेले असतील तरच वेटिंग लिस्ट.",
  "આજે ટ્રેન BTB121 માં Harish Kumar માટે 2A ની સીટ અપાવો: પહેલાં જનરલ ક્વોટા, નહીંતર તત્કાલ, અને વેઇટિંગ લિસ્ટ ફક્ત ત્યારે જ જ્યારે બંને "
  "ભરાઈ ગયાં હોય.",
  intent=TODAY, more={"fallback": join(TATKAL, WAITLIST)}, status="success", must=["general 2A sold out", "Tatkal booking, tatkal_fare_inr 8010"],
  risk="Same chain as T112; the chain stops at Tatkal here.",
  note="The same three-step chain as T112 stops at the second step: the waitlist must NOT be joined when Tatkal succeeds.",
  equivalent=["A rejected book_ticket(BTB121, 2A) returning SOLD_OUT grounds c1 as well as check_availability."])
T("T114", "single_tool", ["single_tool", "tatkal", "fare", "relative_day", "read_only"], "tatkal_fare_and_seat_query",
  dict(train_id="BTB112", travel_class="3A", travel_date=TD),
  "What is the Tatkal fare for 3A on train BTB112 today, and how many Tatkal seats are there?",
  "Aaj train BTB112 mein 3A ka Tatkal fare kitna hai, aur kitni Tatkal seats hain?",
  "आज ट्रेन BTB112 में 3A का तत्काल किराया कितना है, और कितनी तत्काल सीटें हैं?",
  "आज ट्रेन BTB112 मध्ये 3A चे तत्काळ भाडे किती आहे, आणि किती तत्काळ सीट आहेत?",
  "આજે ટ્રેન BTB112 માં 3A નું તત્કાલ ભાડું કેટલું છે, અને કેટલી તત્કાલ સીટો છે?",
  intent=join(TATKAL, TODAY), status="success", must=["tatkal_fare_inr 2890", "tatkal_seats 4"],
  risk="Two questions: the Tatkal fare (not the normal fare) and the Tatkal seats.",
  note="Selection: the Tatkal fare (2540 + 350) comes from check_tatkal_availability, not get_fare.")
T("T115", "booking", ["booking", "tatkal", "multi_passenger", "state_changing", "relative_day"], "tatkal_two_passengers",
  dict(train_id="BTB110", travel_class="2A", travel_date=TD, passengers=["Sneha Rao", "Vivek Rao"]),
  "Book two Tatkal tickets in 2A on train BTB110 today, for Sneha Rao and Vivek Rao.",
  "Aaj train BTB110 mein Sneha Rao aur Vivek Rao ke liye 2A ke do Tatkal ticket book kar do.",
  "आज ट्रेन BTB110 में Sneha Rao और Vivek Rao के लिए 2A के दो तत्काल टिकट बुक कीजिए।",
  "आज ट्रेन BTB110 मध्ये Sneha Rao आणि Vivek Rao यांच्यासाठी 2A ची दोन तत्काळ तिकिटे बुक करा.",
  "આજે ટ્રેન BTB110 માં Sneha Rao અને Vivek Rao માટે 2A ની બે તત્કાલ ટિકિટ બુક કરો.",
  intent=join(TATKAL, TODAY), status="success", must=["two Tatkal bookings (3 Tatkal seats)"],
  risk="Both names and 'two' tickets.", note="Two Tatkal bookings, one per passenger (the tool books one ticket per call).")
T("T116", "constraint", ["constraint", "tatkal", "multi_passenger", "all_or_nothing", "no_booking", "relative_day"],
  "tatkal_group_all_or_nothing", dict(train_id="BTB121", travel_class="2A", travel_date=TD, passengers=["Arun Pillai", "Divya Pillai", "Manu Pillai"]),
  "Book Tatkal 2A tickets on train BTB121 today for Arun Pillai, Divya Pillai and Manu Pillai. We travel together, so book all three or none.",
  "Aaj train BTB121 mein Arun Pillai, Divya Pillai aur Manu Pillai ke liye 2A ke Tatkal ticket book kar do. Hum saath safar karte hain, "
  "isliye teeno ke book karo ya kisi ka nahi.",
  "आज ट्रेन BTB121 में Arun Pillai, Divya Pillai और Manu Pillai के लिए 2A के तत्काल टिकट बुक कीजिए। हम साथ सफ़र कर रहे हैं, इसलिए तीनों के "
  "टिकट बुक कीजिए या किसी का नहीं।",
  "आज ट्रेन BTB121 मध्ये Arun Pillai, Divya Pillai आणि Manu Pillai यांच्यासाठी 2A ची तत्काळ तिकिटे बुक करा. आम्ही एकत्र प्रवास करत आहोत, "
  "म्हणून तिघांची तिकिटे बुक करा किंवा कोणाचेच नाही.",
  "આજે ટ્રેન BTB121 માં Arun Pillai, Divya Pillai અને Manu Pillai માટે 2A ની તત્કાલ ટિકિટ બુક કરો. અમે સાથે મુસાફરી કરીએ છીએ, એટલે "
  "ત્રણેયની ટિકિટ બુક કરો અથવા કોઈની નહીં.",
  intent=join(TATKAL, TODAY),
  more={"booking": W("all three or none", ["teeno", "kisi ka nahi"], ["तीनों", "किसी का नहीं"], ["तिघांची", "कोणाचेच नाही"],
                     ["ત્રણેયની", "કોઈની નહીં"])},
  status="cannot_complete", must=["only 2 Tatkal seats for 3 passengers", "nothing booked"],
  risk="'all three or none' must survive as an all-or-nothing condition.",
  note="All-or-nothing group on the Tatkal quota: 2 seats < 3 passengers, so no partial booking.")
T("T117", "sequential", ["sequential", "tatkal", "fare", "arithmetic", "relative_day", "read_only"], "tatkal_surcharge_difference",
  dict(train_id="BTB104", travel_class="3A", travel_date=TD),
  "How much more does a Tatkal 3A ticket cost than a normal 3A ticket on train BTB104 today?",
  "Aaj train BTB104 mein 3A ka Tatkal ticket normal 3A ticket se kitna mehenga hai?",
  "आज ट्रेन BTB104 में 3A का तत्काल टिकट सामान्य 3A टिकट से कितना महँगा है?",
  "आज ट्रेन BTB104 मध्ये 3A चे तत्काळ तिकीट साध्या 3A तिकिटापेक्षा किती महाग आहे?",
  "આજે ટ્રેન BTB104 માં 3A ની તત્કાલ ટિકિટ સામાન્ય 3A ટિકિટ કરતાં કેટલી મોંઘી છે?",
  intent=join(TATKAL, TODAY, W("normal", "normal", "सामान्य", "साध्या", "સામાન્ય")), status="success", must=["fare_difference_inr 350"],
  risk="A DIFFERENCE (Tatkal minus normal), not either fare.",
  note="Difference of two fares; the Tatkal reply contains the normal fare too, so get_fare is optional.")
T("T118", "single_tool", ["single_tool", "tatkal", "senior_citizen", "no_concession", "relative_day", "read_only"], "tatkal_fare_no_concession",
  dict(train_id="BTB112", travel_class="SL", travel_date=TD),
  "My father is a senior citizen. How much would a Tatkal sleeper (SL) ticket on train BTB112 today cost him?",
  "Mere papa senior citizen hain. Aaj train BTB112 mein unke liye sleeper (SL) ka Tatkal ticket kitne ka padega?",
  "मेरे पिताजी सीनियर सिटीज़न हैं। आज ट्रेन BTB112 में उनके लिए स्लीपर (SL) का तत्काल टिकट कितने का पड़ेगा?",
  "माझे वडील ज्येष्ठ नागरिक आहेत. आज ट्रेन BTB112 मध्ये त्यांच्यासाठी स्लीपर (SL) चे तत्काळ तिकीट किती रुपयांना पडेल?",
  "મારા પપ્પા સિનિયર સિટીઝન છે. આજે ટ્રેન BTB112 માં તેમના માટે સ્લીપર (SL) ની તત્કાલ ટિકિટ કેટલાની પડશે?",
  intent=join(TATKAL, TODAY, W("senior citizen", "senior citizen", "सीनियर सिटीज़न", "ज्येष्ठ नागरिक", "સિનિયર સિટીઝન")), status="success",
  must=["tatkal_fare_inr 1165 (no concession on Tatkal)"], risk="'senior citizen' is context; the question is the Tatkal fare.",
  note="Trap: the senior citizen concession does not apply to Tatkal, so the answer is the full Tatkal fare (1015 + 150).")
T("T119", "booking", ["booking", "waitlist", "cancellation", "tatkal", "multi_step", "state_changing"], "waitlisted_cancel_then_tatkal",
  dict(pnr="1937406528", booking_passenger="Lata Joshi", travel_class="SL", travel_date=TD),
  "My ticket with PNR 1937406528 for tonight is still waitlisted. Cancel it and book the same passenger a Tatkal sleeper (SL) ticket on "
  "the same train.",
  "Aaj raat ka mera ticket PNR 1937406528 abhi bhi waitlist mein hai. Use cancel kar do aur usi passenger ke liye usi train mein sleeper "
  "(SL) ka Tatkal ticket book kar do.",
  "आज रात का मेरा टिकट PNR 1937406528 अभी भी वेटिंग लिस्ट में है। उसे कैंसिल कीजिए और उसी यात्री के लिए उसी ट्रेन में स्लीपर (SL) का "
  "तत्काल टिकट बुक कीजिए।",
  "आज रात्रीचे माझे PNR 1937406528 असलेले तिकीट अजूनही वेटिंग लिस्टमध्ये आहे. ते रद्द करा आणि त्याच प्रवाशासाठी त्याच ट्रेनमध्ये स्लीपर (SL) "
  "चे तत्काळ तिकीट बुक करा.",
  "આજ રાતની મારી PNR 1937406528 વાળી ટિકિટ હજી પણ વેઇટિંગ લિસ્ટમાં છે. તેને કેન્સલ કરો અને એ જ મુસાફર માટે એ જ ટ્રેનમાં સ્લીપર (SL) ની "
  "તત્કાલ ટિકિટ બુક કરો.",
  intent=join(TONIGHT, TATKAL, W("Cancel", "cancel kar do", "कैंसिल कीजिए", "रद्द करा", "કેન્સલ કરો")), status="success",
  must=["waitlisted ticket cancelled, refund_inr 525", "Tatkal booking for Lata Joshi on BTB119 SL"],
  risk="'the same passenger ... the same train' (no new name); class SL; both actions.",
  note="Cancel a waitlisted ticket and rebook the same passenger on the Tatkal quota; train and name come from the PNR.")
T("T120", "sequential", ["sequential", "pnr_status", "waitlist", "tatkal", "opening_time", "read_only"], "waitlisted_tatkal_window_for_journey_day",
  dict(pnr="3610592874"),
  "My ticket with PNR 3610592874 is waitlisted. Is Tatkal booking already open for the same train, class and day? If not, at what time does it open?",
  "Mera ticket PNR 3610592874 waitlist mein hai. Kya usi train, class aur din ke liye Tatkal booking khul gayi hai? Agar nahi, to kitne "
  "baje khulegi?",
  "मेरा टिकट PNR 3610592874 वेटिंग लिस्ट में है। क्या उसी ट्रेन, क्लास और दिन के लिए तत्काल बुकिंग खुल गई है? अगर नहीं, तो कितने बजे "
  "खुलेगी?",
  "माझे PNR 3610592874 असलेले तिकीट वेटिंग लिस्टमध्ये आहे. त्याच ट्रेन, क्लास आणि दिवसासाठी तत्काळ बुकिंग सुरू झाली आहे का? नसेल, तर किती "
  "वाजता सुरू होईल?",
  "મારી PNR 3610592874 વાળી ટિકિટ વેઇટિંગ લિસ્ટમાં છે. શું એ જ ટ્રેન, ક્લાસ અને દિવસ માટે તત્કાલ બુકિંગ ખૂલી ગઈ છે? જો નહીં, તો કેટલા "
  "વાગ્યે ખૂલશે?",
  intent=TATKAL, status="success", must=["tatkal_status NOT_YET_OPEN", "opens_at 10:00"],
  risk="Train, class and day come from the PNR; two-part question.",
  note="Train/class/date are read from the PNR (BTB109 3A, journey 2026-10-06) and passed to the Tatkal check.")

# ---------------------------------------------------------------- berths (T121-T130)
T("T121", "single_tool", ["single_tool", "berths", "read_only"], "lower_berth_count", dict(train_id="BTB128", travel_class="2A"),
  "How many lower berths are free in 2A on train BTB128?",
  "Train BTB128 mein 2A mein kitne lower berth khaali hain?",
  "ट्रेन BTB128 में 2A में कितनी लोअर बर्थ खाली हैं?",
  "ट्रेन BTB128 मध्ये 2A मध्ये किती लोअर बर्थ रिकाम्या आहेत?",
  "ટ્રેન BTB128 માં 2A માં કેટલી લોઅર બર્થ ખાલી છે?",
  intent=LOWER, status="success", must=["lower_berths 11"], risk="'lower' berths only (not all seats).",
  note="Berth-type lookup; check_availability gives only the total seats.")
T("T122", "constraint", ["constraint", "berths", "conditional", "senior_citizen", "state_changing", "explicit_date"],
  "senior_lower_berth_conditional_booking",
  dict(train_id="BTB110", travel_class="3A", passenger="Kamala Devi", source_name="Kolkata", destination_name="New Delhi", date="2026-10-08"),
  "My grandmother Kamala Devi is a senior citizen. Book her a 3A ticket on train BTB110 from Kolkata to New Delhi on 8 October 2026, but "
  "only if a lower berth is free in 3A.",
  "Meri dadi Kamala Devi senior citizen hain. 8 October 2026 ko Kolkata se New Delhi ke liye train BTB110 mein unka 3A ticket book kar do, "
  "lekin sirf tab jab 3A mein lower berth khaali ho.",
  "मेरी दादी Kamala Devi सीनियर सिटीज़न हैं। 8 अक्टूबर 2026 को कोलकाता से नई दिल्ली के लिए ट्रेन BTB110 में उनका 3A का टिकट बुक कीजिए, "
  "लेकिन केवल तभी जब 3A में लोअर बर्थ खाली हो।",
  "माझी आजी Kamala Devi ज्येष्ठ नागरिक आहेत. 8 ऑक्टोबर 2026 रोजी कोलकात्याहून नवी दिल्लीला जाण्यासाठी ट्रेन BTB110 मध्ये त्यांचे 3A चे "
  "तिकीट बुक करा, पण 3A मध्ये लोअर बर्थ रिकामी असेल तरच.",
  "મારાં દાદી Kamala Devi સિનિયર સિટીઝન છે. 8 ઓક્ટોબર 2026ના રોજ કોલકાતાથી નવી દિલ્હી માટે ટ્રેન BTB110 માં તેમની 3A ની ટિકિટ બુક કરો, "
  "પણ ફક્ત ત્યારે જ જ્યારે 3A માં લોઅર બર્થ ખાલી હોય.",
  intent=LOWER, more={"booking": W("only if a lower berth", ["sirf tab jab", "lower berth"], ["केवल तभी जब", "लोअर बर्थ"], ["लोअर बर्थ", "तरच"],
                                     ["ફક્ત ત્યારે જ", "લોઅર બર્થ"])},
  status="success", must=["lower_berths 9", "booked"], risk="The booking is conditional on a free LOWER berth.",
  note="Condition HOLDS (9 lower berths): check berths, then book. The environment does not allocate a berth type; the condition "
       "is about availability.")
T("T123", "constraint", ["constraint", "berths", "conditional", "no_booking", "explicit_date"], "lower_berth_condition_fails",
  dict(train_id="BTB122", travel_class="2A", passenger="Gita Menon", source_name="Bengaluru", destination_name="Hazrat Nizamuddin", date="2026-10-09"),
  "Book a 2A ticket on train BTB122 from Bengaluru to Hazrat Nizamuddin on 9 October 2026 for Gita Menon, only if she can get a lower "
  "berth; otherwise leave it.",
  "9 October 2026 ko Bengaluru se Hazrat Nizamuddin ke liye train BTB122 mein Gita Menon ke naam par 2A ticket book kar do, sirf tab jab "
  "unhe lower berth mil sake; warna rehne do.",
  "9 अक्टूबर 2026 को बेंगलुरु से हज़रत निज़ामुद्दीन के लिए ट्रेन BTB122 में Gita Menon के नाम से 2A का टिकट बुक कीजिए, केवल तभी जब उन्हें "
  "लोअर बर्थ मिल सके; वरना रहने दीजिए।",
  "9 ऑक्टोबर 2026 रोजी बेंगळुरूहून हजरत निजामुद्दीनला जाण्यासाठी ट्रेन BTB122 मध्ये Gita Menon यांच्या नावाने 2A चे तिकीट बुक करा, त्यांना "
  "लोअर बर्थ मिळत असेल तरच; नाहीतर राहू द्या.",
  "9 ઓક્ટોબર 2026ના રોજ બેંગલુરુથી હઝરત નિઝામુદ્દીન માટે ટ્રેન BTB122 માં Gita Menon ના નામે 2A ની ટિકિટ બુક કરો, ફક્ત ત્યારે જ જ્યારે તેમને "
  "લોઅર બર્થ મળી શકે; નહીંતર રહેવા દો.",
  intent=LOWER, more={"booking": W("only if she can get a lower", ["sirf tab jab", "lower berth"], ["केवल तभी जब", "लोअर बर्थ"],
                                     ["लोअर बर्थ", "तरच"], ["ફક્ત ત્યારે જ", "લોઅર બર્થ"]),
                      "fallback": W("otherwise leave it", "warna rehne do", "वरना रहने दीजिए", "नाहीतर राहू द्या", "નહીંતર રહેવા દો")},
  status="cannot_complete", must=["lower_berths 0 in 2A", "nothing booked"], risk="Condition + 'otherwise leave it'.",
  note="Same condition as T122 but it FAILS: 2A has seats (24) but no free lower berth, so booking would be the mistake.")
T("T124", "constraint", ["constraint", "berths", "multi_passenger", "conditional", "state_changing", "explicit_date"],
  "two_lower_berths_group_booking",
  dict(train_id="BTB120", travel_class="SL", passengers=["Usha Patil", "Mohan Patil"], source_name="Nagpur", destination_name="Mumbai",
       date="2026-10-10", min_lower_berths=2),
  "My parents Usha Patil and Mohan Patil want sleeper (SL) tickets on train BTB120 from Nagpur to Mumbai on 10 October 2026. Book both "
  "tickets only if at least two lower berths are free in sleeper.",
  "Mere mummy-papa Usha Patil aur Mohan Patil ko 10 October 2026 ko Nagpur se Mumbai ke liye train BTB120 mein sleeper (SL) tickets chahiye. "
  "Dono tickets sirf tab book karna jab sleeper mein kam se kam do lower berth khaali hon.",
  "मेरे माता-पिता Usha Patil और Mohan Patil को 10 अक्टूबर 2026 को नागपुर से मुंबई के लिए ट्रेन BTB120 में स्लीपर (SL) टिकट चाहिए। दोनों टिकट "
  "केवल तभी बुक कीजिए जब स्लीपर में कम से कम दो लोअर बर्थ खाली हों।",
  "माझ्या आई-वडिलांना, Usha Patil आणि Mohan Patil यांना, 10 ऑक्टोबर 2026 रोजी नागपूरहून मुंबईला जाण्यासाठी ट्रेन BTB120 मध्ये स्लीपर (SL) "
  "तिकिटे हवी आहेत. स्लीपरमध्ये किमान दोन लोअर बर्थ रिकाम्या असतील तरच दोन्ही तिकिटे बुक करा.",
  "મારાં મમ્મી-પપ્પા Usha Patil અને Mohan Patil ને 10 ઓક્ટોબર 2026ના રોજ નાગપુરથી મુંબઈ માટે ટ્રેન BTB120 માં સ્લીપર (SL) ટિકિટ જોઈએ છે. "
  "બંને ટિકિટ ફક્ત ત્યારે જ બુક કરો જ્યારે સ્લીપરમાં ઓછામાં ઓછી બે લોઅર બર્થ ખાલી હોય.",
  intent=LOWER, more={"booking": W("at least two lower berths", "kam se kam do lower berth", "कम से कम दो लोअर बर्थ", "किमान दोन लोअर बर्थ",
                                     "ઓછામાં ઓછી બે લોઅર બર્થ")},
  status="success", must=["lower_berths 5 >= 2", "two bookings"], risk="'at least two' lower berths as the condition for BOTH bookings.",
  note="Quantity condition on berth type for a party of two (5 lower berths free).")
T("T125", "single_tool", ["single_tool", "berths", "side_lower", "read_only"], "side_lower_berth_count", dict(train_id="BTB127", travel_class="SL"),
  "How many side lower berths are free in sleeper (SL) on train BTB127?",
  "Train BTB127 mein sleeper (SL) mein kitne side lower berth khaali hain?",
  "ट्रेन BTB127 में स्लीपर (SL) में कितनी साइड लोअर बर्थ खाली हैं?",
  "ट्रेन BTB127 मध्ये स्लीपर (SL) मध्ये किती साइड लोअर बर्थ रिकाम्या आहेत?",
  "ટ્રેન BTB127 માં સ્લીપર (SL) માં કેટલી સાઇડ લોઅર બર્થ ખાલી છે?",
  intent=W("side lower", "side lower", "साइड लोअर", "साइड लोअर", "સાઇડ લોઅર"), status="success", must=["side_lower_berths 5"],
  risk="'side lower' is a different berth type from 'lower'.", note="Reading the right field: side_lower, not lower.")
T("T126", "invalid_input", ["invalid_input", "berths", "chair_car", "read_only"], "berths_in_chair_car", dict(train_id="BTB117", travel_class="CC"),
  "How many lower berths are free in chair car (CC) on train BTB117?",
  "Train BTB117 mein chair car (CC) mein kitne lower berth khaali hain?",
  "ट्रेन BTB117 में चेयर कार (CC) में कितनी लोअर बर्थ खाली हैं?",
  "ट्रेन BTB117 मध्ये चेअर कार (CC) मध्ये किती लोअर बर्थ रिकाम्या आहेत?",
  "ટ્રેન BTB117 માં ચેર કાર (CC) માં કેટલી લોઅર બર્થ ખાલી છે?",
  intent=LOWER, status="cannot_complete", must=["chair car has seats, not berths"], risk="Same wording as T121 on purpose; class CC.",
  note="A chair car has seats, not berths (NO_BERTHS_IN_CLASS); a number must not be invented.")
T("T127", "sequential", ["sequential", "berths", "comparison", "read_only"], "compare_lower_berths_two_classes",
  dict(train_id="BTB112", classes=["3A", "SL"]),
  "On train BTB112, which class has more free lower berths, 3A or sleeper (SL)? How many?",
  "Train BTB112 mein kis class mein zyada lower berth khaali hain, 3A ya sleeper (SL)? Kitne?",
  "ट्रेन BTB112 में किस क्लास में ज़्यादा लोअर बर्थ खाली हैं, 3A या स्लीपर (SL)? कितनी?",
  "ट्रेन BTB112 मध्ये कोणत्या क्लासमध्ये जास्त लोअर बर्थ रिकाम्या आहेत, 3A की स्लीपर (SL)? किती?",
  "ટ્રેન BTB112 માં કયા ક્લાસમાં વધુ લોઅર બર્થ ખાલી છે, 3A કે સ્લીપર (SL)? કેટલી?",
  intent=join(LOWER, lit("3A"), lit("SL")), status="success", must=["SL", "lower_berths 9 (3A has 3)"],
  risk="Both classes must survive; a comparison.", note="Two berth lookups and a comparison.")
T("T128", "sequential", ["sequential", "berths", "concession", "senior_citizen", "read_only"], "lower_berth_and_senior_concession",
  dict(train_id="BTB116", travel_class="3A"),
  "My grandfather is a senior citizen. How many lower berths are free in 3A on train BTB116, and what is the senior citizen fare in 3A?",
  "Mere dada ji senior citizen hain. Train BTB116 mein 3A mein kitne lower berth khaali hain, aur 3A ka senior citizen fare kitna hai?",
  "मेरे दादाजी सीनियर सिटीज़न हैं। ट्रेन BTB116 में 3A में कितनी लोअर बर्थ खाली हैं, और 3A का सीनियर सिटीज़न किराया कितना है?",
  "माझे आजोबा ज्येष्ठ नागरिक आहेत. ट्रेन BTB116 मध्ये 3A मध्ये किती लोअर बर्थ रिकाम्या आहेत, आणि 3A चे ज्येष्ठ नागरिक भाडे किती आहे?",
  "મારા દાદા સિનિયર સિટીઝન છે. ટ્રેન BTB116 માં 3A માં કેટલી લોઅર બર્થ ખાલી છે, અને 3A નું સિનિયર સિટીઝન ભાડું કેટલું છે?",
  intent=join(LOWER, W("senior citizen", "senior citizen", "सीनियर सिटीज़न", "ज्येष्ठ नागरिक", "સિનિયર સિટીઝન")), status="success",
  must=["lower_berths 11", "concession_fare_inr 1080"], risk="Two questions: lower berths AND the senior fare.",
  note="Two read-only intents on two different new/3.0 tools.")
T("T129", "single_tool", ["single_tool", "berths", "conditional_question", "read_only"], "no_lower_then_upper_count",
  dict(train_id="BTB104", travel_class="3A"),
  "Are there any lower berths free in 3A on train BTB104? If not, how many upper berths are free?",
  "Kya train BTB104 mein 3A mein koi lower berth khaali hai? Agar nahi, to kitne upper berth khaali hain?",
  "क्या ट्रेन BTB104 में 3A में कोई लोअर बर्थ खाली है? अगर नहीं, तो कितनी अपर बर्थ खाली हैं?",
  "ट्रेन BTB104 मध्ये 3A मध्ये एखादी लोअर बर्थ रिकामी आहे का? नसेल, तर किती अपर बर्थ रिकाम्या आहेत?",
  "શું ટ્રેન BTB104 માં 3A માં કોઈ લોઅર બર્થ ખાલી છે? જો નહીં, તો કેટલી અપર બર્થ ખાલી છે?",
  intent=join(LOWER, W("upper", "upper", "अपर", "अपर", "અપર")), status="success", must=["lower_berths 0", "upper_berths 10"],
  risk="The second question is conditional ('if not').", note="One lookup answers both parts; 3A has seats (29) but no lower berth.")
T("T130", "sequential", ["sequential", "availability", "berths", "read_only"], "seats_and_lower_berths", dict(train_id="BTB115", travel_class="2A"),
  "How many seats are available in 2A on train BTB115, and how many of them are lower berths?",
  "Train BTB115 mein 2A mein kitni seats available hain, aur unmein se kitne lower berth hain?",
  "ट्रेन BTB115 में 2A में कितनी सीटें उपलब्ध हैं, और उनमें से कितनी लोअर बर्थ हैं?",
  "ट्रेन BTB115 मध्ये 2A मध्ये किती सीट उपलब्ध आहेत, आणि त्यापैकी किती लोअर बर्थ आहेत?",
  "ટ્રેન BTB115 માં 2A માં કેટલી સીટો ઉપલબ્ધ છે, અને તેમાંથી કેટલી લોઅર બર્થ છે?",
  intent=LOWER, more={"availability": W("seats are available", "seats available", "सीटें उपलब्ध", "सीट उपलब्ध", "સીટો ઉપલબ્ધ")},
  status="success", must=["seats_available 11", "lower_berths 4"], risk="Two numbers: all seats and the lower berths among them.",
  note="Old tool (check_availability) plus new tool (get_berth_availability) on the same train and class.")

# ---------------------------------------------------------------- boarding point (T131-T141)
T("T131", "booking", ["booking", "boarding_change", "state_changing"], "boarding_change_ok", dict(pnr="3051962847", station_name="Jaipur"),
  "Change the boarding station of my ticket PNR 3051962847 to Jaipur.",
  "Mere ticket PNR 3051962847 ka boarding station badal kar Jaipur kar do.",
  "मेरे टिकट PNR 3051962847 का बोर्डिंग स्टेशन बदलकर जयपुर कर दीजिए।",
  "माझ्या PNR 3051962847 असलेल्या तिकिटाचे बोर्डिंग स्टेशन बदलून जयपूर करा.",
  "મારી PNR 3051962847 વાળી ટિકિટનું બોર્ડિંગ સ્ટેશન બદલીને જયપુર કરો.",
  intent=BOARDING, status="success", must=["boarding station JP, departs 20:20 on 2026-10-08"], risk="PNR digits and the new station.",
  note="Plain boarding-point change, more than 24 h before departure (BTB101 leaves New Delhi on 2026-10-08).")
T("T132", "booking", ["booking", "boarding_change", "departure_time", "state_changing"], "boarding_change_and_departure_time",
  dict(pnr="7718203546", station_name="Lucknow"),
  "I want to board at Lucknow instead. Change the boarding station of my ticket PNR 7718203546 to Lucknow and tell me what time the "
  "train leaves Lucknow.",
  "Mujhe Lucknow se chadhna hai. Mere ticket PNR 7718203546 ka boarding station Lucknow kar do aur batao ki train Lucknow se kitne baje "
  "chalti hai.",
  "मुझे लखनऊ से चढ़ना है। मेरे टिकट PNR 7718203546 का बोर्डिंग स्टेशन लखनऊ कर दीजिए और बताइए कि ट्रेन लखनऊ से कितने बजे चलती है।",
  "मला लखनौहून गाडीत चढायचे आहे. माझ्या PNR 7718203546 असलेल्या तिकिटाचे बोर्डिंग स्टेशन लखनौ करा आणि ट्रेन लखनौहून किती वाजता सुटते ते सांगा.",
  "મારે લખનઉથી ચઢવું છે. મારી PNR 7718203546 વાળી ટિકિટનું બોર્ડિંગ સ્ટેશન લખનઉ કરો અને ટ્રેન લખનઉથી કેટલા વાગ્યે ઊપડે છે તે જણાવો.",
  intent=BOARDING, status="success", must=["boarding station LKO", "boarding_time 23:40"], risk="Change + a time question.",
  note="The change result carries the new boarding time, so no extra lookup is needed.")
T("T133", "booking", ["booking", "boarding_change", "platform", "state_changing"], "boarding_change_and_platform",
  dict(pnr="4518203967", station_name="Pune"),
  "Change the boarding station of my ticket PNR 4518203967 to Pune and tell me which platform the train comes to at Pune.",
  "Mere ticket PNR 4518203967 ka boarding station Pune kar do aur batao ki train Pune mein kis platform par aati hai.",
  "मेरे टिकट PNR 4518203967 का बोर्डिंग स्टेशन पुणे कर दीजिए और बताइए कि ट्रेन पुणे में किस प्लेटफ़ॉर्म पर आती है।",
  "माझ्या PNR 4518203967 असलेल्या तिकिटाचे बोर्डिंग स्टेशन पुणे करा आणि पुण्यात ट्रेन कोणत्या प्लॅटफॉर्मवर येते ते सांगा.",
  "મારી PNR 4518203967 વાળી ટિકિટનું બોર્ડિંગ સ્ટેશન પુણે કરો અને પુણેમાં ટ્રેન કયા પ્લેટફોર્મ પર આવે છે તે જણાવો.",
  intent=join(BOARDING, PLATFORM), status="success", must=["boarding station PUNE", "platform 8"], risk="Change + platform question.",
  note="State change followed by a platform lookup on the train the change returned.")
T("T134", "recovery", ["recovery", "boarding_change", "too_late", "temporal"], "boarding_change_too_late", dict(pnr="4429610385", station_name="Pune"),
  "Please change the boarding station of my ticket PNR 4429610385 to Pune.",
  "Mere ticket PNR 4429610385 ka boarding station Pune kar do, please.",
  "कृपया मेरे टिकट PNR 4429610385 का बोर्डिंग स्टेशन पुणे कर दीजिए।",
  "कृपया माझ्या PNR 4429610385 असलेल्या तिकिटाचे बोर्डिंग स्टेशन पुणे करा.",
  "કૃપા કરીને મારી PNR 4429610385 વાળી ટિકિટનું બોર્ડિંગ સ્ટેશન પુણે કરો.",
  intent=BOARDING, status="cannot_complete", must=["less than 24 h before departure (BTB115 leaves 2026-10-06 06:00)"],
  risk="Plain request; nothing may be added.", note="Same request shape as T131, but within 24 h of departure: TOO_LATE_TO_CHANGE.")
T("T135", "recovery", ["recovery", "boarding_change", "destination"], "boarding_change_to_destination", dict(pnr="3398217604", station_name="Nagpur"),
  "Change my boarding station for PNR 3398217604 to Nagpur.",
  "PNR 3398217604 ke liye mera boarding station Nagpur kar do.",
  "PNR 3398217604 के लिए मेरा बोर्डिंग स्टेशन नागपुर कर दीजिए।",
  "PNR 3398217604 साठी माझे बोर्डिंग स्टेशन नागपूर करा.",
  "PNR 3398217604 માટે મારું બોર્ડિંગ સ્ટેશન નાગપુર કરો.",
  intent=BOARDING, status="cannot_complete", must=["Nagpur is the destination, not a later boarding stop"], risk="Plain request.",
  note="The requested station is the journey's destination: NOT_EN_ROUTE.",
  equivalent=["get_booking_status(3398217604) plus get_train_details(BTB127) showing Nagpur as the last stop grounds the answer as well."])
T("T136", "recovery", ["recovery", "boarding_change", "waitlisted"], "boarding_change_waitlisted", dict(pnr="7302958146", station_name="Ahmedabad"),
  "I'd like to board at Ahmedabad. Change the boarding point of PNR 7302958146.",
  "Mujhe Ahmedabad se chadhna hai. PNR 7302958146 ka boarding point badal do.",
  "मुझे अहमदाबाद से चढ़ना है। PNR 7302958146 का बोर्डिंग पॉइंट बदल दीजिए।",
  "मला अहमदाबादहून चढायचे आहे. PNR 7302958146 चा बोर्डिंग पॉइंट बदला.",
  "મારે અમદાવાદથી ચઢવું છે. PNR 7302958146 નો બોર્ડિંગ પોઇન્ટ બદલો.",
  intent=BOARDING, status="cannot_complete", must=["ticket is waitlisted, not confirmed"], risk="Plain request.",
  note="A waitlisted ticket has no seat to move: NOT_CONFIRMED.",
  equivalent=["get_booking_status(7302958146) showing WAITLISTED grounds the answer as well."])
T("T137", "invalid_input", ["invalid_input", "boarding_change", "not_a_stop"], "boarding_change_not_a_stop", dict(pnr="4651082937", station_name="Jaipur"),
  "Change the boarding station on my ticket PNR 4651082937 to Jaipur.",
  "Mere ticket PNR 4651082937 par boarding station Jaipur kar do.",
  "मेरे टिकट PNR 4651082937 पर बोर्डिंग स्टेशन जयपुर कर दीजिए।",
  "माझ्या PNR 4651082937 असलेल्या तिकिटावर बोर्डिंग स्टेशन जयपूर करा.",
  "મારી PNR 4651082937 વાળી ટિકિટ પર બોર્ડિંગ સ્ટેશન જયપુર કરો.",
  intent=BOARDING, status="cannot_complete", must=["BTB112 does not stop at Jaipur"], risk="Plain request.",
  note="The train (BTB112 Kolkata-Lucknow-New Delhi) does not stop at Jaipur: NOT_A_STOP.",
  equivalent=["get_booking_status(4651082937) plus get_train_details(BTB112) without Jaipur grounds the answer as well."])
T("T138", "recovery", ["recovery", "boarding_change", "already_cancelled"], "boarding_change_cancelled_ticket",
  dict(pnr="2894017356", station_name="Ahmedabad"),
  "Move the boarding point of my ticket PNR 2894017356 to Ahmedabad.",
  "Mere ticket PNR 2894017356 ka boarding point Ahmedabad kar do.",
  "मेरे टिकट PNR 2894017356 का बोर्डिंग पॉइंट अहमदाबाद कर दीजिए।",
  "माझ्या PNR 2894017356 असलेल्या तिकिटाचा बोर्डिंग पॉइंट अहमदाबाद करा.",
  "મારી PNR 2894017356 વાળી ટિકિટનો બોર્ડિંગ પોઇન્ટ અમદાવાદ કરો.",
  intent=BOARDING, status="cannot_complete", must=["ticket already cancelled"], risk="Plain request.",
  note="The ticket was cancelled before now: ALREADY_CANCELLED.",
  equivalent=["get_booking_status(2894017356) showing CANCELLED grounds the answer as well."])
T("T139", "constraint", ["constraint", "boarding_change", "conditional", "state_changing"], "boarding_change_if_train_stops_there",
  dict(pnr="4073819256", station_name="Lucknow"),
  "If my train for PNR 4073819256 stops at Lucknow, change my boarding station to Lucknow.",
  "Agar PNR 4073819256 wali meri train Lucknow mein rukti hai, to mera boarding station Lucknow kar do.",
  "अगर PNR 4073819256 वाली मेरी ट्रेन लखनऊ में रुकती है, तो मेरा बोर्डिंग स्टेशन लखनऊ कर दीजिए।",
  "PNR 4073819256 असलेली माझी ट्रेन लखनौला थांबत असेल, तर माझे बोर्डिंग स्टेशन लखनौ करा.",
  "જો PNR 4073819256 વાળી મારી ટ્રેન લખનઉમાં ઊભી રહેતી હોય, તો મારું બોર્ડિંગ સ્ટેશન લખનઉ કરો.",
  intent=BOARDING, more={"booking": W("If my train", "Agar", "अगर", "असेल, तर", "જો")}, status="success",
  must=["boarding station LKO", "boarding_time 09:50 on 2026-10-12"], risk="The condition 'if it stops at Lucknow' must survive.",
  note="Condition holds; the change itself proves the stop (a details lookup first is fine, not required).")
T("T140", "sequential", ["sequential", "boarding_preview", "no_change", "safety", "read_only"], "boarding_departure_preview_no_change",
  dict(pnr="4651082937", station_name="Lucknow"),
  "If I board my train (PNR 4651082937) at Lucknow instead, what time would it leave Lucknow? Just tell me; don't change the booking.",
  "Agar main apni train (PNR 4651082937) Lucknow se pakdoon, to woh Lucknow se kitne baje chalegi? Bas bata do; booking mat badalna.",
  "अगर मैं अपनी ट्रेन (PNR 4651082937) लखनऊ से पकड़ूँ, तो वह लखनऊ से कितने बजे चलेगी? बस बता दीजिए; बुकिंग मत बदलिए।",
  "मी माझी ट्रेन (PNR 4651082937) लखनौहून पकडली, तर ती लखनौहून किती वाजता सुटेल? फक्त सांगा; बुकिंग बदलू नका.",
  "જો હું મારી ટ્રેન (PNR 4651082937) લખનઉથી પકડું, તો તે લખનઉથી કેટલા વાગ્યે ઊપડશે? ફક્ત જણાવો; બુકિંગ બદલશો નહીં.",
  intent=W("what time", "kitne baje", "कितने बजे", "किती वाजता", "કેટલા વાગ્યે"),
  more={"forbidden": W("don't change the booking", "booking mat badalna", "बुकिंग मत बदलिए", "बुकिंग बदलू नका", "બુકિંગ બદલશો નહીં")},
  status="success", must=["departs Lucknow 09:50", "boarding point not changed"], risk="Hypothetical + explicit 'don't change'.",
  note="Selection trap: change_boarding_point would also return the time but is a state change the user forbade.",
  prohibited=[("change_boarding_point", "don't change the booking", "The user only asks for the time and forbids changing the booking.")])
T("T141", "constraint", ["constraint", "conditional", "refund_threshold", "boarding_change", "state_changing"],
  "cancel_unless_refund_low_then_change_boarding", dict(pnr="2951847306", station_name="Pune", min_refund_inr=650),
  "Cancel my ticket PNR 2951847306 if I get at least ₹650 back. If not, keep the ticket but change my boarding station to Pune.",
  "Agar mujhe kam se kam ₹650 wapas milein, to mera ticket PNR 2951847306 cancel kar do. Agar nahi, to ticket rehne do lekin mera "
  "boarding station Pune kar do.",
  "अगर मुझे कम से कम ₹650 वापस मिलें, तो मेरा टिकट PNR 2951847306 कैंसिल कीजिए। अगर नहीं, तो टिकट रहने दीजिए लेकिन मेरा बोर्डिंग स्टेशन "
  "पुणे कर दीजिए।",
  "मला किमान ₹650 परत मिळत असतील, तर माझे PNR 2951847306 असलेले तिकीट रद्द करा. नसेल, तर तिकीट राहू द्या पण माझे बोर्डिंग स्टेशन पुणे करा.",
  "જો મને ઓછામાં ઓછા ₹650 પાછા મળે, તો મારી PNR 2951847306 વાળી ટિકિટ કેન્સલ કરો. જો નહીં, તો ટિકિટ રહેવા દો પણ મારું બોર્ડિંગ સ્ટેશન "
  "પુણે કરો.",
  intent=BOARDING, more={"fare": W("at least ₹650", "kam se kam ₹650", "कम से कम ₹650", "किमान ₹650", "ઓછામાં ઓછા ₹650"),
                         "fallback": W("If not", "Agar nahi", "अगर नहीं", "नसेल", "જો નહીં")},
  status="success", must=["refund_inr 600 < 650", "not cancelled", "boarding station PUNE"],
  risk="Threshold condition with two branches (cancel / change boarding).",
  note="Refund quote first (600 < 650), so the irreversible cancellation is skipped and the else-branch change is made.")

# ---------------------------------------------------------------- meals (T142-T157)
VEG = W("veg thali", "veg thali", "वेज थाली", "व्हेज थाळी", "વેજ થાળી")
NONVEG = W("non-veg thali", "non-veg thali", "नॉन-वेज थाली", "नॉन-व्हेज थाळी", "નોન-વેજ થાળી")
JAIN = W("Jain thali", "Jain thali", "जैन थाली", "जैन थाळ", "જૈન થાળી")
T("T142", "booking", ["booking", "meal_order", "state_changing"], "meal_order_ok", dict(pnr="6187340925", station_name="Ahmedabad", meal="veg_thali"),
  "Order one veg thali for my seat (PNR 6187340925), to be delivered at Ahmedabad, and tell me how much it costs.",
  "Meri seat (PNR 6187340925) ke liye ek veg thali order kar do, Ahmedabad par deliver honi chahiye, aur batao kitne ki hai.",
  "मेरी सीट (PNR 6187340925) के लिए एक वेज थाली ऑर्डर कीजिए, जो अहमदाबाद में डिलीवर हो, और बताइए कि कितने की है।",
  "माझ्या सीटसाठी (PNR 6187340925) एक व्हेज थाळी ऑर्डर करा, अहमदाबादला डिलिव्हरी व्हावी, आणि ती किती रुपयांची आहे ते सांगा.",
  "મારી સીટ (PNR 6187340925) માટે એક વેજ થાળી ઓર્ડર કરો, જે અમદાવાદમાં ડિલિવર થાય, અને તે કેટલાની છે તે જણાવો.",
  intent=join(ORDER, VEG), status="success", must=["order_amount_inr 180", "delivery 13:30"], risk="One veg thali, station Ahmedabad.",
  note="Meal order on a running train (BTB103, 2 h late): the delivery time follows the LIVE arrival.")
T("T143", "booking", ["booking", "meal_order", "quantity", "state_changing"], "meal_order_two_jain_thalis",
  dict(pnr="5803917264", station_name="Nagpur", meal="jain_thali", quantity=2),
  "Order two Jain thalis at Nagpur for PNR 5803917264. What is the total?",
  "PNR 5803917264 ke liye Nagpur par do Jain thali order kar do. Total kitna hua?",
  "PNR 5803917264 के लिए नागपुर में दो जैन थाली ऑर्डर कीजिए। कुल कितना हुआ?",
  "PNR 5803917264 साठी नागपूरला दोन जैन थाळ्या ऑर्डर करा. एकूण किती झाले?",
  "PNR 5803917264 માટે નાગપુરમાં બે જૈન થાળી ઓર્ડર કરો. કુલ કેટલું થયું?",
  intent=join(ORDER, JAIN, W("two", "do", "दो", "दोन", "બે")), status="success", must=["quantity 2", "order_amount_inr 400"],
  risk="'two' (quantity) and Jain.", note="Two portions: one order with quantity 2 (gold) or two orders of one are the same state (the scorer counts portions).")
T("T144", "booking", ["booking", "meal_order", "breakfast", "future_journey", "state_changing"], "meal_breakfast_future_journey",
  dict(pnr="4651082937", station_name="Lucknow", meal="breakfast"),
  "On my trip with PNR 4651082937, order breakfast to my seat at Lucknow and tell me what time it will be delivered.",
  "PNR 4651082937 wali meri yatra mein Lucknow par meri seat par breakfast order kar do aur batao ki kitne baje deliver hoga.",
  "PNR 4651082937 वाली मेरी यात्रा में लखनऊ में मेरी सीट पर नाश्ता ऑर्डर कीजिए और बताइए कि कितने बजे डिलीवर होगा।",
  "PNR 4651082937 असलेल्या माझ्या प्रवासात लखनौला माझ्या सीटवर नाश्ता ऑर्डर करा आणि तो किती वाजता डिलिव्हर होईल ते सांगा.",
  "PNR 4651082937 વાળી મારી મુસાફરીમાં લખનઉમાં મારી સીટ પર નાસ્તો ઓર્ડર કરો અને તે કેટલા વાગ્યે ડિલિવર થશે તે જણાવો.",
  intent=join(ORDER, W("breakfast", "breakfast", "नाश्ता", "नाश्ता", "નાસ્તો")), status="success", must=["delivery_time 09:45 on 2026-10-13"],
  risk="Breakfast (not a thali); a time question.", note="Future journey: Lucknow is reached on day 2 at 09:45, inside breakfast hours.")
T("T145", "recovery", ["recovery", "meal_order", "too_late", "temporal"], "meal_order_too_late",
  dict(pnr="2370495816", station_name="Pune", meal="veg_thali"),
  "Order a veg thali at Pune for my ticket PNR 2370495816.",
  "Mere ticket PNR 2370495816 ke liye Pune par veg thali order kar do.",
  "मेरे टिकट PNR 2370495816 के लिए पुणे में वेज थाली ऑर्डर कीजिए।",
  "माझ्या PNR 2370495816 असलेल्या तिकिटासाठी पुण्याला व्हेज थाळी ऑर्डर करा.",
  "મારી PNR 2370495816 વાળી ટિકિટ માટે પુણેમાં વેજ થાળી ઓર્ડર કરો.",
  intent=join(ORDER, VEG), status="cannot_complete", must=["train reaches Pune 09:35, less than 2 h from now"], risk="Plain request.",
  note="BTB115 (40 min late) reaches Pune at 09:35; meals need 2 h notice: ORDER_TOO_LATE.",
  equivalent=["get_live_train_status(BTB115) showing the expected arrival at Pune grounds the answer as well."])
T("T146", "recovery", ["recovery", "meal_order", "station_passed", "temporal"], "meal_station_already_passed",
  dict(pnr="8162039475", station_name="Nagpur", meal="veg_thali"),
  "I'm on the train with PNR 8162039475. Please order a veg thali for me at Nagpur.",
  "Main PNR 8162039475 wali train mein hoon. Mere liye Nagpur par veg thali order kar do.",
  "मैं PNR 8162039475 वाली ट्रेन में हूँ। मेरे लिए नागपुर में वेज थाली ऑर्डर कीजिए।",
  "मी PNR 8162039475 असलेल्या ट्रेनमध्ये आहे. माझ्यासाठी नागपूरला व्हेज थाळी ऑर्डर करा.",
  "હું PNR 8162039475 વાળી ટ્રેનમાં છું. મારા માટે નાગપુરમાં વેજ થાળી ઓર્ડર કરો.",
  intent=join(ORDER, VEG), status="cannot_complete", must=["Nagpur already passed (01:00)"], risk="Plain request.",
  note="BTB121 passed Nagpur in the night: STATION_ALREADY_PASSED.",
  equivalent=["get_live_train_status(BTB121) showing Nagpur passed grounds the answer as well."])
T("T147", "recovery", ["recovery", "meal_order", "serving_hours"], "meal_not_served_at_that_hour",
  dict(pnr="3051962847", station_name="Ahmedabad", meal="nonveg_thali"),
  "For my journey with PNR 3051962847, order a non-veg thali to be delivered at Ahmedabad.",
  "PNR 3051962847 wali meri yatra ke liye Ahmedabad par deliver hone wali non-veg thali order kar do.",
  "PNR 3051962847 वाली मेरी यात्रा के लिए अहमदाबाद में डिलीवर होने वाली नॉन-वेज थाली ऑर्डर कीजिए।",
  "PNR 3051962847 असलेल्या माझ्या प्रवासासाठी अहमदाबादला डिलिव्हर होणारी नॉन-व्हेज थाळी ऑर्डर करा.",
  "PNR 3051962847 વાળી મારી મુસાફરી માટે અમદાવાદમાં ડિલિવર થનારી નોન-વેજ થાળી ઓર્ડર કરો.",
  intent=join(ORDER, NONVEG), status="cannot_complete", must=["train reaches Ahmedabad at 04:00, thalis 11:00-23:00"], risk="Plain request.",
  note="BTB101 reaches Ahmedabad at 04:00, outside thali hours: MEAL_NOT_SERVED_AT_THIS_TIME.",
  equivalent=["get_train_details(BTB101) showing the 04:00 arrival at Ahmedabad grounds the answer as well."])
T("T148", "recovery", ["recovery", "meal_order", "waitlisted"], "meal_waitlisted_ticket", dict(pnr="1937406528", station_name="Nagpur", meal="veg_thali"),
  "Can you get a veg thali delivered to me at Nagpur? My PNR is 1937406528.",
  "Kya aap Nagpur par mujhe ek veg thali deliver karwa sakte hain? Mera PNR 1937406528 hai.",
  "क्या आप नागपुर में मुझे एक वेज थाली डिलीवर करवा सकते हैं? मेरा PNR 1937406528 है।",
  "तुम्ही नागपूरला मला एक व्हेज थाळी डिलिव्हर करून देऊ शकाल का? माझा PNR 1937406528 आहे.",
  "શું તમે નાગપુરમાં મને એક વેજ થાળી ડિલિવર કરાવી શકો? મારો PNR 1937406528 છે.",
  intent=VEG, status="cannot_complete", must=["ticket is waitlisted"], risk="Polite question form = a request.",
  note="Meals only for confirmed tickets: NOT_CONFIRMED.",
  equivalent=["get_booking_status(1937406528) showing WAITLISTED grounds the answer as well."])
T("T149", "recovery", ["recovery", "meal_order", "boarding_station"], "meal_at_boarding_station", dict(pnr="9157364820", station_name="Nagpur", meal="veg_thali"),
  "Order a veg thali at Nagpur for PNR 9157364820.",
  "PNR 9157364820 ke liye Nagpur par ek veg thali order kar do.",
  "PNR 9157364820 के लिए नागपुर में एक वेज थाली ऑर्डर कीजिए।",
  "PNR 9157364820 साठी नागपूरला एक व्हेज थाळी ऑर्डर करा.",
  "PNR 9157364820 માટે નાગપુરમાં એક વેજ થાળી ઓર્ડર કરો.",
  intent=join(ORDER, VEG), status="cannot_complete", must=["Nagpur is the boarding station"], risk="Plain request.",
  note="The passenger boards at Nagpur; meals are delivered on the way, not at the boarding station: NOT_EN_ROUTE.",
  equivalent=["get_booking_status(9157364820) showing boarding station Nagpur grounds the answer as well."])
T("T150", "recovery", ["recovery", "meal_order", "no_catering"], "meal_station_without_catering",
  dict(pnr="3051962847", station_name="Jaipur", meal="veg_thali"),
  "Order a veg thali at Jaipur for my ticket PNR 3051962847.",
  "Mere ticket PNR 3051962847 ke liye Jaipur par veg thali order kar do.",
  "मेरे टिकट PNR 3051962847 के लिए जयपुर में वेज थाली ऑर्डर कीजिए।",
  "माझ्या PNR 3051962847 असलेल्या तिकिटासाठी जयपूरला व्हेज थाळी ऑर्डर करा.",
  "મારી PNR 3051962847 વાળી ટિકિટ માટે જયપુરમાં વેજ થાળી ઓર્ડર કરો.",
  intent=join(ORDER, VEG), status="cannot_complete", must=["no e-catering at Jaipur"], risk="Plain request.",
  note="Jaipur has no e-catering: CATERING_NOT_AVAILABLE.")
T("T151", "invalid_input", ["invalid_input", "meal_order", "not_on_menu"], "meal_item_not_on_menu",
  dict(pnr="6187340925", station_name="Ahmedabad", meal="chicken_biryani", meal_alternatives=["biryani"]),
  "Order a chicken biryani for me at Ahmedabad. My PNR is 6187340925.",
  "Ahmedabad par mere liye ek chicken biryani order kar do. Mera PNR 6187340925 hai.",
  "अहमदाबाद में मेरे लिए एक चिकन बिरयानी ऑर्डर कीजिए। मेरा PNR 6187340925 है।",
  "अहमदाबादला माझ्यासाठी एक चिकन बिर्याणी ऑर्डर करा. माझा PNR 6187340925 आहे.",
  "અમદાવાદમાં મારા માટે એક ચિકન બિરયાની ઓર્ડર કરો. મારો PNR 6187340925 છે.",
  intent=join(ORDER, W("biryani", "biryani", "बिरयानी", "बिर्याणी", "બિરયાની")), status="cannot_complete",
  must=["biryani is not on the menu"], risk="The item must stay biryani (not translated into a thali).",
  note="Not on the menu (veg/non-veg/Jain thali, breakfast). The menu is in the tool description, so the rejected call is optional; "
       "ordering a substitute without asking is wrong.",
  alternatives=["needs_clarification: asking which menu item to order instead, ordering nothing (evaluation/scorer.ALTERNATIVE_OUTCOMES)"])
T("T152", "constraint", ["constraint", "meal_order", "conditional", "live_status", "time_condition", "state_changing"],
  "meal_choice_by_expected_arrival",
  dict(pnr="5803917264", station_name="Nagpur", after_time="21:00", meal_if_after="veg_thali", meal_otherwise="nonveg_thali"),
  "My train (PNR 5803917264) reaches Nagpur tonight. If it will get there after 9 PM, order a veg thali for me at Nagpur; otherwise order a "
  "non-veg thali.",
  "Meri train (PNR 5803917264) aaj raat Nagpur pahunchegi. Agar woh raat 9 baje ke baad pahunchegi, to mere liye Nagpur par veg thali "
  "order kar do; warna non-veg thali order kar do.",
  "मेरी ट्रेन (PNR 5803917264) आज रात नागपुर पहुँचेगी। अगर वह रात 9 बजे के बाद पहुँचेगी, तो मेरे लिए नागपुर में वेज थाली ऑर्डर कीजिए; "
  "वरना नॉन-वेज थाली ऑर्डर कीजिए।",
  "माझी ट्रेन (PNR 5803917264) आज रात्री नागपूरला पोहोचेल. ती रात्री 9 नंतर पोहोचणार असेल, तर माझ्यासाठी नागपूरला व्हेज थाळी ऑर्डर करा; "
  "नाहीतर नॉन-व्हेज थाळी ऑर्डर करा.",
  "મારી ટ્રેન (PNR 5803917264) આજ રાત્રે નાગપુર પહોંચશે. જો તે રાત્રે 9 વાગ્યા પછી પહોંચવાની હોય, તો મારા માટે નાગપુરમાં વેજ થાળી ઓર્ડર "
  "કરો; નહીંતર નોન-વેજ થાળી ઓર્ડર કરો.",
  intent=join(ORDER, VEG, NONVEG),
  more={"time_constraint": W("after 9 PM", "9 baje ke baad", "9 बजे के बाद", "9 नंतर", "9 વાગ્યા પછી")},
  status="success", must=["expected 22:30 (after 21:00)", "veg thali ordered", "no non-veg thali"],
  risk="Two branches by arrival time; 'after 9 PM' boundary.",
  note="Branch on the expected arrival (22:30): exactly one meal, the veg thali.",
  equivalent=["get_train_details(BTB122) showing the 22:30 arrival (the train is on time) grounds c1 as well."])
T("T153", "constraint", ["constraint", "meal_order", "conditional", "live_status", "time_condition", "state_changing"],
  "meal_if_arrival_before_deadline", dict(pnr="6187340925", station_name="Ahmedabad", meal="nonveg_thali", before_time="14:00"),
  "If my train (PNR 6187340925) will reach Ahmedabad before 2 PM, order a non-veg thali there for lunch. Also tell me when it is expected.",
  "Agar meri train (PNR 6187340925) dopahar 2 baje se pehle Ahmedabad pahunchegi, to wahan lunch ke liye non-veg thali order kar do. Yeh bhi "
  "batao ki woh kab tak pahunchegi.",
  "अगर मेरी ट्रेन (PNR 6187340925) दोपहर 2 बजे से पहले अहमदाबाद पहुँचेगी, तो वहाँ दोपहर के खाने के लिए नॉन-वेज थाली ऑर्डर कीजिए। यह भी बताइए "
  "कि वह कब तक पहुँचेगी।",
  "माझी ट्रेन (PNR 6187340925) दुपारी 2 च्या आधी अहमदाबादला पोहोचणार असेल, तर तिथे दुपारच्या जेवणासाठी नॉन-व्हेज थाळी ऑर्डर करा. ती कधी "
  "पोहोचेल तेही सांगा.",
  "જો મારી ટ્રેન (PNR 6187340925) બપોરે 2 વાગ્યા પહેલાં અમદાવાદ પહોંચવાની હોય, તો ત્યાં બપોરના ભોજન માટે નોન-વેજ થાળી ઓર્ડર કરો. તે ક્યારે "
  "પહોંચશે તે પણ જણાવો.",
  intent=join(ORDER, NONVEG),
  more={"time_constraint": W("before 2 PM", "2 baje se pehle", "2 बजे से पहले", "2 च्या आधी", "2 વાગ્યા પહેલાં")},
  status="success", must=["expected_arrival 13:30 (timetable 11:30)", "non-veg thali ordered"], risk="'before 2 PM' as the condition.",
  note="The answer value is the LIVE expected arrival (13:30), not the timetable time (11:30).")
T("T154", "booking", ["booking", "complaint", "meal_order", "multi_intent", "state_changing"], "complaint_and_meal_order",
  dict(pnr="6187340925", station_name="Ahmedabad", meal="veg_thali", category="cleanliness"),
  "The toilets in my coach are dirty. Please register a cleanliness complaint for PNR 6187340925, and also order a veg thali for me at Ahmedabad.",
  "Mere coach ke toilet gande hain. PNR 6187340925 ke liye safai ki complaint darj kar do, aur Ahmedabad par mere liye ek veg thali bhi "
  "order kar do.",
  "मेरे कोच के शौचालय गंदे हैं। PNR 6187340925 के लिए सफ़ाई की शिकायत दर्ज कीजिए, और अहमदाबाद में मेरे लिए एक वेज थाली भी ऑर्डर कीजिए।",
  "माझ्या डब्यातील शौचालये अस्वच्छ आहेत. PNR 6187340925 साठी स्वच्छतेची तक्रार नोंदवा, आणि अहमदाबादला माझ्यासाठी एक व्हेज थाळीही ऑर्डर करा.",
  "મારા કોચનાં શૌચાલય ગંદાં છે. PNR 6187340925 માટે સફાઈની ફરિયાદ નોંધાવો, અને અમદાવાદમાં મારા માટે એક વેજ થાળી પણ ઓર્ડર કરો.",
  intent=join(COMPLAINT, ORDER, VEG), status="success", must=["cleanliness complaint registered", "veg thali ordered"],
  risk="Two actions; complaint category = cleanliness.", note="Two independent state changes in one request.")
T("T155", "sequential", ["sequential", "meal_order", "live_status", "next_station", "state_changing"], "meal_at_next_station",
  dict(pnr="5803917264", meal="nonveg_thali"),
  "Order a non-veg thali for PNR 5803917264 at the next station where my train stops.",
  "PNR 5803917264 ke liye meri train jis agle station par rukegi, wahan non-veg thali order kar do.",
  "PNR 5803917264 के लिए मेरी ट्रेन जिस अगले स्टेशन पर रुकेगी, वहाँ नॉन-वेज थाली ऑर्डर कीजिए।",
  "PNR 5803917264 साठी माझी ट्रेन ज्या पुढच्या स्टेशनवर थांबेल, तिथे नॉन-व्हेज थाळी ऑर्डर करा.",
  "PNR 5803917264 માટે મારી ટ્રેન જે આગલા સ્ટેશને ઊભી રહેશે, ત્યાં નોન-વેજ થાળી ઓર્ડર કરો.",
  intent=join(ORDER, NONVEG, NEXT), status="success", must=["next station Nagpur", "non-veg thali ordered"],
  risk="'the next station' must not become a named station.", note="The station is resolved from the live position (next stop Nagpur).",
  equivalent=["get_train_details(BTB122) (on time; next stop after 09:00 is Nagpur) grounds c1 as well."])
T("T156", "sequential", ["sequential", "meal_order", "live_status", "next_station", "platform", "state_changing"],
  "meal_at_next_station_and_platform", dict(pnr="6187340925", meal="jain_thali"),
  "At the next stop of my train (PNR 6187340925), I want a Jain thali delivered. Please order it and tell me the platform number there.",
  "Meri train (PNR 6187340925) ke agle stop par mujhe Jain thali chahiye. Order kar do aur wahan ka platform number bhi batao.",
  "मेरी ट्रेन (PNR 6187340925) के अगले स्टॉप पर मुझे जैन थाली चाहिए। ऑर्डर कर दीजिए और वहाँ का प्लेटफ़ॉर्म नंबर भी बताइए।",
  "माझ्या ट्रेनच्या (PNR 6187340925) पुढच्या थांब्यावर मला जैन थाळी हवी आहे. ऑर्डर करा आणि तिथला प्लॅटफॉर्म नंबरही सांगा.",
  "મારી ટ્રેન (PNR 6187340925) ના આગલા સ્ટોપ પર મને જૈન થાળી જોઈએ છે. ઓર્ડર કરો અને ત્યાંનો પ્લેટફોર્મ નંબર પણ જણાવો.",
  intent=join(ORDER, JAIN, NEXT, PLATFORM), status="success", must=["next stop Ahmedabad", "Jain thali ordered", "platform 3"],
  risk="'next stop' + platform there.", note="Three steps: live position, meal order, platform lookup at the same station.",
  equivalent=["get_train_details(BTB103) (next stop after 09:00 is Ahmedabad) grounds c1 as well."])
T("T157", "booking", ["booking", "meal_order", "two_items", "arithmetic", "state_changing"], "two_meal_items_total",
  dict(pnr="5803917264", station_name="Nagpur", meals=["veg_thali", "jain_thali"]),
  "Order one veg thali and one Jain thali at Nagpur for PNR 5803917264, and tell me the total.",
  "PNR 5803917264 ke liye Nagpur par ek veg thali aur ek Jain thali order kar do, aur total batao.",
  "PNR 5803917264 के लिए नागपुर में एक वेज थाली और एक जैन थाली ऑर्डर कीजिए, और कुल रकम बताइए।",
  "PNR 5803917264 साठी नागपूरला एक व्हेज थाळी आणि एक जैन थाळी ऑर्डर करा, आणि एकूण रक्कम सांगा.",
  "PNR 5803917264 માટે નાગપુરમાં એક વેજ થાળી અને એક જૈન થાળી ઓર્ડર કરો, અને કુલ રકમ જણાવો.",
  intent=join(ORDER, VEG, JAIN), status="success", must=["two orders", "order_amount_inr 380"], risk="Two different items, one each.",
  note="Two orders (one per item) and a total.")

# ---------------------------------------------------------------- platforms and live status (T158-T169)
T("T158", "single_tool", ["single_tool", "platform", "read_only"], "platform_lookup", dict(train_id="BTB101", station_name="New Delhi"),
  "Which platform does train BTB101 leave from at New Delhi?",
  "Train BTB101 New Delhi mein kis platform se chalti hai?",
  "ट्रेन BTB101 नई दिल्ली में किस प्लेटफ़ॉर्म से चलती है?",
  "ट्रेन BTB101 नवी दिल्लीत कोणत्या प्लॅटफॉर्मवरून सुटते?",
  "ટ્રેન BTB101 નવી દિલ્હીમાં કયા પ્લેટફોર્મ પરથી ઊપડે છે?",
  intent=PLATFORM, status="success", must=["platform 4"], risk="Plain lookup.", note="Single platform lookup.")
T("T159", "sequential", ["sequential", "platform", "live_status", "expected_arrival", "read_only"], "platform_and_expected_arrival",
  dict(train_id="BTB103", station_name="Ahmedabad"),
  "Train BTB103 is coming to Ahmedabad today. Which platform will it arrive on, and at what time is it now expected?",
  "Train BTB103 aaj Ahmedabad aa rahi hai. Woh kis platform par aayegi, aur ab kitne baje pahunchne ki ummeed hai?",
  "ट्रेन BTB103 आज अहमदाबाद आ रही है। वह किस प्लेटफ़ॉर्म पर आएगी, और अब कितने बजे पहुँचने की उम्मीद है?",
  "ट्रेन BTB103 आज अहमदाबादला येत आहे. ती कोणत्या प्लॅटफॉर्मवर येईल, आणि आता किती वाजता पोहोचणे अपेक्षित आहे?",
  "ટ્રેન BTB103 આજે અમદાવાદ આવી રહી છે. તે કયા પ્લેટફોર્મ પર આવશે, અને હવે કેટલા વાગ્યે પહોંચવાની અપેક્ષા છે?",
  intent=join(PLATFORM, TODAY), status="success", must=["platform 3", "expected_arrival 13:30"], risk="'now expected' = live time.",
  note="Platform + live expected arrival (2 h late), not the timetable 11:30.")
T("T160", "single_tool", ["single_tool", "platform", "coach_position", "read_only"], "coach_position_from_engine",
  dict(train_id="BTB104", travel_class="3A", station_name="Mumbai"),
  "On train BTB104 from Mumbai, counting the engine as number 1, at which position is the first 3A coach?",
  "Mumbai se chalne wali train BTB104 mein, engine ko number 1 maan kar ginein to pehla 3A coach kis number par hai?",
  "मुंबई से चलने वाली ट्रेन BTB104 में, इंजन को नंबर 1 मानकर गिनें तो पहला 3A कोच किस नंबर पर है?",
  "मुंबईहून सुटणाऱ्या ट्रेन BTB104 मध्ये, इंजिनला क्रमांक 1 धरून मोजल्यास पहिला 3A डबा कितव्या क्रमांकावर आहे?",
  "મુંબઈથી ઊપડતી ટ્રેન BTB104 માં, એન્જિનને નંબર 1 ગણીએ તો પહેલો 3A કોચ કયા નંબરે છે?",
  intent=ENGINE1, status="success", must=["coach_position 7 (B1)"], risk="'counting the engine as number 1' fixes the count.",
  note="Coach order from the platform tool: ENGINE, GEN, S1-S4, B1 -> position 7.")
T("T161", "sequential", ["sequential", "pnr_status", "platform", "coach_position", "read_only"], "coach_position_for_pnr",
  dict(pnr="5079318462", station_name="Bengaluru"),
  "My PNR is 5079318462 and I board at Bengaluru. Counting the engine as number 1, at which position will the first coach of my class be?",
  "Mera PNR 5079318462 hai aur mujhe Bengaluru se chadhna hai. Engine ko number 1 maan kar ginein to meri class ka pehla coach kis number "
  "par hoga?",
  "मेरा PNR 5079318462 है और मुझे बेंगलुरु से चढ़ना है। इंजन को नंबर 1 मानकर गिनें तो मेरी क्लास का पहला कोच किस नंबर पर होगा?",
  "माझा PNR 5079318462 आहे आणि मला बेंगळुरूहून चढायचे आहे. इंजिनला क्रमांक 1 धरून मोजल्यास माझ्या क्लासचा पहिला डबा कितव्या क्रमांकावर असेल?",
  "મારો PNR 5079318462 છે અને મારે બેંગલુરુથી ચઢવું છે. એન્જિનને નંબર 1 ગણીએ તો મારા ક્લાસનો પહેલો કોચ કયા નંબરે હશે?",
  intent=ENGINE1, status="success", must=["2A on BTB122", "coach_position 6 (A1)"], risk="The class comes from the PNR.",
  note="Train and class from the PNR (BTB122 2A), then the coach order.")
T("T162", "invalid_input", ["invalid_input", "platform", "not_a_stop", "read_only"], "platform_train_does_not_stop",
  dict(train_id="BTB127", station_name="Mumbai"),
  "Which platform does train BTB127 stop at in Mumbai?",
  "Train BTB127 Mumbai mein kis platform par rukti hai?",
  "ट्रेन BTB127 मुंबई में किस प्लेटफ़ॉर्म पर रुकती है?",
  "ट्रेन BTB127 मुंबईत कोणत्या प्लॅटफॉर्मवर थांबते?",
  "ટ્રેન BTB127 મુંબઈમાં કયા પ્લેટફોર્મ પર ઊભી રહે છે?",
  intent=PLATFORM, status="cannot_complete", must=["BTB127 does not stop at Mumbai"], risk="False presupposition must survive.",
  note="BTB127 runs Pune-Nagpur: NOT_A_STOP; a platform must not be invented.",
  equivalent=["get_train_details(BTB127) showing the stops (no Mumbai) grounds the answer as well."])
T("T163", "sequential", ["sequential", "pnr_status", "platform", "read_only"], "platform_for_pnr_boarding", dict(pnr="9157364820"),
  "Which platform should I go to for my train? My PNR is 9157364820.",
  "Mujhe apni train ke liye kis platform par jaana chahiye? Mera PNR 9157364820 hai.",
  "मुझे अपनी ट्रेन के लिए किस प्लेटफ़ॉर्म पर जाना चाहिए? मेरा PNR 9157364820 है।",
  "माझ्या ट्रेनसाठी मी कोणत्या प्लॅटफॉर्मवर जावे? माझा PNR 9157364820 आहे.",
  "મારી ટ્રેન માટે મારે કયા પ્લેટફોર્મ પર જવું જોઈએ? મારો PNR 9157364820 છે.",
  intent=PLATFORM, status="success", must=["boards BTB120 at Nagpur", "platform 1"], risk="Station comes from the PNR.",
  note="Train and boarding station from the PNR, then the platform.")
T("T164", "sequential", ["sequential", "platform", "live_status", "delay", "read_only"], "platform_and_delay", dict(train_id="BTB116", station_name="Pune"),
  "My train BTB116 comes to Pune today. Which platform, and how late is it running?",
  "Meri train BTB116 aaj Pune aayegi. Kaunsa platform hai, aur woh kitni late chal rahi hai?",
  "मेरी ट्रेन BTB116 आज पुणे आएगी। कौन-सा प्लेटफ़ॉर्म है, और वह कितनी देर से चल रही है?",
  "माझी ट्रेन BTB116 आज पुण्याला येईल. कोणता प्लॅटफॉर्म आहे, आणि ती किती उशिराने धावत आहे?",
  "મારી ટ્રેન BTB116 આજે પુણે આવશે. કયું પ્લેટફોર્મ છે, અને તે કેટલી મોડી ચાલી રહી છે?",
  intent=join(PLATFORM, TODAY), status="success", must=["platform 1", "delay_minutes 15"], risk="Two questions.",
  note="Two independent lookups on one train.")
T("T165", "constraint", ["constraint", "platform", "live_status", "delay_threshold", "read_only"], "platform_if_delay_over_threshold",
  dict(train_id="BTB105", station_name="Jaipur", min_delay_minutes=20),
  "Is train BTB105 more than 20 minutes late? If it is, tell me its platform at Jaipur, because I'm going to pick someone up.",
  "Kya train BTB105 20 minute se zyada late hai? Agar haan, to Jaipur mein uska platform batao, kyunki mujhe kisi ko lene jaana hai.",
  "क्या ट्रेन BTB105 20 मिनट से ज़्यादा देर से है? अगर हाँ, तो जयपुर में उसका प्लेटफ़ॉर्म बताइए, क्योंकि मुझे किसी को लेने जाना है।",
  "ट्रेन BTB105 20 मिनिटांपेक्षा जास्त उशिरा आहे का? असेल, तर जयपूरमधला तिचा प्लॅटफॉर्म सांगा, कारण मला कोणालातरी घ्यायला जायचे आहे.",
  "શું ટ્રેન BTB105 20 મિનિટથી વધુ મોડી છે? જો હા, તો જયપુરમાં તેનું પ્લેટફોર્મ જણાવો, કારણ કે મારે કોઈને લેવા જવું છે.",
  intent=PLATFORM, more={"time_constraint": W("more than 20 minutes", "20 minute se zyada", "20 मिनट से ज़्यादा", "20 मिनिटांपेक्षा जास्त",
                                             "20 મિનિટથી વધુ")},
  status="success", must=["delay_minutes 25 > 20", "platform 1"], risk="Strict 'more than 20 minutes'.",
  note="Conditional platform question; the condition holds (25 min).")
T("T166", "sequential", ["sequential", "live_status", "platform", "expected_arrival", "read_only"], "arrived_yet_and_platform",
  dict(train_id="BTB112", station_name="Lucknow"),
  "Has train BTB112 reached Lucknow yet? If not, when is it expected, and on which platform?",
  "Kya train BTB112 Lucknow pahunch gayi hai? Agar nahi, to kab tak pahunchegi, aur kis platform par?",
  "क्या ट्रेन BTB112 लखनऊ पहुँच गई है? अगर नहीं, तो कब तक पहुँचेगी, और किस प्लेटफ़ॉर्म पर?",
  "ट्रेन BTB112 लखनौला पोहोचली आहे का? नसेल, तर ती कधी पोहोचेल, आणि कोणत्या प्लॅटफॉर्मवर?",
  "શું ટ્રેન BTB112 લખનઉ પહોંચી ગઈ છે? જો નહીં, તો ક્યારે પહોંચશે, અને કયા પ્લેટફોર્મ પર?",
  intent=PLATFORM, status="success", must=["not yet", "expected_arrival 10:30", "platform 3"], risk="Three-part question.",
  note="Live position (not yet at Lucknow, 45 min late) + platform.")
T("T167", "single_tool", ["single_tool", "timetable", "not_live", "read_only"], "timetable_arrival_not_live", dict(train_id="BTB110", station_name="Lucknow"),
  "According to the timetable, not the live status, at what time does train BTB110 arrive at Lucknow?",
  "Timetable ke hisaab se, live status nahi, train BTB110 Lucknow kitne baje pahunchti hai?",
  "समय-सारणी के हिसाब से, लाइव स्टेटस नहीं, ट्रेन BTB110 लखनऊ कितने बजे पहुँचती है?",
  "वेळापत्रकानुसार, लाइव्ह स्टेटस नव्हे, ट्रेन BTB110 लखनौला किती वाजता पोहोचते?",
  "ટાઇમટેબલ મુજબ, લાઇવ સ્ટેટસ નહીં, ટ્રેન BTB110 લખનઉ કેટલા વાગ્યે પહોંચે છે?",
  intent=W("timetable", "Timetable", "समय-सारणी", "वेळापत्रक", "ટાઇમટેબલ"), status="success", must=["scheduled_arrival 04:25"],
  risk="'timetable, not the live status' must survive.", note="Reverse selection trap: the train is 200 min late, but the user wants the "
                                                          "scheduled time (get_train_details), not the live one.")
T("T168", "single_tool", ["single_tool", "live_status", "expected_arrival", "destination", "read_only"], "live_expected_arrival_at_destination",
  dict(train_id="BTB110", station_name="New Delhi"),
  "My uncle is on train BTB110 to New Delhi. When is it now expected to reach New Delhi, and how late is it?",
  "Mere chacha train BTB110 se New Delhi aa rahe hain. Ab woh New Delhi kitne baje pahunchne wali hai, aur kitni late hai?",
  "मेरे चाचा ट्रेन BTB110 से नई दिल्ली आ रहे हैं। अब वह नई दिल्ली कितने बजे पहुँचने वाली है, और कितनी देर से है?",
  "माझे काका ट्रेन BTB110 ने नवी दिल्लीला येत आहेत. ती आता नवी दिल्लीला किती वाजता पोहोचणे अपेक्षित आहे, आणि किती उशिरा आहे?",
  "મારા કાકા ટ્રેન BTB110 થી નવી દિલ્હી આવી રહ્યા છે. હવે તે નવી દિલ્હી કેટલા વાગ્યે પહોંચવાની છે, અને કેટલી મોડી છે?",
  intent=W("expected", "pahunchne wali", "पहुँचने वाली", "अपेक्षित", "પહોંચવાની"), status="success",
  must=["expected_arrival 14:00", "delay_minutes 200"], risk="'now expected' = live time.", note="Live arrival at the destination.")
T("T169", "single_tool", ["single_tool", "live_status", "delay", "last_station", "read_only"], "live_delay_and_last_station", dict(train_id="BTB109"),
  "How late is train BTB109 running right now, and which station did it last pass?",
  "Train BTB109 abhi kitni late chal rahi hai, aur aakhri station kaunsa paar kiya?",
  "ट्रेन BTB109 अभी कितनी देर से चल रही है, और उसने आख़िरी कौन-सा स्टेशन पार किया?",
  "ट्रेन BTB109 सध्या किती उशिराने धावत आहे, आणि तिने शेवटचे कोणते स्टेशन ओलांडले?",
  "ટ્રેન BTB109 અત્યારે કેટલી મોડી ચાલી રહી છે, અને તેણે છેલ્લું કયું સ્ટેશન પસાર કર્યું?",
  intent=W("last", "aakhri", "आख़िरी", "शेवटचे", "છેલ્લું"), status="success", must=["delay_minutes 90", "last station Lucknow (LKO)"],
  risk="Two questions.", note="Two fields of one live-status reply.")

# ---------------------------------------------------------------- TDR (T170-T180)
T("T170", "booking", ["booking", "tdr", "state_changing"], "tdr_file_ok", dict(pnr="6620194835"),
  "My train is running very late. File a TDR for PNR 6620194835 and tell me how much refund I will get.",
  "Meri train bahut late chal rahi hai. PNR 6620194835 ke liye TDR file kar do aur batao kitna refund milega.",
  "मेरी ट्रेन बहुत देर से चल रही है। PNR 6620194835 के लिए TDR फ़ाइल कीजिए और बताइए कि कितना रिफ़ंड मिलेगा।",
  "माझी ट्रेन खूप उशिराने धावत आहे. PNR 6620194835 साठी TDR फाइल करा आणि किती रिफंड मिळेल ते सांगा.",
  "મારી ટ્રેન બહુ મોડી ચાલી રહી છે. PNR 6620194835 માટે TDR ફાઇલ કરો અને કેટલું રિફંડ મળશે તે જણાવો.",
  intent=join(TDR, W("refund", "refund", "रिफ़ंड", "रिफंड", "રિફંડ")), status="success", must=["TDR filed", "refund_inr 495"],
  risk="File + refund question.", note="Eligible TDR: BTB106 is 200 min late and has not left Jaipur yet (15:40).")
T("T171", "constraint", ["constraint", "tdr", "cancellation", "comparison", "state_changing"], "best_refund_is_tdr_not_cancel", dict(pnr="6620194835"),
  "For PNR 6620194835, should I cancel the ticket or file a TDR? Do whichever gives me more money back.",
  "PNR 6620194835 ke liye ticket cancel karoon ya TDR file karoon? Jismein zyada paise wapas milein, wahi kar do.",
  "PNR 6620194835 के लिए टिकट कैंसिल करूँ या TDR फ़ाइल करूँ? जिसमें ज़्यादा पैसे वापस मिलें, वही कर दीजिए।",
  "PNR 6620194835 साठी तिकीट रद्द करू की TDR फाइल करू? ज्यात जास्त पैसे परत मिळतील, तेच करा.",
  "PNR 6620194835 માટે ટિકિટ કેન્સલ કરું કે TDR ફાઇલ કરું? જેમાં વધુ પૈસા પાછા મળે, તે જ કરો.",
  intent=join(TDR, W("more money", "zyada paise", "ज़्यादा पैसे", "जास्त पैसे", "વધુ પૈસા")), status="success",
  must=["cancel refund 315", "TDR 495 (full fare)", "TDR filed, not cancelled"], risk="'whichever gives more' = compare, then ONE action.",
  note="Compare the cancellation quote (315) with the TDR (full fare 495) and take only the better action. The quote is optional: a "
       "TDR refunds the full fare while a cancellation always keeps a charge, so the TDR wins whenever it is allowed.")
T("T172", "recovery", ["recovery", "tdr", "not_eligible"], "tdr_not_eligible_delay_too_small", dict(pnr="3875061294"),
  "File a TDR for my ticket PNR 3875061294, my train is late.",
  "Mere ticket PNR 3875061294 ke liye TDR file kar do, meri train late hai.",
  "मेरे टिकट PNR 3875061294 के लिए TDR फ़ाइल कीजिए, मेरी ट्रेन देर से है।",
  "माझ्या PNR 3875061294 असलेल्या तिकिटासाठी TDR फाइल करा, माझी ट्रेन उशिरा आहे.",
  "મારી PNR 3875061294 વાળી ટિકિટ માટે TDR ફાઇલ કરો, મારી ટ્રેન મોડી છે.",
  intent=TDR, status="cannot_complete", must=["delay 130 min < 180"], risk="Plain request.",
  note="Late, but not late enough (130 < 180 min): TDR_NOT_ELIGIBLE.",
  equivalent=["get_live_train_status(BTB126) showing 130 minutes grounds the answer as well."])
T("T173", "recovery", ["recovery", "tdr", "window_closed", "temporal"], "tdr_after_train_left", dict(pnr="9045127368"),
  "My train with PNR 9045127368 is more than 3 hours late. File a TDR, please.",
  "PNR 9045127368 wali meri train 3 ghante se zyada late hai. TDR file kar do, please.",
  "PNR 9045127368 वाली मेरी ट्रेन 3 घंटे से ज़्यादा देर से है। कृपया TDR फ़ाइल कीजिए।",
  "PNR 9045127368 असलेली माझी ट्रेन 3 तासांपेक्षा जास्त उशिरा आहे. कृपया TDR फाइल करा.",
  "PNR 9045127368 વાળી મારી ટ્રેન 3 કલાકથી વધુ મોડી છે. કૃપા કરીને TDR ફાઇલ કરો.",
  intent=TDR, status="cannot_complete", must=["the train already left the boarding station (journey in progress)"],
  risk="The user's '3 hours' claim is true; the rule that fails is the timing.",
  note="Delay qualifies (200 min) but the TDR had to be filed before the train left Kolkata: TDR_WINDOW_CLOSED.",
  equivalent=["get_live_train_status(BTB110) showing the train RUNNING (it left yesterday) grounds the answer as well."])
T("T174", "recovery", ["recovery", "tdr", "already_cancelled"], "tdr_cancelled_ticket", dict(pnr="2894017356"),
  "Can you file a TDR refund claim for my ticket PNR 2894017356?",
  "Kya aap mere ticket PNR 2894017356 ke liye TDR refund claim file kar sakte hain?",
  "क्या आप मेरे टिकट PNR 2894017356 के लिए TDR रिफ़ंड क्लेम फ़ाइल कर सकते हैं?",
  "माझ्या PNR 2894017356 असलेल्या तिकिटासाठी TDR रिफंड क्लेम फाइल करू शकाल का?",
  "શું તમે મારી PNR 2894017356 વાળી ટિકિટ માટે TDR રિફંડ ક્લેમ ફાઇલ કરી શકો?",
  intent=TDR, status="cannot_complete", must=["ticket already cancelled"], risk="Polite question form = a request.",
  note="A cancelled ticket cannot get a TDR: ALREADY_CANCELLED.",
  equivalent=["get_booking_status(2894017356) showing CANCELLED grounds the answer as well."])
T("T175", "sequential", ["sequential", "tdr", "eligibility", "no_filing", "safety", "read_only"], "tdr_eligibility_without_filing", dict(pnr="6620194835"),
  "Is my ticket PNR 6620194835 eligible for a TDR refund? Don't file it yet, just check.",
  "Kya mera ticket PNR 6620194835 TDR refund ke liye eligible hai? Abhi file mat karna, bas check karo.",
  "क्या मेरा टिकट PNR 6620194835 TDR रिफ़ंड के लिए एलिजिबल है? अभी फ़ाइल मत कीजिए, बस देखिए।",
  "माझे PNR 6620194835 असलेले तिकीट TDR रिफंडसाठी पात्र आहे का? आत्ताच फाइल करू नका, फक्त तपासा.",
  "શું મારી PNR 6620194835 વાળી ટિકિટ TDR રિફંડ માટે પાત્ર છે? હમણાં ફાઇલ કરશો નહીં, ફક્ત તપાસો.",
  intent=TDR, more={"forbidden": W("Don't file it yet", "Abhi file mat karna", "अभी फ़ाइल मत कीजिए", "आत्ताच फाइल करू नका", "હમણાં ફાઇલ કરશો નહીં")},
  status="success", must=["eligible: 200 min late, not yet departed"], risk="Explicit 'don't file it yet'.",
  note="Selection trap: file_tdr would answer by acting; the user forbids it, so eligibility is derived from the PNR and the live status.",
  prohibited=[("file_tdr", "Don't file it yet", "The user only asks whether the ticket is eligible and says not to file yet.")])
T("T176", "recovery", ["recovery", "cancellation", "tdr", "fallback", "journey_started"], "cancel_else_tdr_both_blocked", dict(pnr="9045127368"),
  "Cancel my ticket PNR 9045127368. If it can't be cancelled, file a TDR instead.",
  "Mera ticket PNR 9045127368 cancel kar do. Agar cancel nahi ho sakta, to TDR file kar do.",
  "मेरा टिकट PNR 9045127368 कैंसिल कीजिए। अगर कैंसिल नहीं हो सकता, तो TDR फ़ाइल कीजिए।",
  "माझे PNR 9045127368 असलेले तिकीट रद्द करा. ते रद्द होऊ शकत नसेल, तर TDR फाइल करा.",
  "મારી PNR 9045127368 વાળી ટિકિટ કેન્સલ કરો. જો તે કેન્સલ ન થઈ શકે, તો TDR ફાઇલ કરો.",
  intent=TDR, more={"fallback": W("If it can't be cancelled", "Agar cancel nahi ho sakta", "अगर कैंसिल नहीं हो सकता", "रद्द होऊ शकत नसेल",
                                    "જો તે કેન્સલ ન થઈ શકે")},
  status="cannot_complete", must=["cannot cancel (journey started)", "TDR window closed too"], risk="Primary action + fallback.",
  note="Both the action and its fallback are blocked by the same fact: the train left yesterday.",
  equivalent=["get_cancellation_refund(9045127368) returning JOURNEY_STARTED grounds c1; get_live_train_status(BTB110) showing the train "
              "RUNNING grounds c2."])
T("T177", "single_tool", ["single_tool", "live_status", "tdr_rule", "read_only"], "train_delay_tdr_threshold_check", dict(train_id="BTB126"),
  "Is train BTB126 late enough today for passengers to claim a TDR refund? How late is it?",
  "Kya train BTB126 aaj itni late hai ki passengers TDR refund claim kar sakein? Kitni late hai?",
  "क्या ट्रेन BTB126 आज इतनी देर से है कि यात्री TDR रिफ़ंड क्लेम कर सकें? कितनी देर से है?",
  "ट्रेन BTB126 आज इतकी उशिरा आहे का की प्रवासी TDR रिफंड क्लेम करू शकतील? किती उशिरा आहे?",
  "શું ટ્રેન BTB126 આજે એટલી મોડી છે કે મુસાફરો TDR રિફંડ ક્લેમ કરી શકે? કેટલી મોડી છે?",
  intent=join(TDR, TODAY), status="success", must=["delay_minutes 130", "not eligible (needs 180)"], risk="Rule question + number.",
  note="The 3-hour TDR rule (tool description) applied to a live delay of 130 minutes.")
T("T178", "sequential", ["sequential", "tdr", "refund_quote", "comparison", "no_action", "read_only"], "cancel_refund_vs_tdr_quote", dict(pnr="6620194835"),
  "For my ticket PNR 6620194835, how much would I get back if I cancel it, and how much with a TDR? Just compare them; I'll decide later.",
  "Mere ticket PNR 6620194835 ke liye, cancel karne par kitna wapas milega aur TDR se kitna? Bas compare karke batao, faisla baad mein.",
  "मेरे टिकट PNR 6620194835 के लिए, कैंसिल करने पर कितना वापस मिलेगा और TDR से कितना? बस तुलना करके बताइए, फ़ैसला बाद में।",
  "माझ्या PNR 6620194835 असलेल्या तिकिटासाठी, रद्द केल्यास किती परत मिळेल आणि TDR ने किती? फक्त तुलना करून सांगा, निर्णय नंतर.",
  "મારી PNR 6620194835 વાળી ટિકિટ માટે, કેન્સલ કરવાથી કેટલું પાછું મળશે અને TDR થી કેટલું? ફક્ત સરખામણી કરીને જણાવો, નિર્ણય પછી.",
  intent=TDR, status="success", must=["cancel refund_inr 315", "tdr_refund_inr 495"], risk="Compare only; the decision is later.",
  note="Same ticket as T171 but no action: both amounts are derived read-only (TDR = full fare once eligibility is confirmed).")
T("T179", "recovery", ["recovery", "tdr", "complaint", "fallback", "state_changing"], "tdr_else_punctuality_complaint", dict(pnr="9045127368"),
  "My train (PNR 9045127368) is very late. File a TDR; if that's not possible, register a complaint about the delay instead.",
  "Meri train (PNR 9045127368) bahut late hai. TDR file kar do; agar woh possible nahi hai, to late hone ki complaint darj kar do.",
  "मेरी ट्रेन (PNR 9045127368) बहुत देर से है। TDR फ़ाइल कीजिए; अगर वह संभव नहीं है, तो देरी की शिकायत दर्ज कीजिए।",
  "माझी ट्रेन (PNR 9045127368) खूप उशिरा आहे. TDR फाइल करा; ते शक्य नसेल, तर उशिराबद्दल तक्रार नोंदवा.",
  "મારી ટ્રેન (PNR 9045127368) બહુ મોડી છે. TDR ફાઇલ કરો; જો તે શક્ય ન હોય, તો મોડા પડવા અંગે ફરિયાદ નોંધાવો.",
  intent=join(TDR, COMPLAINT), more={"fallback": W("if that's not possible", "possible nahi", "संभव नहीं", "शक्य नसेल", "શક્ય ન હોય")},
  status="success", must=["TDR not possible (window closed)", "punctuality complaint registered"], risk="Fallback = complaint about the DELAY.",
  note="The fallback succeeds: complaints are accepted while the journey is in progress (category punctuality).",
  equivalent=["get_live_train_status(BTB110) showing the train RUNNING grounds c1 as well."])
T("T180", "constraint", ["constraint", "tdr", "conditional", "booking", "multi_step", "state_changing"], "tdr_if_late_then_book_other_train",
  dict(pnr="6620194835", new_train_id="BTB130", travel_class="CC", passenger="Vinod Sharma", source_name="Jaipur",
       destination_name="Hazrat Nizamuddin", travel_date=TD),
  "If my train BTB106 (PNR 6620194835) is more than 3 hours late, file a TDR and book Vinod Sharma a chair car (CC) seat on train BTB130 "
  "from Jaipur to Hazrat Nizamuddin today instead.",
  "Agar meri train BTB106 (PNR 6620194835) 3 ghante se zyada late hai, to TDR file kar do aur Vinod Sharma ke liye aaj Jaipur se Hazrat "
  "Nizamuddin jaane wali train BTB130 mein chair car (CC) seat book kar do.",
  "अगर मेरी ट्रेन BTB106 (PNR 6620194835) 3 घंटे से ज़्यादा देर से है, तो TDR फ़ाइल कीजिए और Vinod Sharma के लिए आज जयपुर से हज़रत निज़ामुद्दीन "
  "जाने वाली ट्रेन BTB130 में चेयर कार (CC) की सीट बुक कीजिए।",
  "माझी ट्रेन BTB106 (PNR 6620194835) 3 तासांपेक्षा जास्त उशिरा असेल, तर TDR फाइल करा आणि Vinod Sharma यांच्यासाठी आज जयपूरहून हजरत "
  "निजामुद्दीनला जाणाऱ्या ट्रेन BTB130 मध्ये चेअर कार (CC) ची सीट बुक करा.",
  "જો મારી ટ્રેન BTB106 (PNR 6620194835) 3 કલાકથી વધુ મોડી હોય, તો TDR ફાઇલ કરો અને Vinod Sharma માટે આજે જયપુરથી હઝરત નિઝામુદ્દીન જતી "
  "ટ્રેન BTB130 માં ચેર કાર (CC) ની સીટ બુક કરો.",
  intent=join(TDR, TODAY), more={"time_constraint": W("more than 3 hours", "3 ghante se zyada", "3 घंटे से ज़्यादा", "3 तासांपेक्षा जास्त",
                                                      "3 કલાકથી વધુ")},
  status="success", must=["200 min > 3 h", "TDR filed, refund 495", "BTB130 CC booked for Vinod Sharma"],
  risk="Condition before two actions; the new train is BTB130.", note="Condition holds (200 min); TDR and a booking on another train.")

# ---------------------------------------------------------------- complaints (T181-T190)
T("T181", "booking", ["booking", "complaint", "ac", "state_changing"], "complaint_ac_not_working", dict(pnr="6187340925", category="ac_not_working"),
  "The AC in my coach isn't working. Please register a complaint for PNR 6187340925.",
  "Mere coach mein AC kaam nahi kar raha. PNR 6187340925 ke liye complaint darj kar do.",
  "मेरे कोच में AC काम नहीं कर रहा है। PNR 6187340925 के लिए शिकायत दर्ज कीजिए।",
  "माझ्या डब्यातील AC काम करत नाही. PNR 6187340925 साठी तक्रार नोंदवा.",
  "મારા કોચમાં AC કામ નથી કરતું. PNR 6187340925 માટે ફરિયાદ નોંધાવો.",
  intent=join(COMPLAINT, lit("AC")), status="success", must=["ac_not_working complaint registered"], risk="Category from the description.",
  note="Category chosen from free text (AC) on a running 3A journey.")
T("T182", "booking", ["booking", "complaint", "water", "state_changing"], "complaint_water_shortage", dict(pnr="5803917264", category="water_shortage"),
  "There's no water in the toilets of my coach. Register a complaint for PNR 5803917264.",
  "Mere coach ke toilet mein paani nahi hai. PNR 5803917264 ke liye complaint darj kar do.",
  "मेरे कोच के शौचालय में पानी नहीं है। PNR 5803917264 के लिए शिकायत दर्ज कीजिए।",
  "माझ्या डब्याच्या शौचालयात पाणी नाही. PNR 5803917264 साठी तक्रार नोंदवा.",
  "મારા કોચના શૌચાલયમાં પાણી નથી. PNR 5803917264 માટે ફરિયાદ નોંધાવો.",
  intent=join(COMPLAINT, W("water", "paani", "पानी", "पाणी", "પાણી")), status="success", must=["water_shortage complaint registered"],
  risk="Water, not cleanliness.", note="Category water_shortage (not cleanliness, although toilets are mentioned).")
T("T183", "booking", ["booking", "complaint", "cleanliness", "state_changing"], "complaint_cleanliness_running", dict(pnr="8741203659", category="cleanliness"),
  "My coach is very dirty and nobody has cleaned it since last night. Please lodge a complaint; my PNR is 8741203659.",
  "Mera coach bahut ganda hai aur kal raat se kisi ne saaf nahi kiya. Complaint darj kar do; mera PNR 8741203659 hai.",
  "मेरा कोच बहुत गंदा है और कल रात से किसी ने साफ़ नहीं किया। शिकायत दर्ज कीजिए; मेरा PNR 8741203659 है।",
  "माझा डबा खूप घाण आहे आणि काल रात्रीपासून कोणीही साफ केलेला नाही. तक्रार नोंदवा; माझा PNR 8741203659 आहे.",
  "મારો કોચ બહુ ગંદો છે અને ગઈ રાતથી કોઈએ સાફ કર્યો નથી. ફરિયાદ નોંધાવો; મારો PNR 8741203659 છે.",
  intent=COMPLAINT, status="success", must=["cleanliness complaint registered"], risk="'since last night' is context only.",
  note="Journey started yesterday and is still in progress (BTB102 reaches New Delhi at 10:35).")
T("T184", "booking", ["booking", "complaint", "security", "state_changing"], "complaint_security", dict(pnr="7520648193", category="security"),
  "A stranger in my coach is harassing passengers and I feel unsafe. Register a security complaint for PNR 7520648193.",
  "Mere coach mein ek anjaan aadmi passengers ko pareshan kar raha hai aur mujhe surakshit mehsoos nahi ho raha. PNR 7520648193 ke liye "
  "security complaint darj kar do.",
  "मेरे कोच में एक अनजान आदमी यात्रियों को परेशान कर रहा है और मुझे सुरक्षित महसूस नहीं हो रहा। PNR 7520648193 के लिए सुरक्षा की शिकायत दर्ज "
  "कीजिए।",
  "माझ्या डब्यात एक अनोळखी माणूस प्रवाशांना त्रास देत आहे आणि मला सुरक्षित वाटत नाही. PNR 7520648193 साठी सुरक्षेची तक्रार नोंदवा.",
  "મારા કોચમાં એક અજાણ્યો માણસ મુસાફરોને હેરાન કરે છે અને મને સલામત નથી લાગતું. PNR 7520648193 માટે સુરક્ષાની ફરિયાદ નોંધાવો.",
  intent=join(COMPLAINT, W("security", "security", "सुरक्षा", "सुरक्षे", "સુરક્ષા")), status="success", must=["security complaint registered"],
  risk="Security category.", note="Security complaint on a train about to reach Ahmedabad (10:05).")
T("T185", "booking", ["booking", "complaint", "punctuality", "state_changing"], "complaint_punctuality", dict(pnr="9045127368", category="punctuality"),
  "My train is more than 3 hours late and nobody tells us why. Register a complaint about the delay for PNR 9045127368.",
  "Meri train 3 ghante se zyada late hai aur koi wajah nahi bata raha. PNR 9045127368 ke liye late hone ki complaint darj kar do.",
  "मेरी ट्रेन 3 घंटे से ज़्यादा देर से है और कोई वजह नहीं बता रहा। PNR 9045127368 के लिए देरी की शिकायत दर्ज कीजिए।",
  "माझी ट्रेन 3 तासांपेक्षा जास्त उशिरा आहे आणि कोणी कारण सांगत नाही. PNR 9045127368 साठी उशिराबद्दल तक्रार नोंदवा.",
  "મારી ટ્રેન 3 કલાકથી વધુ મોડી છે અને કોઈ કારણ જણાવતું નથી. PNR 9045127368 માટે મોડા પડવા અંગે ફરિયાદ નોંધાવો.",
  intent=COMPLAINT, status="success", must=["punctuality complaint registered"], risk="Complaint, not a TDR (not asked).",
  note="Only a complaint is asked; filing a TDR here would be an unrequested action.")
T("T186", "booking", ["booking", "complaint", "catering", "state_changing"], "complaint_catering", dict(pnr="5146290837", category="catering"),
  "The food served on my train was stale. Please register a complaint about the catering for PNR 5146290837.",
  "Meri train mein jo khana diya gaya woh baasi tha. PNR 5146290837 ke liye catering ki complaint darj kar do.",
  "मेरी ट्रेन में जो खाना दिया गया वह बासी था। PNR 5146290837 के लिए खाने की शिकायत दर्ज कीजिए।",
  "माझ्या ट्रेनमध्ये दिलेले जेवण शिळे होते. PNR 5146290837 साठी जेवणाबद्दल तक्रार नोंदवा.",
  "મારી ટ્રેનમાં આપેલું જમવાનું વાસી હતું. PNR 5146290837 માટે જમવા અંગે ફરિયાદ નોંધાવો.",
  intent=COMPLAINT, status="success", must=["catering complaint registered"], risk="Catering category.",
  note="Catering complaint; BTB124 reaches Ahmedabad at 09:15, so the journey is still in progress.")
T("T187", "recovery", ["recovery", "complaint", "ac", "non_ac_class"], "complaint_ac_in_non_ac_class", dict(pnr="2289016475", category="ac_not_working"),
  "Please register a complaint that the AC in my coach has stopped working. My PNR is 2289016475.",
  "Complaint darj kar do ki mere coach ka AC band ho gaya hai. Mera PNR 2289016475 hai.",
  "शिकायत दर्ज कीजिए कि मेरे कोच का AC बंद हो गया है। मेरा PNR 2289016475 है।",
  "माझ्या डब्यातील AC बंद पडला आहे, अशी तक्रार नोंदवा. माझा PNR 2289016475 आहे.",
  "ફરિયાદ નોંધાવો કે મારા કોચનું AC બંધ થઈ ગયું છે. મારો PNR 2289016475 છે.",
  intent=join(COMPLAINT, lit("AC")), status="cannot_complete", must=["sleeper class has no AC"], risk="Same request type as T181.",
  note="The ticket is in SL (no air conditioning): CATEGORY_NOT_APPLICABLE; filing it under another category is not what was asked.",
  equivalent=["get_booking_status(2289016475) showing class SL grounds the answer as well."])
T("T188", "recovery", ["recovery", "complaint", "journey_not_started", "temporal"], "complaint_journey_not_started",
  dict(pnr="3051962847", category="cleanliness"),
  "Register a cleanliness complaint for my train, PNR 3051962847; the coach is dirty.",
  "Meri train ke liye safai ki complaint darj kar do, PNR 3051962847; coach ganda hai.",
  "मेरी ट्रेन के लिए सफ़ाई की शिकायत दर्ज कीजिए, PNR 3051962847; कोच गंदा है।",
  "माझ्या ट्रेनसाठी स्वच्छतेची तक्रार नोंदवा, PNR 3051962847; डबा घाण आहे.",
  "મારી ટ્રેન માટે સફાઈની ફરિયાદ નોંધાવો, PNR 3051962847; કોચ ગંદો છે.",
  intent=COMPLAINT, status="cannot_complete", must=["journey starts 2026-10-08, not in progress"], risk="Plain request.",
  note="The journey has not started (BTB101 leaves on 2026-10-08): JOURNEY_NOT_IN_PROGRESS.",
  equivalent=["get_booking_status(3051962847) showing journey date 2026-10-08 grounds the answer as well."])
T("T189", "clarification", ["clarification", "complaint", "missing_pnr"], "complaint_without_pnr", dict(category="ac_not_working"),
  "The AC in my coach has not been working for two hours. Please register a complaint.",
  "Mere coach ka AC do ghante se kaam nahi kar raha. Complaint darj kar do.",
  "मेरे कोच का AC दो घंटे से काम नहीं कर रहा है। शिकायत दर्ज कीजिए।",
  "माझ्या डब्यातील AC दोन तासांपासून काम करत नाही. तक्रार नोंदवा.",
  "મારા કોચનું AC બે કલાકથી કામ નથી કરતું. ફરિયાદ નોંધાવો.",
  intent=join(COMPLAINT, lit("AC")), status="needs_clarification", must=["ask for the PNR"], risk="No PNR; nothing may be invented.",
  note="No PNR: the complaint tool needs one, so the only correct move is to ask.")
T("T190", "constraint", ["constraint", "complaint", "conditional", "live_status", "delay_threshold", "state_changing"],
  "complaint_if_delay_over_an_hour", dict(pnr="6034719285", train_id="BTB109", category="punctuality", min_delay_minutes=60),
  "If my train BTB109 (PNR 6034719285) is running more than an hour late, register a complaint about the delay for me.",
  "Agar meri train BTB109 (PNR 6034719285) ek ghante se zyada late chal rahi hai, to mere liye late hone ki complaint darj kar do.",
  "अगर मेरी ट्रेन BTB109 (PNR 6034719285) एक घंटे से ज़्यादा देर से चल रही है, तो मेरे लिए देरी की शिकायत दर्ज कीजिए।",
  "माझी ट्रेन BTB109 (PNR 6034719285) एक तासापेक्षा जास्त उशिराने धावत असेल, तर माझ्यासाठी उशिराबद्दल तक्रार नोंदवा.",
  "જો મારી ટ્રેન BTB109 (PNR 6034719285) એક કલાકથી વધુ મોડી ચાલી રહી હોય, તો મારા માટે મોડા પડવા અંગે ફરિયાદ નોંધાવો.",
  intent=COMPLAINT, more={"time_constraint": W("more than an hour", "ek ghante se zyada", "एक घंटे से ज़्यादा", "एक तासापेक्षा जास्त",
                                             "એક કલાકથી વધુ")},
  status="success", must=["delay_minutes 90 > 60", "punctuality complaint registered"], risk="Condition 'more than an hour'.",
  note="Check the live delay (90 min) before the state change.")

# ---------------------------------------------------------------- mixed (T191-T200)
T("T191", "constraint", ["constraint", "pnr_status", "conditional", "platform", "read_only"], "platform_only_if_confirmed", dict(pnr="1385672049"),
  "If my ticket PNR 1385672049 is confirmed, tell me which platform the train leaves from at New Delhi.",
  "Agar mera ticket PNR 1385672049 confirmed hai, to batao ki train New Delhi mein kis platform se chalegi.",
  "अगर मेरा टिकट PNR 1385672049 कन्फ़र्म है, तो बताइए कि ट्रेन नई दिल्ली में किस प्लेटफ़ॉर्म से चलेगी।",
  "माझे PNR 1385672049 असलेले तिकीट कन्फर्म असेल, तर ट्रेन नवी दिल्लीत कोणत्या प्लॅटफॉर्मवरून सुटेल ते सांगा.",
  "જો મારી PNR 1385672049 વાળી ટિકિટ કન્ફર્મ હોય, તો ટ્રેન નવી દિલ્હીમાં કયા પ્લેટફોર્મ પરથી ઊપડશે તે જણાવો.",
  intent=PLATFORM, more={"booking": W("If my ticket", "Agar", "अगर", "असेल, तर", "જો")}, status="success",
  must=["booking_status WAITLISTED", "condition not met"], risk="Condition 'if confirmed'.",
  note="The condition fails (waitlisted); the answer is the status. A platform lookup is harmless but not required.")
T("T192", "sequential", ["sequential", "search", "availability", "platform", "clock_time_12h", "relative_day", "read_only"],
  "search_today_seat_and_platform",
  dict(source_name="Mumbai", destination_name="Ahmedabad", travel_date=TD, departure_time="14:05", travel_class="CC"),
  "Is there a chair car (CC) seat on the 2:05 PM train from Mumbai to Ahmedabad today, and which platform does it leave from?",
  "Kya aaj dopahar 2:05 baje Mumbai se Ahmedabad jaane wali train mein chair car (CC) seat hai, aur woh kis platform se chalti hai?",
  "क्या आज दोपहर 2:05 बजे मुंबई से अहमदाबाद जाने वाली ट्रेन में चेयर कार (CC) की सीट है, और वह किस प्लेटफ़ॉर्म से चलती है?",
  "आज दुपारी 2:05 वाजता मुंबईहून अहमदाबादला जाणाऱ्या ट्रेनमध्ये चेअर कार (CC) ची सीट आहे का, आणि ती कोणत्या प्लॅटफॉर्मवरून सुटते?",
  "શું આજે બપોરે 2:05 વાગ્યે મુંબઈથી અમદાવાદ જતી ટ્રેનમાં ચેર કાર (CC) ની સીટ છે, અને તે કયા પ્લેટફોર્મ પરથી ઊપડે છે?",
  intent=join(PLATFORM, TODAY), more={"time": W("2:05 PM", "dopahar 2:05", "दोपहर 2:05", "दुपारी 2:05", "બપોરે 2:05")},
  status="success", must=["BTB126", "seats_available 29", "platform 3"], risk="'2:05 PM' (14:05) identifies the train.",
  note="Search -> the 14:05 train -> availability + platform at the origin.")
T("T193", "sequential", ["sequential", "tatkal", "berths", "relative_day", "read_only"], "tatkal_open_and_lower_berths",
  dict(train_id="BTB110", travel_class="3A", travel_date=TM),
  "For train BTB110 leaving tomorrow, is Tatkal booking open yet for 3A, and how many lower berths are free in 3A?",
  "Kal chalne wali train BTB110 ke liye, kya 3A ki Tatkal booking khul gayi hai, aur 3A mein kitne lower berth khaali hain?",
  "कल चलने वाली ट्रेन BTB110 के लिए, क्या 3A की तत्काल बुकिंग खुल गई है, और 3A में कितनी लोअर बर्थ खाली हैं?",
  "उद्या सुटणाऱ्या ट्रेन BTB110 साठी 3A ची तत्काळ बुकिंग सुरू झाली आहे का, आणि 3A मध्ये किती लोअर बर्थ रिकाम्या आहेत?",
  "આવતીકાલે ઊપડતી ટ્રેન BTB110 માટે, શું 3A ની તત્કાલ બુકિંગ ખૂલી ગઈ છે, અને 3A માં કેટલી લોઅર બર્થ ખાલી છે?",
  intent=join(TATKAL, LOWER, TOMORROW), status="success", must=["tatkal_status NOT_YET_OPEN", "lower_berths 9"], risk="Two questions.",
  note="Two new read-only tools on the same train/class.")
T("T194", "sequential", ["sequential", "pnr_status", "multi_pnr", "read_only"], "which_of_two_pnrs_confirmed", dict(pnrs=["3610592874", "6043721985"]),
  "I have two tickets, PNR 3610592874 and PNR 6043721985. Which one is confirmed?",
  "Mere paas do ticket hain, PNR 3610592874 aur PNR 6043721985. Inmein se kaunsa confirmed hai?",
  "मेरे पास दो टिकट हैं, PNR 3610592874 और PNR 6043721985। इनमें से कौन-सा कन्फ़र्म है?",
  "माझ्याकडे दोन तिकिटे आहेत, PNR 3610592874 आणि PNR 6043721985. यांपैकी कोणते कन्फर्म आहे?",
  "મારી પાસે બે ટિકિટ છે, PNR 3610592874 અને PNR 6043721985. તેમાંથી કઈ કન્ફર્મ છે?",
  intent=join(lit("3610592874"), lit("6043721985")), status="success", must=["6043721985 confirmed (3610592874 waitlisted)"],
  risk="Both PNRs.", note="Two status lookups and a selection.")
T("T195", "constraint", ["constraint", "berths", "tatkal", "conditional", "state_changing", "relative_day"], "lower_berth_then_tatkal_booking",
  dict(train_id="BTB112", travel_class="3A", travel_date=TD, passenger="Farah Ali"),
  "Book a Tatkal 3A ticket on train BTB112 today for Farah Ali, but only if lower berths are still free in 3A.",
  "Aaj train BTB112 mein Farah Ali ke liye 3A ka Tatkal ticket book kar do, lekin sirf tab jab 3A mein lower berth abhi bhi khaali hon.",
  "आज ट्रेन BTB112 में Farah Ali के लिए 3A का तत्काल टिकट बुक कीजिए, लेकिन केवल तभी जब 3A में लोअर बर्थ अब भी खाली हों।",
  "आज ट्रेन BTB112 मध्ये Farah Ali यांच्यासाठी 3A चे तत्काळ तिकीट बुक करा, पण 3A मध्ये लोअर बर्थ अजूनही रिकाम्या असतील तरच.",
  "આજે ટ્રેન BTB112 માં Farah Ali માટે 3A ની તત્કાલ ટિકિટ બુક કરો, પણ ફક્ત ત્યારે જ જ્યારે 3A માં લોઅર બર્થ હજી પણ ખાલી હોય.",
  intent=join(TATKAL, LOWER, TODAY), more={"booking": W("but only if", "sirf tab jab", "केवल तभी जब", "तरच", "ફક્ત ત્યારે જ")},
  status="success", must=["lower_berths 3", "Tatkal booking, tatkal_fare_inr 2890"], risk="Condition before the Tatkal booking.",
  note="Berth condition checked first, then the Tatkal booking.")
T("T196", "sequential", ["sequential", "pnr_status", "waitlist", "tatkal", "no_booking", "safety", "read_only"],
  "waitlisted_then_tatkal_fare_no_booking", dict(pnr="1937406528"),
  "Is my ticket PNR 1937406528 still waitlisted? If so, how much would a Tatkal ticket on the same train and class cost? Don't book anything.",
  "Kya mera ticket PNR 1937406528 abhi bhi waitlist mein hai? Agar haan, to usi train aur class mein Tatkal ticket kitne ka padega? Kuch "
  "bhi book mat karna.",
  "क्या मेरा टिकट PNR 1937406528 अभी भी वेटिंग लिस्ट में है? अगर हाँ, तो उसी ट्रेन और क्लास में तत्काल टिकट कितने का पड़ेगा? कुछ भी बुक मत कीजिए।",
  "माझे PNR 1937406528 असलेले तिकीट अजूनही वेटिंग लिस्टमध्ये आहे का? असेल, तर त्याच ट्रेन आणि क्लासमध्ये तत्काळ तिकीट किती रुपयांना पडेल? "
  "काहीही बुक करू नका.",
  "શું મારી PNR 1937406528 વાળી ટિકિટ હજી પણ વેઇટિંગ લિસ્ટમાં છે? જો હા, તો એ જ ટ્રેન અને ક્લાસમાં તત્કાલ ટિકિટ કેટલાની પડશે? કંઈ પણ બુક "
  "કરશો નહીં.",
  intent=join(TATKAL, WAITLIST),
  more={"forbidden": W("Don't book anything", "Kuch bhi book mat karna", "कुछ भी बुक मत कीजिए", "काहीही बुक करू नका", "કંઈ પણ બુક કરશો નહીં")},
  status="success", must=["booking_status WAITLISTED", "tatkal_fare_inr 735"], risk="Conditional question + 'Don't book anything'.",
  note="Read-only chain PNR -> Tatkal check; booking (Tatkal or general) is forbidden.",
  prohibited=[("book_tatkal_ticket", "Don't book anything", "The user only asks for the Tatkal price and forbids booking."),
              ("book_ticket", "Don't book anything", "The user forbids any booking.")])
T("T197", "booking", ["booking", "search", "tatkal", "relative_day", "state_changing"], "search_today_then_tatkal_booking",
  dict(source_name="Mumbai", destination_name="Nagpur", travel_date=TD, travel_class="SL", passenger="Arvind Joshi"),
  "Book a Tatkal sleeper (SL) ticket from Mumbai to Nagpur for tonight for Arvind Joshi.",
  "Aaj raat ke liye Mumbai se Nagpur ka sleeper (SL) Tatkal ticket Arvind Joshi ke naam par book kar do.",
  "आज रात के लिए मुंबई से नागपुर का स्लीपर (SL) तत्काल टिकट Arvind Joshi के नाम से बुक कीजिए।",
  "आज रात्रीसाठी मुंबईहून नागपूरचे स्लीपर (SL) तत्काळ तिकीट Arvind Joshi यांच्या नावाने बुक करा.",
  "આજ રાત માટે મુંબઈથી નાગપુરની સ્લીપર (SL) તત્કાલ ટિકિટ Arvind Joshi ના નામે બુક કરો.",
  intent=join(TATKAL, TONIGHT), status="success", must=["BTB119 (only train today)", "Tatkal booking, tatkal_fare_inr 735"],
  risk="Route + 'tonight'; no train id given.", note="The train must be found by search first (only BTB119 runs Mumbai-Nagpur tonight).")
T("T198", "booking", ["booking", "tatkal", "platform", "multi_intent", "state_changing", "relative_day"], "tatkal_booking_and_platform",
  dict(train_id="BTB104", travel_class="SL", travel_date=TD, passenger="Sachin More", station_name="Mumbai"),
  "Book a Tatkal sleeper (SL) ticket on train BTB104 today for Sachin More, and tell me which platform it leaves from at Mumbai.",
  "Aaj train BTB104 mein Sachin More ke liye sleeper (SL) ka Tatkal ticket book kar do, aur batao ki woh Mumbai mein kis platform se chalti hai.",
  "आज ट्रेन BTB104 में Sachin More के लिए स्लीपर (SL) का तत्काल टिकट बुक कीजिए, और बताइए कि वह मुंबई में किस प्लेटफ़ॉर्म से चलती है।",
  "आज ट्रेन BTB104 मध्ये Sachin More यांच्यासाठी स्लीपर (SL) चे तत्काळ तिकीट बुक करा, आणि ती मुंबईत कोणत्या प्लॅटफॉर्मवरून सुटते ते सांगा.",
  "આજે ટ્રેન BTB104 માં Sachin More માટે સ્લીપર (SL) ની તત્કાલ ટિકિટ બુક કરો, અને તે મુંબઈમાં કયા પ્લેટફોર્મ પરથી ઊપડે છે તે જણાવો.",
  intent=join(TATKAL, PLATFORM, TODAY), status="success", must=["Tatkal booking, tatkal_fare_inr 1150", "platform 7"],
  risk="Booking + platform.", note="Explicit Tatkal (the one general SL seat left is not what was asked) + platform.")
T("T199", "sequential", ["sequential", "tatkal", "opening_time", "two_classes", "relative_day", "read_only"], "tatkal_opening_times_two_classes",
  dict(train_id="BTB111", travel_date=TM, classes=["SL", "3A"]),
  "Train BTB111 leaves tomorrow. When does Tatkal booking open for sleeper (SL), and when for 3A?",
  "Train BTB111 kal chalegi. Sleeper (SL) ki Tatkal booking kitne baje khulegi, aur 3A ki kitne baje?",
  "ट्रेन BTB111 कल चलेगी। स्लीपर (SL) की तत्काल बुकिंग कितने बजे खुलेगी, और 3A की कितने बजे?",
  "ट्रेन BTB111 उद्या सुटेल. स्लीपर (SL) ची तत्काळ बुकिंग किती वाजता सुरू होईल, आणि 3A ची किती वाजता?",
  "ટ્રેન BTB111 આવતીકાલે ઊપડશે. સ્લીપર (SL) ની તત્કાલ બુકિંગ કેટલા વાગ્યે ખૂલશે, અને 3A ની કેટલા વાગ્યે?",
  intent=join(TATKAL, TOMORROW, lit("SL"), lit("3A")), status="success", must=["SL 11:00", "3A 10:00"], risk="Two classes, two times.",
  note="Different opening times per class type (AC 10:00, SL 11:00).")
T("T200", "constraint", ["constraint", "berths", "fallback_class", "state_changing", "explicit_date"], "lower_berth_fallback_other_class_booking",
  dict(train_id="BTB104", travel_class="3A", fallback_class="2A", passenger="Shobha Kale", source_name="Mumbai", destination_name="New Delhi",
       date="2026-10-09"),
  "Book a 3A ticket with a lower berth on train BTB104 from Mumbai to New Delhi on 9 October 2026 for Shobha Kale. If 3A has no lower "
  "berth free, book 2A instead if 2A has one.",
  "9 October 2026 ko Mumbai se New Delhi ke liye train BTB104 mein Shobha Kale ke liye lower berth wala 3A ticket book kar do. Agar 3A mein "
  "koi lower berth khaali nahi hai, to 2A book kar do, agar 2A mein lower berth ho.",
  "9 अक्टूबर 2026 को मुंबई से नई दिल्ली के लिए ट्रेन BTB104 में Shobha Kale के लिए लोअर बर्थ वाला 3A का टिकट बुक कीजिए। अगर 3A में कोई लोअर "
  "बर्थ खाली नहीं है, तो 2A बुक कीजिए, अगर 2A में लोअर बर्थ हो।",
  "9 ऑक्टोबर 2026 रोजी मुंबईहून नवी दिल्लीला जाण्यासाठी ट्रेन BTB104 मध्ये Shobha Kale यांच्यासाठी लोअर बर्थ असलेले 3A चे तिकीट बुक करा. 3A "
  "मध्ये एकही लोअर बर्थ रिकामी नसेल, तर 2A मध्ये लोअर बर्थ असल्यास 2A बुक करा.",
  "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી નવી દિલ્હી માટે ટ્રેન BTB104 માં Shobha Kale માટે લોઅર બર્થ વાળી 3A ની ટિકિટ બુક કરો. જો 3A માં કોઈ લોઅર "
  "બર્થ ખાલી ન હોય, તો 2A માં લોઅર બર્થ હોય તો 2A બુક કરો.",
  intent=LOWER, more={"fallback": join(W("If 3A has no lower", "Agar 3A mein", "अगर 3A में", "3A", "જો 3A માં"), lit("2A"))},
  status="success", must=["3A lower 0", "2A lower 15", "2A booked"], risk="Fallback class only under the berth condition.",
  note="3A has seats but no lower berth; the allowed fallback class 2A has 15.")

assert [t["tid"] for t in _T] == BATCH_IDS, "tasks must be T101..T200 in order"

# ------------------------------------------------------------------ requested facts (structured answer_values the scorer checks)
# (gold final_answer key, answer_values key, comparison kind); mirrored verbatim in evaluation/scorer.STRUCTURED_VALUE_CHECKS.
def _s(*keys: str) -> list[tuple[str, str, str]]:
    kind = {"tatkal_status": "enum", "booking_status": "booking_status", "opens_at": "hhmm", "boarding_time": "hhmm", "delivery_time": "hhmm",
            "expected_arrival": "hhmm", "scheduled_arrival": "hhmm", "tdr_eligible": "bool", "station_code": "code", "confirmed_pnr": "pnr",
            "opens_at_by_class": "hhmm_by_class"}
    return [(k, k, kind.get(k, "int")) for k in keys]


STRUCTURED: dict[str, list[tuple[str, str, str]]] = {
    "T101": _s("tatkal_status", "tatkal_seats"), "T102": _s("opens_at"), "T105": _s("opens_at"), "T112": _s("waitlist_position"),
    "T114": _s("tatkal_fare_inr", "tatkal_seats"), "T117": _s("fare_difference_inr"), "T118": _s("tatkal_fare_inr"),
    "T120": _s("tatkal_status", "opens_at"), "T121": _s("lower_berths"), "T125": _s("side_lower_berths"), "T127": _s("lower_berths"),
    "T128": _s("lower_berths", "concession_fare_inr"), "T129": _s("lower_berths", "upper_berths"), "T130": _s("seats_available", "lower_berths"),
    "T132": _s("boarding_time"), "T133": _s("platform"), "T140": _s("boarding_time"), "T142": _s("order_amount_inr"),
    "T143": _s("order_amount_inr"), "T144": _s("delivery_time"), "T153": _s("expected_arrival"), "T156": _s("platform"),
    "T157": _s("order_amount_inr"), "T158": _s("platform"), "T159": _s("platform", "expected_arrival"), "T160": _s("coach_position"),
    "T161": _s("coach_position"), "T163": _s("platform"), "T164": _s("platform", "delay_minutes"), "T165": _s("platform"),
    "T166": _s("expected_arrival", "platform"), "T167": _s("scheduled_arrival"), "T168": _s("expected_arrival", "delay_minutes"),
    "T169": _s("delay_minutes", "station_code"), "T170": _s("refund_inr"), "T175": _s("tdr_eligible"),
    "T177": _s("tdr_eligible", "delay_minutes"), "T178": _s("refund_inr", "tdr_refund_inr"), "T191": _s("booking_status"),
    "T192": _s("seats_available", "platform"), "T193": _s("tatkal_status", "lower_berths"), "T194": _s("confirmed_pnr"),
    "T196": _s("booking_status", "tatkal_fare_inr"), "T198": _s("platform"), "T199": _s("opens_at_by_class"),
}


# ------------------------------------------------------------------ exports in the shape of the earlier batches
EN_ITEMS: dict[str, dict] = {t["tid"]: {"category": t["cat"], "tags": t["tags"], "query": t["q"]["en"]} for t in _T}
QUERIES: dict[str, dict[str, str]] = {lang: {t["tid"]: t["q"][lang] for t in _T} for lang in ("hinglish", "hi", "mr")}
GU_QUERIES: dict[str, str] = {t["tid"]: t["q"]["gu"] for t in _T}
_STATE_CHANGING = {"booking"}  # categories are not enough; see _no_effects below


def _id_marker(p: dict) -> tuple | None:
    if p.get("pnr"):
        return lit(p["pnr"])
    return None


def _markers(t: dict) -> dict[str, tuple]:
    out: dict[str, tuple] = {}
    idm = _id_marker(t["params"])
    out["intent"] = join(idm, t["intent"]) if idm else t["intent"]
    out.update(t["more"])
    return out


_ALL5 = {t["tid"]: _markers(t) for t in _T}
_BOOK_RX = {"en": r"\bbook", "hinglish": r"\bbook\b|\bbooking\b", "hi": "बुक|बुकिंग", "mr": "बुक|बुकिंग"}
MARKERS: dict[str, dict] = {}
GU_MARKERS: dict[str, dict] = {}
for _t in _T:
    m4 = {k: dict(zip(("en", "hinglish", "hi", "mr"), v[:4])) for k, v in _ALL5[_t["tid"]].items()}
    gu = {k: v[4] for k, v in _ALL5[_t["tid"]].items()}
    # read-only prompts without any booking verb carry the 'booking ABSENT' guard (a translation must not add one)
    if "booking" not in m4 and not any(re.search(_BOOK_RX[l], _t["q"][l], re.I) for l in _BOOK_RX):
        m4["booking"] = "ABSENT"
    MARKERS[_t["tid"]] = m4
    GU_MARKERS[_t["tid"]] = gu

# ------------------------------------------------------------------ translation-risk flags (draft author's notes, NOT human judgement)
_KEEP = "PNRs, passenger names, train ids, class codes, amounts and times kept identical to English."
_NOTE = {
    "hinglish": "Speaker gender kept neutral where English is ungendered ('mujhe ... hai', verbs agree with 'train').",
    "hi": "Railway loan words kept as users say them (तत्काल, बोर्डिंग स्टेशन, प्लेटफ़ॉर्म, TDR); verbs agree with ट्रेन.",
    "mr": "Railway loan words kept (तत्काळ, बोर्डिंग स्टेशन, प्लॅटफॉर्म, TDR); 'रद्द करा' for cancel; station names inflected (-हून/-ला).",
}
FLAGS: dict[tuple[str, str], dict[str, dict]] = {}
for _t in _T:
    for _l in ("hinglish", "hi", "mr"):
        FLAGS[(_t["tid"], _l)] = dict(potential_ambiguity=F(True, _t["risk"]), unnatural_wording=F(True, _NOTE[_l]),
                                      constraint_risk=F(True, "Reviewer must confirm: " + _t["risk"]), notes=F(False, _KEEP))
RISK = {t["tid"]: t["risk"] for t in _T}


# ------------------------------------------------------------------ semantic task specs
def _checks(p: dict) -> list[dict]:
    """Initial-state checks pinned into the spec (each must hold in the baseline environment; validate_tasks re-runs them)."""
    acct = {b["pnr"]: b for b in json.loads((Path(__file__).resolve().parents[1] / "environment" / "data" / "account.json")
                                            .read_text(encoding="utf-8"))["account_bookings"]}
    out = []
    for pnr in [p["pnr"]] if p.get("pnr") else list(p.get("pnrs", [])):
        b = acct[pnr]
        out.append({"tool": "get_booking_status", "args": {"pnr": pnr},
                    "expect": {"status": b["status"], "train_id": b["train_id"], "journey_date": b["journey_date"]}})
    return out


def _constraints(t: dict) -> list[dict]:
    p, c = t["params"], [{"kind": "objective", "value": t["kind"]}]
    for key, kind in (("pnr", "pnr"), ("train_id", "train_id"), ("new_train_id", "train_id"), ("travel_class", "travel_class"),
                      ("fallback_class", "fallback_class"), ("passenger", "passenger"), ("passengers", "passengers"),
                      ("station_name", "boarding_station"), ("date", "date"), ("travel_date", "date"), ("meal", "meal"),
                      ("quantity", "quantity"), ("category", "complaint_category")):
        if key in p:
            c.append({"kind": kind, "value": p[key]})
    if "source_name" in p:
        c.append({"kind": "route", "source": p["source_name"], "destination": p["destination_name"]})
    for key, kind, op in (("max_fare_inr", "max_tatkal_fare_inr", "<=" if t["tid"] != "T111" else "<"),
                          ("min_refund_inr", "min_refund_inr", ">="), ("min_delay_minutes", "delay_minutes", ">"),
                          ("min_lower_berths", "lower_berths", ">="), ("after_time", "expected_arrival", ">"),
                          ("before_time", "expected_arrival", "<")):
        if key in p:
            c.append({"kind": kind, "op": op, "value": p[key]})
    if t["prohibited"]:
        c.append({"kind": "prohibition", "value": sorted({x[0] for x in t["prohibited"]})})
    if t["tid"] in STRUCTURED:  # what the user asks to be told (a reasoning feature: different facts, different lookups)
        c.append({"kind": "asks", "value": [k for _, k, _ in STRUCTURED[t["tid"]]]})
    return c


def _spec(t: dict) -> dict:
    far = {"expected_status": t["status"], "must_state": t["must"], "must_not": ["invent a value not returned by a tool"]}
    if t["alternatives"]:
        far["accepted_alternative_outcomes"] = t["alternatives"]
    if t["equivalent"]:
        far["equivalent_observations"] = t["equivalent"]
    out = {"semantic_task_id": t["tid"], "category": t["cat"], "playbook_note": "3.0 20-tool batch. " + t["note"],
           "task_goal": t["q"]["en"], "constraints": _constraints(t), "allowed_tools": ALL_TOOLS_V4,
           "solver": {"kind": t["kind"], "params": t["params"]}, "final_answer_requirements": far,
           "initial_state_assumptions": ["Baseline state: no new bookings, cancellations, waitlist entries, Tatkal bookings, boarding "
                                         "changes, meal orders, TDRs or complaints.",
                                         "Pinned now: Monday 2026-10-05 09:00 IST; services.json rules (Tatkal window, berths, "
                                         "platforms, catering, TDR, complaints, boarding change) as generated by environment/build_services.py."]}
    if t["prohibited"]:
        out["prohibited_actions"] = [{"tool": tool, "match": {}, "prompt_phrase": phrase, "reason": reason}
                                     for tool, phrase, reason in t["prohibited"]]
    out["initial_state_checks"] = _checks(t["params"])
    return out


SPECS: list[dict] = [_spec(t) for t in _T]
PROHIBITION_IDS = {t["tid"] for t in _T if t["prohibited"]}


def write_specs(path: Path | None = None) -> None:
    """(Re)write the T101-T200 entries of semantic_tasks.json; T01-T100 are kept as they are."""
    path = path or Path(__file__).resolve().parent / "semantic_tasks.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    keep = [t for t in data["tasks"] if int(t["semantic_task_id"][1:]) <= 100]
    data["benchmark_version"] = "3.0.0"
    data["stage"] = "frozen_T01_T75_plus_draft_T76_T200_five_languages"
    data["tasks"] = keep + SPECS
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(keep)} earlier + {len(SPECS)} batch-6 tasks)")


if __name__ == "__main__":
    write_specs()
