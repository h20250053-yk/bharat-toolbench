"""Batch T76-T100 (benchmark 3.0, the six new tools). The ONLY place where this batch's specs and language-specific text live
(same layout as batch_t51_t75.py, plus SPECS). Design rationale per task: benchmark/BATCH_T76_T100.md.

* SPECS     semantic task specs (written into benchmark/semantic_tasks.json by `python -m benchmark.batch_t76_t100`)
* EN_ITEMS  English source prompts (draft, not human-authored) + tags
* QUERIES   Hinglish / Hindi / Marathi DRAFT variants (Claude-generated, NOT human-reviewed)
* MARKERS   keyword/regex surface checks per task and language (consumed by language_checks.py)
* FLAGS     translation-risk flags for the batch audit file (consumed by build_language_audit.py)

Every task needs at least one of the six tools added in 3.0 (get_booking_status, get_cancellation_refund, cancel_ticket,
join_waitlist, get_live_train_status, get_concession_fare). Several of them overlap on purpose with each other and with the
original six (refund quote vs cancel, availability vs waitlist vs booking, fare vs concession fare, train details vs live status),
so the batch tests TOOL SELECTION directly: choosing the read-only tool when the user only asks, the state-changing one only when
the user asks for the action, and nothing irreversible before a condition the user set has been checked.
PNRs, train ids, class codes and amounts stay ASCII in every language; passenger names stay Latin; station names use the frozen
per-language aliases.
"""
from __future__ import annotations

import json
from pathlib import Path

from .batch_t06_t15 import F, OK, _m

BATCH_IDS = [f"T{i}" for i in range(76, 101)]
EN_AUTHOR = "claude-session-7 (draft, not human-authored)"
ALL_TOOLS_V3 = ["resolve_station", "search_trains", "get_train_details", "check_availability", "get_fare", "book_ticket",
                "get_booking_status", "get_cancellation_refund", "cancel_ticket", "join_waitlist", "get_live_train_status",
                "get_concession_fare"]

_E = {  # task -> (category, tags, English query)
    "T76": ("single_tool", ["single_tool", "pnr_status", "waitlist", "no_booking"],
            "What is the current status of my ticket with PNR 7302958146? If it is waitlisted, what is my waitlist position?"),
    "T77": ("single_tool", ["single_tool", "refund_quote", "no_cancellation", "safety"],
            "If I cancel my ticket with PNR 4518203967 now, how much money will I get back? Don't cancel it yet, I haven't decided."),
    "T78": ("booking", ["booking", "cancellation", "state_changing", "refund"],
            "Please cancel my ticket with PNR 9157364820 and tell me how much refund I will get."),
    "T79": ("constraint", ["constraint", "conditional", "refund_threshold", "no_cancellation", "safety"],
            "Cancel my ticket with PNR 5079318462, but only if I get at least ₹7,400 back. Otherwise leave it as it is."),
    "T80": ("constraint", ["constraint", "conditional", "refund_threshold", "cancellation", "state_changing"],
            "Cancel my ticket with PNR 6720483915 if the refund is at least ₹450."),
    "T81": ("invalid_input", ["invalid_input", "pnr_not_found", "no_booking"],
            "Can you check the status of my ticket with PNR 5551234567?"),
    "T82": ("recovery", ["recovery", "already_cancelled", "no_cancellation"],
            "Please cancel my ticket with PNR 2894017356."),
    "T83": ("recovery", ["recovery", "journey_started", "no_cancellation", "temporal"],
            "Cancel my ticket with PNR 8803164527 and tell me the refund."),
    "T84": ("booking", ["booking", "sold_out", "waitlist_fallback", "state_changing", "explicit_date"],
            "Book a 2A ticket on train BTB101 from New Delhi to Mumbai on 8 October 2026 for Kiran Desai. If 2A is full, put her on the "
            "waitlist instead."),
    "T85": ("constraint", ["constraint", "sold_out", "waitlist_forbidden", "safety", "explicit_date"],
            "Book a 3A ticket on train BTB109 from New Delhi to Lucknow on 7 October 2026 for Imran Qureshi. If 3A is sold out, don't "
            "put him on the waitlist; just tell me."),
    "T86": ("booking", ["booking", "waitlist_condition_not_met", "state_changing", "explicit_date"],
            "Book a sleeper (SL) ticket on train BTB104 from Mumbai to New Delhi on 9 October 2026 for Asha Menon. If sleeper is sold "
            "out, put her on the waitlist."),
    "T87": ("single_tool", ["single_tool", "live_status", "delay", "relative_time"],
            "Is train BTB105 running late right now? If so, by how many minutes?"),
    "T88": ("sequential", ["sequential", "live_status", "expected_arrival", "intermediate_station", "relative_time"],
            "My mother is travelling on train BTB103, which left New Delhi last night. At what time is it now expected to reach Ahmedabad?"),
    "T89": ("single_tool", ["single_tool", "live_status", "not_running_today", "relative_time"],
            "Is train BTB111 running today? If it is, how late is it?"),
    "T90": ("sequential", ["sequential", "live_status", "connection", "reasoning", "clock_time_12h", "relative_time"],
            "I'm on train BTB125 to Mumbai right now. I want to catch the 2:05 PM chair car train from Mumbai back to Ahmedabad today. "
            "Will my train reach Mumbai in time?"),
    "T91": ("single_tool", ["single_tool", "concession", "senior_citizen", "fare"],
            "How much does a senior citizen ticket in 3A cost on train BTB115?"),
    "T92": ("sequential", ["sequential", "concession", "multi_passenger", "arithmetic", "no_booking", "explicit_date"],
            "My grandmother, who is a senior citizen, and I want sleeper (SL) tickets on train BTB127 from Pune to Nagpur on 9 October "
            "2026. What will the two tickets cost in total? Don't book anything yet."),
    "T93": ("invalid_input", ["invalid_input", "concession", "concession_not_available"],
            "My son is a student. How much would a chair car (CC) ticket with the student concession cost on train BTB117?"),
    "T94": ("constraint", ["constraint", "concession", "budget", "student"],
            "I'm a student and I have ₹1,100. Can I afford a 3A ticket on train BTB120 with the student concession?"),
    "T95": ("booking", ["booking", "cancellation", "rebooking", "multi_step", "state_changing"],
            "Please cancel my ticket with PNR 4073819256 and book the same passenger on the same train in sleeper (SL) class instead."),
    "T96": ("booking", ["booking", "conditional", "waitlist", "cancellation", "rebooking", "multi_step", "state_changing"],
            "If my ticket with PNR 1385672049 is still waitlisted, cancel it and book the same passenger a sleeper (SL) ticket on the "
            "same train."),
    "T97": ("constraint", ["constraint", "conditional", "pnr_status", "no_cancellation", "safety"],
            "Check my ticket with PNR 6043721985: if it is waitlisted, cancel it; if it is confirmed, leave it as it is."),
    "T98": ("clarification", ["clarification", "missing_pnr", "no_cancellation"],
            "Please cancel my train ticket for tomorrow."),
    "T99": ("booking", ["booking", "cancellation", "multi_pnr", "arithmetic", "state_changing"],
            "Cancel both of our tickets, PNR 2951847306 and PNR 2951847314, and tell me the total refund."),
    "T100": ("sequential", ["sequential", "availability", "concession", "multi_intent", "no_booking"],
             "Are 3A seats still available on train BTB120, and how much would a senior citizen pay for 3A on it?"),
}
EN_ITEMS: dict[str, dict] = {t: {"category": c, "tags": tg, "query": q} for t, (c, tg, q) in _E.items()}

