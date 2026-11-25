"""Gujarati (gu) for the 3.0 batch T76-T100 (the six new tools). Merged into benchmark/batch_gujarati.py (same conventions as there).

PNRs, train ids, class codes, amounts and dates use ASCII digits / Latin letters, separated from Gujarati suffixes by a space
('BTB101 માં'); passenger names stay Latin; station names use the frozen Gujarati aliases. Loan words that Gujarati railway users
say every day are kept as such (કેન્સલ, રિફંડ, વેઇટિંગ લિસ્ટ, સ્ટેટસ, કન્સેશન, સિનિયર સિટીઝન).
"""
from __future__ import annotations

from .batch_t06_t15 import F, OK

IDS = [f"T{i}" for i in range(76, 101)]

QUERIES: dict[str, str] = {
    "T76": "મારી PNR 7302958146 વાળી ટિકિટનું હાલનું સ્ટેટસ શું છે? જો તે વેઇટિંગ લિસ્ટમાં હોય, તો વેઇટિંગ લિસ્ટમાં મારો નંબર કેટલો છે?",
    "T77": "જો હું મારી PNR 4518203967 વાળી ટિકિટ અત્યારે કેન્સલ કરું, તો મને કેટલા પૈસા પાછા મળશે? હમણાં કેન્સલ કરશો નહીં, મેં હજી નક્કી "
           "કર્યું નથી.",
    "T78": "મારી PNR 9157364820 વાળી ટિકિટ કેન્સલ કરો અને કેટલું રિફંડ મળશે તે જણાવો.",
    "T79": "મારી PNR 5079318462 વાળી ટિકિટ કેન્સલ કરો, પણ ફક્ત ત્યારે જ જ્યારે ઓછામાં ઓછા ₹7,400 પાછા મળે. નહીંતર તેને એમ જ રહેવા દો.",
    "T80": "જો રિફંડ ઓછામાં ઓછું ₹450 હોય, તો મારી PNR 6720483915 વાળી ટિકિટ કેન્સલ કરો.",
    "T81": "શું તમે મારી PNR 5551234567 વાળી ટિકિટનું સ્ટેટસ તપાસી શકો?",
    "T82": "મારી PNR 2894017356 વાળી ટિકિટ કેન્સલ કરો.",
    "T83": "મારી PNR 8803164527 વાળી ટિકિટ કેન્સલ કરો અને રિફંડ જણાવો.",
    "T84": "8 ઓક્ટોબર 2026ના રોજ નવી દિલ્હીથી મુંબઈ માટે ટ્રેન BTB101 માં Kiran Desai ના નામે 2A ની ટિકિટ બુક કરો. જો 2A ભરાઈ ગયું હોય, "
           "તો તેમને વેઇટિંગ લિસ્ટમાં મૂકો.",
    "T85": "7 ઓક્ટોબર 2026ના રોજ નવી દિલ્હીથી લખનઉ માટે ટ્રેન BTB109 માં Imran Qureshi ના નામે 3A ની ટિકિટ બુક કરો. જો 3A સોલ્ડ આઉટ "
           "હોય, તો તેમને વેઇટિંગ લિસ્ટમાં મૂકશો નહીં; ફક્ત મને જણાવો.",
    "T86": "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી નવી દિલ્હી માટે ટ્રેન BTB104 માં Asha Menon ના નામે સ્લીપર (SL) ટિકિટ બુક કરો. જો સ્લીપર સોલ્ડ "
           "આઉટ હોય, તો તેમને વેઇટિંગ લિસ્ટમાં મૂકો.",
    "T87": "શું ટ્રેન BTB105 અત્યારે મોડી ચાલી રહી છે? જો હા, તો કેટલી મિનિટ મોડી?",
    "T88": "મારાં મમ્મી ટ્રેન BTB103 માં મુસાફરી કરી રહ્યાં છે, જે ગઈ રાત્રે નવી દિલ્હીથી ઊપડી હતી. હવે તે અમદાવાદ કેટલા વાગ્યે પહોંચવાની "
           "અપેક્ષા છે?",
    "T89": "શું ટ્રેન BTB111 આજે ચાલી રહી છે? જો ચાલતી હોય, તો કેટલી મોડી છે?",
    "T90": "હું અત્યારે મુંબઈ જતી ટ્રેન BTB125 માં છું. મારે આજે બપોરે 2:05 વાગ્યે મુંબઈથી અમદાવાદ પાછી જતી ચેર કાર ટ્રેન પકડવાની છે. "
           "શું મારી ટ્રેન સમયસર મુંબઈ પહોંચશે?",
    "T91": "ટ્રેન BTB115 માં સિનિયર સિટીઝન માટે 3A ની ટિકિટ કેટલાની છે?",
    "T92": "મારાં દાદી, જે સિનિયર સિટીઝન છે, અને મારે 9 ઓક્ટોબર 2026ના રોજ પુણેથી નાગપુર માટે ટ્રેન BTB127 માં સ્લીપર (SL) ટિકિટ લેવી "
           "છે. બંને ટિકિટનું કુલ ભાડું કેટલું થશે? હમણાં કંઈ પણ બુક કરશો નહીં.",
    "T93": "મારો દીકરો વિદ્યાર્થી છે. ટ્રેન BTB117 માં સ્ટુડન્ટ કન્સેશન સાથે ચેર કાર (CC) ની ટિકિટ કેટલાની પડશે?",
    "T94": "હું વિદ્યાર્થી છું અને મારી પાસે ₹1,100 છે. શું સ્ટુડન્ટ કન્સેશન સાથે ટ્રેન BTB120 ની 3A ટિકિટ મારા બજેટમાં આવી જશે?",
    "T95": "મારી PNR 4073819256 વાળી ટિકિટ કેન્સલ કરો અને એ જ મુસાફર માટે એ જ ટ્રેનમાં સ્લીપર (SL) ક્લાસની ટિકિટ બુક કરો.",
    "T96": "જો મારી PNR 1385672049 વાળી ટિકિટ હજી પણ વેઇટિંગ લિસ્ટમાં હોય, તો તેને કેન્સલ કરો અને એ જ મુસાફર માટે એ જ ટ્રેનમાં સ્લીપર "
           "(SL) ટિકિટ બુક કરો.",
    "T97": "મારી PNR 6043721985 વાળી ટિકિટ તપાસો: જો તે વેઇટિંગ લિસ્ટમાં હોય તો કેન્સલ કરો; જો કન્ફર્મ હોય તો તેને એમ જ રહેવા દો.",
    "T98": "મારી આવતીકાલની ટ્રેન ટિકિટ કેન્સલ કરો.",
    "T99": "અમારી બંને ટિકિટ, PNR 2951847306 અને PNR 2951847314, કેન્સલ કરો અને કુલ રિફંડ જણાવો.",
    "T100": "શું ટ્રેન BTB120 માં હજી પણ 3A ની સીટો ઉપલબ્ધ છે, અને તેમાં સિનિયર સિટીઝને 3A માટે કેટલું ચૂકવવું પડશે?",
}

