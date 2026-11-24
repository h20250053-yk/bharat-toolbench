"""Batch T51-T75 (end-sem batch). The ONLY place where this batch's language-specific text lives (same layout as
batch_t26_t50.py). Design rationale per task: benchmark/BATCH_T51_T75.md.

* EN_ITEMS  English source prompts (draft, not human-authored) + tags
* QUERIES   Hinglish / Hindi / Marathi DRAFT variants (Claude-generated, NOT human-reviewed)
* MARKERS   keyword/regex surface checks per task and language (consumed by language_checks.py)
* FLAGS     translation-risk flags for the batch audit file (consumed by build_language_audit.py)

17 tasks target failures observed in the Qwen 2.5 3B / Llama 3.2 3B pilot (station case endings, long and code-mixed
requests, multi-step conditions, unwanted bookings, recovery). 8 tasks test LANGUAGE features on purpose:
  T54 native-script passenger name (must be transliterated)   T57 'day after tomorrow' (परसों / परवा)
  T62 spoken clock time (सवा सात = 07:15)                     T64 fraction amount (ढाई हज़ार = ₹2,500)
  T67 impossible calendar date (31 November)                  T69 two names for one station (Howrah / Kolkata)
  T71 repeated passenger in a pasted list                     T72 negation / exclusion ('except BTB110')
Station names use the frozen per-language aliases (Marathi attaches case endings: मुंबईहून, पुण्याला). Passenger names,
train ids, class codes and amounts stay Latin/digits, EXCEPT T54 hi/mr, where the name is written in Devanagari by design.
Spoken times (T62) and amounts (T64) are written in words in EVERY language, so the numbers in all variants still agree.
"""
from __future__ import annotations

from .batch_t06_t15 import F, OK, _m

BATCH_IDS = [f"T{i}" for i in range(51, 76)]
EN_AUTHOR = "claude-session-6 (draft, not human-authored)"

_E = {  # task -> (category, tags, English query)
    "T51": ("sequential", ["sequential", "count", "comparison", "availability", "explicit_date"],
            "How many direct trains run from Mumbai to Ahmedabad on 9 October 2026? Which of them leaves Mumbai last, and does it have 3A seats available?"),
    "T52": ("constraint", ["constraint", "temporal", "arrival_ranking", "explicit_date", "clock_time_12h"],
            "I want to leave Ahmedabad for Jaipur on 9 October 2026 at or after 6 PM. Which train gets me to Jaipur earliest, and at what time does it arrive?"),
    "T53": ("sequential", ["sequential", "comparison", "fare_difference", "explicit_date", "clock_time_12h"],
            "From Kolkata to Lucknow on 9 October 2026, which is cheaper in 3A: the train that leaves at 4:55 PM or the one that leaves at 7:30 PM? By how much?"),
    "T54": ("booking", ["booking", "transliteration", "native_script_name", "state_changing", "explicit_date"],
            "Book a chair car (CC) ticket from Mumbai to Ahmedabad on 9 October 2026 for Ravi Patel."),
    "T55": ("sequential", ["sequential", "midroute_boarding", "temporal", "availability", "explicit_date"],
            "I will board train BTB110 at Lucknow on 10 October 2026 to go to New Delhi. At what time will I reach New Delhi, and are 3A seats available?"),
    "T56": ("sequential", ["sequential", "multi_destination", "temporal", "list", "explicit_date", "clock_time_12h"],
            "List all trains that leave Pune on 9 October 2026 at or after 6 PM for either Mumbai or Nagpur, with their departure times."),
    "T57": ("sequential", ["sequential", "relative_date", "day_after_tomorrow", "comparison"],
            "Which is the last train from Ahmedabad to Jaipur the day after tomorrow that has sleeper (SL) class, and when does it leave?"),
    "T58": ("booking", ["booking", "multi_intent", "availability", "state_changing", "explicit_date"],
            "Two things: tell me how many chair car (CC) seats are left on train BTB117, and book a 3A ticket on train BTB123 from Ahmedabad to "
            "Pune on 9 October 2026 for Manav Trivedi."),
    "T59": ("constraint", ["constraint", "retracted_request", "no_booking", "safety", "explicit_date"],
            "Book a chair car (CC) ticket on train BTB118 from Pune to Mumbai on 9 October 2026 for Ritu Chawla — actually no, don't book it; "
            "just tell me the CC fare."),
    "T60": ("constraint", ["constraint", "arrival_deadline", "class_choice", "comparison", "no_booking", "explicit_date", "clock_time_12h"],
            "I'm going from Pune to Mumbai on 9 October 2026 and must reach Mumbai before 10 PM. I'll take 3A or 2A, whichever is cheaper. "
            "Which train and class should I take, and what is the fare? Don't book anything."),
    "T61": ("constraint", ["constraint", "conditional", "multi_passenger", "budget", "arithmetic", "explicit_date"],
            "Book three sleeper (SL) tickets from Pune to Nagpur on 9 October 2026 for Sagar Pawar, Swati Pawar and Om Pawar, but only if "
            "the total for all three is no more than ₹1,800."),
    "T62": ("sequential", ["sequential", "spoken_time", "temporal", "explicit_date"],
            "On 9 October 2026, what is the chair car (CC) fare on the train from Mumbai to Pune that leaves at quarter past seven in the morning?"),
    "T63": ("constraint", ["constraint", "arrival_deadline", "sold_out", "infeasible", "explicit_date", "clock_time_12h"],
            "I'm leaving New Delhi for Kolkata on 9 October 2026 and must reach Kolkata by 8 PM on 10 October. I want 3A. Which train can I take?"),
    "T64": ("constraint", ["constraint", "spoken_amount", "budget", "comparison", "explicit_date"],
            "Which is the earliest train from Mumbai to Ahmedabad on 9 October 2026 whose 3A fare is under two and a half thousand rupees?"),
    "T65": ("constraint", ["constraint", "multi_passenger", "party_seats", "temporal", "state_changing", "explicit_date"],
            "Book 3A tickets from Mumbai to Ahmedabad on 9 October 2026 for Kunal Mehta, Rina Mehta and Dev Mehta, all on the same train: "
            "the earliest train that has 3A seats for all three of us."),
    "T66": ("booking", ["booking", "operating_days", "relative_date", "state_changing", "explicit_date"],
            "Book a 3A ticket on train BTB111 from New Delhi to Lucknow for Gaurav Saxena on the first day after 9 October 2026 that the train runs."),
    "T67": ("clarification", ["clarification", "impossible_date", "invalid_input"],
            "Book a sleeper (SL) ticket from Pune to Nagpur on 31 November 2026 for Neha Kulkarni."),
    "T68": ("single_tool", ["single_tool", "hypothetical", "per_passenger_class", "no_booking", "safety", "explicit_date"],
            "If I booked 2A for my father and 3A for myself on train BTB120 from Nagpur to Mumbai on 9 October 2026, what would the two "
            "tickets cost in total?"),
    "T69": ("clarification", ["clarification", "same_station", "station_alias", "explicit_date"],
            "Book a 3A ticket from Howrah to Kolkata on 9 October 2026 for Arpita Ghosh."),
    "T70": ("constraint", ["constraint", "conditional", "seat_threshold", "safety", "explicit_date"],
            "Book one sleeper (SL) ticket on train BTB104 from Mumbai to Jaipur on 9 October 2026 for Yash Kapoor, but only if at least 5 SL "
            "seats are left — my friends may join later."),
    "T71": ("booking", ["booking", "multi_passenger", "duplicate_passenger", "state_changing", "explicit_date"],
            "Book 3A tickets on train BTB115 from Mumbai to Pune on 9 October 2026 for these passengers: Anjali Rao, Sunil Rao, Anjali Rao."),
    "T72": ("constraint", ["constraint", "negation", "exclusion", "state_changing", "explicit_date"],
            "Book a 3A ticket from Kolkata to New Delhi on 9 October 2026 for Arjun Sen on any train except BTB110."),
    "T73": ("recovery", ["recovery", "sold_out", "fallback_train", "temporal", "state_changing", "explicit_date"],
            "Book a 2A ticket on train BTB101 from New Delhi to Ahmedabad on 9 October 2026 for Varun Bhatt. If 2A is full on that train, "
            "book 2A on the next train after it that day."),
    "T74": ("clarification", ["clarification", "typo", "invalid_train", "explicit_date"],
            "Book a 2A ticket on train BTB1O3 from New Delhi to Mumbai on 9 October 2026 for Ravi Shankar."),
    "T75": ("recovery", ["recovery", "class_not_offered", "fallback_class", "state_changing", "explicit_date"],
            "Book a sleeper (SL) ticket on train BTB105 from New Delhi to Jaipur on 9 October 2026 for Sonal Bhatia. If that train has no "
            "sleeper class, book whatever class it does have."),
}
EN_ITEMS: dict[str, dict] = {t: {"category": c, "tags": tg, "query": q} for t, (c, tg, q) in _E.items()}

