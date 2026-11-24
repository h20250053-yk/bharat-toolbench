"""Gujarati (gu) for the end-sem batch T51-T75. Merged into benchmark/batch_gujarati.py (same conventions as there).

The 8 language-feature tasks keep their feature in Gujarati:
  T54 native-script name 'રવિ પટેલ' (must become 'Ravi Patel')   T57 'પરમ દિવસે' (day after tomorrow)
  T62 spoken time 'સવા સાત' (07:15)                             T64 fraction amount 'અઢી હજાર' (₹2,500)
  T67 impossible date '31 નવેમ્બર'                               T69 two names for one station 'હાવડાથી કોલકાતા'
  T71 repeated passenger in the list                             T72 exclusion 'BTB110 સિવાયની'
"""
from __future__ import annotations

from .batch_t06_t15 import F, OK

IDS = [f"T{i}" for i in range(51, 76)]

QUERIES: dict[str, str] = {
    "T51": "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી અમદાવાદ માટે કેટલી સીધી ટ્રેનો છે? તેમાંથી મુંબઈથી સૌથી છેલ્લે કઈ ટ્રેન ઊપડે છે, અને શું તેમાં 3A ની "
           "સીટો ઉપલબ્ધ છે?",
    "T52": "મારે 9 ઓક્ટોબર 2026ના રોજ સાંજે 6 વાગ્યે અથવા તે પછી અમદાવાદથી જયપુર જવા નીકળવું છે. કઈ ટ્રેન જયપુર સૌથી વહેલી પહોંચાડે છે, અને "
           "તે કેટલા વાગ્યે પહોંચે છે?",
    "T53": "9 ઓક્ટોબર 2026ના રોજ કોલકાતાથી લખનઉ માટે 3A માં કઈ ટ્રેન સસ્તી છે: સાંજે 4:55 વાગ્યાવાળી કે સાંજે 7:30 વાગ્યાવાળી? કેટલી સસ્તી છે?",
    "T54": "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી અમદાવાદ માટે રવિ પટેલના નામે ચેર કાર (CC) ટિકિટ બુક કરો.",
    "T55": "10 ઓક્ટોબર 2026ના રોજ લખનઉથી નવી દિલ્હી જવા માટે ટ્રેન BTB110 પકડવાની છે. નવી દિલ્હી કેટલા વાગ્યે પહોંચીશું, અને શું 3A ની સીટો "
           "ઉપલબ્ધ છે?",
    "T56": "9 ઓક્ટોબર 2026ના રોજ સાંજે 6 વાગ્યે અથવા તે પછી પુણેથી મુંબઈ કે નાગપુર જતી બધી ટ્રેનો તેમના ઊપડવાના સમય સાથે જણાવો.",
    "T57": "પરમ દિવસે અમદાવાદથી જયપુર જતી, સ્લીપર (SL) ક્લાસ ધરાવતી છેલ્લી ટ્રેન કઈ છે, અને તે કેટલા વાગ્યે ઊપડે છે?",
    "T58": "બે કામ છે: ટ્રેન BTB117 માં ચેર કાર (CC) ની કેટલી સીટો બાકી છે તે જણાવો, અને 9 ઓક્ટોબર 2026ના રોજ અમદાવાદથી પુણે માટે ટ્રેન BTB123 "
           "માં Manav Trivedi ના નામે 3A ની ટિકિટ બુક કરો.",
    "T59": "9 ઓક્ટોબર 2026ના રોજ પુણેથી મુંબઈ માટે ટ્રેન BTB118 માં Ritu Chawla ના નામે ચેર કાર (CC) ટિકિટ બુક કરો — ના, રહેવા દો, બુક કરશો "
           "નહીં; ફક્ત CC નું ભાડું જણાવો.",
    "T60": "9 ઓક્ટોબર 2026ના રોજ પુણેથી મુંબઈ જવું છે અને રાત્રે 10 વાગ્યા પહેલાં મુંબઈ પહોંચવું જરૂરી છે. 3A કે 2A, જે સસ્તું હોય તે લઈશું. "
           "કઈ ટ્રેન અને કયો ક્લાસ લેવો જોઈએ, અને ભાડું કેટલું છે? કંઈ પણ બુક કરશો નહીં.",
    "T61": "9 ઓક્ટોબર 2026ના રોજ પુણેથી નાગપુર માટે Sagar Pawar, Swati Pawar અને Om Pawar માટે સ્લીપર (SL) ની ત્રણ ટિકિટ બુક કરો, પણ ફક્ત "
           "ત્યારે જ જ્યારે ત્રણેયનું કુલ ભાડું ₹1,800 થી વધુ ન હોય.",
    "T62": "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી પુણે માટે સવારે સવા સાત વાગ્યે ઊપડતી ટ્રેનમાં ચેર કાર (CC) નું ભાડું કેટલું છે?",
    "T63": "9 ઓક્ટોબર 2026ના રોજ નવી દિલ્હીથી કોલકાતા જવું છે અને 10 ઓક્ટોબરે રાત્રે 8 વાગ્યા સુધીમાં કોલકાતા પહોંચવું છે. મને 3A જોઈએ છે. "
           "કઈ ટ્રેન લઈ શકાય?",
    "T64": "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી અમદાવાદની એવી સૌથી પહેલી ટ્રેન કઈ છે જેનું 3A ભાડું અઢી હજાર રૂપિયાથી ઓછું હોય?",
    "T65": "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી અમદાવાદ માટે Kunal Mehta, Rina Mehta અને Dev Mehta ની 3A ટિકિટ બુક કરો, ત્રણેય એક જ ટ્રેનમાં: એવી "
           "સૌથી પહેલી ટ્રેન જેમાં અમારા ત્રણેય માટે 3A ની સીટો હોય.",
    "T66": "ટ્રેન BTB111 માં નવી દિલ્હીથી લખનઉ માટે Gaurav Saxena ના નામે 3A ની ટિકિટ બુક કરો, 9 ઓક્ટોબર 2026 પછી આ ટ્રેન જે પહેલા દિવસે "
           "ચાલતી હોય તે દિવસ માટે.",
    "T67": "31 નવેમ્બર 2026ના રોજ પુણેથી નાગપુર માટે Neha Kulkarni ના નામે સ્લીપર (SL) ટિકિટ બુક કરો.",
    "T68": "જો 9 ઓક્ટોબર 2026ના રોજ નાગપુરથી મુંબઈ માટે ટ્રેન BTB120 માં હું મારા પિતાજી માટે 2A અને મારા માટે 3A બુક કરું, તો બંને ટિકિટનું "
           "કુલ ભાડું કેટલું થાય?",
    "T69": "9 ઓક્ટોબર 2026ના રોજ હાવડાથી કોલકાતા માટે Arpita Ghosh ના નામે 3A ની ટિકિટ બુક કરો.",
    "T70": "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી જયપુર માટે ટ્રેન BTB104 માં Yash Kapoor ના નામે સ્લીપર (SL) ની એક ટિકિટ બુક કરો, પણ ફક્ત ત્યારે જ "
           "જ્યારે ઓછામાં ઓછી 5 SL સીટો બાકી હોય — મારા મિત્રો પછીથી સાથે આવી શકે છે.",
    "T71": "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી પુણે માટે ટ્રેન BTB115 માં આ મુસાફરોની 3A ટિકિટ બુક કરો: Anjali Rao, Sunil Rao, Anjali Rao.",
    "T72": "9 ઓક્ટોબર 2026ના રોજ કોલકાતાથી નવી દિલ્હી માટે Arjun Sen ના નામે 3A ની ટિકિટ બુક કરો, BTB110 સિવાયની કોઈ પણ ટ્રેનમાં.",
    "T73": "9 ઓક્ટોબર 2026ના રોજ નવી દિલ્હીથી અમદાવાદ માટે ટ્રેન BTB101 માં Varun Bhatt ના નામે 2A ની ટિકિટ બુક કરો. જો એ ટ્રેનમાં 2A ભરાઈ "
           "ગયું હોય, તો એ જ દિવસે તેના પછી ઊપડતી પહેલી ટ્રેનમાં 2A બુક કરો.",
    "T74": "9 ઓક્ટોબર 2026ના રોજ નવી દિલ્હીથી મુંબઈ માટે ટ્રેન BTB1O3 માં Ravi Shankar ના નામે 2A ની ટિકિટ બુક કરો.",
    "T75": "9 ઓક્ટોબર 2026ના રોજ નવી દિલ્હીથી જયપુર માટે ટ્રેન BTB105 માં Sonal Bhatia ના નામે સ્લીપર (SL) ટિકિટ બુક કરો. જો એ ટ્રેનમાં "
           "સ્લીપર ક્લાસ ન હોય, તો તેમાં જે પણ ક્લાસ હોય તેમાં બુક કરો.",
}