_BOOK = ["બુક કરો"]
_CANCEL = ["કેન્સલ કરો"]
_SENIOR = ["સિનિયર સિટીઝન"]
_STUDENT = ["સ્ટુડન્ટ કન્સેશન"]
MARKERS: dict[str, dict[str, list[str]]] = {
    "T76": {"intent": ["7302958146", "સ્ટેટસ", "વેઇટિંગ લિસ્ટમાં મારો નંબર"]},
    "T77": {"intent": ["4518203967", "કેટલા પૈસા પાછા મળશે"], "forbidden": ["હમણાં કેન્સલ કરશો નહીં"]},
    "T78": {"intent": ["9157364820", *_CANCEL, "રિફંડ"]},
    "T79": {"intent": ["5079318462", *_CANCEL], "fare": ["ફક્ત ત્યારે જ જ્યારે ઓછામાં ઓછા ₹7,400 પાછા"], "fallback": ["નહીંતર તેને એમ જ રહેવા દો"]},
    "T80": {"intent": ["6720483915", *_CANCEL], "fare": ["જો રિફંડ ઓછામાં ઓછું ₹450"]},
    "T81": {"intent": ["5551234567", "સ્ટેટસ"]},
    "T82": {"intent": ["2894017356", *_CANCEL]},
    "T83": {"intent": ["8803164527", *_CANCEL, "રિફંડ"]},
    "T84": {"availability": ["જો 2A ભરાઈ ગયું હોય"], "fallback": ["વેઇટિંગ લિસ્ટ", "વેઇટિંગ લિસ્ટમાં મૂકો"], "booking": _BOOK},
    "T85": {"availability": ["જો 3A સોલ્ડ આઉટ"], "forbidden": ["વેઇટિંગ લિસ્ટમાં મૂકશો નહીં"], "booking": _BOOK},
    "T86": {"availability": ["જો સ્લીપર સોલ્ડ આઉટ"], "fallback": ["વેઇટિંગ લિસ્ટમાં મૂકો"], "booking": _BOOK},
    "T87": {"intent": ["અત્યારે મોડી ચાલી રહી", "કેટલી મિનિટ"]},
    "T88": {"intent": ["ગઈ રાત્રે નવી દિલ્હીથી ઊપડી", "અમદાવાદ કેટલા વાગ્યે પહોંચવાની"]},
    "T89": {"intent": ["આજે ચાલી રહી", "કેટલી મોડી"]},
    "T90": {"intent": ["અત્યારે મુંબઈ જતી ટ્રેન BTB125 માં", "સમયસર મુંબઈ પહોંચશે"], "time": ["બપોરે 2:05"]},
    "T91": {"intent": _SENIOR},
    "T92": {"intent": [*_SENIOR, "બંને ટિકિટનું કુલ ભાડું"], "forbidden": ["હમણાં કંઈ પણ બુક કરશો નહીં"]},
    "T93": {"intent": _STUDENT},
    "T94": {"intent": _STUDENT, "fare": ["મારી પાસે ₹1,100", "બજેટમાં"]},
    "T95": {"intent": ["4073819256", *_CANCEL, "એ જ મુસાફર માટે એ જ ટ્રેનમાં"], "booking": _BOOK},
    "T96": {"intent": ["1385672049", *_CANCEL, "એ જ મુસાફર", "એ જ ટ્રેનમાં"], "booking": [*_BOOK, "હજી પણ વેઇટિંગ લિસ્ટમાં હોય, તો"]},
    "T97": {"intent": ["6043721985", "વેઇટિંગ લિસ્ટમાં હોય તો કેન્સલ કરો", "કન્ફર્મ હોય તો તેને એમ જ રહેવા દો"]},
    "T98": {"intent": [*_CANCEL, "આવતીકાલની"]},
    "T99": {"intent": ["2951847306", "2951847314", *_CANCEL, "કુલ રિફંડ"]},
    "T100": {"intent": _SENIOR, "availability": ["હજી પણ 3A ની સીટો ઉપલબ્ધ"]},
}