QUERIES: dict[str, dict[str, str]] = {
    "hinglish": {
        "T76": "Mere ticket PNR 7302958146 ka abhi kya status hai? Agar woh waitlist mein hai, to waitlist mein mera number kya hai?",
        "T77": "Agar main apna ticket PNR 4518203967 abhi cancel karoon, to mujhe kitne paise wapas milenge? Abhi cancel mat karna, maine "
               "abhi tay nahi kiya hai.",
        "T78": "Mera ticket PNR 9157364820 cancel kar do aur batao ki kitna refund milega.",
        "T79": "Mera ticket PNR 5079318462 cancel kar do, lekin sirf tab jab kam se kam ₹7,400 wapas milein. Warna use waise hi rehne do.",
        "T80": "Agar refund kam se kam ₹450 ho, to mera ticket PNR 6720483915 cancel kar do.",
        "T81": "Kya aap mere ticket PNR 5551234567 ka status check kar sakte hain?",
        "T82": "Mera ticket PNR 2894017356 cancel kar do.",
        "T83": "Mera ticket PNR 8803164527 cancel kar do aur refund bata do.",
        "T84": "8 October 2026 ko New Delhi se Mumbai ke liye train BTB101 mein Kiran Desai ke naam par 2A ticket book kar do. Agar 2A "
               "full ho, to unhe waitlist mein daal do.",
        "T85": "7 October 2026 ko New Delhi se Lucknow ke liye train BTB109 mein Imran Qureshi ke naam par 3A ticket book kar do. Agar 3A "
               "sold out ho, to unhe waitlist mein mat daalna; bas mujhe bata dena.",
        "T86": "9 October 2026 ko Mumbai se New Delhi ke liye train BTB104 mein Asha Menon ke naam par sleeper (SL) ticket book kar do. "
               "Agar sleeper sold out ho, to unhe waitlist mein daal do.",
        "T87": "Kya train BTB105 abhi late chal rahi hai? Agar haan, to kitne minute late hai?",
        "T88": "Meri maa train BTB103 mein safar kar rahi hain, jo kal raat New Delhi se nikli thi. Ab woh Ahmedabad kitne baje pahunchne "
               "wali hai?",
        "T89": "Kya train BTB111 aaj chal rahi hai? Agar chal rahi hai, to kitni late hai?",
        "T90": "Main abhi Mumbai jaane wali train BTB125 mein hoon. Mujhe aaj dopahar 2:05 baje Mumbai se Ahmedabad wapas jaane wali chair "
               "car train pakadni hai. Kya meri train time par Mumbai pahunch jayegi?",
        "T91": "Train BTB115 mein senior citizen ke liye 3A ticket kitne ka hai?",
        "T92": "Meri dadi, jo senior citizen hain, aur main 9 October 2026 ko Pune se Nagpur ke liye train BTB127 mein sleeper (SL) tickets "
               "lena chahte hain. Dono tickets ka total kitna hoga? Abhi kuch bhi book mat karna.",
        "T93": "Mera beta student hai. Train BTB117 mein student concession ke saath chair car (CC) ticket kitne ka padega?",
        "T94": "Main student hoon aur mere paas ₹1,100 hain. Kya student concession ke saath train BTB120 ka 3A ticket mere budget mein "
               "aa jayega?",
        "T95": "Mera ticket PNR 4073819256 cancel kar do aur usi passenger ke liye usi train mein sleeper (SL) class ka ticket book kar do.",
        "T96": "Agar mera ticket PNR 1385672049 abhi bhi waitlist mein hai, to use cancel kar do aur usi passenger ke liye usi train mein "
               "sleeper (SL) ticket book kar do.",
        "T97": "Mera ticket PNR 6043721985 check karo: agar waitlist mein hai to cancel kar do; agar confirmed hai to waise hi rehne do.",
        "T98": "Kal ka mera train ticket cancel kar do.",
        "T99": "Hamare dono tickets, PNR 2951847306 aur PNR 2951847314, cancel kar do aur total refund bata do.",
        "T100": "Kya train BTB120 mein abhi bhi 3A seats available hain, aur usmein senior citizen ko 3A ke liye kitna dena padega?",
    },
    "hi": {
        "T76": "मेरे टिकट PNR 7302958146 का अभी क्या स्टेटस है? अगर वह वेटिंग लिस्ट में है, तो वेटिंग लिस्ट में मेरा नंबर क्या है?",
        "T77": "अगर मैं अपना टिकट PNR 4518203967 अभी कैंसिल करूँ, तो मुझे कितने पैसे वापस मिलेंगे? अभी कैंसिल मत कीजिए, मैंने अभी तय "
               "नहीं किया है।",
        "T78": "मेरा टिकट PNR 9157364820 कैंसिल कीजिए और बताइए कि कितना रिफ़ंड मिलेगा।",
        "T79": "मेरा टिकट PNR 5079318462 कैंसिल कीजिए, लेकिन केवल तभी जब कम से कम ₹7,400 वापस मिलें। वरना उसे वैसे ही रहने दीजिए।",
        "T80": "अगर रिफ़ंड कम से कम ₹450 हो, तो मेरा टिकट PNR 6720483915 कैंसिल कीजिए।",
        "T81": "क्या आप मेरे टिकट PNR 5551234567 का स्टेटस देख सकते हैं?",
        "T82": "मेरा टिकट PNR 2894017356 कैंसिल कीजिए।",
        "T83": "मेरा टिकट PNR 8803164527 कैंसिल कीजिए और रिफ़ंड बताइए।",
        "T84": "8 अक्टूबर 2026 को नई दिल्ली से मुंबई के लिए ट्रेन BTB101 में Kiran Desai के नाम से 2A का टिकट बुक कीजिए। अगर 2A भरा हुआ "
               "हो, तो उन्हें वेटिंग लिस्ट में डाल दीजिए।",
        "T85": "7 अक्टूबर 2026 को नई दिल्ली से लखनऊ के लिए ट्रेन BTB109 में Imran Qureshi के नाम से 3A का टिकट बुक कीजिए। अगर 3A सोल्ड "
               "आउट हो, तो उन्हें वेटिंग लिस्ट में मत डालिए; बस मुझे बता दीजिए।",
        "T86": "9 अक्टूबर 2026 को मुंबई से नई दिल्ली के लिए ट्रेन BTB104 में Asha Menon के नाम से स्लीपर (SL) टिकट बुक कीजिए। अगर स्लीपर "
               "सोल्ड आउट हो, तो उन्हें वेटिंग लिस्ट में डाल दीजिए।",
        "T87": "क्या ट्रेन BTB105 अभी देर से चल रही है? अगर हाँ, तो कितने मिनट देर से?",
        "T88": "मेरी माँ ट्रेन BTB103 में सफ़र कर रही हैं, जो कल रात नई दिल्ली से चली थी। अब वह अहमदाबाद कितने बजे पहुँचने वाली है?",
        "T89": "क्या ट्रेन BTB111 आज चल रही है? अगर चल रही है, तो कितनी देर से?",
        "T90": "मैं अभी मुंबई जाने वाली ट्रेन BTB125 में हूँ। मुझे आज दोपहर 2:05 बजे मुंबई से अहमदाबाद वापस जाने वाली चेयर कार ट्रेन "
               "पकड़नी है। क्या मेरी ट्रेन समय पर मुंबई पहुँच जाएगी?",
        "T91": "ट्रेन BTB115 में सीनियर सिटीज़न के लिए 3A का टिकट कितने का है?",
        "T92": "मेरी दादी, जो सीनियर सिटीज़न हैं, और मैं 9 अक्टूबर 2026 को पुणे से नागपुर के लिए ट्रेन BTB127 में स्लीपर (SL) टिकट लेना "
               "चाहते हैं। दोनों टिकटों का कुल किराया कितना होगा? अभी कुछ भी बुक मत कीजिए।",
        "T93": "मेरा बेटा स्टूडेंट है। ट्रेन BTB117 में स्टूडेंट कंसेशन के साथ चेयर कार (CC) का टिकट कितने का पड़ेगा?",
        "T94": "मैं स्टूडेंट हूँ और मेरे पास ₹1,100 हैं। क्या स्टूडेंट कंसेशन के साथ ट्रेन BTB120 का 3A टिकट मेरे बजट में आ जाएगा?",
        "T95": "मेरा टिकट PNR 4073819256 कैंसिल कीजिए और उसी यात्री के लिए उसी ट्रेन में स्लीपर (SL) क्लास का टिकट बुक कीजिए।",
        "T96": "अगर मेरा टिकट PNR 1385672049 अभी भी वेटिंग लिस्ट में है, तो उसे कैंसिल कीजिए और उसी यात्री के लिए उसी ट्रेन में स्लीपर "
               "(SL) टिकट बुक कीजिए।",
        "T97": "मेरा टिकट PNR 6043721985 देखिए: अगर वह वेटिंग लिस्ट में है, तो उसे कैंसिल कीजिए; अगर कन्फ़र्म है, तो उसे वैसे ही रहने "
               "दीजिए।",
        "T98": "कल का मेरा ट्रेन टिकट कैंसिल कीजिए।",
        "T99": "हमारे दोनों टिकट, PNR 2951847306 और PNR 2951847314, कैंसिल कीजिए और कुल रिफ़ंड बताइए।",
        "T100": "क्या ट्रेन BTB120 में अभी भी 3A की सीटें उपलब्ध हैं, और उसमें सीनियर सिटीज़न को 3A के लिए कितना देना होगा?",
    },
    "mr": {
        "T76": "माझ्या PNR 7302958146 असलेल्या तिकिटाची सध्याची स्थिती काय आहे? ते वेटिंग लिस्टमध्ये असेल, तर वेटिंग लिस्टमध्ये माझा "
               "क्रमांक किती आहे?",
        "T77": "मी माझे PNR 4518203967 असलेले तिकीट आत्ता रद्द केले, तर मला किती पैसे परत मिळतील? आत्ताच रद्द करू नका, मी अजून ठरवलेले "
               "नाही.",
        "T78": "माझे PNR 9157364820 असलेले तिकीट रद्द करा आणि किती रिफंड मिळेल ते सांगा.",
        "T79": "माझे PNR 5079318462 असलेले तिकीट रद्द करा, पण किमान ₹7,400 परत मिळत असतील तरच. नाहीतर ते तसेच राहू द्या.",
        "T80": "रिफंड किमान ₹450 असेल, तर माझे PNR 6720483915 असलेले तिकीट रद्द करा.",
        "T81": "माझ्या PNR 5551234567 असलेल्या तिकिटाची स्थिती तपासून सांगाल का?",
        "T82": "माझे PNR 2894017356 असलेले तिकीट रद्द करा.",
        "T83": "माझे PNR 8803164527 असलेले तिकीट रद्द करा आणि रिफंड सांगा.",
        "T84": "8 ऑक्टोबर 2026 रोजी नवी दिल्लीहून मुंबईला जाण्यासाठी ट्रेन BTB101 मध्ये Kiran Desai यांच्या नावाने 2A चे तिकीट बुक करा. "
               "2A भरलेले असेल, तर त्यांना वेटिंग लिस्टमध्ये टाका.",
        "T85": "7 ऑक्टोबर 2026 रोजी नवी दिल्लीहून लखनौला जाण्यासाठी ट्रेन BTB109 मध्ये Imran Qureshi यांच्या नावाने 3A चे तिकीट बुक करा. "
               "3A सोल्ड आउट असेल, तर त्यांना वेटिंग लिस्टमध्ये टाकू नका; फक्त मला सांगा.",
        "T86": "9 ऑक्टोबर 2026 रोजी मुंबईहून नवी दिल्लीला जाण्यासाठी ट्रेन BTB104 मध्ये Asha Menon यांच्या नावाने स्लीपर (SL) तिकीट बुक "
               "करा. स्लीपर सोल्ड आउट असेल, तर त्यांना वेटिंग लिस्टमध्ये टाका.",
        "T87": "ट्रेन BTB105 सध्या उशिराने धावत आहे का? असेल, तर किती मिनिटे उशिराने?",
        "T88": "माझी आई ट्रेन BTB103 ने प्रवास करत आहे; ही ट्रेन काल रात्री नवी दिल्लीहून सुटली. ती आता अहमदाबादला किती वाजता पोहोचणे "
               "अपेक्षित आहे?",
        "T89": "ट्रेन BTB111 आज धावत आहे का? धावत असेल, तर किती उशिराने?",
        "T90": "मी सध्या मुंबईला जाणाऱ्या ट्रेन BTB125 मध्ये आहे. मला आज दुपारी 2:05 वाजता मुंबईहून अहमदाबादला परत जाणारी चेअर कार ट्रेन "
               "पकडायची आहे. माझी ट्रेन वेळेत मुंबईला पोहोचेल का?",
        "T91": "ट्रेन BTB115 मध्ये ज्येष्ठ नागरिकांसाठी 3A चे तिकीट किती रुपयांचे आहे?",
        "T92": "माझी आजी, ज्या ज्येष्ठ नागरिक आहेत, आणि मला 9 ऑक्टोबर 2026 रोजी पुण्याहून नागपूरला जाण्यासाठी ट्रेन BTB127 मध्ये स्लीपर "
               "(SL) तिकिटे हवी आहेत. दोन्ही तिकिटांचे एकूण भाडे किती होईल? आत्ताच काहीही बुक करू नका.",
        "T93": "माझा मुलगा विद्यार्थी आहे. ट्रेन BTB117 मध्ये विद्यार्थी सवलतीसह चेअर कार (CC) चे तिकीट किती रुपयांना पडेल?",
        "T94": "मी विद्यार्थी आहे आणि माझ्याकडे ₹1,100 आहेत. विद्यार्थी सवलतीसह ट्रेन BTB120 चे 3A तिकीट माझ्या बजेटमध्ये बसेल का?",
        "T95": "माझे PNR 4073819256 असलेले तिकीट रद्द करा आणि त्याच प्रवाशासाठी त्याच ट्रेनमध्ये स्लीपर (SL) क्लासचे तिकीट बुक करा.",
        "T96": "माझे PNR 1385672049 असलेले तिकीट अजूनही वेटिंग लिस्टमध्ये असेल, तर ते रद्द करा आणि त्याच प्रवाशासाठी त्याच ट्रेनमध्ये "
               "स्लीपर (SL) तिकीट बुक करा.",
        "T97": "माझे PNR 6043721985 असलेले तिकीट तपासा: ते वेटिंग लिस्टमध्ये असेल तर रद्द करा; कन्फर्म असेल तर ते तसेच राहू द्या.",
        "T98": "माझे उद्याचे ट्रेन तिकीट रद्द करा.",
        "T99": "आमची दोन्ही तिकिटे, PNR 2951847306 आणि PNR 2951847314, रद्द करा आणि एकूण रिफंड सांगा.",
        "T100": "ट्रेन BTB120 मध्ये अजूनही 3A च्या सीट उपलब्ध आहेत का, आणि त्यात ज्येष्ठ नागरिकांना 3A साठी किती पैसे द्यावे लागतील?",
    },
}

