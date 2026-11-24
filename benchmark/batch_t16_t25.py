"""Batch T16-T25: the ONLY place where this batch's language-specific text lives (same layout as batch_t06_t15.py).

* EN_ITEMS  English source prompts (draft, not human-authored) + tags
* QUERIES   Hinglish / Hindi / Marathi DRAFT variants (Claude-generated, NOT human-reviewed)
* MARKERS   keyword/regex surface checks per task and language (consumed by language_checks.py)
* FLAGS     translation-risk flags for the batch audit file (consumed by build_language_audit.py)

All four variants of a task share ONE spec and ONE gold label. Station names use the frozen per-language aliases;
passenger names, train ids and class codes stay Latin. Hindi Howrah uses the decomposed nukta exactly as stations.json.
"""
from __future__ import annotations

from .batch_t06_t15 import F, OK, _m

BATCH_IDS = ["T16", "T17", "T18", "T19", "T20", "T21", "T22", "T23", "T24", "T25"]
EN_AUTHOR = "claude-session-4 (draft, not human-authored)"
_HWH_HI = "\u0939\u093e\u0935\u0921\u093c\u093e"  # हावड़ा (decomposed nukta, as in stations.json)

EN_ITEMS: dict[str, dict] = {
    "T16": {"category": "single_tool", "tags": ["single_tool", "resolve_station", "station_identity"],
            "query": "What is the station code for Howrah, and what is the station's full official name?"},
    "T17": {"category": "single_tool", "tags": ["single_tool", "train_details", "segment_distance"],
            "query": "On train BTB115, how many kilometres is it from Pune to Bengaluru?"},
    "T18": {"category": "invalid_input", "tags": ["invalid_input", "unknown_station", "explicit_date"],
            "query": "Show me the trains from Chennai to Bengaluru on 9 October 2026."},
    "T19": {"category": "clarification", "tags": ["clarification", "missing_passenger", "explicit_date"],
            "query": "Book a 3A ticket on train BTB116 from Bengaluru to Pune on 9 October 2026."},
    "T20": {"category": "recovery", "tags": ["recovery", "no_trains_on_route", "explicit_date"],
            "query": "Book a sleeper (SL) ticket from Lucknow to Pune on 9 October 2026 for Neha Shah."},
    "T21": {"category": "clarification", "tags": ["clarification", "contradictory_constraints", "explicit_date"],
            "query": "Book a sleeper (SL) ticket on train BTB107 from Ahmedabad to Jaipur on 9 October 2026 for Farhan Ali."},
    "T22": {"category": "booking", "tags": ["booking", "earliest_with_seats", "sold_out_skip", "state_changing", "explicit_date"],
            "query": "Book a 2A ticket from Ahmedabad to Mumbai on 9 October 2026 for Karan Malhotra, on the earliest-departing "
                     "train that still has 2A seats available."},
    "T23": {"category": "booking", "tags": ["booking", "round_trip", "state_changing", "explicit_date"],
            "query": "Book a sleeper (SL) round trip for Ishaan Desai: from Pune to Nagpur on 8 October 2026, and back from Nagpur "
                     "to Pune on 10 October 2026."},
    "T24": {"category": "constraint", "tags": ["constraint", "infeasible", "budget", "explicit_date"],
            "query": "I need a 2A ticket from Kolkata to Lucknow on 9 October 2026 that costs no more than ₹3,500. Which train can I take?"},
    "T25": {"category": "constraint", "tags": ["constraint", "cross_midnight_window", "explicit_date", "clock_time_12h"],
            "query": "Which trains leave Lucknow for Kolkata between 11 PM on 9 October 2026 and 5 AM on 10 October?"},
}