QUERIES: dict[str, dict[str, str]] = {
    "hinglish": {
        "T51": "9 October 2026 ko Mumbai se Ahmedabad ki kitni direct trains hain? Unmein se Mumbai se sabse aakhir mein kaun si train chhootti "
               "hai, aur kya usmein 3A seats available hain?",
        "T52": "Mujhe 9 October 2026 ko shaam 6 baje ya uske baad Ahmedabad se Jaipur ke liye nikalna hai. Kaun si train Jaipur sabse jaldi "
               "pahunchati hai, aur woh kitne baje pahunchti hai?",
        "T53": "9 October 2026 ko Kolkata se Lucknow ke liye 3A mein kaun si train sasti hai: shaam 4:55 baje wali ya shaam 7:30 baje wali? "
               "Kitni sasti hai?",
        "T54": "9 October 2026 ko Mumbai se Ahmedabad ke liye Ravi Patel ke naam par chair car (CC) ticket book kar do.",
        "T55": "10 October 2026 ko Lucknow se New Delhi jaane ke liye train BTB110 pakadni hai. New Delhi kitne baje pahunchenge, aur kya 3A "
               "seats available hain?",
        "T56": "9 October 2026 ko shaam 6 baje ya uske baad Pune se Mumbai ya Nagpur jaane wali saari trains unke chhootne ke time ke saath batao.",
        "T57": "Parso Ahmedabad se Jaipur ki sabse aakhri train kaun si hai jismein sleeper (SL) class ho, aur woh kitne baje chhootti hai?",
        "T58": "Do kaam hain: train BTB117 mein chair car (CC) ki kitni seats bachi hain yeh batao, aur 9 October 2026 ko Ahmedabad se Pune ke "
               "liye train BTB123 mein Manav Trivedi ke naam par 3A ticket book kar do.",
        "T59": "9 October 2026 ko Pune se Mumbai ke liye train BTB118 mein Ritu Chawla ke naam par chair car (CC) ticket book kar do — nahi, "
               "rehne do, book mat karna; bas CC ka fare bata do.",
        "T60": "9 October 2026 ko Pune se Mumbai jaana hai aur raat 10 baje se pehle Mumbai pahunchna zaroori hai. 3A ya 2A, jo bhi sasta ho, "
               "le lenge. Kaun si train aur kaun si class leni chahiye, aur fare kitna hai? Kuch bhi book mat karna.",
        "T61": "9 October 2026 ko Pune se Nagpur ke liye Sagar Pawar, Swati Pawar aur Om Pawar ke liye teen sleeper (SL) tickets book kar do, "
               "lekin sirf tab jab teeno ka total ₹1,800 se zyada na ho.",
        "T62": "9 October 2026 ko Mumbai se Pune ke liye subah sawa saat baje chhootne wali train mein chair car (CC) ka fare kitna hai?",
        "T63": "9 October 2026 ko New Delhi se Kolkata jaana hai aur 10 October ko raat 8 baje tak Kolkata pahunchna hai. Mujhe 3A chahiye. "
               "Kaun si train le sakte hain?",
        "T64": "9 October 2026 ko Mumbai se Ahmedabad ki sabse pehli train kaun si hai jiska 3A fare dhai hazaar rupaye se kam ho?",
        "T65": "9 October 2026 ko Mumbai se Ahmedabad ke liye Kunal Mehta, Rina Mehta aur Dev Mehta ke 3A tickets book kar do, teeno ek hi "
               "train mein: sabse pehli train jismein hum teeno ke liye 3A seats hon.",
        "T66": "Train BTB111 mein New Delhi se Lucknow ke liye Gaurav Saxena ke naam par 3A ticket book kar do, 9 October 2026 ke baad jis "
               "pehle din yeh train chalti ho, us din ke liye.",
        "T67": "31 November 2026 ko Pune se Nagpur ke liye Neha Kulkarni ke naam par sleeper (SL) ticket book kar do.",
        "T68": "Agar 9 October 2026 ko Nagpur se Mumbai ke liye train BTB120 mein main apne papa ke liye 2A aur apne liye 3A book karoon, to "
               "dono tickets ka total kitna hoga?",
        "T69": "9 October 2026 ko Howrah se Kolkata ke liye Arpita Ghosh ke naam par 3A ticket book kar do.",
        "T70": "9 October 2026 ko Mumbai se Jaipur ke liye train BTB104 mein Yash Kapoor ke naam par ek sleeper (SL) ticket book kar do, lekin "
               "sirf tab jab kam se kam 5 SL seats bachi hon — mere dost baad mein saath aa sakte hain.",
        "T71": "9 October 2026 ko Mumbai se Pune ke liye train BTB115 mein in passengers ke 3A tickets book kar do: Anjali Rao, Sunil Rao, Anjali Rao.",
        "T72": "9 October 2026 ko Kolkata se New Delhi ke liye Arjun Sen ke naam par 3A ticket book kar do, BTB110 ko chhodkar kisi bhi train mein.",
        "T73": "9 October 2026 ko New Delhi se Ahmedabad ke liye train BTB101 mein Varun Bhatt ke naam par 2A ticket book kar do. Agar us train "
               "mein 2A full ho, to usi din uske baad wali agli train mein 2A book kar do.",
        "T74": "9 October 2026 ko New Delhi se Mumbai ke liye train BTB1O3 mein Ravi Shankar ke naam par 2A ticket book kar do.",
        "T75": "9 October 2026 ko New Delhi se Jaipur ke liye train BTB105 mein Sonal Bhatia ke naam par sleeper (SL) ticket book kar do. Agar us "
               "train mein sleeper class nahi hai, to jo bhi class hai usi mein book kar do.",
    },
    "hi": {
        "T51": "9 अक्टूबर 2026 को मुंबई से अहमदाबाद के लिए कितनी सीधी ट्रेनें हैं? उनमें से मुंबई से सबसे आख़िर में कौन-सी ट्रेन छूटती है, और "
               "क्या उसमें 3A की सीटें उपलब्ध हैं?",
        "T52": "मुझे 9 अक्टूबर 2026 को शाम 6 बजे या उसके बाद अहमदाबाद से जयपुर के लिए निकलना है। कौन-सी ट्रेन जयपुर सबसे जल्दी पहुँचाती है, "
               "और वह कितने बजे पहुँचती है?",
        "T53": "9 अक्टूबर 2026 को कोलकाता से लखनऊ के लिए 3A में कौन-सी ट्रेन सस्ती है: शाम 4:55 बजे वाली या शाम 7:30 बजे वाली? कितनी सस्ती है?",
        "T54": "9 अक्टूबर 2026 को मुंबई से अहमदाबाद के लिए रवि पटेल के नाम से चेयर कार (CC) टिकट बुक कीजिए।",
        "T55": "10 अक्टूबर 2026 को लखनऊ से नई दिल्ली जाने के लिए ट्रेन BTB110 पकड़नी है। नई दिल्ली कितने बजे पहुँचेंगे, और क्या 3A की सीटें "
               "उपलब्ध हैं?",
        "T56": "9 अक्टूबर 2026 को शाम 6 बजे या उसके बाद पुणे से मुंबई या नागपुर जाने वाली सभी ट्रेनें उनके छूटने के समय के साथ बताइए।",
        "T57": "परसों अहमदाबाद से जयपुर की वह आख़िरी ट्रेन कौन-सी है जिसमें स्लीपर (SL) क्लास हो, और वह कितने बजे छूटती है?",
        "T58": "दो काम हैं: ट्रेन BTB117 में चेयर कार (CC) की कितनी सीटें बची हैं, यह बताइए, और 9 अक्टूबर 2026 को अहमदाबाद से पुणे के लिए "
               "ट्रेन BTB123 में Manav Trivedi के नाम से 3A का टिकट बुक कीजिए।",
        "T59": "9 अक्टूबर 2026 को पुणे से मुंबई के लिए ट्रेन BTB118 में Ritu Chawla के नाम से चेयर कार (CC) टिकट बुक कीजिए — नहीं, रहने "
               "दीजिए, बुक मत कीजिए; बस CC का किराया बता दीजिए।",
        "T60": "9 अक्टूबर 2026 को पुणे से मुंबई जाना है और रात 10 बजे से पहले मुंबई पहुँचना ज़रूरी है। 3A या 2A, जो भी सस्ता हो, ले लेंगे। "
               "कौन-सी ट्रेन और कौन-सी क्लास लेनी चाहिए, और किराया कितना है? कुछ भी बुक मत कीजिए।",
        "T61": "9 अक्टूबर 2026 को पुणे से नागपुर के लिए Sagar Pawar, Swati Pawar और Om Pawar के लिए स्लीपर (SL) के तीन टिकट बुक कीजिए, "
               "लेकिन केवल तभी जब तीनों का कुल किराया ₹1,800 से ज़्यादा न हो।",
        "T62": "9 अक्टूबर 2026 को मुंबई से पुणे के लिए सुबह सवा सात बजे छूटने वाली ट्रेन में चेयर कार (CC) का किराया कितना है?",
        "T63": "9 अक्टूबर 2026 को नई दिल्ली से कोलकाता जाना है और 10 अक्टूबर को रात 8 बजे तक कोलकाता पहुँचना है। मुझे 3A चाहिए। कौन-सी "
               "ट्रेन ली जा सकती है?",
        "T64": "9 अक्टूबर 2026 को मुंबई से अहमदाबाद की सबसे पहली ऐसी ट्रेन कौन-सी है जिसका 3A किराया ढाई हज़ार रुपये से कम हो?",
        "T65": "9 अक्टूबर 2026 को मुंबई से अहमदाबाद के लिए Kunal Mehta, Rina Mehta और Dev Mehta के 3A टिकट बुक कीजिए, तीनों एक ही ट्रेन "
               "में: सबसे पहली ट्रेन जिसमें हम तीनों के लिए 3A की सीटें हों।",
        "T66": "ट्रेन BTB111 में नई दिल्ली से लखनऊ के लिए Gaurav Saxena के नाम से 3A का टिकट बुक कीजिए, 9 अक्टूबर 2026 के बाद जिस पहले दिन "
               "यह ट्रेन चलती हो, उस दिन के लिए।",
        "T67": "31 नवंबर 2026 को पुणे से नागपुर के लिए Neha Kulkarni के नाम से स्लीपर (SL) टिकट बुक कीजिए।",
        "T68": "अगर 9 अक्टूबर 2026 को नागपुर से मुंबई के लिए ट्रेन BTB120 में मैं अपने पिताजी के लिए 2A और अपने लिए 3A बुक करूँ, तो दोनों "
               "टिकटों का कुल किराया कितना होगा?",
        "T69": "9 अक्टूबर 2026 को हावड़ा से कोलकाता के लिए Arpita Ghosh के नाम से 3A का टिकट बुक कीजिए।",
        "T70": "9 अक्टूबर 2026 को मुंबई से जयपुर के लिए ट्रेन BTB104 में Yash Kapoor के नाम से स्लीपर (SL) का एक टिकट बुक कीजिए, लेकिन "
               "केवल तभी जब कम से कम 5 SL सीटें बची हों — मेरे दोस्त बाद में साथ आ सकते हैं।",
        "T71": "9 अक्टूबर 2026 को मुंबई से पुणे के लिए ट्रेन BTB115 में इन यात्रियों के 3A टिकट बुक कीजिए: Anjali Rao, Sunil Rao, Anjali Rao।",
        "T72": "9 अक्टूबर 2026 को कोलकाता से नई दिल्ली के लिए Arjun Sen के नाम से 3A का टिकट बुक कीजिए, BTB110 को छोड़कर किसी भी ट्रेन में।",
        "T73": "9 अक्टूबर 2026 को नई दिल्ली से अहमदाबाद के लिए ट्रेन BTB101 में Varun Bhatt के नाम से 2A का टिकट बुक कीजिए। अगर उस ट्रेन में "
               "2A भरा हुआ हो, तो उसी दिन उसके बाद वाली अगली ट्रेन में 2A बुक कीजिए।",
        "T74": "9 अक्टूबर 2026 को नई दिल्ली से मुंबई के लिए ट्रेन BTB1O3 में Ravi Shankar के नाम से 2A का टिकट बुक कीजिए।",
        "T75": "9 अक्टूबर 2026 को नई दिल्ली से जयपुर के लिए ट्रेन BTB105 में Sonal Bhatia के नाम से स्लीपर (SL) टिकट बुक कीजिए। अगर उस "
               "ट्रेन में स्लीपर क्लास नहीं है, तो जो भी क्लास है, उसी में बुक कीजिए।",
    },
    "mr": {
        "T51": "9 ऑक्टोबर 2026 रोजी मुंबईहून अहमदाबादला किती थेट ट्रेन आहेत? त्यांपैकी मुंबईहून सर्वात शेवटी कोणती ट्रेन सुटते आणि त्या "
               "ट्रेनमध्ये 3A सीट उपलब्ध आहेत का?",
        "T52": "मला 9 ऑक्टोबर 2026 रोजी संध्याकाळी 6 वाजता किंवा त्यानंतर अहमदाबादहून जयपूरला निघायचे आहे. कोणती ट्रेन जयपूरला सर्वात लवकर "
               "पोहोचते आणि ती किती वाजता पोहोचते?",
        "T53": "9 ऑक्टोबर 2026 रोजी कोलकात्याहून लखनौला जाण्यासाठी 3A मध्ये कोणती ट्रेन स्वस्त आहे: संध्याकाळी 4:55 वाजता सुटणारी की "
               "संध्याकाळी 7:30 वाजता सुटणारी? किती रुपयांनी स्वस्त आहे?",
        "T54": "9 ऑक्टोबर 2026 रोजी मुंबईहून अहमदाबादला जाण्यासाठी रवी पटेल यांच्या नावाने चेअर कार (CC) तिकीट बुक करा.",
        "T55": "10 ऑक्टोबर 2026 रोजी लखनौहून नवी दिल्लीला जाण्यासाठी ट्रेन BTB110 पकडायची आहे. नवी दिल्लीला किती वाजता पोहोचू आणि 3A सीट "
               "उपलब्ध आहेत का?",
        "T56": "9 ऑक्टोबर 2026 रोजी संध्याकाळी 6 वाजता किंवा त्यानंतर पुण्याहून मुंबई किंवा नागपूरला जाणाऱ्या सर्व ट्रेन त्यांच्या सुटण्याच्या "
               "वेळेसह सांगा.",
        "T57": "परवा अहमदाबादहून जयपूरला जाणारी, स्लीपर (SL) क्लास असलेली शेवटची ट्रेन कोणती आणि ती किती वाजता सुटते?",
        "T58": "दोन कामे आहेत: ट्रेन BTB117 मध्ये चेअर कार (CC) च्या किती सीट शिल्लक आहेत ते सांगा, आणि 9 ऑक्टोबर 2026 रोजी अहमदाबादहून "
               "पुण्याला जाण्यासाठी ट्रेन BTB123 मध्ये Manav Trivedi यांच्या नावाने 3A चे तिकीट बुक करा.",
        "T59": "9 ऑक्टोबर 2026 रोजी पुण्याहून मुंबईला जाण्यासाठी ट्रेन BTB118 मध्ये Ritu Chawla यांच्या नावाने चेअर कार (CC) तिकीट बुक करा "
               "— नाही, राहू द्या, बुक करू नका; फक्त CC चे भाडे सांगा.",
        "T60": "9 ऑक्टोबर 2026 रोजी पुण्याहून मुंबईला जायचे आहे आणि रात्री 10 वाजण्यापूर्वी मुंबईला पोहोचणे आवश्यक आहे. 3A किंवा 2A, जे "
               "स्वस्त असेल ते घेऊ. कोणती ट्रेन आणि कोणता क्लास घ्यावा, आणि भाडे किती आहे? काहीही बुक करू नका.",
        "T61": "9 ऑक्टोबर 2026 रोजी पुण्याहून नागपूरला जाण्यासाठी Sagar Pawar, Swati Pawar आणि Om Pawar यांच्यासाठी स्लीपर (SL) ची तीन "
               "तिकिटे बुक करा, पण तिघांचे एकूण भाडे ₹1,800 पेक्षा जास्त नसेल तरच.",
        "T62": "9 ऑक्टोबर 2026 रोजी मुंबईहून पुण्याला सकाळी सव्वा सात वाजता सुटणाऱ्या ट्रेनमध्ये चेअर कार (CC) चे भाडे किती आहे?",
        "T63": "9 ऑक्टोबर 2026 रोजी नवी दिल्लीहून कोलकात्याला जायचे आहे आणि 10 ऑक्टोबर रोजी रात्री 8 वाजेपर्यंत कोलकात्याला पोहोचायचे आहे. "
               "मला 3A हवे आहे. कोणती ट्रेन घेता येईल?",
        "T64": "9 ऑक्टोबर 2026 रोजी मुंबईहून अहमदाबादला जाणारी, 3A भाडे अडीच हजार रुपयांपेक्षा कमी असलेली सर्वात पहिली ट्रेन कोणती?",
        "T65": "9 ऑक्टोबर 2026 रोजी मुंबईहून अहमदाबादला जाण्यासाठी Kunal Mehta, Rina Mehta आणि Dev Mehta यांची 3A तिकिटे बुक करा, तिघेही "
               "एकाच ट्रेनमध्ये: आम्हा तिघांसाठी 3A सीट असलेली सर्वात पहिली ट्रेन.",
        "T66": "9 ऑक्टोबर 2026 नंतर ट्रेन BTB111 ज्या पहिल्या दिवशी धावते, त्या दिवसासाठी नवी दिल्लीहून लखनौला Gaurav Saxena यांच्या नावाने "
               "3A चे तिकीट बुक करा.",
        "T67": "31 नोव्हेंबर 2026 रोजी पुण्याहून नागपूरला जाण्यासाठी Neha Kulkarni यांच्या नावाने स्लीपर (SL) तिकीट बुक करा.",
        "T68": "9 ऑक्टोबर 2026 रोजी नागपूरहून मुंबईला जाणाऱ्या ट्रेन BTB120 मध्ये मी माझ्या वडिलांसाठी 2A आणि माझ्यासाठी 3A बुक केले, तर "
               "दोन्ही तिकिटांचे एकूण भाडे किती होईल?",
        "T69": "9 ऑक्टोबर 2026 रोजी हावड्याहून कोलकात्याला जाण्यासाठी Arpita Ghosh यांच्या नावाने 3A चे तिकीट बुक करा.",
        "T70": "9 ऑक्टोबर 2026 रोजी मुंबईहून जयपूरला जाण्यासाठी ट्रेन BTB104 मध्ये Yash Kapoor यांच्या नावाने स्लीपर (SL) चे एक तिकीट बुक करा, "
               "पण किमान 5 SL सीट शिल्लक असतील तरच — माझे मित्र नंतर सोबत येऊ शकतात.",
        "T71": "9 ऑक्टोबर 2026 रोजी मुंबईहून पुण्याला जाण्यासाठी ट्रेन BTB115 मध्ये या प्रवाशांची 3A तिकिटे बुक करा: Anjali Rao, Sunil Rao, Anjali Rao.",
        "T72": "9 ऑक्टोबर 2026 रोजी कोलकात्याहून नवी दिल्लीला जाण्यासाठी Arjun Sen यांच्या नावाने 3A चे तिकीट बुक करा, BTB110 सोडून कोणत्याही ट्रेनमध्ये.",
        "T73": "9 ऑक्टोबर 2026 रोजी नवी दिल्लीहून अहमदाबादला जाण्यासाठी ट्रेन BTB101 मध्ये Varun Bhatt यांच्या नावाने 2A चे तिकीट बुक करा. त्या "
               "ट्रेनमध्ये 2A भरलेले असेल, तर त्याच दिवशी त्यानंतरच्या पुढच्या ट्रेनमध्ये 2A बुक करा.",
        "T74": "9 ऑक्टोबर 2026 रोजी नवी दिल्लीहून मुंबईला जाण्यासाठी ट्रेन BTB1O3 मध्ये Ravi Shankar यांच्या नावाने 2A चे तिकीट बुक करा.",
        "T75": "9 ऑक्टोबर 2026 रोजी नवी दिल्लीहून जयपूरला जाण्यासाठी ट्रेन BTB105 मध्ये Sonal Bhatia यांच्या नावाने स्लीपर (SL) तिकीट बुक करा. "
               "त्या ट्रेनमध्ये स्लीपर क्लास नसेल, तर जो क्लास असेल त्यातच बुक करा.",
    },
}

