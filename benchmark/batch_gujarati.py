"""Gujarati (gu), the 5th language. The ONLY place where Gujarati benchmark text lives.

Coverage: all 75 tasks. T01-T50 are defined here; T51-T75 in benchmark/batch_gujarati_t51_t75.py and merged at the end of
this module. The English, Hinglish, Hindi and Marathi files are NOT touched: Gujarati has its own file, languages/gu.jsonl.

* GU_IDS    tasks that have a Gujarati variant
* QUERIES   Gujarati DRAFT queries (Claude-generated, NOT human-reviewed)
* MARKERS   Gujarati regexes for every surface-check marker the task already has in the other languages
            (merged into language_checks._M under the key "gu")
* FLAGS     translation-risk flags for languages/batch_gu_T01_T50_language_audit.json and batch_gu_T51_T75_language_audit.json

Conventions (same rules as Hindi/Marathi):
  * station names use the frozen Gujarati aliases in environment/data/stations.json; Gujarati attaches case endings
    (મુંબઈથી = from Mumbai, નાગપુરમાં = in Nagpur), like Marathi, so the base name must be recovered before resolve_station;
  * passenger names, train ids, class codes, amounts and booking ids stay Latin/ASCII digits (no Gujarati digits);
  * a space separates a Gujarati suffix from a Latin or digit token ('BTB103 માં', '3A ની', 'Vikram Singh માટે'),
    as is common in typed Gujarati, so ids and class codes stay intact; dates use '9 ઓક્ટોબર 2026ના રોજ';
  * the polite imperative 'બુક કરો' is the booking verb; 'બુક કરશો નહીં' is the prohibition;
  * the speaker stays gender-neutral (Gujarati first-person verbs are mostly ungendered: 'મારે ... જવું છે').
"""
from __future__ import annotations

from .batch_t06_t15 import F, OK

GU_IDS_T01_T50 = [f"T{i:02d}" for i in range(1, 51)]
GU_IDS = list(GU_IDS_T01_T50)  # extended with T51-T75 at the end of this module
AUTHOR = "Claude-generated draft"
MONTH_WORDS = ("ઓક્ટોબર", "ઑક્ટોબર")  # both spellings are in common use; the drafts use ઓક્ટોબર