QUERIES: dict[str, dict[str, str]] = {
    "hinglish": {
        "T16": "Howrah ka station code kya hai, aur station ka poora official naam kya hai?",
        "T17": "Train BTB115 mein Pune se Bengaluru tak kitne kilometre ka safar hai?",
        "T18": "9 October 2026 ko Chennai se Bengaluru ki trains dikha do.",
        "T19": "9 October 2026 ko Bengaluru se Pune ke liye train BTB116 mein ek 3A ticket book kar do.",
        "T20": "9 October 2026 ko Lucknow se Pune ke liye Neha Shah ke naam par sleeper (SL) ticket book kar do.",
        "T21": "9 October 2026 ko Ahmedabad se Jaipur ke liye train BTB107 mein Farhan Ali ke naam par sleeper (SL) ticket book kar do.",
        "T22": "9 October 2026 ko Ahmedabad se Mumbai ke liye Karan Malhotra ke naam par 2A ticket book kar do, un trains mein se "
               "jinmein abhi bhi 2A seats available hain, sabse pehle nikalne wali train mein.",
        "T23": "Ishaan Desai ke liye sleeper (SL) mein aane-jaane ka ticket book kar do: 8 October 2026 ko Pune se Nagpur, aur "
               "10 October 2026 ko Nagpur se Pune wapas.",
        "T24": "Mujhe 9 October 2026 ko Kolkata se Lucknow ka 2A ticket chahiye jo ₹3,500 se zyada ka na ho. Kaun si train mil sakti hai?",
        "T25": "9 October 2026 ki raat 11 baje se 10 October ki subah 5 baje ke beech Lucknow se Kolkata ke liye kaun-kaun si trains nikalti hain?",
    },
    "hi": {
        "T16": f"{_HWH_HI} का स्टेशन कोड क्या है, और स्टेशन का पूरा आधिकारिक नाम क्या है?",
        "T17": "ट्रेन BTB115 में पुणे से बेंगलुरु तक कितने किलोमीटर का सफ़र है?",
        "T18": "9 अक्टूबर 2026 को चेन्नई से बेंगलुरु की ट्रेनें दिखाइए।",
        "T19": "9 अक्टूबर 2026 को बेंगलुरु से पुणे के लिए ट्रेन BTB116 में 3A का एक टिकट बुक कीजिए।",
        "T20": "9 अक्टूबर 2026 को लखनऊ से पुणे के लिए Neha Shah के नाम से स्लीपर (SL) टिकट बुक कीजिए।",
        "T21": "9 अक्टूबर 2026 को अहमदाबाद से जयपुर के लिए ट्रेन BTB107 में Farhan Ali के नाम से स्लीपर (SL) टिकट बुक कीजिए।",
        "T22": "9 अक्टूबर 2026 को अहमदाबाद से मुंबई के लिए Karan Malhotra के नाम से 2A का टिकट बुक कीजिए — उन ट्रेनों में से "
               "जिनमें अभी भी 2A की सीटें उपलब्ध हैं, सबसे पहले निकलने वाली ट्रेन में।",
        "T23": "Ishaan Desai के लिए स्लीपर (SL) में आने-जाने का टिकट बुक कीजिए: 8 अक्टूबर 2026 को पुणे से नागपुर, और "
               "10 अक्टूबर 2026 को नागपुर से पुणे वापसी।",
        "T24": "मुझे 9 अक्टूबर 2026 को कोलकाता से लखनऊ का 2A टिकट चाहिए, जिसका किराया ₹3,500 से ज़्यादा न हो। कौन-सी ट्रेन मिल सकती है?",
        "T25": "9 अक्टूबर 2026 की रात 11 बजे से 10 अक्टूबर की सुबह 5 बजे के बीच लखनऊ से कोलकाता के लिए कौन-कौन सी ट्रेनें निकलती हैं?",
    },
    "mr": {
        "T16": "हावडा स्टेशनचा कोड काय आहे आणि त्या स्टेशनचे पूर्ण अधिकृत नाव काय आहे?",
        "T17": "ट्रेन BTB115 च्या मार्गावर पुणे ते बेंगळुरू अंतर किती किलोमीटर आहे?",
        "T18": "9 ऑक्टोबर 2026 रोजी चेन्नईहून बेंगळुरूला जाणाऱ्या ट्रेन दाखवा.",
        "T19": "9 ऑक्टोबर 2026 रोजी बेंगळुरूहून पुण्याला जाण्यासाठी ट्रेन BTB116 मध्ये 3A चे एक तिकीट बुक करा.",
        "T20": "9 ऑक्टोबर 2026 रोजी लखनौहून पुण्याला जाण्यासाठी Neha Shah यांच्या नावाने स्लीपर (SL) तिकीट बुक करा.",
        "T21": "9 ऑक्टोबर 2026 रोजी अहमदाबादहून जयपूरला जाण्यासाठी ट्रेन BTB107 मध्ये Farhan Ali यांच्या नावाने स्लीपर (SL) तिकीट बुक करा.",
        "T22": "9 ऑक्टोबर 2026 रोजी अहमदाबादहून मुंबईला जाणाऱ्या आणि 2A सीट उपलब्ध असलेल्या ट्रेनपैकी सर्वात आधी सुटणाऱ्या ट्रेनमध्ये Karan Malhotra यांच्या नावाने 2A चे तिकीट बुक करा.",
        "T23": "Ishaan Desai यांच्यासाठी स्लीपर (SL) मध्ये जाण्या-येण्याची तिकिटे बुक करा: 8 ऑक्टोबर 2026 रोजी पुणे ते नागपूर आणि 10 ऑक्टोबर 2026 रोजी नागपूर ते पुणे परतीचा प्रवास.",
        "T24": "मला 9 ऑक्टोबर 2026 रोजी कोलकात्याहून लखनौला जाण्यासाठी 2A चे तिकीट हवे आहे, ज्याचे भाडे ₹3,500 पेक्षा जास्त नसावे. कोणती ट्रेन घेता येईल?",
        "T25": "9 ऑक्टोबर 2026 रोजी रात्री 11 वाजल्यापासून 10 ऑक्टोबर रोजी सकाळी 5 वाजेपर्यंत लखनौहून कोलकात्याला जाणाऱ्या कोणकोणत्या ट्रेन सुटतात?",
    },
}