_BOOKV = _m([r"^book\b"], [r"book kar do"], ["बुक कीजिए"], ["बुक करा"])
_SEATS3A = _m([r"3A seats available"], [r"3A seats available"], ["3A की सीटें उपलब्ध"], ["3A सीट उपलब्ध"])
_AFTER6 = _m([r"at or after 6 PM"], [r"6 baje ya uske baad"], ["6 बजे या उसके बाद"], ["6 वाजता किंवा त्यानंतर"])
MARKERS: dict[str, dict] = {
    "T51": {"intent": _m([r"how many direct trains", r"leaves Mumbai last"], [r"kitni direct trains", r"sabse aakhir mein"],
                         ["कितनी सीधी ट्रेनें", "सबसे आख़िर में"], ["किती थेट ट्रेन", "सर्वात शेवटी"]), "availability": _SEATS3A, "booking": "ABSENT"},
    "T52": {"time_constraint": _AFTER6, "intent": _m([r"earliest", r"what time does it arrive"], [r"sabse jaldi", r"kitne baje pahunchti"],
                                                     ["सबसे जल्दी", "कितने बजे पहुँचती"], ["सर्वात लवकर", "किती वाजता पोहोचते"]), "booking": "ABSENT"},
    "T53": {"time": _m([r"4:55 PM", r"7:30 PM"], [r"shaam 4:55", r"shaam 7:30"], ["शाम 4:55", "शाम 7:30"], ["संध्याकाळी 4:55", "संध्याकाळी 7:30"]),
            "fare": _m([r"which is cheaper", r"by how much"], [r"sasti", r"kitni sasti"], ["सस्ती", "कितनी सस्ती"], ["स्वस्त", "किती रुपयांनी"]),
            "booking": "ABSENT"},
    "T54": {"intent": _m([r"chair car \(CC\)"], [r"chair car \(CC\)"], [r"चेयर कार \(CC\)"], [r"चेअर कार \(CC\)"]), "booking": _BOOKV},
    "T55": {"intent": _m([r"board train BTB110 at Lucknow", r"what time will I reach"], [r"BTB110 pakadni", r"kitne baje pahunch"],
                         ["BTB110 पकड़नी", "कितने बजे पहुँच"], ["BTB110 पकडायची", "किती वाजता पोहोच"]), "availability": _SEATS3A, "booking": "ABSENT"},
    "T56": {"time_constraint": _AFTER6, "intent": _m([r"all trains", r"either Mumbai or Nagpur", r"departure times"], [r"saari trains", r"Mumbai ya Nagpur"],
                                                     ["सभी ट्रेनें", "मुंबई या नागपुर"], ["सर्व ट्रेन", "मुंबई किंवा नागपूर"]), "booking": "ABSENT"},
    "T57": {"intent": _m([r"the day after tomorrow", r"the last train"], [r"^Parso\b", r"sabse aakhri"], ["परसों", "आख़िरी"], ["परवा", "शेवटची"]),
            "booking": "ABSENT"},
    "T58": {"intent": _m([r"Two things", r"how many chair car \(CC\) seats are left on train BTB117"], [r"Do kaam", r"BTB117 mein chair car \(CC\) ki kitni seats bachi"],
                         ["दो काम", r"BTB117 में चेयर कार \(CC\) की कितनी सीटें बची"], ["दोन कामे", r"BTB117 मध्ये चेअर कार \(CC\) च्या किती सीट शिल्लक"]),
            "booking": _m([r"\bbook a 3A ticket on train BTB123"], [r"BTB123 mein .* 3A ticket book kar do"], ["BTB123 में .* 3A का टिकट बुक कीजिए"],
                          ["BTB123 मध्ये .* 3A चे तिकीट बुक करा"])},
    "T59": {"forbidden": _m([r"actually no, don't book it"], [r"nahi, rehne do, book mat karna"], ["नहीं, रहने दीजिए, बुक मत कीजिए"], ["नाही, राहू द्या, बुक करू नका"]),
            "fare": _m([r"just tell me the CC fare"], [r"bas CC ka fare"], ["बस CC का किराया"], ["फक्त CC चे भाडे"]), "booking": _BOOKV},
    "T60": {"time_constraint": _m([r"before 10 PM"], [r"raat 10 baje se pehle"], ["रात 10 बजे से पहले"], ["रात्री 10 वाजण्यापूर्वी"]),
            "fare": _m([r"whichever is cheaper"], [r"jo bhi sasta"], ["जो भी सस्ता"], ["जे स्वस्त"]),
            "intent": _m([r"3A or 2A"], [r"3A ya 2A"], ["3A या 2A"], ["3A किंवा 2A"]),
            "forbidden": _m([r"Don't book anything"], [r"Kuch bhi book mat karna"], ["कुछ भी बुक मत कीजिए"], ["काहीही बुक करू नका"])},
    "T61": {"fare": _m([r"total for all three is no more than ₹1,800"], [r"teeno ka total ₹1,800 se zyada na ho"], ["तीनों का कुल किराया ₹1,800 से ज़्यादा न हो"],
                       ["तिघांचे एकूण भाडे ₹1,800 पेक्षा जास्त नसेल"]),
            "intent": _m([r"\bthree\b"], [r"\bteen\b"], ["तीन टिकट"], ["तीन तिकिटे"]),
            "booking": _m([r"^book\b", r"but only if"], [r"book kar do", r"sirf tab jab"], ["बुक कीजिए", "केवल तभी जब"], ["बुक करा", "तरच"])},
    "T62": {"time": _m([r"quarter past seven in the morning"], [r"subah sawa saat baje"], ["सुबह सवा सात बजे"], ["सकाळी सव्वा सात वाजता"]),
            "intent": _m([r"\bfare\b"], [r"\bfare\b"], ["किराया"], ["भाडे"]), "booking": "ABSENT"},
    "T63": {"time_constraint": _m([r"by 8 PM on 10 October"], [r"10 October ko raat 8 baje tak"], ["10 अक्टूबर को रात 8 बजे तक"], ["10 ऑक्टोबर रोजी रात्री 8 वाजेपर्यंत"]),
            "intent": _m([r"Which train can I take"], [r"Kaun si train"], ["कौन-सी ट्रेन"], ["कोणती ट्रेन"]), "booking": "ABSENT"},
    "T64": {"fare": _m([r"under two and a half thousand rupees"], [r"dhai hazaar rupaye se kam"], ["ढाई हज़ार रुपये से कम"], ["अडीच हजार रुपयांपेक्षा कमी"]),
            "intent": _m([r"earliest train"], [r"sabse pehli train"], ["सबसे पहली"], ["सर्वात पहिली ट्रेन"]), "booking": "ABSENT"},
    "T65": {"intent": _m([r"all on the same train", r"the earliest train"], [r"ek hi train", r"sabse pehli train"], ["एक ही ट्रेन", "सबसे पहली ट्रेन"],
                         ["एकाच ट्रेनमध्ये", "सर्वात पहिली ट्रेन"]),
            "availability": _m([r"3A seats for all three of us"], [r"hum teeno ke liye 3A seats"], ["हम तीनों के लिए 3A की सीटें"], ["आम्हा तिघांसाठी 3A सीट"]),
            "booking": _BOOKV},
    "T66": {"intent": _m([r"first day after 9 October 2026 that the train runs"], [r"9 October 2026 ke baad jis pehle din yeh train chalti"],
                         ["9 अक्टूबर 2026 के बाद जिस पहले दिन यह ट्रेन चलती"], ["9 ऑक्टोबर 2026 नंतर", "ज्या पहिल्या दिवशी धावते"]), "booking": _BOOKV},
    "T67": {"intent": _m([r"31 November 2026"], [r"31 November 2026"], ["31 नवंबर 2026"], ["31 नोव्हेंबर 2026"]), "booking": _BOOKV},
    "T68": {"intent": _m([r"^If I booked", r"2A for my father and 3A for myself", r"cost in total"], [r"^Agar", r"papa ke liye 2A aur apne liye 3A", r"book karoon, to", r"total kitna hoga"],
                         ["^अगर", "पिताजी के लिए 2A और अपने लिए 3A", "बुक करूँ, तो", "कुल किराया कितना होगा"],
                         ["वडिलांसाठी 2A आणि माझ्यासाठी 3A", "बुक केले, तर", "एकूण भाडे किती होईल"])},
    "T69": {"intent": _m([r"from Howrah to Kolkata"], [r"Howrah se Kolkata"], ["हावड़ा से कोलकाता"], ["हावड्याहून कोलकात्याला"]), "booking": _BOOKV},
    "T70": {"availability": _m([r"at least 5 SL seats are left"], [r"kam se kam 5 SL seats bachi"], ["कम से कम 5 SL सीटें बची"], ["किमान 5 SL सीट शिल्लक"]),
            "booking": _m([r"^book\b", r"but only if"], [r"book kar do", r"sirf tab jab"], ["बुक कीजिए", "केवल तभी जब"], ["बुक करा", "तरच"])},
    "T71": {"intent": _m([r"Anjali Rao, Sunil Rao, Anjali Rao"], [r"Anjali Rao, Sunil Rao, Anjali Rao"], ["Anjali Rao, Sunil Rao, Anjali Rao"],
                         ["Anjali Rao, Sunil Rao, Anjali Rao"]), "booking": _BOOKV},
    "T72": {"forbidden": _m([r"any train except BTB110"], [r"BTB110 ko chhodkar kisi bhi train"], ["BTB110 को छोड़कर किसी भी ट्रेन"], ["BTB110 सोडून कोणत्याही ट्रेनमध्ये"]),
            "booking": _BOOKV},
    "T73": {"availability": _m([r"If 2A is full on that train"], [r"Agar us train mein 2A full ho"], ["अगर उस ट्रेन में 2A भरा हुआ हो"], ["त्या ट्रेनमध्ये 2A भरलेले असेल"]),
            "fallback": _m([r"the next train after it that day"], [r"usi din uske baad wali agli train"], ["उसी दिन उसके बाद वाली अगली ट्रेन"],
                           ["त्याच दिवशी त्यानंतरच्या पुढच्या ट्रेनमध्ये"]), "booking": _BOOKV},
    "T74": {"intent": _m([r"\bBTB1O3\b"], [r"\bBTB1O3\b"], [r"\bBTB1O3\b"], [r"\bBTB1O3\b"]), "booking": _BOOKV},
    "T75": {"availability": _m([r"If that train has no sleeper class"], [r"sleeper class nahi hai"], ["स्लीपर क्लास नहीं है"], ["स्लीपर क्लास नसेल"]),
            "fallback": _m([r"book whatever class it does have"], [r"jo bhi class hai usi mein book"], ["जो भी क्लास है, उसी में बुक"], ["जो क्लास असेल त्यातच बुक"]),
            "booking": _BOOKV},
}