_RISK = {
    "T76": "Both questions (status AND waitlist position); PNR digits identical.",
    "T77": "'હમણાં કેન્સલ કરશો નહીં' must stay an explicit prohibition.",
    "T78": "Two intents: cancel AND report the refund.",
    "T79": "'ઓછામાં ઓછા ₹7,400' (inclusive) is a CONDITION for cancelling; 'નહીંતર ... એમ જ રહેવા દો'.",
    "T80": "'ઓછામાં ઓછું ₹450' (inclusive) must stay a condition.",
    "T81": "Only a status question.",
    "T82": "A plain cancellation request.",
    "T83": "Cancel + refund.",
    "T84": "Fallback = the WAITLIST on the same train and class.",
    "T85": "'વેઇટિંગ લિસ્ટમાં મૂકશો નહીં' must keep its negative meaning.",
    "T86": "The waitlist is only a fallback if sleeper is sold out.",
    "T87": "'અત્યારે' (right now); two questions.",
    "T88": "'ગઈ રાત્રે' (last night) and the EXPECTED arrival at Ahmedabad.",
    "T89": "'આજે' (today); the second question is conditional.",
    "T90": "'બપોરે 2:05' (14:05), 'આજે'; a yes/no question, not a booking.",
    "T91": "Senior citizen concession, class 3A.",
    "T92": "ONE senior + ONE normal ticket; 'હમણાં કંઈ પણ બુક કરશો નહીં'.",
    "T93": "Student concession, class CC.",
    "T94": "Budget ₹1,100, STUDENT concession; yes/no.",
    "T95": "'એ જ મુસાફર ... એ જ ટ્રેનમાં' (same passenger, same train); class SL.",
    "T96": "Condition 'હજી પણ વેઇટિંગ લિસ્ટમાં હોય' before both actions.",
    "T97": "Both branches: waitlisted -> cancel, confirmed -> leave it.",
    "T98": "'આવતીકાલની' only; no PNR, nothing invented.",
    "T99": "Both PNRs and the TOTAL refund.",
    "T100": "Two questions: 3A availability AND the senior citizen fare.",
}
_NOTE = {
    "T77": "'મેં હજી નક્કી કર્યું નથી' is gender-neutral.",
    "T88": "Honorific plural 'મારાં મમ્મી ... કરી રહ્યાં છે'.",
    "T90": "'હું ... માં છું' avoids a gendered verb; 'પાછી જતી' agrees with ટ્રેન (feminine).",
    "T92": "'મારાં દાદી ... અને મારે ... લેવી છે' keeps the speaker gender-neutral.",
    "T93": "'કન્સેશન' is the loan word railway users say; 'રાહત' would also be understood.",
}
_KEEP = ("PNRs, passenger names, train ids, class codes and amounts use ASCII digits / Latin letters, separated from Gujarati suffixes "
         "by a space; station names use the frozen Gujarati aliases.")
FLAGS: dict[tuple[str, str], dict[str, dict]] = {
    (t, "gu"): dict(potential_ambiguity=F(True, _RISK[t]), unnatural_wording=F(True, _NOTE[t]) if t in _NOTE else OK,
                    constraint_risk=F(True, "Reviewer must confirm: " + _RISK[t]), notes=F(False, _KEEP))
    for t in IDS
}
