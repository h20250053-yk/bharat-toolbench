"""Batch T06-T15: the ONLY place where the batch's language-specific text lives.

* EN_ITEMS        English source prompts (draft, not human-authored) + tags
* QUERIES         Hinglish / Hindi / Marathi DRAFT variants (Claude-generated, NOT human-reviewed)
* MARKERS         keyword/regex surface checks per task and language (consumed by language_checks.py)
* FLAGS           translation-risk flags for the batch audit file (consumed by build_language_audit.py)

All four variants of a task share ONE semantic spec and ONE gold label (benchmark/semantic_tasks.json,
benchmark/gold_labels.json). Only the surface language differs. Nothing here is human-verified:
every item stays review_status="draft", reviewer=None. Station names use the frozen per-language aliases in
environment/data/stations.json; passenger names, train ids and class codes stay Latin in every language.
Hindi Nizamuddin uses the decomposed nukta (U+091C U+093C) exactly as in stations.json.
"""
from __future__ import annotations

BATCH_IDS = ["T06", "T07", "T08", "T09", "T10", "T11", "T12", "T13", "T14", "T15"]
EN_AUTHOR = "claude-session-3 (draft, not human-authored)"
_NZM_HI = "\u0939\u091c\u093c\u0930\u0924 \u0928\u093f\u091c\u093c\u093e\u092e\u0941\u0926\u094d\u0926\u0940\u0928"  # हज़रत निज़ामुद्दीन

# ------------------------------------------------------------------ English source (category, query, tags)
EN_ITEMS: dict[str, dict] = {
    "T06": {"category": "single_tool", "tags": ["single_tool", "train_details", "operating_days"],
            "query": "On which days of the week does train BTB111 leave New Delhi? Can I catch it from New Delhi on a Monday?"},
    "T07": {"category": "sequential", "tags": ["sequential", "intermediate_stop", "explicit_date", "after_midnight"],
            "query": "I'm taking the train from Hazrat Nizamuddin to Bengaluru on 8 October 2026. My brother wants to meet me on the "
                     "platform when it stops at Nagpur. At what time does the train arrive at Nagpur?"},
    "T08": {"category": "recovery", "tags": ["recovery", "empty_window", "fallback_allowed", "explicit_date", "clock_time_12h"],
            "query": "I want to travel from New Delhi to Lucknow on 8 October 2026, leaving between 12 noon and 5 PM. If no train "
                     "leaves in that time, tell me the first train that leaves after 5 PM instead."},
    "T09": {"category": "clarification", "tags": ["clarification", "ambiguous_station", "explicit_date"],
            "query": "Book a chair car (CC) ticket from Delhi to Jaipur on 7 October 2026 for Rohan Mehta."},
    "T10": {"category": "recovery", "tags": ["recovery", "sold_out", "fallback_allowed", "state_changing", "explicit_date"],
            "query": "Book a 2A ticket on train BTB101 from New Delhi to Mumbai on 10 October 2026 for Sneha Patil. If 2A is sold "
                     "out, book 3A on the same train instead."},
    "T11": {"category": "invalid_input", "tags": ["invalid_input", "class_not_offered"],
            "query": "What is the sleeper (SL) fare on train BTB109? If that train has no sleeper class, tell me which classes it "
                     "does have."},
    "T12": {"category": "constraint", "tags": ["constraint", "arrival_deadline", "overnight", "explicit_date", "clock_time_12h"],
            "query": "I'm travelling from Jaipur to Ahmedabad and will leave on 9 October 2026. I must reach Ahmedabad by 9:30 AM "
                     "on 10 October, and I want to leave Jaipur as late as possible. Which train should I take?"},
    "T13": {"category": "booking", "tags": ["booking", "multi_passenger", "state_changing", "explicit_date", "clock_time_12h"],
            "query": "Book two 3A tickets from Mumbai to Ahmedabad on 9 October 2026 on the train that leaves at 5 PM, one for "
                     "Priya Nair and one for Arjun Nair."},
    "T14": {"category": "sequential", "tags": ["sequential", "class_comparison", "availability", "explicit_date"],
            "query": "I'm travelling on train BTB119 from Mumbai to Nagpur on 9 October 2026. Which is the cheapest class on that "
                     "train that still has seats available, and what is its fare?"},
    "T15": {"category": "constraint", "tags": ["constraint", "multi_passenger", "all_or_nothing", "no_fallback", "explicit_date"],
            "query": "Book chair car (CC) tickets on train BTB130 from Jaipur to Hazrat Nizamuddin on 10 October 2026 for Meera "
                     "Joshi and Sameer Joshi. We must travel together, so book only if there are seats for both of us; otherwise "
                     "don't book anything and just tell me."},
}