QUERIES: dict[str, str] = {
    "T01": "ટ્રેન BTB103 માં 2A ક્લાસનું ભાડું કેટલું છે?",
    "T02": "7 ઓક્ટોબર 2026ના રોજ નાગપુરથી પુણે જતી એકમાત્ર ટ્રેનમાં 3A ની સીટ ઉપલબ્ધ છે કે નહીં? સાથે સાથે 3A નું ભાડું પણ જણાવો.",
    "T03": "મને 8 ઓક્ટોબર 2026ના રોજ જયપુરથી અમદાવાદ માટે 3A ની ટિકિટ જોઈએ છે. મારે સાંજે 6 વાગ્યે અથવા તે પછી નીકળવું છે, ભાડું ₹3,000 થી "
           "વધુ ન હોવું જોઈએ, અને સીટો ઉપલબ્ધ હોવી જોઈએ. કઈ ટ્રેન યોગ્ય રહેશે? કંઈ પણ બુક કરશો નહીં, ફક્ત ટ્રેન જણાવો.",
    "T04": "7 ઓક્ટોબર 2026ના રોજ મુંબઈથી પુણે માટે સૌથી સસ્તી સ્લીપર (SL) ટિકિટ Ananya Kulkarni ના નામે બુક કરો.",
    "T05": "ટ્રેન BTB103 માં Vikram Singh માટે 3A ની ટિકિટ બુક કરો, પણ ફક્ત ત્યારે જ જ્યારે સીટો ઉપલબ્ધ હોય. જો 3A સોલ્ડ આઉટ હોય, તો બીજા કોઈ "
           "ક્લાસ કે બીજી કોઈ ટ્રેનમાં બુક કરશો નહીં, ફક્ત મને જણાવો.",
    "T06": "ટ્રેન BTB111 અઠવાડિયાના કયા કયા દિવસે નવી દિલ્હીથી ઊપડે છે? શું સોમવારે નવી દિલ્હીથી આ ટ્રેન મળી શકે?",
    "T07": "8 ઓક્ટોબર 2026ના રોજ મારી હઝરત નિઝામુદ્દીનથી બેંગલુરુની ટ્રેન છે. ટ્રેન નાગપુરમાં ઊભી રહેશે ત્યારે મારો ભાઈ મને પ્લેટફોર્મ પર મળવા "
           "માગે છે. ટ્રેન નાગપુર કેટલા વાગ્યે પહોંચશે?",
    "T08": "મારે 8 ઓક્ટોબર 2026ના રોજ નવી દિલ્હીથી લખનઉ જવું છે, અને બપોરે 12 વાગ્યાથી સાંજે 5 વાગ્યા વચ્ચે નીકળવું છે. જો એ સમય દરમિયાન "
           "કોઈ ટ્રેન ન ઊપડતી હોય, તો તેના બદલે સાંજે 5 વાગ્યા પછી ઊપડતી પહેલી ટ્રેન જણાવો.",
    "T09": "7 ઓક્ટોબર 2026ના રોજ દિલ્હીથી જયપુરની ચેર કાર (CC) ટિકિટ Rohan Mehta ના નામે બુક કરો.",
    "T10": "10 ઓક્ટોબર 2026ના રોજ નવી દિલ્હીથી મુંબઈ માટે ટ્રેન BTB101 માં Sneha Patil ના નામે 2A ની ટિકિટ બુક કરો. જો 2A સોલ્ડ આઉટ હોય, "
           "તો તેના બદલે એ જ ટ્રેનમાં 3A બુક કરો.",
    "T11": "ટ્રેન BTB109 માં સ્લીપર (SL) નું ભાડું કેટલું છે? જો એ ટ્રેનમાં સ્લીપર ક્લાસ ન હોય, તો જણાવો કે તેમાં કયા કયા ક્લાસ છે.",
    "T12": "મારે 9 ઓક્ટોબર 2026ના રોજ જયપુરથી અમદાવાદ જવું છે. 10 ઓક્ટોબરે સવારે 9:30 વાગ્યા સુધીમાં અમદાવાદ પહોંચવું જરૂરી છે, અને "
           "જયપુરથી શક્ય તેટલું મોડું નીકળવું છે. મારે કઈ ટ્રેન લેવી જોઈએ?",
    "T13": "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી અમદાવાદ જતી સાંજે 5 વાગ્યાની ટ્રેનમાં 3A ની બે ટિકિટ બુક કરો, એક Priya Nair માટે અને એક Arjun Nair માટે.",
    "T14": "9 ઓક્ટોબર 2026ના રોજ મારી મુંબઈથી નાગપુરની ટ્રેન BTB119 છે. આ ટ્રેનમાં હજુ પણ સીટો ઉપલબ્ધ હોય એવો સૌથી સસ્તો ક્લાસ કયો છે, "
           "અને તેનું ભાડું કેટલું છે?",
    "T15": "10 ઓક્ટોબર 2026ના રોજ જયપુરથી હઝરત નિઝામુદ્દીન માટે ટ્રેન BTB130 માં Meera Joshi અને Sameer Joshi માટે ચેર કાર (CC) ની ટિકિટ "
           "બુક કરો. અમારે સાથે મુસાફરી કરવી છે, એટલે ફક્ત ત્યારે જ બુક કરો જ્યારે અમારા બંને માટે સીટો હોય; નહીંતર કંઈ પણ બુક કરશો નહીં, "
           "ફક્ત મને જણાવો.",
    "T16": "હાવડાનો સ્ટેશન કોડ શું છે, અને સ્ટેશનનું પૂરું સત્તાવાર નામ શું છે?",
    "T17": "ટ્રેન BTB115 માં પુણેથી બેંગલુરુ સુધી કેટલા કિલોમીટરની મુસાફરી છે?",
    "T18": "9 ઓક્ટોબર 2026ના રોજ ચેન્નઈથી બેંગલુરુની ટ્રેનો બતાવો.",
    "T19": "9 ઓક્ટોબર 2026ના રોજ બેંગલુરુથી પુણે માટે ટ્રેન BTB116 માં 3A ની એક ટિકિટ બુક કરો.",
    "T20": "9 ઓક્ટોબર 2026ના રોજ લખનઉથી પુણે માટે Neha Shah ના નામે સ્લીપર (SL) ટિકિટ બુક કરો.",
    "T21": "9 ઓક્ટોબર 2026ના રોજ અમદાવાદથી જયપુર માટે ટ્રેન BTB107 માં Farhan Ali ના નામે સ્લીપર (SL) ટિકિટ બુક કરો.",
    "T22": "9 ઓક્ટોબર 2026ના રોજ અમદાવાદથી મુંબઈ માટે Karan Malhotra ના નામે 2A ની ટિકિટ બુક કરો — જે ટ્રેનોમાં હજુ પણ 2A ની સીટો ઉપલબ્ધ "
           "છે તેમાંથી સૌથી પહેલાં ઊપડતી ટ્રેનમાં.",
    "T23": "Ishaan Desai માટે સ્લીપર (SL) માં જવા-આવવાની ટિકિટ બુક કરો: 8 ઓક્ટોબર 2026ના રોજ પુણેથી નાગપુર, અને 10 ઓક્ટોબર 2026ના રોજ "
           "નાગપુરથી પુણે પરત.",
    "T24": "મને 9 ઓક્ટોબર 2026ના રોજ કોલકાતાથી લખનઉની 2A ટિકિટ જોઈએ છે, જેનું ભાડું ₹3,500 થી વધુ ન હોય. કઈ ટ્રેન મળી શકે?",
    "T25": "9 ઓક્ટોબર 2026ની રાત્રે 11 વાગ્યાથી 10 ઓક્ટોબરની સવારે 5 વાગ્યા વચ્ચે લખનઉથી કોલકાતા જવા માટે કઈ કઈ ટ્રેનો ઊપડે છે?",
    "T26": "ટ્રેન BTB102 માં 3A ની કેટલી સીટો બાકી છે?",
    "T27": "9 ઓક્ટોબર 2026ના રોજ પુણેથી મુંબઈ માટે ટ્રેન BTB124 માં Aditi Rao ના નામે સ્લીપર (SL) ટિકિટ બુક કરો.",
    "T28": "ટ્રેન BTB150 કયા કયા સ્ટેશનો પર ઊભી રહે છે?",
    "T29": "9 ઓક્ટોબર 2026ના રોજ કોલકાતાથી નવી દિલ્હી માટે ટ્રેન BTB110 માં Suresh Menon ના નામે ફર્સ્ટ એસી (1A) ટિકિટ બુક કરો.",
    "T30": "2 ઓક્ટોબર 2026ના રોજ પુણેથી નાગપુર માટે Rohit Pawar ના નામે સ્લીપર (SL) ટિકિટ બુક કરો.",
    "T31": "9 ઓક્ટોબર 2026ના રોજ બૉમ્બે સેન્ટ્રલથી અમદાવાદની સૌથી પહેલી ટ્રેન કઈ છે?",
    "T32": "8 ઓક્ટોબર 2026ના રોજ નાગપુરથી પુણે માટે ટ્રેન BTB128 માં Kiran Rao ના નામે 2A ની ટિકિટ બુક કરો, જો 2A નું ભાડું ₹2,000 થી ઓછું "
           "હોય; નહીંતર એ જ ટ્રેનમાં 3A બુક કરો.",
    "T33": "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી પુણે માટે Anil Joshi, Sunita Joshi અને Rohan Joshi ની ટિકિટ બુક કરો. અમે ત્રણેય એક જ ટ્રેન અને "
           "એક જ ક્લાસમાં સાથે મુસાફરી કરીશું, એટલે કોઈ પણ ક્લાસમાં એવો સૌથી સસ્તો વિકલ્પ પસંદ કરો જેમાં અમારા ત્રણેય માટે સીટો હોય.",
    "T34": "10 ઓક્ટોબર 2026ના રોજ અમદાવાદથી મુંબઈ જતી જે ટ્રેનોનું 3A ભાડું ₹3,000 કે તેથી ઓછું છે, તેમાંથી કઈ ટ્રેનની મુસાફરી સૌથી ઓછા "
           "સમયની છે? શું તેમાં 3A ની સીટો ઉપલબ્ધ છે?",
    "T35": "આ શનિવારે નવી દિલ્હીથી લખનઉ માટે Deepak Yadav ના નામે સ્લીપર (SL) ટિકિટ બુક કરો.",
    "T36": "9 ઓક્ટોબર 2026ના રોજ કોલકાતાથી લખનઉ માટે ટ્રેન BTB112 માં Pooja Sen ના નામે એસી ટિકિટ બુક કરો.",
    "T37": "Rahul Verma, BTB110, 2A, કોલકાતાથી નવી દિલ્હી, 9 ઓક્ટોબર 2026.",
    "T38": "9 ઓક્ટોબર 2026ના રોજ અમદાવાદથી મુંબઈ માટે ટ્રેન BTB103 માં Nikhil Bose ના નામે 3A ની ટિકિટ બુક કરો. જો તે ભરાઈ ગઈ હોય, તો તેના "
           "બદલે એ જ દિવસે એ જ રૂટ પરની બીજી ટ્રેનોમાંથી સૌથી સસ્તી ટ્રેનમાં 3A બુક કરો.",
    "T39": "7 ઓક્ટોબર 2026ના રોજ નવી દિલ્હીથી લખનઉ માટે ટ્રેન BTB111 માં Meera Nair ના નામે 2A ની ટિકિટ બુક કરો, પણ ફક્ત ત્યારે જ જ્યારે "
           "એ દિવસે ટ્રેન ચાલતી હોય.",
    "T40": "લખનઉથી જયપુરની કોઈ સીધી ટ્રેન નથી, એટલે 9 ઓક્ટોબર 2026ના રોજ નવી દિલ્હીમાં ટ્રેન બદલવી પડશે. ટ્રેન બદલવા માટે ઓછામાં ઓછો 1 "
           "કલાક જોઈએ, અને જયપુર શક્ય તેટલું વહેલું પહોંચવું છે. કઈ બે ટ્રેનો લેવી જોઈએ?",
    "T41": "Sameer Khan માટે આ બે ભાગવાળી મુસાફરી બુક કરો: 9 ઓક્ટોબર 2026ના રોજ મુંબઈથી નાગપુર ટ્રેન BTB119 માં 3A, અને પછી 11 ઓક્ટોબર "
           "2026ના રોજ નાગપુરથી બેંગલુરુ ટ્રેન BTB121 માં 2A. મને બંને ભાગ જોઈએ છે, એટલે જો કોઈ પણ એક ભાગ બુક ન થઈ શકે, તો કંઈ પણ બુક "
           "કરશો નહીં.",
    "T42": "9 ઓક્ટોબર 2026ના રોજ બેંગલુરુથી નાગપુર માટે ટ્રેન BTB122 માં મારા પિતાજી Ramesh Gupta માટે 2A અને મારા (Ajay Gupta) માટે 3A બુક કરો.",
    "T43": "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી અમદાવાદ માટે Tanvi Shah ના નામે 3A ની ટિકિટ બુક કરો. ટ્રેન 10 ઓક્ટોબરે સવારે 7 વાગ્યા સુધીમાં "
           "અમદાવાદ પહોંચી જવી જોઈએ, અને 3A નું ભાડું ₹3,000 કે તેથી ઓછું હોવું જોઈએ.",
    "T44": "જો 9 ઓક્ટોબર 2026ના રોજ સાંજે 5:20 વાગ્યે નવી દિલ્હીથી ઊપડતી કોલકાતાની ટ્રેન લઈએ, તો કોલકાતા કઈ તારીખે અને કેટલા વાગ્યે પહોંચીશું?",
    "T45": "કૃપા કરીને બુકિંગ આઈડી BK0042 વાળી મારી ટિકિટ રદ કરો.",
    "T46": "9 ઓક્ટોબર 2026ના રોજ નાગપુરથી મુંબઈ માટે ટ્રેન BTB120 માં Asha Iyer અને Vikram Iyer માટે સ્લીપર (SL) ની ત્રણ ટિકિટ બુક કરો.",
    "T47": "9 ઓક્ટોબર 2026ના રોજ દિલ્હીથી જયપુર માટે ટ્રેન BTB129 માં Kavita Joshi ના નામે ચેર કાર (CC) ટિકિટ બુક કરો.",
    "T48": "9 ઓક્ટોબર 2026ના રોજ જયપુરથી નવી દિલ્હી માટે ટ્રેન BTB104 માં Leela Das, Arjun Das અને Maya Das માટે સ્લીપર (SL) ટિકિટ બુક કરો. "
           "જો બધા માટે સીટો ન હોય, તો મેં જે ક્રમમાં નામ લખ્યાં છે એ જ ક્રમમાં શક્ય હોય એટલી ટિકિટ બુક કરો.",
    "T49": "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી પુણે માટે Farah Khan ના નામે 3A ની ટિકિટ બુક કરો, એવી ટ્રેનમાં જે આગળ બેંગલુરુ સુધી જાય છે.",
    "T50": "9 ઓક્ટોબર 2026ના રોજ મુંબઈથી પુણે માટે ટ્રેન BTB117 માં Imran Sheikh ના નામે ચેર કાર (CC) ટિકિટ બુક કરો. તે પછી, જો CC ની કોઈ "
           "સીટ હજુ પણ બાકી હોય, તો Zoya Ali માટે પણ એક ટિકિટ બુક કરો. પછી જણાવો કે CC ની કેટલી સીટો બાકી છે.",
}