_BOOKV = _m([r"^book\b"], [r"book kar do"], ["बुक कीजिए"], ["बुक करा"])
MARKERS: dict[str, dict] = {
    "T16": {"intent": _m([r"station code", r"full official name"], [r"station code", r"poora official naam"],
                         ["स्टेशन कोड", "पूरा आधिकारिक नाम"], ["कोड", "पूर्ण अधिकृत नाव"]), "booking": "ABSENT"},
    "T17": {"intent": _m([r"how many kilometres"], [r"kitne kilometre"], ["कितने किलोमीटर"], ["किती किलोमीटर"]), "booking": "ABSENT"},
    "T18": {"intent": _m([r"\bChennai\b", r"\btrains\b"], [r"\bChennai\b", r"trains dikha do"], ["चेन्नई", "ट्रेनें दिखाइए"], ["चेन्नई", "ट्रेन दाखवा"]),
            "booking": "ABSENT"},
    "T19": {"intent": _m([r"^book a 3A ticket"], [r"ek 3A ticket"], ["3A का एक टिकट"], ["3A चे एक तिकीट"]), "booking": _BOOKV},
    "T20": {"intent": _m([r"\bsleeper\b"], [r"\bsleeper\b"], ["स्लीपर"], ["स्लीपर"]), "booking": _BOOKV},
    "T21": {"intent": _m([r"\bsleeper\b"], [r"\bsleeper\b"], ["स्लीपर"], ["स्लीपर"]), "booking": _BOOKV},
    "T22": {"intent": _m([r"earliest-departing train"], [r"sabse pehle nikalne wali"], ["सबसे पहले निकलने वाली"], ["सर्वात आधी सुटणाऱ्या"]),
            "availability": _m([r"still has 2A seats available"], [r"abhi bhi 2A seats available"], ["अभी भी 2A की सीटें उपलब्ध"], ["2A सीट उपलब्ध"]),
            "time_constraint": _m([r"earliest-departing train that still has 2A seats"], [r"un trains mein se jinmein abhi bhi 2A seats"],
                                  ["उन ट्रेनों में से जिनमें अभी भी 2A की सीटें"], ["ट्रेनपैकी सर्वात आधी सुटणाऱ्या"]),
            "booking": _BOOKV},
    "T23": {"intent": _m([r"round trip", r"back from Nagpur to Pune"], [r"aane-jaane", r"Nagpur se Pune wapas"], ["आने-जाने", "नागपुर से पुणे वापसी"],
                         ["जाण्या-येण्याची तिकिटे", "नागपूर ते पुणे परतीचा"]), "booking": _BOOKV},
    "T24": {"intent": _m([r"which train"], [r"kaun si train"], ["कौन-सी ट्रेन"], ["कोणती ट्रेन"]),
            "fare": _m([r"no more than ₹3,500"], [r"₹3,500 se zyada ka na ho"], ["₹3,500 से ज़्यादा न हो"], ["₹3,500 पेक्षा जास्त नसावे"]),
            "booking": "ABSENT"},
    "T25": {"intent": _m([r"which trains"], [r"kaun-kaun si trains"], ["कौन-कौन सी ट्रेनें"], ["कोणकोणत्या ट्रेन"]),
            "time": _m([r"11 PM", r"5 AM"], [r"raat 11 baje", r"subah 5 baje"], ["रात 11 बजे", "सुबह 5 बजे"], ["रात्री 11", "सकाळी 5"]),
            "time_constraint": _m([r"between 11 PM on 9 October 2026 and 5 AM on 10 October"], [r"9 October 2026 ki raat 11 baje se 10 October ki subah 5 baje ke beech"],
                                  ["9 अक्टूबर 2026 की रात 11 बजे से 10 अक्टूबर की सुबह 5 बजे के बीच"], ["9 ऑक्टोबर 2026 रोजी रात्री 11 वाजल्यापासून", "10 ऑक्टोबर रोजी सकाळी 5 वाजेपर्यंत"]),
            "booking": "ABSENT"},
}