# ------------------------------------------------------------------ non-English DRAFTS
QUERIES: dict[str, dict[str, str]] = {
    "hinglish": {
        "T06": "Train BTB111 hafte ke kaun-kaun se din New Delhi se chalti hai? Kya Monday ko New Delhi se yeh train mil sakti hai?",
        "T07": "8 October 2026 ko meri Hazrat Nizamuddin se Bengaluru ki train hai. Jab train Nagpur mein rukegi, tab mera bhai "
               "mujhse platform par milna chahta hai. Train Nagpur kitne baje pahunchegi?",
        "T08": "Mujhe 8 October 2026 ko New Delhi se Lucknow jaana hai, aur dopahar 12 baje se shaam 5 baje ke beech nikalna hai. "
               "Agar us beech koi train nahi nikalti, to uski jagah shaam 5 baje ke baad nikalne wali pehli train bata do.",
        "T09": "7 October 2026 ko Delhi se Jaipur ka chair car (CC) ticket Rohan Mehta ke naam par book kar do.",
        "T10": "10 October 2026 ko New Delhi se Mumbai ke liye train BTB101 mein Sneha Patil ke naam par 2A ticket book kar do. "
               "Agar 2A sold out ho, to uski jagah usi train mein 3A book kar dena.",
        "T11": "Train BTB109 mein sleeper (SL) ka fare kitna hai? Agar us train mein sleeper class nahi hai, to bata do ki usmein "
               "kaun-kaun si classes hain.",
        "T12": "Mujhe 9 October 2026 ko Jaipur se Ahmedabad jaana hai. 10 October ko subah 9:30 baje tak Ahmedabad pahunchna "
               "zaroori hai, aur Jaipur se jitna ho sake utni der se nikalna hai. Mujhe kaun si train leni chahiye?",
        "T13": "9 October 2026 ko Mumbai se Ahmedabad jaane wali shaam 5 baje ki train mein do 3A tickets book kar do, ek Priya "
               "Nair ke liye aur ek Arjun Nair ke liye.",
        "T14": "9 October 2026 ko meri Mumbai se Nagpur ki train BTB119 hai. Is train mein sabse sasti class kaun si hai jismein "
               "abhi bhi seats available hain, aur uska fare kitna hai?",
        "T15": "10 October 2026 ko Jaipur se Hazrat Nizamuddin ke liye train BTB130 mein Meera Joshi aur Sameer Joshi ke liye "
               "chair car (CC) tickets book karo. Humein saath mein travel karna hai, isliye sirf tab book karna jab hum dono ke "
               "liye seats hon; warna kuch bhi book mat karna, bas mujhe bata dena.",
    },
    "hi": {
        "T06": "ट्रेन BTB111 सप्ताह के किन-किन दिनों में नई दिल्ली से चलती है? क्या सोमवार को नई दिल्ली से यह ट्रेन मिल सकती है?",
        "T07": f"8 अक्टूबर 2026 को मेरी {_NZM_HI} से बेंगलुरु की ट्रेन है। जब ट्रेन नागपुर में रुकेगी, तब मेरा भाई मुझसे "
               "प्लेटफ़ॉर्म पर मिलना चाहता है। ट्रेन नागपुर कितने बजे पहुँचेगी?",
        "T08": "मुझे 8 अक्टूबर 2026 को नई दिल्ली से लखनऊ जाना है, और दोपहर 12 बजे से शाम 5 बजे के बीच निकलना है। अगर उस समय "
               "के बीच कोई ट्रेन नहीं निकलती, तो उसकी जगह शाम 5 बजे के बाद निकलने वाली पहली ट्रेन बता दीजिए।",
        "T09": "7 अक्टूबर 2026 को दिल्ली से जयपुर का चेयर कार (CC) टिकट Rohan Mehta के नाम से बुक कीजिए।",
        "T10": "10 अक्टूबर 2026 को नई दिल्ली से मुंबई के लिए ट्रेन BTB101 में Sneha Patil के नाम से 2A का टिकट बुक कीजिए। "
               "अगर 2A सोल्ड आउट हो, तो उसकी जगह उसी ट्रेन में 3A बुक कीजिए।",
        "T11": "ट्रेन BTB109 में स्लीपर (SL) का किराया कितना है? अगर उस ट्रेन में स्लीपर क्लास नहीं है, तो बताइए कि उसमें "
               "कौन-कौन सी क्लास हैं।",
        "T12": "मुझे 9 अक्टूबर 2026 को जयपुर से अहमदाबाद जाना है। 10 अक्टूबर को सुबह 9:30 बजे तक अहमदाबाद पहुँचना ज़रूरी है, "
               "और मुझे जयपुर से जितना हो सके उतनी देर से निकलना है। मुझे कौन-सी ट्रेन लेनी चाहिए?",
        "T13": "9 अक्टूबर 2026 को मुंबई से अहमदाबाद जाने वाली शाम 5 बजे की ट्रेन में 3A के दो टिकट बुक कीजिए, एक Priya Nair "
               "के लिए और एक Arjun Nair के लिए।",
        "T14": "9 अक्टूबर 2026 को मेरी मुंबई से नागपुर की ट्रेन BTB119 है। इस ट्रेन में वह सबसे सस्ती क्लास कौन-सी है जिसमें "
               "अभी भी सीटें उपलब्ध हैं, और उसका किराया कितना है?",
        "T15": f"10 अक्टूबर 2026 को जयपुर से {_NZM_HI} के लिए ट्रेन BTB130 में Meera Joshi और Sameer Joshi के लिए चेयर कार "
               "(CC) के टिकट बुक कीजिए। हमें साथ में यात्रा करनी है, इसलिए केवल तभी बुक कीजिए जब हम दोनों के लिए सीटें हों; "
               "वरना कुछ भी बुक मत कीजिए, बस मुझे बता दीजिए।",
    },
    "mr": {
        "T06": "ट्रेन BTB111 आठवड्यातील कोणकोणत्या दिवशी नवी दिल्लीहून सुटते? सोमवारी नवी दिल्लीहून ही ट्रेन पकडता येईल का?",
        "T07": "8 ऑक्टोबर 2026 रोजी मी हजरत निजामुद्दीनहून बेंगळुरूला ट्रेनने जाणार आहे. ट्रेन नागपूरला थांबेल तेव्हा माझ्या भावाला मला प्लॅटफॉर्मवर भेटायचे आहे. ट्रेन नागपूरला किती वाजता पोहोचेल?",
        "T08": "मला 8 ऑक्टोबर 2026 रोजी नवी दिल्लीहून लखनौला जायचे आहे आणि दुपारी 12 ते संध्याकाळी 5 या वेळेत निघायचे आहे. त्या वेळेत कोणतीही ट्रेन सुटत नसेल, तर संध्याकाळी 5 नंतर सुटणारी पहिली ट्रेन सांगा.",
        "T09": "7 ऑक्टोबर 2026 रोजी दिल्लीहून जयपूरला जाण्यासाठी Rohan Mehta यांच्या नावाने चेअर कार (CC) चे तिकीट बुक करा.",
        "T10": "10 ऑक्टोबर 2026 रोजी नवी दिल्लीहून मुंबईला जाण्यासाठी ट्रेन BTB101 मध्ये Sneha Patil यांच्या नावाने 2A चे तिकीट बुक करा. 2A सोल्ड आउट असेल, तर त्याच ट्रेनमध्ये 3A बुक करा.",
        "T11": "ट्रेन BTB109 मध्ये स्लीपर (SL) चे भाडे किती आहे? त्या ट्रेनमध्ये स्लीपर क्लास नसेल, तर कोणकोणते क्लास उपलब्ध आहेत ते सांगा.",
        "T12": "मला 9 ऑक्टोबर 2026 रोजी जयपूरहून अहमदाबादला जायचे आहे. 10 ऑक्टोबर रोजी सकाळी 9:30 पर्यंत अहमदाबादला पोहोचणे आवश्यक आहे आणि मला जयपूरहून शक्य तितक्या उशिरा निघायचे आहे. मी कोणती ट्रेन घ्यावी?",
        "T13": "9 ऑक्टोबर 2026 रोजी मुंबईहून अहमदाबादला जाणाऱ्या संध्याकाळी 5 वाजताच्या ट्रेनमध्ये 3A ची दोन तिकिटे बुक करा - एक Priya Nair यांच्यासाठी आणि एक Arjun Nair यांच्यासाठी.",
        "T14": "9 ऑक्टोबर 2026 रोजी मी मुंबईहून नागपूरला ट्रेन BTB119 ने प्रवास करणार आहे. या ट्रेनमध्ये सीट उपलब्ध असलेला सर्वात स्वस्त क्लास कोणता आहे आणि त्याचे भाडे किती आहे?",
        "T15": "10 ऑक्टोबर 2026 रोजी जयपूरहून हजरत निजामुद्दीनला जाण्यासाठी ट्रेन BTB130 मध्ये Meera Joshi आणि Sameer Joshi यांच्यासाठी चेअर कार (CC) ची तिकिटे बुक करा. आम्हाला एकत्र प्रवास करायचा आहे, त्यामुळे आम्हा दोघांसाठी सीट उपलब्ध असतील तरच बुक करा; अन्यथा काहीही बुक करू नका आणि फक्त मला सांगा.",
    },
}