_BOOK = ["બુક કરો"]
_SEATS3A = ["3A ની સીટો ઉપલબ્ધ"]
_AFTER6 = ["6 વાગ્યે અથવા તે પછી"]
MARKERS: dict[str, dict[str, list[str]]] = {
    "T51": {"intent": ["કેટલી સીધી ટ્રેનો", "સૌથી છેલ્લે"], "availability": _SEATS3A},
    "T52": {"time_constraint": _AFTER6, "intent": ["સૌથી વહેલી", "કેટલા વાગ્યે પહોંચે"]},
    "T53": {"time": ["સાંજે 4:55", "સાંજે 7:30"], "fare": ["સસ્તી", "કેટલી સસ્તી"]},
    "T54": {"intent": [r"ચેર કાર \(CC\)"], "booking": _BOOK},
    "T55": {"intent": ["BTB110 પકડવાની", "કેટલા વાગ્યે પહોંચ"], "availability": _SEATS3A},
    "T56": {"time_constraint": _AFTER6, "intent": ["બધી ટ્રેનો", "મુંબઈ કે નાગપુર"]},
    "T57": {"intent": ["^પરમ દિવસે", "છેલ્લી ટ્રેન"]},
    "T58": {"intent": ["બે કામ", r"BTB117 માં ચેર કાર \(CC\) ની કેટલી સીટો બાકી"], "booking": ["BTB123 માં .* 3A ની ટિકિટ બુક કરો"]},
    "T59": {"forbidden": ["ના, રહેવા દો, બુક કરશો નહીં"], "fare": ["ફક્ત CC નું ભાડું"], "booking": _BOOK},
    "T60": {"time_constraint": ["રાત્રે 10 વાગ્યા પહેલાં"], "fare": ["જે સસ્તું"], "intent": ["3A કે 2A"], "forbidden": ["કંઈ પણ બુક કરશો નહીં"]},
    "T61": {"fare": ["ત્રણેયનું કુલ ભાડું ₹1,800 થી વધુ ન હોય"], "intent": ["ત્રણ ટિકિટ"], "booking": ["બુક કરો", "ફક્ત ત્યારે જ"]},
    "T62": {"time": ["સવારે સવા સાત વાગ્યે"], "intent": ["ભાડું"]},
    "T63": {"time_constraint": ["10 ઓક્ટોબરે રાત્રે 8 વાગ્યા સુધીમાં"], "intent": ["કઈ ટ્રેન"]},
    "T64": {"fare": ["અઢી હજાર રૂપિયાથી ઓછું"], "intent": ["સૌથી પહેલી"]},
    "T65": {"intent": ["એક જ ટ્રેનમાં", "સૌથી પહેલી ટ્રેન"], "availability": ["અમારા ત્રણેય માટે 3A ની સીટો"], "booking": _BOOK},
    "T66": {"intent": ["9 ઓક્ટોબર 2026 પછી", "જે પહેલા દિવસે ચાલતી"], "booking": _BOOK},
    "T67": {"intent": ["31 નવેમ્બર 2026"], "booking": _BOOK},
    "T68": {"intent": ["^જો", "પિતાજી માટે 2A અને મારા માટે 3A", "બુક કરું, તો", "કુલ ભાડું કેટલું થાય"]},
    "T69": {"intent": ["હાવડાથી કોલકાતા"], "booking": _BOOK},
    "T70": {"availability": ["ઓછામાં ઓછી 5 SL સીટો બાકી"], "booking": ["બુક કરો", "ફક્ત ત્યારે જ"]},
    "T71": {"intent": ["Anjali Rao, Sunil Rao, Anjali Rao"], "booking": _BOOK},
    "T72": {"forbidden": ["BTB110 સિવાયની કોઈ પણ ટ્રેનમાં"], "booking": _BOOK},
    "T73": {"availability": ["જો એ ટ્રેનમાં 2A ભરાઈ ગયું"], "fallback": ["એ જ દિવસે તેના પછી ઊપડતી પહેલી ટ્રેનમાં"], "booking": _BOOK},
    "T74": {"intent": [r"\bBTB1O3\b"], "booking": _BOOK},
    "T75": {"availability": ["સ્લીપર ક્લાસ ન હોય"], "fallback": ["જે પણ ક્લાસ હોય તેમાં બુક"], "booking": _BOOK},
}