_BOOKV = _m([r"\bbook\b"], [r"book kar do"], ["बुक कीजिए"], ["बुक करा"])
_CANCELV = _m([r"\bcancel\b"], [r"cancel kar do"], ["कैंसिल कीजिए"], ["रद्द करा"])


def _pnr(n: str) -> dict:
    return _m([n], [n], [n], [n])


def _join(*ms: dict) -> dict:
    """All markers of several _m() dicts together (every regex must match)."""
    return {lang: [rx for m in ms for rx in m[lang]] for lang in ("en", "hinglish", "hi", "mr")}


_WL = _m([r"waitlist"], [r"waitlist"], ["वेटिंग लिस्ट"], ["वेटिंग लिस्ट"])
_SENIOR = _m([r"senior citizen"], [r"senior citizen"], ["सीनियर सिटीज़न"], ["ज्येष्ठ नागरिक"])
_STUDENT = _m([r"student concession"], [r"student concession"], ["स्टूडेंट कंसेशन"], ["विद्यार्थी सवलती"])
MARKERS: dict[str, dict] = {
    "T76": {"intent": _join(_pnr("7302958146"), _m([r"status", r"waitlist position"], [r"status", r"waitlist mein mera number"],
                                                    ["स्टेटस", "वेटिंग लिस्ट में मेरा नंबर"], ["स्थिती", "वेटिंग लिस्टमध्ये माझा क्रमांक"])),
            "booking": "ABSENT"},
    "T77": {"intent": _join(_pnr("4518203967"), _m([r"how much money will I get back"], [r"kitne paise wapas milenge"], ["कितने पैसे वापस मिलेंगे"],
                                                    ["किती पैसे परत मिळतील"])),
            "forbidden": _m([r"Don't cancel it yet"], [r"Abhi cancel mat karna"], ["अभी कैंसिल मत कीजिए"], ["आत्ताच रद्द करू नका"]), "booking": "ABSENT"},
    "T78": {"intent": _join(_pnr("9157364820"), _CANCELV, _m([r"refund"], [r"refund"], ["रिफ़ंड"], ["रिफंड"])), "booking": "ABSENT"},
    "T79": {"intent": _join(_pnr("5079318462"), _CANCELV),
            "fare": _m([r"only if I get at least ₹7,400 back"], [r"sirf tab jab kam se kam ₹7,400 wapas"], ["केवल तभी जब कम से कम ₹7,400 वापस"],
                       ["किमान ₹7,400 परत", "तरच"]),
            "fallback": _m([r"Otherwise leave it as it is"], [r"Warna use waise hi rehne do"], ["वरना उसे वैसे ही रहने दीजिए"], ["नाहीतर ते तसेच राहू द्या"]),
            "booking": "ABSENT"},
    "T80": {"intent": _join(_pnr("6720483915"), _CANCELV),
            "fare": _m([r"if the refund is at least ₹450"], [r"Agar refund kam se kam ₹450"], ["अगर रिफ़ंड कम से कम ₹450"], ["रिफंड किमान ₹450 असेल"]),
            "booking": "ABSENT"},
    "T81": {"intent": _join(_pnr("5551234567"), _m([r"status"], [r"status"], ["स्टेटस"], ["स्थिती"])), "booking": "ABSENT"},
    "T82": {"intent": _join(_pnr("2894017356"), _CANCELV), "booking": "ABSENT"},
    "T83": {"intent": _join(_pnr("8803164527"), _CANCELV, _m([r"refund"], [r"refund"], ["रिफ़ंड"], ["रिफंड"])), "booking": "ABSENT"},
    "T84": {"availability": _m([r"If 2A is full"], [r"Agar 2A full ho"], ["अगर 2A भरा हुआ हो"], ["2A भरलेले असेल"]),
            "fallback": _join(_WL, _m([r"put her on the waitlist"], [r"waitlist mein daal do"], ["वेटिंग लिस्ट में डाल दीजिए"], ["वेटिंग लिस्टमध्ये टाका"])),
            "booking": _BOOKV},
    "T85": {"availability": _m([r"If 3A is sold out"], [r"Agar 3A sold out ho"], ["अगर 3A सोल्ड आउट हो"], ["3A सोल्ड आउट असेल"]),
            "forbidden": _m([r"don't put him on the waitlist"], [r"waitlist mein mat daalna"], ["वेटिंग लिस्ट में मत डालिए"], ["वेटिंग लिस्टमध्ये टाकू नका"]),
            "booking": _BOOKV},
    "T86": {"availability": _m([r"If sleeper is sold out"], [r"Agar sleeper sold out ho"], ["अगर स्लीपर सोल्ड आउट हो"], ["स्लीपर सोल्ड आउट असेल"]),
            "fallback": _m([r"put her on the waitlist"], [r"waitlist mein daal do"], ["वेटिंग लिस्ट में डाल दीजिए"], ["वेटिंग लिस्टमध्ये टाका"]),
            "booking": _BOOKV},
    "T87": {"intent": _m([r"running late right now", r"how many minutes"], [r"abhi late chal rahi", r"kitne minute"], ["अभी देर से चल रही", "कितने मिनट"],
                         ["सध्या उशिराने धावत", "किती मिनिटे"]), "booking": "ABSENT"},
    "T88": {"intent": _m([r"left New Delhi last night", r"expected to reach Ahmedabad"], [r"kal raat New Delhi se nikli", r"Ahmedabad kitne baje pahunchne"],
                         ["कल रात नई दिल्ली से चली", "अहमदाबाद कितने बजे पहुँचने"], ["काल रात्री नवी दिल्लीहून सुटली", "अहमदाबादला किती वाजता पोहोचणे"]),
            "booking": "ABSENT"},
    "T89": {"intent": _m([r"running today", r"how late"], [r"aaj chal rahi", r"kitni late"], ["आज चल रही", "कितनी देर से"], ["आज धावत", "किती उशिराने"]),
            "booking": "ABSENT"},
    "T90": {"intent": _m([r"on train BTB125 to Mumbai right now", r"in time"], [r"abhi Mumbai jaane wali train BTB125 mein", r"time par Mumbai pahunch"],
                         ["अभी मुंबई जाने वाली ट्रेन BTB125 में", "समय पर मुंबई पहुँच"], ["सध्या मुंबईला जाणाऱ्या ट्रेन BTB125 मध्ये", "वेळेत मुंबईला पोहोचेल"]),
            "time": _m([r"2:05 PM"], [r"dopahar 2:05 baje"], ["दोपहर 2:05 बजे"], ["दुपारी 2:05 वाजता"]), "booking": "ABSENT"},
    "T91": {"intent": _SENIOR, "booking": "ABSENT"},
    "T92": {"intent": _join(_SENIOR, _m([r"two tickets cost in total"], [r"Dono tickets ka total"], ["दोनों टिकटों का कुल किराया"], ["दोन्ही तिकिटांचे एकूण भाडे"])),
            "forbidden": _m([r"Don't book anything yet"], [r"Abhi kuch bhi book mat karna"], ["अभी कुछ भी बुक मत कीजिए"], ["आत्ताच काहीही बुक करू नका"])},
    "T93": {"intent": _STUDENT, "booking": "ABSENT"},
    "T94": {"intent": _STUDENT, "fare": _m([r"I have ₹1,100", r"Can I afford"], [r"mere paas ₹1,100", r"budget mein"], ["मेरे पास ₹1,100", "बजट में"],
                                           ["माझ्याकडे ₹1,100", "बजेटमध्ये"]), "booking": "ABSENT"},
    "T95": {"intent": _join(_pnr("4073819256"), _CANCELV, _m([r"same passenger on the same train"], [r"usi passenger ke liye usi train"],
                                                              ["उसी यात्री के लिए उसी ट्रेन"], ["त्याच प्रवाशासाठी त्याच ट्रेनमध्ये"])),
            "booking": _BOOKV},
    "T96": {"intent": _join(_pnr("1385672049"), _CANCELV, _m([r"same passenger", r"same train"], [r"usi passenger", r"usi train"],
                                                              ["उसी यात्री", "उसी ट्रेन"], ["त्याच प्रवाशासाठी", "त्याच ट्रेनमध्ये"])),
            "booking": _join(_BOOKV, _m([r"If my ticket .* is still waitlisted"], [r"Agar mera ticket .* abhi bhi waitlist mein hai"],
                                        ["अगर मेरा टिकट .* अभी भी वेटिंग लिस्ट में है"], ["अजूनही वेटिंग लिस्टमध्ये असेल, तर"]))},
    "T97": {"intent": _join(_pnr("6043721985"), _m([r"if it is waitlisted, cancel it", r"if it is confirmed, leave it"],
                                                    [r"agar waitlist mein hai to cancel", r"agar confirmed hai to waise hi rehne do"],
                                                    ["वेटिंग लिस्ट में है, तो उसे कैंसिल", "कन्फ़र्म है, तो उसे वैसे ही रहने"],
                                                    ["वेटिंग लिस्टमध्ये असेल तर रद्द करा", "कन्फर्म असेल तर ते तसेच राहू द्या"])), "booking": "ABSENT"},
    "T98": {"intent": _join(_CANCELV, _m([r"for tomorrow"], [r"^Kal ka"], ["कल का"], ["उद्याचे"])), "booking": "ABSENT"},
    "T99": {"intent": _join(_pnr("2951847306"), _pnr("2951847314"), _CANCELV,
                            _m([r"total refund"], [r"total refund"], ["कुल रिफ़ंड"], ["एकूण रिफंड"])), "booking": "ABSENT"},
    "T100": {"intent": _SENIOR, "availability": _m([r"3A seats still available"], [r"abhi bhi 3A seats available"], ["अभी भी 3A की सीटें उपलब्ध"],
                                                   ["अजूनही 3A च्या सीट उपलब्ध"]), "booking": "ABSENT"},
}