# ------------------------------------------------------------------ surface-check markers (every regex must match)
# Keys follow language_checks._M: intent / time / time_constraint / fare / availability / booking / forbidden / fallback.
# "ABSENT" for booking = no booking verb may appear (read-only tasks).
def _m(en, hinglish, hi, mr):
    return {"en": en, "hinglish": hinglish, "hi": hi, "mr": mr}


MARKERS: dict[str, dict] = {
    "T06": {"intent": _m([r"which days of the week", r"\bNew Delhi\b", r"\bMonday\b"], [r"kaun-kaun se din", r"New Delhi", r"\bMonday\b"],
                         ["किन-किन दिनों", "नई दिल्ली", "सोमवार"], ["कोणकोणत्या दिवशी", "नवी दिल्ली", "सोमवारी"]),
            "booking": "ABSENT"},
    "T07": {"intent": _m([r"what time", r"arrive at Nagpur"], [r"kitne baje", r"Nagpur"], ["कितने बजे", "नागपुर"], ["किती वाजता", "नागपूर"]),
            "booking": "ABSENT"},
    "T08": {"intent": _m([r"first train"], [r"pehli train"], ["पहली ट्रेन"], ["पहिली ट्रेन"]),
            "time": _m([r"12 noon", r"5 PM"], [r"dopahar 12 baje", r"shaam 5 baje"], ["दोपहर 12 बजे", "शाम 5 बजे"], ["दुपारी 12", "संध्याकाळी 5"]),
            "time_constraint": _m([r"between 12 noon and 5 PM", r"after 5 PM"], [r"12 baje se shaam 5 baje ke beech", r"5 baje ke baad"],
                                  ["12 बजे से शाम 5 बजे के बीच", "5 बजे के बाद"], ["12 ते संध्याकाळी 5 या वेळेत", "5 नंतर"]),
            "fallback": _m([r"if no train leaves", r"instead"], [r"agar us beech koi train nahi", r"uski jagah"],
                           ["कोई ट्रेन नहीं निकलती", "उसकी जगह"], ["कोणतीही ट्रेन सुटत नसेल", "पहिली ट्रेन"]),
            "booking": "ABSENT"},
    "T09": {"intent": _m([r"chair car"], [r"chair car"], ["चेयर कार"], ["चेअर कार"]),
            "booking": _m([r"^book\b"], [r"book kar do"], ["बुक कीजिए"], ["बुक करा"])},
    "T10": {"intent": _m([r"\b3A\b"], [r"\b3A\b"], [r"(?<![0-9A-Za-z])3A(?![0-9A-Za-z])"], [r"(?<![0-9A-Za-z])3A(?![0-9A-Za-z])"]),
            "availability": _m([r"if 2A is sold out"], [r"agar 2A sold out"], ["अगर 2A सोल्ड आउट"], ["2A सोल्ड आउट"]),
            "booking": _m([r"^book a 2A ticket", r"book 3A"], [r"2A ticket book kar do", r"3A book kar dena"], ["2A का टिकट बुक कीजिए", "3A बुक कीजिए"],
                          ["2A चे तिकीट बुक करा", "3A बुक करा"]),
            "fallback": _m([r"same train", r"instead"], [r"usi train", r"uski jagah"], ["उसी ट्रेन", "उसकी जगह"], ["त्याच ट्रेनमध्ये", "3A"])},
    "T11": {"intent": _m([r"\bfare\b", r"which classes"], [r"\bfare\b", r"kaun-kaun si classes"], ["किराया", "कौन-कौन सी क्लास"], ["भाडे", "कोणकोणते क्लास"]),
            "fallback": _m([r"if that train has no sleeper class"], [r"agar us train mein sleeper class nahi"], ["अगर उस ट्रेन में स्लीपर क्लास नहीं"],
                           ["त्या ट्रेनमध्ये स्लीपर क्लास नसेल"]),
            "booking": "ABSENT"},
    "T12": {"intent": _m([r"which train"], [r"kaun si train"], ["कौन-सी ट्रेन"], ["कोणती ट्रेन"]),
            "time": _m([r"9:30 AM", r"10 October"], [r"subah 9:30 baje", r"10 October"], ["सुबह 9:30 बजे", "10 अक्टूबर"], ["सकाळी 9:30", "10 ऑक्टोबर"]),
            "time_constraint": _m([r"by 9:30 AM on 10 October", r"as late as possible"], [r"9:30 baje tak", r"jitna ho sake utni der se"],
                                  ["9:30 बजे तक", "जितना हो सके उतनी देर से"], ["9:30 पर्यंत", "शक्य तितक्या उशिरा"]),
            "booking": "ABSENT"},
    "T13": {"intent": _m([r"two 3A tickets", r"one for"], [r"do 3A tickets", r"ek Priya"], ["3A के दो टिकट", "एक Priya"], ["3A ची दोन तिकिटे", "एक Priya"]),
            "time": _m([r"leaves at 5 PM"], [r"shaam 5 baje ki train"], ["शाम 5 बजे की ट्रेन"], ["संध्याकाळी 5 वाजताच्या ट्रेन"]),
            "booking": _m([r"^book\b"], [r"book kar do"], ["बुक कीजिए"], ["बुक करा"])},
    "T14": {"intent": _m([r"which is the cheapest class", r"\bfare\b"], [r"sabse sasti class", r"\bfare\b"], ["सबसे सस्ती क्लास", "किराया"],
                         ["सर्वात स्वस्त क्लास", "भाडे"]),
            "fare": _m([r"cheapest"], [r"sabse sasti"], ["सबसे सस्ती"], ["सर्वात स्वस्त"]),
            "availability": _m([r"still has seats available"], [r"abhi bhi seats available"], ["अभी भी सीटें उपलब्ध"], ["सीट उपलब्ध असलेला"]),
            "booking": "ABSENT"},
    "T15": {"intent": _m([r"travel together", r"just tell me"], [r"saath mein travel", r"bas mujhe bata dena"], ["साथ में यात्रा", "बस मुझे बता दीजिए"],
                         ["एकत्र प्रवास", "फक्त मला सांगा"]),
            "availability": _m([r"only if there are seats for both of us"], [r"sirf tab book karna jab hum dono ke liye seats hon"],
                               ["केवल तभी बुक कीजिए जब हम दोनों के लिए सीटें हों"], ["आम्हा दोघांसाठी सीट उपलब्ध असतील तरच"]),
            "booking": _m([r"^book\b", r"only if"], [r"book karo", r"sirf tab"], ["बुक कीजिए", "केवल तभी"], ["बुक करा", "तरच"]),
            "forbidden": _m([r"don't book anything"], [r"kuch bhi book mat karna"], ["कुछ भी बुक मत कीजिए"], ["काहीही बुक करू नका"]),
            "fallback": _m([r"otherwise"], [r"warna"], ["वरना"], ["अन्यथा"])},
}