_RISK = {
    "T51": "Two questions (count, then the last train) plus the seat question; 'સીધી' (direct) must not be dropped.",
    "T52": "Inclusive 'સાંજે 6 વાગ્યે અથવા તે પછી' + 'reaches Jaipur EARLIEST' (arrival, not departure).",
    "T53": "Both clock times (4:55 PM, 7:30 PM) and 'કેટલી સસ્તી' (by how much).",
    "T54": "The name is written in Gujarati script (રવિ પટેલ) BY DESIGN; a reviewer must NOT romanise it.",
    "T55": "Boarding at Lucknow on 10 October (not the train's start date).",
    "T56": "Two destinations ('મુંબઈ કે નાગપુર'), one inclusive time bound, 'બધી ટ્રેનો' (all trains).",
    "T57": "'પરમ દિવસે' must stay relative (no date). Like Hindi परसों it can also mean 'day before yesterday'; the future context fixes it.",
    "T58": "Both intents: the BTB117 CC seat question AND the BTB123 booking.",
    "T59": "The retraction ('ના, રહેવા દો, બુક કરશો નહીં') must clearly cancel the booking request.",
    "T60": "Strict 'રાત્રે 10 વાગ્યા પહેલાં', the 3A/2A choice by fare, and no booking.",
    "T61": "The budget applies to the TOTAL for all three (₹1,800), not to one ticket.",
    "T62": "The time must stay SPOKEN ('સવા સાત' = 7:15), never '7:15'; not 'સાડા સાત' (7:30) or 'પોણા સાત' (6:45).",
    "T63": "Arrival deadline 'by 8 PM on 10 October' (inclusive) and class 3A.",
    "T64": "The amount must stay in WORDS ('અઢી હજાર' = 2,500), never '₹2,500'; 'ઓછું' is strict (under).",
    "T65": "Same train for all three; earliest train with enough 3A seats for ALL three.",
    "T66": "'9 ઓક્ટોબર 2026 પછી ... જે પહેલા દિવસે ચાલતી હોય' must not become 'on 9 October'.",
    "T67": "The impossible date '31 નવેમ્બર' must be kept; a reviewer must not 'fix' it.",
    "T68": "The hypothetical ('જો ... બુક કરું, તો ... કેટલું થાય') must not become an order.",
    "T69": "Both station names (હાવડા AND કોલકાતા) must be kept, though they are the same station.",
    "T70": "Threshold 'ઓછામાં ઓછી 5 SL સીટો' (inclusive); only ONE ticket requested.",
    "T71": "The repeated name must be kept (Anjali Rao twice).",
    "T72": "The exclusion 'BTB110 સિવાયની' must keep its negative meaning.",
    "T73": "Fallback = the NEXT later train the same day, same class. 'આગલી' was avoided (it can mean 'previous').",
    "T74": "The typo 'BTB1O3' (letter O) must be kept exactly.",
    "T75": "Explicit permission to take whatever class the train has, after SL is not offered.",
}
_NOTE = {
    "T52": "'પહોંચાડે છે' = gets (me) there; speaker kept neutral with 'મારે ... નીકળવું છે'.",
    "T53": "'4:55 વાગ્યાવાળી' = the 4:55 one (colloquial).",
    "T54": "Genitive attached directly to the Gujarati name ('રવિ પટેલના નામે'), as natural Gujarati writes it.",
    "T55": "'પહોંચીશું' (we) keeps the speaker gender-neutral.",
    "T57": "'પરમ દિવસે' = day after tomorrow.",
    "T59": "'ના, રહેવા દો' = no, leave it.",
    "T60": "'લઈશું' (we'll take) keeps the speaker gender-neutral.",
    "T62": "'સવા સાત' = quarter past seven.",
    "T64": "'અઢી હજાર' = two and a half thousand.",
    "T66": "Date clause at the end, mirroring Hindi.",
    "T68": "Subjunctive 'બુક કરું' carries the hypothetical; ungendered.",
    "T69": "'હાવડાથી' = from Howrah; both names are aliases of HWH.",
    "T72": "'BTB110 સિવાયની કોઈ પણ ટ્રેનમાં' = on any train except BTB110.",
    "T73": "'તેના પછી ઊપડતી પહેલી ટ્રેન' = the first train leaving after it.",
}
_KEEP = ("Passenger names, train ids, class codes, amounts and dates use Latin letters / ASCII digits, separated from Gujarati "
         "suffixes by a space; station names use the frozen Gujarati aliases.")
FLAGS: dict[tuple[str, str], dict[str, dict]] = {
    (t, "gu"): dict(potential_ambiguity=F(True, _RISK[t]), unnatural_wording=F(True, _NOTE[t]) if t in _NOTE else OK,
                    constraint_risk=F(True, "Reviewer must confirm: " + _RISK[t]),
                    notes=F(False, _KEEP if t != "T54" else "Passenger name in Gujarati script BY DESIGN; ids, classes and digits kept Latin/ASCII."))
    for t in IDS
}