_NOTRANSL = "Clarification task: the variant must NOT add the missing information (a reviewer must not 'fix' the prompt)."
FLAGS: dict[tuple[str, str], dict[str, dict]] = {
    ("T16", "hinglish"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=OK, notes=F(False, "'official naam' kept as a loanword, common in Hinglish.")),
    ("T16", "hi"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'आधिकारिक नाम' is formal; 'पूरा नाम' alone is more colloquial but weaker than 'official'."), constraint_risk=OK,
                        notes=F(False, "Uses the decomposed-nukta alias exactly as in stations.json.")),
    ("T16", "mr"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'स्टेशनचा कोड' (loanword) vs 'स्थानकाचा संकेतांक' (formal); loanword chosen."), constraint_risk=OK, notes=OK),
    ("T17", "hinglish"): dict(potential_ambiguity=F(True, "'kitne kilometre ka safar' = segment distance Pune->Bengaluru, not the full train route."), unnatural_wording=OK, constraint_risk=OK, notes=OK),
    ("T17", "hi"): dict(potential_ambiguity=F(True, "'पुणे से बेंगलुरु तक' must bound the segment (intended)."), unnatural_wording=OK, constraint_risk=OK, notes=OK),
    ("T17", "mr"): dict(potential_ambiguity=F(True, "'पुणे ते बेंगळुरू हे अंतर' = the Pune-Bengaluru distance (intended)."), unnatural_wording=OK, constraint_risk=OK, notes=OK),
    ("T18", "hinglish"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=F(True, "Chennai must stay Chennai (not 'Madras' or a nearby station); both are absent from the network anyway."), notes=OK),
    ("T18", "hi"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=F(True, "'चेन्नई' must not be replaced by a station that exists."), notes=OK),
    ("T18", "mr"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'ट्रेन दाखवा' (singular form used for plural) is natural colloquially."), constraint_risk=OK, notes=OK),
    ("T19", "hinglish"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=F(True, _NOTRANSL + " No passenger name anywhere."), notes=F(False, "'ek' renders English 'a' (one ticket).")),
    ("T19", "hi"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=F(True, _NOTRANSL), notes=OK),
    ("T19", "mr"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=F(True, _NOTRANSL), notes=OK),
    ("T20", "hinglish"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=F(True, "Route must stay Lucknow -> Pune; a 'helpful' change of city would create a bookable task."), notes=OK),
    ("T20", "hi"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=F(True, "Route must stay लखनऊ -> पुणे."), notes=OK),
    ("T20", "mr"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=F(True, "Route must stay लखनौ -> पुणे."), notes=OK),
    ("T21", "hinglish"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=F(True, "Both the train id and the stated direction (Ahmedabad se Jaipur) must survive; the conflict is the task."), notes=OK),
    ("T21", "hi"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=F(True, "Direction 'अहमदाबाद से जयपुर' must be kept in this order."), notes=OK),
    ("T21", "mr"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=F(True, "Direction 'अहमदाबाद ते जयपूर' must be kept in this order."), notes=OK),
    ("T22", "hinglish"): dict(potential_ambiguity=F(True, "Restructured as 'among trains that still have 2A seats, the one that leaves first' to avoid the reading 'the first train overall, which must also have seats'."),
                              unnatural_wording=F(True, "Long trailing clause; a reviewer may prefer two sentences."), constraint_risk=F(True, "Earliest-with-seats is the scored reasoning; 'sabse pehle' alone would be wrong."), notes=OK),
    ("T22", "hi"): dict(potential_ambiguity=F(True, "'उन ट्रेनों में से जिनमें ... सबसे पहले निकलने वाली' scopes 'earliest' over trains with seats (intended)."),
                        unnatural_wording=F(True, "Dash + trailing clause is written register."), constraint_risk=F(True, "Same as Hinglish."), notes=OK),
    ("T22", "mr"): dict(potential_ambiguity=F(True, "'ज्या ट्रेनमध्ये ... त्यांपैकी सर्वात आधी सुटणाऱ्या' scopes 'earliest' over trains with seats (intended)."),
                        unnatural_wording=F(True, "Correlative 'ज्या ... त्यांपैकी' is natural but long."), constraint_risk=F(True, "Same as Hinglish."), notes=OK),
    ("T23", "hinglish"): dict(potential_ambiguity=F(True, "'aane-jaane ka ticket' = round trip; the two legs and dates are then spelled out, as in English."), unnatural_wording=OK, constraint_risk=OK, notes=OK),
    ("T23", "hi"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'आने-जाने का टिकट' (one noun) for two bookings; the legs are listed explicitly."), constraint_risk=OK, notes=OK),
    ("T23", "mr"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'जाण्या-येण्याचे तिकीट' + 'परतीचा प्रवास'; a reviewer may prefer 'परतीचे तिकीट'."), constraint_risk=OK, notes=OK),
    ("T24", "hinglish"): dict(potential_ambiguity=F(True, "'₹3,500 se zyada ka na ho' = fare <= 3500 (intended)."), unnatural_wording=OK,
                              constraint_risk=F(True, "English 'Which train can I take?' rendered impersonally ('mil sakti hai') for gender neutrality."), notes=OK),
    ("T24", "hi"): dict(potential_ambiguity=F(True, "'₹3,500 से ज़्यादा न हो' = fare <= 3500."), unnatural_wording=OK, constraint_risk=OK, notes=OK),
    ("T24", "mr"): dict(potential_ambiguity=F(True, "'₹3,500 पेक्षा जास्त नसावे' = fare <= 3500 (same wording as pilot T03)."), unnatural_wording=OK, constraint_risk=OK, notes=OK),
    ("T25", "hinglish"): dict(potential_ambiguity=F(True, "'9 ki raat 11 baje se 10 ki subah 5 baje ke beech' spans two dates (intended)."), unnatural_wording=OK,
                              constraint_risk=F(True, "Both dates must survive; dropping '10 October' would turn this into a same-date window."), notes=OK),
    ("T25", "hi"): dict(potential_ambiguity=F(True, "'की रात 11 बजे से ... की सुबह 5 बजे के बीच' spans two dates (intended)."), unnatural_wording=OK, constraint_risk=F(True, "Both dates must survive."), notes=OK),
    ("T25", "mr"): dict(potential_ambiguity=F(True, "Two-date window stated explicitly."), unnatural_wording=F(True, "'कोलकाता येथे जाण्यासाठी' chosen over the inflected 'कोलकात्याला' to keep the frozen alias form."),
                        constraint_risk=F(True, "Both dates must survive."), notes=OK),
}