# ------------------------------------------------------------------ translation-risk flags (draft author's notes, NOT human judgement)
def F(flag: bool, detail: str) -> dict:
    return {"flag": flag, "detail": detail}


OK = F(False, "none identified by the draft author (not a human judgement)")
_GENDER = "Speaker gender kept neutral on purpose (verbs agree with 'train' or use 'mujhe/मुझे ... hai'), because English is ungendered."

FLAGS: dict[tuple[str, str], dict[str, dict]] = {
    ("T06", "hinglish"): dict(potential_ambiguity=F(True, "'New Delhi se chalti hai' must read as 'departs from New Delhi' (origin weekdays), not 'runs via'."),
                              unnatural_wording=OK, constraint_risk=OK, notes=F(False, "'Monday' kept in English, as is common in Hinglish. " + _GENDER)),
    ("T06", "hi"): dict(potential_ambiguity=F(True, "'चलती है' can mean 'runs' generally; with 'नई दिल्ली से' it should read as 'departs New Delhi'. Reviewer to confirm."),
                        unnatural_wording=F(True, "'सप्ताह के किन-किन दिनों में' is slightly formal; 'हफ़्ते के किन दिनों' is more colloquial."),
                        constraint_risk=OK, notes=F(False, "English 'Can I catch it' rendered impersonally as 'यह ट्रेन मिल सकती है' (gender-neutral).")),
    ("T06", "mr"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'मिळू शकते का' (can I get it) for 'catch'; a reviewer may prefer 'पकडता येईल का'."),
                        constraint_risk=OK, notes=F(False, "'सुटते' = departs, which matches the origin-weekday meaning precisely.")),
    ("T07", "hinglish"): dict(potential_ambiguity=F(True, "'kitne baje pahunchegi' asks the clock time only, like English; the date (next day) is not asked in any variant."),
                              unnatural_wording=OK, constraint_risk=OK, notes=F(False, "English 'I'm taking the train' rendered as 'meri ... train hai' (my train is), gender-neutral.")),
    ("T07", "hi"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'प्लेटफ़ॉर्म' loanword; 'मिलना चाहता है' is natural."), constraint_risk=OK,
                        notes=F(False, "Station name uses the decomposed-nukta alias exactly as in stations.json.")),
    ("T07", "mr"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'माझी ... ट्रेन आहे' (my train is) restructures 'I'm taking'; reviewer to confirm it is natural."),
                        constraint_risk=OK, notes=F(False, "'नागपूरला' attaches the dative suffix to the alias; the alias still appears verbatim.")),
    ("T08", "hinglish"): dict(potential_ambiguity=F(True, "'12 baje se 5 baje ke beech' must read as inclusive 12:00-17:00, like English 'between'. Gold has no train at the boundaries, so inclusivity does not change the answer."),
                              unnatural_wording=OK, constraint_risk=F(True, "Fallback rule 'shaam 5 baje ke baad ... pehli train' must be read as strictly after 17:00; no train departs at exactly 17:00."),
                              notes=F(False, "'dopahar'/'shaam' added to disambiguate 12 and 5 as noon/PM, as in the pilot's T03.")),
    ("T08", "hi"): dict(potential_ambiguity=F(True, "'उस समय के बीच' is a little redundant; reviewer may prefer 'उस बीच'."), unnatural_wording=OK,
                        constraint_risk=F(True, "Fallback condition 'अगर ... कोई ट्रेन नहीं निकलती' + 'उसकी जगह' must survive as a conditional alternative."), notes=OK),
    ("T08", "mr"): dict(potential_ambiguity=F(True, "'दुपारी 12 ते संध्याकाळी 5 या वेळेत' = between 12 noon and 5 PM; inclusivity not explicit (as in English)."),
                        unnatural_wording=OK, constraint_risk=F(True, "'संध्याकाळी 5 नंतर' = after 5 PM (strict)."), notes=F(False, "'एकही ट्रेन' = not a single train; matches 'no train'.")),
    ("T09", "hinglish"): dict(potential_ambiguity=F(True, "INTENDED ambiguity: 'Delhi' must stay generic. Using 'New Delhi'/'Nai Dilli' would remove it."), unnatural_wording=OK,
                              constraint_risk=F(True, "If a reviewer 'corrects' Delhi to a specific station, the task changes category."), notes=F(False, "'Delhi' (not 'Dilli') chosen as the most common Hinglish spelling; both are ambiguous in the environment.")),
    ("T09", "hi"): dict(potential_ambiguity=F(True, "INTENDED ambiguity: 'दिल्ली' must not become 'नई दिल्ली'."), unnatural_wording=F(True, "'चेयर कार' loanword; 'कुर्सीयान' would be very formal."),
                        constraint_risk=F(True, "Do not add a station qualifier during review."), notes=OK),
    ("T09", "mr"): dict(potential_ambiguity=F(True, "INTENDED ambiguity: 'दिल्ली' must not become 'नवी दिल्ली'."), unnatural_wording=F(True, "'चेअर कार' spelling vs 'चेयर कार'; reviewer to choose."),
                        constraint_risk=F(True, "Do not add a station qualifier during review."), notes=F(False, "Structure mirrors the pilot T04 Marathi booking sentence.")),
    ("T10", "hinglish"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=F(True, "Fallback must stay restricted to 3A on the SAME train ('usi train mein'); a looser 'koi aur class' would widen it."),
                              notes=F(False, "'sold out' kept as an English loanword.")),
    ("T10", "hi"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'सोल्ड आउट' transliterated loanword, consistent with pilot T05."),
                        constraint_risk=F(True, "'उसकी जगह उसी ट्रेन में 3A' carries both 'instead' and 'same train'."), notes=OK),
    ("T10", "mr"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'सोल्ड आउट' loanword vs 'संपले असेल'; kept for consistency with pilot T05."),
                        constraint_risk=F(True, "'त्याऐवजी त्याच ट्रेनमध्ये 3A' carries both 'instead' and 'same train'."), notes=OK),
    ("T11", "hinglish"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=F(True, "The conditional follow-up ('agar ... nahi hai, to bata do ...') is the scored part; it must not be dropped."),
                              notes=F(False, "'classes' pluralised with English -es, typical in Hinglish.")),
    ("T11", "hi"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'कौन-कौन सी क्लास हैं' mixes a loanword with Hindi plural agreement; 'श्रेणियाँ' would be formal."), constraint_risk=OK, notes=OK),
    ("T11", "mr"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'क्लास' treated as masculine ('कोणकोणते क्लास'); reviewer to confirm gender usage."), constraint_risk=OK, notes=OK),
    ("T12", "hinglish"): dict(potential_ambiguity=F(True, "'9:30 baje tak' = by 09:30 (inclusive deadline). 'jitna ho sake utni der se' = as late as possible; must not read as 'whenever'."),
                              unnatural_wording=OK, constraint_risk=F(True, "Highest-risk batch item: next-day deadline + latest-departure objective must both survive."), notes=F(False, "Deadline date '10 October' has no year in every variant, as in English.")),
    ("T12", "hi"): dict(potential_ambiguity=F(True, "'जितना हो सके उतनी देर से' = as late as possible."), unnatural_wording=OK,
                        constraint_risk=F(True, "Deadline and objective in one sentence; reviewer to confirm neither is weakened."), notes=OK),
    ("T12", "mr"): dict(potential_ambiguity=F(True, "'9:30 पर्यंत' = by 09:30 (inclusive)."), unnatural_wording=F(True, "'मी कोणती ट्रेन घ्यावी?' is natural; '10 ऑक्टोबरला' uses the dative suffix."),
                        constraint_risk=F(True, "'शक्य तितक्या उशिरा' = as late as possible."), notes=OK),
    ("T13", "hinglish"): dict(potential_ambiguity=F(True, "'shaam 5 baje ki train' identifies the 17:00 departure; 'shaam' disambiguates 5 PM."), unnatural_wording=OK,
                              constraint_risk=F(True, "Two separate passengers ('ek ... aur ek ...') must survive; a single two-name booking is impossible in the environment."), notes=OK),
    ("T13", "hi"): dict(potential_ambiguity=F(True, "'शाम 5 बजे की ट्रेन' = the 5 PM train (departure)."), unnatural_wording=F(True, "Latin-script names inside Devanagari (environment's Latin-only passenger rule)."),
                        constraint_risk=OK, notes=OK),
    ("T13", "mr"): dict(potential_ambiguity=F(True, "'संध्याकाळी 5 वाजताच्या ट्रेनमध्ये' = in the 5 PM train (departure)."), unnatural_wording=F(True, "'यांच्यासाठी' adds an honorific absent in English (as in pilot T04/T05)."),
                        constraint_risk=OK, notes=OK),
    ("T14", "hinglish"): dict(potential_ambiguity=F(True, "'sabse sasti class ... jismein abhi bhi seats available hain' must bind 'with seats' to the class, not to the train."),
                              unnatural_wording=OK, constraint_risk=OK, notes=F(False, "English 'I'm travelling on' rendered as 'meri ... train hai' (gender-neutral).")),
    ("T14", "hi"): dict(potential_ambiguity=F(True, "Relative clause 'वह ... क्लास ... जिसमें' makes the seat condition attach to the class (intended)."), unnatural_wording=OK, constraint_risk=OK, notes=OK),
    ("T14", "mr"): dict(potential_ambiguity=F(True, "Participial 'सीट उपलब्ध असलेला सर्वात स्वस्त क्लास' attaches the seat condition to the class (intended)."),
                        unnatural_wording=F(True, "Long pre-nominal participle; a reviewer may split it."), constraint_risk=OK, notes=OK),
    ("T15", "hinglish"): dict(potential_ambiguity=F(True, "'hum dono ke liye seats hon' = seats for BOTH (2), not 'seats exist'."), unnatural_wording=OK,
                              constraint_risk=F(True, "Three coupled conditions (together, only if both, otherwise nothing). Dropping 'dono' would turn this into T05-style 'seats available'."), notes=OK),
    ("T15", "hi"): dict(potential_ambiguity=F(True, "'हम दोनों के लिए सीटें' = seats for both of us."), unnatural_wording=F(True, "'केवल तभी ... जब' slightly formal (as in pilot T05)."),
                        constraint_risk=F(True, "'दोनों' carries the quantity; it must not be dropped."), notes=F(False, "Station name uses the decomposed-nukta alias exactly as in stations.json.")),
    ("T15", "mr"): dict(potential_ambiguity=F(True, "'आम्हा दोघांसाठी सीट असतील तरच' = only if there are seats for both of us."), unnatural_wording=OK,
                        constraint_risk=F(True, "'दोघांसाठी' carries the quantity; it must not be dropped."), notes=F(False, "'तरच' strongly encodes 'only if' (as in pilot T05).")),
}