_BOOK = ["બુક કરો"]
# Gujarati regexes for the markers that already exist for each task (keys must match the other languages' keys exactly;
# "ABSENT" markers need nothing here: they are checked with the Gujarati booking-verb pattern in language_checks._BOOK).
MARKERS: dict[str, dict[str, list[str]]] = {
    "T01": {"intent": ["ભાડું", "કેટલું"]},
    "T02": {"intent": ["સીટ", "ભાડું", "એકમાત્ર ટ્રેન"], "availability": ["ઉપલબ્ધ"]},
    "T03": {"intent": ["કઈ ટ્રેન", "ટિકિટ"], "time": ["સાંજે 6 વાગ્યે"], "time_constraint": ["6 વાગ્યે અથવા તે પછી"],
            "fare": ["₹3,000 થી વધુ ન"], "availability": ["સીટો ઉપલબ્ધ હોવી જોઈએ"], "forbidden": ["કંઈ પણ બુક કરશો નહીં"]},
    "T04": {"intent": ["બુક કરો", "સ્લીપર"], "fare": ["સૌથી સસ્તી"], "booking": _BOOK},
    "T05": {"intent": ["3A ની ટિકિટ બુક કરો", "ફક્ત મને જણાવો"], "availability": ["ફક્ત ત્યારે જ જ્યારે સીટો ઉપલબ્ધ હોય"],
            "booking": ["બુક કરો", "ફક્ત ત્યારે જ"], "forbidden": ["બીજા કોઈ ક્લાસ કે બીજી કોઈ ટ્રેનમાં બુક કરશો નહીં"],
            "fallback": ["સોલ્ડ આઉટ", "બીજા કોઈ ક્લાસ"]},
    "T06": {"intent": ["કયા કયા દિવસે", "નવી દિલ્હી", "સોમવારે"]},
    "T07": {"intent": ["કેટલા વાગ્યે", "નાગપુર"]},
    "T08": {"intent": ["પહેલી ટ્રેન"], "time": ["બપોરે 12 વાગ્યા", "સાંજે 5 વાગ્યા"], "time_constraint": ["12 વાગ્યાથી સાંજે 5 વાગ્યા વચ્ચે", "5 વાગ્યા પછી"],
            "fallback": ["કોઈ ટ્રેન ન ઊપડતી", "તેના બદલે"]},
    "T09": {"intent": ["ચેર કાર"], "booking": _BOOK},
    "T10": {"intent": [r"(?<![0-9A-Za-z])3A(?![0-9A-Za-z])"], "availability": ["જો 2A સોલ્ડ આઉટ"], "booking": ["2A ની ટિકિટ બુક કરો", "3A બુક કરો"],
            "fallback": ["એ જ ટ્રેનમાં", "તેના બદલે"]},
    "T11": {"intent": ["ભાડું", "કયા કયા ક્લાસ"], "fallback": ["જો એ ટ્રેનમાં સ્લીપર ક્લાસ ન હોય"]},
    "T12": {"intent": ["કઈ ટ્રેન"], "time": ["સવારે 9:30 વાગ્યા", "10 ઓક્ટોબરે"], "time_constraint": ["9:30 વાગ્યા સુધીમાં", "શક્ય તેટલું મોડું"]},
    "T13": {"intent": ["3A ની બે ટિકિટ", "એક Priya"], "time": ["સાંજે 5 વાગ્યાની ટ્રેન"], "booking": _BOOK},
    "T14": {"intent": ["સૌથી સસ્તો ક્લાસ", "ભાડું"], "fare": ["સૌથી સસ્તો"], "availability": ["હજુ પણ સીટો ઉપલબ્ધ"]},
    "T15": {"intent": ["સાથે મુસાફરી", "ફક્ત મને જણાવો"], "availability": ["ફક્ત ત્યારે જ બુક કરો જ્યારે અમારા બંને માટે સીટો હોય"],
            "booking": ["બુક કરો", "ફક્ત ત્યારે જ"], "forbidden": ["કંઈ પણ બુક કરશો નહીં"], "fallback": ["નહીંતર"]},
    "T16": {"intent": ["સ્ટેશન કોડ", "પૂરું સત્તાવાર નામ"]},
    "T17": {"intent": ["કેટલા કિલોમીટર"]},
    "T18": {"intent": ["ચેન્નઈ", "ટ્રેનો બતાવો"]},
    "T19": {"intent": ["3A ની એક ટિકિટ"], "booking": _BOOK},
    "T20": {"intent": ["સ્લીપર"], "booking": _BOOK},
    "T21": {"intent": ["સ્લીપર"], "booking": _BOOK},
    "T22": {"intent": ["સૌથી પહેલાં ઊપડતી"], "availability": ["હજુ પણ 2A ની સીટો ઉપલબ્ધ"], "time_constraint": ["જે ટ્રેનોમાં હજુ પણ 2A ની સીટો"],
            "booking": _BOOK},
    "T23": {"intent": ["જવા-આવવાની", "નાગપુરથી પુણે પરત"], "booking": _BOOK},
    "T24": {"intent": ["કઈ ટ્રેન"], "fare": ["₹3,500 થી વધુ ન હોય"]},
    "T25": {"intent": ["કઈ કઈ ટ્રેનો"], "time": ["રાત્રે 11 વાગ્યા", "સવારે 5 વાગ્યા"],
            "time_constraint": ["9 ઓક્ટોબર 2026ની રાત્રે 11 વાગ્યાથી 10 ઓક્ટોબરની સવારે 5 વાગ્યા વચ્ચે"]},
    "T26": {"intent": ["કેટલી સીટો બાકી"]},
    "T27": {"intent": ["સ્લીપર"], "booking": _BOOK},
    "T28": {"intent": ["કયા કયા સ્ટેશનો", "ઊભી રહે"]},
    "T29": {"intent": [r"ફર્સ્ટ એસી \(1A\)"], "booking": _BOOK},
    "T30": {"intent": ["સ્લીપર"], "booking": _BOOK},
    "T31": {"intent": ["બૉમ્બે સેન્ટ્રલ", "સૌથી પહેલી ટ્રેન"]},
    "T32": {"fare": ["જો 2A નું ભાડું ₹2,000 થી ઓછું"], "fallback": ["નહીંતર એ જ ટ્રેનમાં 3A"], "booking": _BOOK},
    "T33": {"fare": ["સૌથી સસ્તો વિકલ્પ"], "availability": ["અમારા ત્રણેય માટે સીટો"], "intent": ["એક જ ટ્રેન અને એક જ ક્લાસ"], "booking": _BOOK},
    "T34": {"intent": ["સૌથી ઓછા સમય"], "fare": ["₹3,000 કે તેથી ઓછું"], "availability": ["3A ની સીટો ઉપલબ્ધ"]},
    "T35": {"intent": ["આ શનિવારે"], "booking": _BOOK},
    "T36": {"intent": ["એસી ટિકિટ"], "booking": _BOOK},
    "T37": {"intent": [r"^Rahul Verma, BTB110, 2A"]},
    "T38": {"availability": ["જો તે ભરાઈ ગઈ"], "fallback": ["એ જ દિવસે એ જ રૂટ પરની બીજી ટ્રેનોમાંથી સૌથી સસ્તી"], "booking": _BOOK},
    "T39": {"forbidden": ["ફક્ત ત્યારે જ જ્યારે એ દિવસે ટ્રેન ચાલતી હોય"], "booking": _BOOK},
    "T40": {"time_constraint": ["ઓછામાં ઓછો 1 કલાક"], "intent": ["શક્ય તેટલું વહેલું", "બે ટ્રેનો"]},
    "T41": {"forbidden": ["જો કોઈ પણ એક ભાગ બુક ન થઈ શકે, તો કંઈ પણ બુક કરશો નહીં"], "intent": ["BTB119 માં 3A", "BTB121 માં 2A"], "booking": _BOOK},
    "T42": {"intent": ["Ramesh Gupta માટે 2A", r"Ajay Gupta\) માટે 3A"], "booking": _BOOK},
    "T43": {"time_constraint": ["10 ઓક્ટોબરે સવારે 7 વાગ્યા સુધીમાં"], "fare": ["₹3,000 કે તેથી ઓછું"], "booking": _BOOK},
    "T44": {"time": ["સાંજે 5:20 વાગ્યે"], "intent": ["કઈ તારીખે", "કેટલા વાગ્યે"]},
    "T45": {"intent": ["રદ", "BK0042"]},
    "T46": {"intent": ["ત્રણ ટિકિટ"], "booking": _BOOK},
    "T47": {"intent": ["ચેર કાર"], "booking": _BOOK},
    "T48": {"fallback": ["એ જ ક્રમમાં", "શક્ય હોય એટલી ટિકિટ બુક કરો"], "availability": ["બધા માટે સીટો ન હોય"], "booking": _BOOK},
    "T49": {"intent": ["આગળ બેંગલુરુ સુધી જાય"], "booking": _BOOK},
    "T50": {"availability": ["જો CC ની કોઈ સીટ હજુ પણ બાકી હોય"], "intent": ["CC ની કેટલી સીટો બાકી"], "booking": _BOOK},
}