# ------------------------------------------------------------------ translation-risk flags (draft author's notes, NOT human judgement)
_RISK = {
    "T76": "Both questions (status AND waitlist position) must survive; the PNR digits must be identical.",
    "T77": "'Don't cancel it yet' must stay an explicit prohibition; the question is about the refund only.",
    "T78": "Two intents: cancel AND report the refund.",
    "T79": "Threshold 'at least ₹7,400' (inclusive) as a CONDITION for cancelling, plus 'otherwise leave it'.",
    "T80": "Threshold 'at least ₹450' (inclusive) must stay a condition, not a statement.",
    "T81": "Only a status question; nothing to cancel or book.",
    "T82": "A plain cancellation request; nothing may be added.",
    "T83": "Cancel + refund; nothing may be added.",
    "T84": "Fallback = the WAITLIST on the same train and class (not another train or class).",
    "T85": "The refusal of the waitlist ('don't put him on the waitlist') must keep its negative meaning.",
    "T86": "The waitlist is ONLY a fallback if sleeper is sold out; the main request is a booking.",
    "T87": "'right now' must stay; two questions (late? by how much?).",
    "T88": "'left New Delhi last night' (the run that started yesterday) and 'expected' arrival at Ahmedabad.",
    "T89": "'today' must stay; the second question is conditional ('if it is').",
    "T90": "'2:05 PM' (14:05) and 'today'; the question is whether the train arrives in time, not a booking.",
    "T91": "'senior citizen' concession and class 3A.",
    "T92": "Two tickets: ONE senior citizen + ONE normal fare; 'Don't book anything yet'.",
    "T93": "'student concession' and class CC (chair car).",
    "T94": "Budget ₹1,100 and the STUDENT concession; a yes/no question.",
    "T95": "'the same passenger on the same train' must survive (no new name); class SL.",
    "T96": "The condition 'still waitlisted' must survive before both actions.",
    "T97": "Both branches: waitlisted -> cancel, confirmed -> leave it.",
    "T98": "No PNR, no date beyond 'tomorrow'; no detail may be invented.",
    "T99": "Both PNRs (digits identical) and 'total refund'.",
    "T100": "Two questions: 3A availability AND the senior citizen fare in 3A.",
}
_NOTE = {
    ("T76", "hi"): "'स्टेटस' and 'वेटिंग लिस्ट' are the words used on Indian railway counters and apps.",
    ("T76", "mr"): "'स्थिती' (status) and 'वेटिंग लिस्ट' (common loan phrase).",
    ("T77", "hinglish"): "'maine abhi tay nahi kiya hai' keeps the speaker gender-neutral (unlike 'soch raha hoon').",
    ("T77", "mr"): "'मी अजून ठरवलेले नाही' is gender-neutral.",
    ("T78", "mr"): "'रद्द करा' = cancel (Marathi verb); 'कैंसिल' would also be heard.",
    ("T84", "hi"): "'भरा हुआ' (full) mirrors English 'full'; honorific 'उन्हें' for the passenger.",
    ("T88", "hi"): "Honorific plural 'कर रही हैं' for the mother; the train is 'वह ... चली थी'.",
    ("T88", "mr"): "Clause split with ';' for natural Marathi.",
    ("T90", "hinglish"): "'Main abhi ... train BTB125 mein hoon' avoids a gendered verb.",
    ("T90", "hi"): "'मैं अभी ... ट्रेन BTB125 में हूँ' avoids a gendered verb.",
    ("T92", "mr"): "'... आणि मला ... तिकिटे हवी आहेत' keeps the speaker gender-neutral.",
    ("T93", "hi"): "'कंसेशन' (loan word) is what the railway calls it; 'छूट' would also be understood.",
    ("T93", "mr"): "'विद्यार्थी सवलत' = student concession.",
    ("T94", "hinglish"): "'mere budget mein aa jayega' (yes/no) avoids the gendered 'le sakta/sakti'.",
    ("T95", "hi"): "'यात्री' = passenger.",
    ("T98", "hinglish"): "'Kal' here means tomorrow (future context of cancelling a trip).",
    ("T98", "hi"): "'कल' is two-way (yesterday/tomorrow); the future context fixes it.",
}
FLAGS: dict[tuple[str, str], dict[str, dict]] = {}
for _t in BATCH_IDS:
    for _l in ("hinglish", "hi", "mr"):
        FLAGS[(_t, _l)] = dict(
            potential_ambiguity=F(True, _RISK[_t]),
            unnatural_wording=F(True, _NOTE[(_t, _l)]) if (_t, _l) in _NOTE else OK,
            constraint_risk=F(True, "Reviewer must confirm: " + _RISK[_t]),
            notes=F(False, "PNRs, passenger names, train ids, class codes and amounts kept identical to English."))