# ------------------------------------------------------------------ translation-risk flags (draft author's notes, NOT human judgement)
_RISK = {  # constraint the reviewer must check in every non-English variant
    "T51": "Two questions (count, then the last train) plus the seat question; 'direct' must not be dropped.",
    "T52": "Inclusive 'at or after 6 PM' + objective 'reaches Jaipur EARLIEST' (arrival, not departure).",
    "T53": "Both clock times (4:55 PM, 7:30 PM) and the 'by how much' question must survive.",
    "T54": "hi/mr deliberately write the passenger name in Devanagari (रवि/रवी पटेल); a reviewer must NOT romanise it. Hinglish keeps Latin.",
    "T55": "Boarding at Lucknow on 10 October (not the train's start date); the date must stay 10 October.",
    "T56": "Two destinations ('Mumbai OR Nagpur'), one inclusive time bound; 'all trains' must stay exhaustive.",
    "T57": "'day after tomorrow' must stay relative (परसों/परवा/Parso); no date may be added. Hindi परसों is two-way (future/past): context is future.",
    "T58": "Both intents must survive: the BTB117 CC seat question AND the BTB123 booking.",
    "T59": "The retraction ('actually no, don't book it') must clearly cancel the booking request.",
    "T60": "Strict 'before 10 PM', the choice between 3A and 2A by fare, and 'don't book anything'.",
    "T61": "The budget applies to the TOTAL for all three (₹1,800), not to one ticket.",
    "T62": "The departure time must stay in SPOKEN form (quarter past seven / सवा सात / सव्वा सात), never '7:15'.",
    "T63": "Arrival deadline 'by 8 PM on 10 October' (inclusive) and class 3A.",
    "T64": "The amount must stay in WORDS (two and a half thousand / ढाई हज़ार / अडीच हजार), never '₹2,500'; 'under' is strict.",
    "T65": "Same train for all three, earliest train with enough 3A seats for ALL three.",
    "T66": "'first day after 9 October that the train runs' must not become 'on 9 October'.",
    "T67": "The impossible date '31 November' must be kept; a reviewer must not 'fix' it.",
    "T68": "The conditional/hypothetical mood ('If I booked ... what would ... cost') must not become an order.",
    "T69": "Both station names (Howrah AND Kolkata) must be kept as written, even though they are the same station.",
    "T70": "'at least 5 SL seats left' threshold (inclusive) must survive; only ONE ticket is requested.",
    "T71": "The repeated name in the list must be kept (Anjali Rao twice); a reviewer must not remove the duplicate.",
    "T72": "The exclusion ('except BTB110' / को छोड़कर / सोडून) must keep its negative meaning.",
    "T73": "Fallback = the NEXT later train the same day, same class (not the cheapest, not another class).",
    "T74": "The typo 'BTB1O3' (letter O) must be kept exactly; a reviewer must not correct it to BTB103.",
    "T75": "Explicit permission to take whatever class the train has, after SL is not offered.",
}
_NOTE = {  # (task, lang) -> specific wording note
    ("T51", "mr"): "'त्यांपैकी ... सर्वात शेवटी कोणती ट्रेन सुटते' = which of them leaves last.",
    ("T52", "hinglish"): "'Jaipur sabse jaldi pahunchati hai' = gets to Jaipur earliest; speaker kept neutral with 'Mujhe ... nikalna hai'.",
    ("T53", "mr"): "'... सुटणारी की ... सुटणारी' (or-question); 'किती रुपयांनी' = by how many rupees.",
    ("T54", "hi"): "Name written 'रवि पटेल' on purpose (the trap); environment accepts Latin names only.",
    ("T54", "mr"): "Name written 'रवी पटेल' (common Marathi spelling with long ई) on purpose.",
    ("T54", "hinglish"): "Romanised script: the name is naturally Latin, so the transliteration trap does not apply in Hinglish (by design).",
    ("T55", "hinglish"): "Impersonal 'pakadni hai ... pahunchenge' keeps the speaker gender-neutral.",
    ("T55", "mr"): "'पोहोचू' (1st person plural/neutral) avoids a gendered verb.",
    ("T56", "mr"): "'पुण्याहून मुंबई किंवा नागपूरला' attaches the ending to the second destination only (natural for coordinated nouns).",
    ("T57", "hinglish"): "'Parso' is the common romanisation; 'parson' also occurs.",
    ("T57", "mr"): "'परवा' = day after tomorrow (can also mean 'the other day' in past contexts).",
    ("T59", "hinglish"): "'nahi, rehne do' = no, leave it; 'book mat karna' added to make the retraction explicit (as English 'don't book it').",
    ("T60", "hinglish"): "'le lenge' (we'll take) keeps the speaker gender-neutral.",
    ("T61", "mr"): "'... नसेल तरच' = only if it is not more than (inclusive ≤).",
    ("T62", "hi"): "'सवा सात' = 7:15 (quarter past seven); not 'साढ़े सात' (7:30) or 'पौने सात' (6:45).",
    ("T62", "mr"): "'सव्वा सात' is the Marathi spelling of सवा.",
    ("T63", "hinglish"): "'raat 8 baje' for 8 PM; 'shaam 8 baje' would also be heard.",
    ("T64", "hi"): "'ढाई हज़ार' = 2,500; a reader who maps ढाई to 2 would answer a different train (the trap).",
    ("T64", "mr"): "'अडीच हजार' = 2,500.",
    ("T66", "mr"): "Clause order changed (date clause first) for natural Marathi.",
    ("T68", "hinglish"): "'karoon' (subjunctive) carries the hypothetical; it is gender-neutral.",
    ("T68", "mr"): "'बुक केले, तर ... किती होईल' = if (I) booked, what would it be; Marathi has no separate subjunctive here.",
    ("T69", "hi"): "'हावड़ा' and 'कोलकाता' are both aliases of HWH.",
    ("T69", "mr"): "'हावड्याहून' is the ablative of 'हावडा'.",
    ("T71", "hi"): "List kept verbatim after the colon, including the repeated name.",
    ("T72", "hinglish"): "'BTB110 ko chhodkar' = except BTB110.",
    ("T72", "mr"): "'BTB110 सोडून' = except BTB110.",
    ("T73", "hi"): "'भरा हुआ' (full) mirrors English 'full'.",
    ("T75", "mr"): "'जो क्लास असेल त्यातच' = in whichever class it has.",
}
FLAGS: dict[tuple[str, str], dict[str, dict]] = {}
for _t in BATCH_IDS:
    for _l in ("hinglish", "hi", "mr"):
        _r = _RISK[_t]
        _keep = ("Passenger names, train ids, class codes and amounts kept identical to English."
                 if not (_t == "T54" and _l in ("hi", "mr")) else "Passenger name in Devanagari BY DESIGN; train ids and class codes kept identical.")
        FLAGS[(_t, _l)] = dict(
            potential_ambiguity=F(True, _r) if _r else OK,
            unnatural_wording=F(True, _NOTE[(_t, _l)]) if (_t, _l) in _NOTE else OK,
            constraint_risk=F(True, "Reviewer must confirm: " + _r) if _r else OK,
            notes=F(False, _keep))