# ------------------------------------------------------------------ translation-risk flags (draft author's notes, NOT human judgement)
_RISK = {  # Gujarati-specific constraint the reviewer must check
    "T02": "'એકમાત્ર ટ્રેન' = 'the only train' (gold relies on exactly one Nagpur->Pune train).",
    "T03": "Inclusive 'સાંજે 6 વાગ્યે અથવા તે પછી' (at or after 6 PM), '₹3,000 થી વધુ ન' (<= 3000), seats required, and no booking: four coupled constraints.",
    "T05": "Only-if ('ફક્ત ત્યારે જ જ્યારે') + no other class OR train ('બીજા કોઈ ક્લાસ કે બીજી કોઈ ટ્રેનમાં' must read as neither).",
    "T08": "Window 12 noon-5 PM and the fallback 'first train after 5 PM' (strictly after).",
    "T09": "'દિલ્હી' must stay generic (New Delhi vs Hazrat Nizamuddin); 'નવી દિલ્હી' must not be used.",
    "T10": "Fallback is 3A on the SAME train ('એ જ ટ્રેનમાં').",
    "T12": "Arrival deadline 'by 9:30 AM on 10 October' (inclusive) + 'leave as late as possible'.",
    "T15": "All-or-nothing for both passengers; 'નહીંતર કંઈ પણ બુક કરશો નહીં'.",
    "T18": "'ચેન્નઈ' must stay (it is intentionally not in the environment).",
    "T19": "No passenger name may be added (the missing name is the task).",
    "T22": "'સૌથી પહેલાં ઊપડતી' = earliest-DEPARTING among trains that still have 2A seats.",
    "T23": "Both dates and the return direction must survive.",
    "T25": "Window crosses midnight (11 PM on 9 Oct to 5 AM on 10 Oct).",
    "T28": "Train id BTB150 must stay unchanged (intentionally invalid).",
    "T29": "'ફર્સ્ટ એસી (1A)' must not become an existing class.",
    "T30": "The past date (2 October) must be kept.",
    "T31": "'બૉમ્બે સેન્ટ્રલ' must stay as the user's (unresolvable) name; 'મુંબઈ સેન્ટ્રલ' would remove the recovery step.",
    "T32": "Strict '₹2,000 થી ઓછું' (under) and the else-branch ('નહીંતર એ જ ટ્રેનમાં 3A').",
    "T33": "Three passengers, same train AND class, cheapest option in ANY class with seats for all three.",
    "T34": "Fare ceiling '₹3,000 કે તેથી ઓછું' (inclusive) + shortest journey + seat question.",
    "T35": "'આ શનિવારે' must stay relative (no date added); 'આવતા શનિવારે' could mean the 17th.",
    "T36": "'એસી' must stay unspecific (not 3A/2A).",
    "T37": "No verb may be added; the intent ambiguity is the task.",
    "T38": "Cheapest OTHER train, same route, same day, same class. Wording avoids 'બીજી સૌથી સસ્તી' (= second-cheapest).",
    "T39": "'ફક્ત ત્યારે જ જ્યારે એ દિવસે ટ્રેન ચાલતી હોય' is the binding condition.",
    "T40": "At least 1 hour to change (inclusive), earliest arrival, change at New Delhi; no booking verb.",
    "T41": "All-or-nothing over both legs.",
    "T42": "Class-to-passenger binding (father 2A, speaker 3A) must not be swapped.",
    "T43": "Arrival 'by 7 AM on 10 October' (inclusive) and fare at most ₹3,000.",
    "T44": "Departure 5:20 PM on 9 October; the question asks for the arrival DATE and time.",
    "T45": "Cancellation must stay a cancellation; BK0042 unchanged.",
    "T46": "'ત્રણ ટિકિટ' vs two names: the count must not be corrected.",
    "T47": "'દિલ્હી' must stay generic (the train id resolves it).",
    "T48": "Partial booking allowed, in the listed order.",
    "T49": "'આગળ બેંગલુરુ સુધી જાય' = the train continues beyond Pune to Bengaluru.",
    "T50": "Order (Imran, then conditionally Zoya) and the final 'seats left' question.",
}
_NOTE = {  # (task) -> specific wording note
    "T01": "'ક્લાસનું ભાડું' (loanword 'ક્લાસ'); 'શ્રેણી' would be formal.",
    "T02": "'સાથે સાથે ... પણ' = 'and also' (plain 'સાથે' alone read as clipped).",
    "T05": "'સોલ્ડ આઉટ' loanword kept, as in Hindi; 'ભરાઈ ગઈ' is the native alternative.",
    "T06": "'ઊપડે છે' = departs (origin weekdays), not 'passes through'.",
    "T07": "'ઊભી રહેશે' = will stop (halt).",
    "T12": "'10 ઓક્ટોબરે' without year, mirroring English.",
    "T16": "'હાવડાનો' attaches the genitive to the station name.",
    "T17": "'પુણેથી બેંગલુરુ સુધી' = from Pune to Bengaluru (segment).",
    "T23": "'જવા-આવવાની ટિકિટ' = round-trip ticket (the usual order); 'પરત' = return.",
    "T31": "Spelt 'બૉમ્બે' with the open-o sign, as commonly written.",
    "T35": "'આ શનિવારે' = this Saturday.",
    "T38": "'બીજી ટ્રેનોમાંથી સૌથી સસ્તી' = cheapest among the other trains.",
    "T42": "'મારા (Ajay Gupta) માટે' keeps the name next to 'for me'.",
    "T44": "'લઈએ ... પહોંચીશું' (we) keeps the speaker gender-neutral.",
    "T45": "'કૃપા કરીને' = please; 'રદ કરો' = cancel.",
    "T48": "'મેં જે ક્રમમાં નામ લખ્યાં છે એ જ ક્રમમાં' = in exactly the order I wrote the names.",
}
_KEEP = ("Passenger names, train ids, class codes, amounts and dates use Latin letters / ASCII digits, separated from Gujarati "
         "suffixes by a space (e.g. 'BTB103 માં'); station names use the frozen Gujarati aliases.")