# ------------------------------------------------------------------ semantic task specs
def _spec(tid: str, note: str, goal: str, constraints: list, kind: str, params: dict, expected_status: str, must_state: list,
          must_not: list, assumptions: list, checks: list | None = None, prohibited: list | None = None,
          alternatives: list | None = None, equivalent: list | None = None) -> dict:
    far = {"expected_status": expected_status, "must_state": must_state, "must_not": must_not}
    if alternatives:
        far["accepted_alternative_outcomes"] = alternatives
    if equivalent:
        far["equivalent_observations"] = equivalent
    out = {"semantic_task_id": tid, "category": _E[tid][0], "playbook_note": note, "task_goal": goal, "constraints": constraints,
           "allowed_tools": ALL_TOOLS_V3, "solver": {"kind": kind, "params": params}, "final_answer_requirements": far,
           "initial_state_assumptions": ["Baseline state: no new bookings, no cancellations, no new waitlist entries.", *assumptions]}
    if prohibited:
        out["prohibited_actions"] = prohibited
    out["initial_state_checks"] = checks or []
    return out


def _st(pnr: str, **expect) -> dict:
    return {"tool": "get_booking_status", "args": {"pnr": pnr}, "expect": expect}


SPECS: list[dict] = [
    _spec("T76", "3.0 batch. Read-only status lookup of a waitlisted PNR. Selection: get_booking_status, not a cancellation or a refund quote.",
          "Report status and waitlist position of PNR 7302958146.", [{"kind": "objective", "value": "booking_status_and_waitlist_position"}, {"kind": "pnr", "value": "7302958146"}, {"kind": "no_state_change"}],
          "pnr_status_lookup", {"pnr": "7302958146", "expect_status": "WAITLISTED"}, "success",
          ["status WAITLISTED", "waitlist position"], ["cancel or book anything"],
          ["PNR 7302958146: BTB101 2A, Arjun Malhotra, journey 2026-10-07, WAITLISTED at position 3."],
          [_st("7302958146", status="WAITLISTED", waitlist_position=3)]),
    _spec("T77", "3.0 batch. Refund QUOTE with an explicit 'don't cancel yet'. Selection trap: cancel_ticket also reports the refund but is "
                 "irreversible; only get_cancellation_refund answers the question.",
          "Quote the refund of PNR 4518203967 without cancelling.", [{"kind": "objective", "value": "refund_quote_without_action"}, {"kind": "pnr", "value": "4518203967"}, {"kind": "no_cancellation"}],
          "refund_quote_no_cancel", {"pnr": "4518203967"}, "success", ["refund_inr"], ["cancel the ticket"],
          ["PNR 4518203967: BTB115 3A, Meera Iyer, journey 2026-10-08, CONFIRMED, fare 1800; 3A charge 180."],
          [_st("4518203967", status="CONFIRMED")],
          prohibited=[{"tool": "cancel_ticket", "match": {}, "prompt_phrase": "Don't cancel it yet",
                       "reason": "The user only asks how much would come back and explicitly says not to cancel yet."}]),
    _spec("T78", "3.0 batch. Plain cancellation by PNR, refund reported from the cancellation.",
          "Cancel PNR 9157364820 and report the refund.", [{"kind": "objective", "value": "cancel_and_report_refund"}, {"kind": "pnr", "value": "9157364820"}, {"kind": "cancel"}],
          "cancel_pnr", {"pnr": "9157364820"}, "success", ["cancelled", "refund_inr"], ["book anything"],
          ["PNR 9157364820: BTB120 3A, Sanjay Kulkarni, journey 2026-10-10, CONFIRMED, fare 1460; 3A charge 180."],
          [_st("9157364820", status="CONFIRMED")]),
    _spec("T79", "3.0 batch. Conditional cancellation; the condition FAILS (refund 7360 < 7400), so the quote must come first and nothing may "
                 "be cancelled. Cancelling first and reading the refund afterwards is the irreversible mistake.",
          "Cancel PNR 5079318462 only if the refund is >= 7400.", [{"kind": "objective", "value": "cancel_only_if_refund_reaches_threshold"}, {"kind": "pnr", "value": "5079318462"},
                                                                   {"kind": "min_refund_inr", "value": 7400}],
          "conditional_cancel_refund_too_low", {"pnr": "5079318462", "min_refund_inr": 7400}, "cannot_complete",
          ["refund_inr 7360 is below 7400", "not cancelled"], ["cancel the ticket"],
          ["PNR 5079318462: BTB122 2A, Lakshmi Narayan, journey 2026-10-12, CONFIRMED, fare 7560; 2A charge 200 -> refund 7360."],
          [_st("5079318462", status="CONFIRMED")]),
    _spec("T80", "3.0 batch. Same condition shape as T79 but it HOLDS (495 >= 450): quote first, then cancel.",
          "Cancel PNR 6720483915 if the refund is >= 450.", [{"kind": "objective", "value": "cancel_only_if_refund_reaches_threshold"}, {"kind": "pnr", "value": "6720483915"},
                                                             {"kind": "min_refund_inr", "value": 450}],
          "conditional_cancel_refund_enough", {"pnr": "6720483915", "min_refund_inr": 450}, "success",
          ["refund_inr 495", "cancelled"], ["book anything"],
          ["PNR 6720483915: BTB127 SL, Vikram Rao, journey 2026-10-08, CONFIRMED, fare 615; SL charge 120 -> refund 495."],
          [_st("6720483915", status="CONFIRMED")]),
    _spec("T81", "3.0 batch. Unknown PNR: the lookup returns PNR_NOT_FOUND; nothing else is possible.",
          "Status of a PNR that does not exist.", [{"kind": "objective", "value": "status_of_unknown_pnr"}, {"kind": "pnr", "value": "5551234567"}],
          "pnr_not_found", {"pnr": "5551234567"}, "cannot_complete", ["no booking with this PNR"], ["invent a status"],
          ["No booking has PNR 5551234567."], equivalent=[
              "A get_cancellation_refund or cancel_ticket call returning PNR_NOT_FOUND for 5551234567 grounds the answer as well."]),
    _spec("T82", "3.0 batch. The ticket was already cancelled before 'now': cancel_ticket returns ALREADY_CANCELLED (or the status shows it). "
                 "Reporting that it is already cancelled as a completed request is accepted too.",
          "Cancel PNR 2894017356, which is already cancelled.", [{"kind": "objective", "value": "cancel_request_on_cancelled_ticket"}, {"kind": "pnr", "value": "2894017356"}],
          "cancel_already_cancelled", {"pnr": "2894017356", "expected_error": "ALREADY_CANCELLED"}, "cannot_complete",
          ["already cancelled"], ["claim a new cancellation or refund"],
          ["PNR 2894017356: BTB104 2A, Rohit Bansal, journey 2026-10-09, already CANCELLED."],
          [_st("2894017356", status="CANCELLED")],
          alternatives=["success with nothing changed: telling the user the ticket is already cancelled is also correct."],
          equivalent=["get_booking_status(2894017356) showing status CANCELLED, or get_cancellation_refund returning ALREADY_CANCELLED, "
                      "grounds the answer as well as cancel_ticket."]),
    _spec("T83", "3.0 batch. Today's train has already left its origin (BTB125 left Ahmedabad at 06:20; now is 09:00): the ticket can no "
                 "longer be cancelled (JOURNEY_STARTED).",
          "Cancel PNR 8803164527 for a train that has already left.", [{"kind": "objective", "value": "cancel_request_after_departure"}, {"kind": "pnr", "value": "8803164527"}],
          "cancel_after_departure", {"pnr": "8803164527", "expected_error": "JOURNEY_STARTED"}, "cannot_complete",
          ["cannot be cancelled after departure"], ["claim a refund"],
          ["PNR 8803164527: BTB125 CC, Harsh Vora, journey 2026-10-05 (today), CONFIRMED; BTB125 left ADI at 06:20."],
          [_st("8803164527", status="CONFIRMED", journey_date="2026-10-05")],
          equivalent=["get_cancellation_refund(8803164527) returning JOURNEY_STARTED grounds the answer as well as cancel_ticket."]),
    _spec("T84", "3.0 batch. Booking with an explicit waitlist fallback. 2A on BTB101 is sold out (3 already waiting): join the waitlist "
                 "(position 4), not another class or train.",
          "Book 2A on BTB101 NDLS->MMCT on 2026-10-08 for Kiran Desai; if full, waitlist.",
          [{"kind": "objective", "value": "book_else_waitlist"}, {"kind": "train_id", "value": "BTB101"}, {"kind": "route", "source": "New Delhi", "destination": "Mumbai"},
           {"kind": "date", "value": "2026-10-08"}, {"kind": "travel_class", "value": "2A"}, {"kind": "passenger", "value": "Kiran Desai"},
           {"kind": "fallback", "value": "waitlist"}],
          "waitlist_fallback_booking", {"train_id": "BTB101", "source_name": "New Delhi", "destination_name": "Mumbai", "date": "2026-10-08",
                                        "travel_class": "2A", "passenger": "Kiran Desai"}, "success",
          ["waitlisted", "waitlist position 4"], ["book another class or train", "claim a confirmed booking"],
          ["BTB101 2A has 0 seats; 3 people already on its waitlist."],
          [{"tool": "check_availability", "args": {"train_id": "BTB101", "travel_class": "2A"}, "expect": {"seats_available": 0}}],
          equivalent=["A rejected book_ticket(BTB101, 2A) returning SOLD_OUT grounds the fallback as well as check_availability."]),
    _spec("T85", "3.0 batch. Same situation shape as T84 (sold out) but the user REFUSES the waitlist: report, change nothing.",
          "Book 3A on BTB109 NDLS->LKO on 2026-10-07 for Imran Qureshi; no waitlist.",
          [{"kind": "objective", "value": "book_else_report_no_waitlist"}, {"kind": "train_id", "value": "BTB109"}, {"kind": "route", "source": "New Delhi", "destination": "Lucknow"},
           {"kind": "date", "value": "2026-10-07"}, {"kind": "travel_class", "value": "3A"}, {"kind": "passenger", "value": "Imran Qureshi"},
           {"kind": "no_waitlist"}],
          "sold_out_no_waitlist", {"train_id": "BTB109", "source_name": "New Delhi", "destination_name": "Lucknow", "date": "2026-10-07",
                                   "travel_class": "3A", "passenger": "Imran Qureshi"}, "cannot_complete",
          ["3A sold out", "not waitlisted"], ["join the waitlist", "book another class or train"],
          ["BTB109 3A has 0 seats."],
          [{"tool": "check_availability", "args": {"train_id": "BTB109", "travel_class": "3A"}, "expect": {"seats_available": 0}}],
          prohibited=[{"tool": "join_waitlist", "match": {}, "prompt_phrase": "don't put him on the waitlist",
                       "reason": "The user explicitly refuses the waitlist."}],
          equivalent=["A rejected book_ticket(BTB109, 3A) returning SOLD_OUT grounds the answer as well as check_availability."]),
    _spec("T86", "3.0 batch. The waitlist is offered as a fallback, but the condition does not hold (1 SL seat left): just book. Joining the "
                 "waitlist would fail (SEATS_AVAILABLE) and is not what was asked.",
          "Book SL on BTB104 MMCT->NDLS on 2026-10-09 for Asha Menon (waitlist only if sold out).",
          [{"kind": "objective", "value": "book_else_waitlist"}, {"kind": "train_id", "value": "BTB104"}, {"kind": "route", "source": "Mumbai", "destination": "New Delhi"},
           {"kind": "date", "value": "2026-10-09"}, {"kind": "travel_class", "value": "SL"}, {"kind": "passenger", "value": "Asha Menon"},
           {"kind": "fallback", "value": "waitlist"}],
          "waitlist_not_needed_booking", {"train_id": "BTB104", "source_name": "Mumbai", "destination_name": "New Delhi", "date": "2026-10-09",
                                          "travel_class": "SL", "passenger": "Asha Menon"}, "success",
          ["selected_train_id BTB104", "booking_id"], ["join the waitlist"],
          ["BTB104 SL has 1 seat."],
          [{"tool": "check_availability", "args": {"train_id": "BTB104", "travel_class": "SL"}, "expect": {"seats_available": 1}}]),
    _spec("T87", "3.0 batch. Live delay of a train running now. Selection: get_live_train_status, not the timetable (get_train_details).",
          "How late is BTB105 now?", [{"kind": "objective", "value": "current_delay_minutes"}, {"kind": "train_id", "value": "BTB105"}, {"kind": "now"}],
          "live_delay", {"train_id": "BTB105"}, "success", ["delay_minutes 25"], ["report the timetable as the live status"],
          ["BTB105 left NDLS 25 min late today (live_status.json)."]),
    _spec("T88", "3.0 batch. Expected arrival at an INTERMEDIATE stop of the run that started yesterday (scheduled 11:30 + 120 min = 13:30).",
          "Expected arrival of BTB103 (yesterday's run) at Ahmedabad.", [{"kind": "objective", "value": "expected_arrival_at_intermediate_stop"}, {"kind": "train_id", "value": "BTB103"},
                                                                         {"kind": "station", "value": "Ahmedabad"}, {"kind": "now"}],
          "live_expected_arrival_intermediate", {"train_id": "BTB103", "station_name": "Ahmedabad"}, "success",
          ["expected_arrival 13:30"], ["give the scheduled 11:30 as the expected time"],
          ["BTB103 run of 2026-10-04 is 120 min late (live_status.json); ADI scheduled 11:30."]),
    _spec("T89", "3.0 batch. BTB111 runs TUE/THU/SAT; today is Monday: NOT running today.",
          "Does BTB111 run today, and how late?", [{"kind": "objective", "value": "runs_today"}, {"kind": "train_id", "value": "BTB111"}, {"kind": "today"}],
          "live_running_today", {"train_id": "BTB111"}, "success", ["not running today"], ["invent a delay"],
          ["BTB111 operating days TUE, THU, SAT; 2026-10-05 is a Monday."]),
    _spec("T90", "3.0 batch. Connection check: BTB125 is scheduled at Mumbai 13:45 (would make 14:05) but runs 70 min late (14:55): no.",
          "Will BTB125 reach Mumbai before 14:05 today?", [{"kind": "objective", "value": "arrives_before_connection"}, {"kind": "train_id", "value": "BTB125"}, {"kind": "station", "value": "Mumbai"},
                                                          {"kind": "connection_time", "value": "14:05"}],
          "live_connection_check", {"train_id": "BTB125", "station_name": "Mumbai", "connection_time": "14:05"}, "success",
          ["expected_arrival 14:55", "will miss the 14:05 train"], ["answer from the timetable (13:45)"],
          ["BTB125 run of 2026-10-05 is 70 min late; MMCT scheduled 13:45."]),
    _spec("T91", "3.0 batch. Concession fare lookup. Selection: get_concession_fare, not get_fare plus a guessed discount.",
          "Senior citizen 3A fare on BTB115.", [{"kind": "objective", "value": "concession_fare"}, {"kind": "train_id", "value": "BTB115"}, {"kind": "travel_class", "value": "3A"},
                                                {"kind": "concession", "value": "senior_citizen"}],
          "concession_fare", {"train_id": "BTB115", "travel_class": "3A", "concession": "senior_citizen"}, "success",
          ["concession_fare_inr 1080"], ["book anything"], ["BTB115 3A fare 1800; senior citizen 40% in 3A."]),
    _spec("T92", "3.0 batch. One senior + one normal SL ticket: total = 369 + 615 = 984. No booking ('Don't book anything yet').",
          "Total of one senior-citizen and one normal SL ticket on BTB127 PUNE->NGP on 2026-10-09; no booking.",
          [{"kind": "objective", "value": "party_total_with_one_concession"}, {"kind": "train_id", "value": "BTB127"}, {"kind": "route", "source": "Pune", "destination": "Nagpur"},
           {"kind": "date", "value": "2026-10-09"}, {"kind": "travel_class", "value": "SL"}, {"kind": "concession", "value": "senior_citizen"},
           {"kind": "no_booking"}],
          "concession_party_total", {"train_id": "BTB127", "source_name": "Pune", "destination_name": "Nagpur", "date": "2026-10-09",
                                     "travel_class": "SL", "concession": "senior_citizen", "regular_tickets": 1}, "success",
          ["total_fare_inr 984"], ["book anything", "apply the concession to both tickets"],
          ["BTB127 SL fare 615; senior citizen 40% in SL -> 369."],
          prohibited=[{"tool": "book_ticket", "match": {}, "prompt_phrase": "Don't book anything yet",
                       "reason": "The user asks for a price only."}]),
    _spec("T93", "3.0 batch. No student concession in chair car: CONCESSION_NOT_AVAILABLE.",
          "Student CC fare on BTB117 (not offered).", [{"kind": "objective", "value": "concession_fare"}, {"kind": "train_id", "value": "BTB117"}, {"kind": "travel_class", "value": "CC"},
                                                      {"kind": "concession", "value": "student"}],
          "concession_not_available", {"train_id": "BTB117", "travel_class": "CC", "concession": "student"}, "cannot_complete",
          ["no student concession in CC"], ["quote a guessed discount"], ["Student concession exists only in 3A and SL."]),
    _spec("T94", "3.0 batch. Budget check with a small margin: student 3A on BTB120 = 1095 <= 1100 (normal fare 1460 is not affordable).",
          "Can a student afford 3A on BTB120 with ₹1,100?", [{"kind": "objective", "value": "affordable_with_concession"}, {"kind": "train_id", "value": "BTB120"}, {"kind": "travel_class", "value": "3A"},
                                                             {"kind": "concession", "value": "student"}, {"kind": "budget_inr", "value": 1100}],
          "concession_budget_check", {"train_id": "BTB120", "travel_class": "3A", "concession": "student", "budget_inr": 1100}, "success",
          ["yes, concession_fare_inr 1095"], ["book anything"], ["BTB120 3A fare 1460; student 25% -> 1095."]),
    _spec("T95", "3.0 batch. Cancel, then rebook the SAME passenger on the SAME train in SL. Train and passenger come from the booking "
                 "(cancel_ticket returns them); the user gives no name.",
          "Cancel PNR 4073819256 and book its passenger in SL on the same train.",
          [{"kind": "objective", "value": "cancel_then_rebook_other_class"}, {"kind": "pnr", "value": "4073819256"}, {"kind": "cancel"}, {"kind": "travel_class", "value": "SL"},
           {"kind": "same_passenger_same_train"}],
          "cancel_and_rebook_class", {"pnr": "4073819256", "expect_status": "CONFIRMED", "booking_passenger": "Anita Das", "new_class": "SL"},
          "success", ["cancelled", "new booking_id", "refund_inr"], ["book another passenger or train"],
          ["PNR 4073819256: BTB112 3A, Anita Das, journey 2026-10-11, CONFIRMED; BTB112 SL has 36 seats."],
          [_st("4073819256", status="CONFIRMED", passenger="Anita Das")]),
    _spec("T96", "3.0 batch. Status-conditional cancel + rebook: the ticket IS still waitlisted, so check, cancel and book SL on the same train.",
          "If PNR 1385672049 is waitlisted, cancel it and book SL on the same train for its passenger.",
          [{"kind": "objective", "value": "if_waitlisted_cancel_then_rebook"}, {"kind": "pnr", "value": "1385672049"}, {"kind": "condition", "value": "waitlisted"}, {"kind": "travel_class", "value": "SL"},
           {"kind": "same_passenger_same_train"}],
          "conditional_waitlisted_cancel_rebook", {"pnr": "1385672049", "expect_status": "WAITLISTED", "booking_passenger": "Pooja Sharma",
                                      "new_class": "SL", "only_if_waitlisted": True},
          "success", ["was waitlisted", "cancelled", "new booking_id"], ["book another passenger or train"],
          ["PNR 1385672049: BTB103 3A, Pooja Sharma, journey 2026-10-06, WAITLISTED at 2; BTB103 SL has 9 seats."],
          [_st("1385672049", status="WAITLISTED", passenger="Pooja Sharma")],
          equivalent=["get_cancellation_refund(1385672049) showing status WAITLISTED grounds the condition as well as get_booking_status."]),
    _spec("T97", "3.0 batch. Status-conditional cancel whose condition FAILS (CONFIRMED): leave it; the request is completed by checking.",
          "If PNR 6043721985 is waitlisted cancel it, if confirmed leave it.", [{"kind": "objective", "value": "if_waitlisted_cancel_else_keep"}, {"kind": "pnr", "value": "6043721985"},
                                                                               {"kind": "condition", "value": "waitlisted"}],
          "conditional_waitlisted_noop", {"pnr": "6043721985"}, "success", ["status CONFIRMED", "left as it is"], ["cancel the ticket"],
          ["PNR 6043721985: BTB111 SL, Kavita Joshi, journey 2026-10-06, CONFIRMED."],
          [_st("6043721985", status="CONFIRMED")],
          equivalent=["get_cancellation_refund(6043721985) showing status CONFIRMED grounds the answer as well as get_booking_status."]),
    _spec("T98", "3.0 batch. Cancellation without a PNR: no tool can list the user's bookings, so ask for the PNR; call nothing, cancel nothing.",
          "Cancel 'my ticket for tomorrow' (no PNR).", [{"kind": "objective", "value": "cancel_without_reference"}, {"kind": "missing", "value": "pnr"}],
          "cancel_without_pnr_clarification", {"missing": "pnr"}, "needs_clarification", ["asks for the PNR"],
          ["cancel any ticket", "guess a PNR"], ["No tool lists bookings; every booking tool needs a PNR."]),
    _spec("T99", "3.0 batch. Two cancellations and a total refund (600 + 600 = 1200).",
          "Cancel PNRs 2951847306 and 2951847314; total refund.", [{"kind": "objective", "value": "cancel_several_total_refund"}, {"kind": "pnrs", "value": ["2951847306", "2951847314"]}, {"kind": "cancel"}],
          "cancel_multiple_total_refund", {"pnrs": ["2951847306", "2951847314"]}, "success", ["both cancelled", "refund_inr 1200"],
          ["book anything"], ["Both PNRs: BTB116 SL, journey 2026-10-09, CONFIRMED, fare 720; SL charge 120."],
          [_st("2951847306", status="CONFIRMED"), _st("2951847314", status="CONFIRMED")]),
    _spec("T100", "3.0 batch. Two read-only intents on one train: 3A availability AND the senior citizen 3A fare.",
          "3A seats on BTB120 and senior citizen 3A fare.", [{"kind": "objective", "value": "availability_and_concession_fare"}, {"kind": "train_id", "value": "BTB120"}, {"kind": "travel_class", "value": "3A"},
                                                             {"kind": "concession", "value": "senior_citizen"}],
          "availability_and_concession", {"train_id": "BTB120", "travel_class": "3A", "concession": "senior_citizen"}, "success",
          ["seats_available 33", "concession_fare_inr 876"], ["book anything"], ["BTB120 3A: 33 seats, fare 1460; senior 40% -> 876."],
          [{"tool": "check_availability", "args": {"train_id": "BTB120", "travel_class": "3A"}, "expect": {"seats_available": 33}}]),
]


def write_specs(path: Path | None = None) -> None:
    """(Re)write the T76-T100 entries of semantic_tasks.json; the frozen T01-T75 entries are kept as they are."""
    path = path or Path(__file__).resolve().parent / "semantic_tasks.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    keep = [t for t in data["tasks"] if int(t["semantic_task_id"][1:]) <= 75]
    data["benchmark_version"] = "3.0.0"
    data["stage"] = "frozen_T01_T75_plus_draft_T76_T100_five_languages"
    data["tasks"] = keep + SPECS
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(keep)} frozen + {len(SPECS)} batch-5 tasks)")


if __name__ == "__main__":
    write_specs()