FLAGS: dict[tuple[str, str], dict[str, dict]] = {
    (t, "gu"): dict(potential_ambiguity=F(True, _RISK[t]) if t in _RISK else OK,
                    unnatural_wording=F(True, _NOTE[t]) if t in _NOTE else OK,
                    constraint_risk=F(True, "Reviewer must confirm: " + _RISK[t]) if t in _RISK else OK,
                    notes=F(False, _KEEP))
    for t in GU_IDS_T01_T50
}

# ------------------------------------------------------------------ T51-T75 (benchmark/batch_gujarati_t51_t75.py)
from . import batch_gujarati_t51_t75 as _t51  # noqa: E402

GU_IDS_T51_T75 = list(_t51.IDS)
GU_IDS += GU_IDS_T51_T75
QUERIES.update(_t51.QUERIES)
MARKERS.update(_t51.MARKERS)
FLAGS.update(_t51.FLAGS)

# ------------------------------------------------------------------ T76-T100, benchmark 3.0 (benchmark/batch_gujarati_t76_t100.py)
from . import batch_gujarati_t76_t100 as _t76  # noqa: E402

GU_IDS_T76_T100 = list(_t76.IDS)
GU_IDS += GU_IDS_T76_T100
QUERIES.update(_t76.QUERIES)
MARKERS.update(_t76.MARKERS)
FLAGS.update(_t76.FLAGS)

# ------------------------------------------------------------------ T101-T200, 20-tool stage (benchmark/batch_gujarati_t101_t200.py)
from . import batch_gujarati_t101_t200 as _t101  # noqa: E402

GU_IDS_T101_T200 = list(_t101.IDS)
GU_IDS += GU_IDS_T101_T200
QUERIES.update(_t101.QUERIES)
MARKERS.update(_t101.MARKERS)
FLAGS.update(_t101.FLAGS)
