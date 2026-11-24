"""Batch T26-T50 (internal design phases A: T26-T35, B: T36-T45, C: T46-T50). The ONLY place where this batch's
language-specific text lives (same layout as batch_t06_t15.py / batch_t16_t25.py).

* EN_ITEMS  English source prompts (draft, not human-authored) + tags
* QUERIES   Hinglish / Hindi / Marathi DRAFT variants (Claude-generated, NOT human-reviewed)
* MARKERS   keyword/regex surface checks per task and language (consumed by language_checks.py)
* FLAGS     translation-risk flags for the batch audit file (consumed by build_language_audit.py)

Station names use the frozen per-language aliases; passenger names, train ids, class codes and booking ids stay Latin.
Speaker gender is kept neutral in Hindi/Hinglish/Marathi wherever English is ungendered (impersonal or plural forms).
"""
from __future__ import annotations

from .batch_t06_t15 import F, OK, _m

BATCH_IDS = [f"T{i}" for i in range(26, 51)]
EN_AUTHOR = "claude-session-5 (draft, not human-authored)"

_E = {  # task -> (category, tags, English query)
    "T26": ("single_tool", ["single_tool", "availability"], "How many 3A seats are left on train BTB102?"),
    "T27": ("booking", ["booking", "direct_booking", "state_changing", "explicit_date"],
            "Book a sleeper (SL) ticket on train BTB124 from Pune to Mumbai on 9 October 2026 for Aditi Rao."),
    "T28": ("invalid_input", ["invalid_input", "invalid_train"], "Which stations does train BTB150 stop at?"),
    "T29": ("invalid_input", ["invalid_input", "invalid_class", "no_substitution", "explicit_date"],
            "Book a First AC (1A) ticket on train BTB110 from Kolkata to New Delhi on 9 October 2026 for Suresh Menon."),
    "T30": ("invalid_input", ["invalid_input", "past_date", "explicit_date"],
            "Book a sleeper (SL) ticket from Pune to Nagpur on 2 October 2026 for Rohit Pawar."),
    "T31": ("recovery", ["recovery", "retry_after_error", "explicit_date"],
            "Which is the first train from Bombay Central to Ahmedabad on 9 October 2026?"),
    "T32": ("booking", ["booking", "conditional", "fare_condition", "state_changing", "explicit_date"],
            "Book a 2A ticket on train BTB128 from Nagpur to Pune on 8 October 2026 for Kiran Rao if the 2A fare is under ₹2,000; "
            "otherwise book 3A on the same train."),
    "T33": ("constraint", ["constraint", "multi_passenger", "comparison", "state_changing", "explicit_date"],
            "Book tickets from Mumbai to Pune on 9 October 2026 for Anil Joshi, Sunita Joshi and Rohan Joshi. We will travel together "
            "on the same train in the same class, so choose the cheapest option, in any class, that has seats for all three of us."),
    "T34": ("sequential", ["sequential", "comparison", "duration", "budget", "explicit_date"],
            "Among the trains from Ahmedabad to Mumbai on 10 October 2026 whose 3A fare is at most ₹3,000, which one has the shortest "
            "journey time? Does it have 3A seats available?"),
    "T35": ("booking", ["booking", "relative_date", "state_changing"],
            "Book a sleeper (SL) ticket from New Delhi to Lucknow this Saturday for Deepak Yadav."),
    "T36": ("clarification", ["clarification", "ambiguous_class", "explicit_date"],
            "Book an AC ticket on train BTB112 from Kolkata to Lucknow on 9 October 2026 for Pooja Sen."),
    "T37": ("clarification", ["clarification", "ambiguous_intent", "explicit_date"], "Rahul Verma, BTB110, 2A, Kolkata to New Delhi, 9 October 2026."),
    "T38": ("recovery", ["recovery", "sold_out", "fallback_train", "comparison", "state_changing", "explicit_date"],
            "Book a 3A ticket on train BTB103 from Ahmedabad to Mumbai on 9 October 2026 for Nikhil Bose. If it is full, book 3A on the "
            "cheapest other train on that route that day instead."),
    "T39": ("constraint", ["constraint", "conditional", "operating_days", "explicit_date"],
            "Book a 2A ticket on train BTB111 from New Delhi to Lucknow on 7 October 2026 for Meera Nair, but only if the train runs on that day."),
    "T40": ("sequential", ["sequential", "multi_leg", "connection", "temporal", "explicit_date"],
            "There is no direct train from Lucknow to Jaipur, so I will change at New Delhi on 9 October 2026. I need at least 1 hour to "
            "change trains and want to reach Jaipur as early as possible. Which two trains should I take?"),
    "T41": ("constraint", ["constraint", "multi_leg", "all_or_nothing", "explicit_date"],
            "Book this two-part journey for Sameer Khan: 3A on train BTB119 from Mumbai to Nagpur on 9 October 2026, and then 2A on train "
            "BTB121 from Nagpur to Bengaluru on 11 October 2026. I need both legs, so if either leg can't be booked, don't book anything."),
    "T42": ("booking", ["booking", "multi_passenger", "per_passenger_class", "state_changing", "explicit_date"],
            "Book 2A for my father, Ramesh Gupta, and 3A for me, Ajay Gupta, on train BTB122 from Bengaluru to Nagpur on 9 October 2026."),
    "T43": ("constraint", ["constraint", "arrival_deadline", "budget", "state_changing", "explicit_date"],
            "Book a 3A ticket from Mumbai to Ahmedabad on 9 October 2026 for Tanvi Shah. The train must reach Ahmedabad by 7 AM on "
            "10 October, and the 3A fare must be at most ₹3,000."),
    "T44": ("sequential", ["sequential", "temporal", "overnight", "explicit_date", "clock_time_12h"],
            "If I take the train that leaves New Delhi at 5:20 PM on 9 October 2026 for Kolkata, on what date and at what time will I reach Kolkata?"),
    "T45": ("invalid_input", ["invalid_input", "unsupported_action"], "Please cancel my ticket with booking ID BK0042."),
    "T46": ("clarification", ["clarification", "count_conflict", "multi_passenger", "explicit_date"],
            "Book three sleeper (SL) tickets on train BTB120 from Nagpur to Mumbai on 9 October 2026 for Asha Iyer and Vikram Iyer."),
    "T47": ("booking", ["booking", "disambiguation_by_tool", "state_changing", "explicit_date"],
            "Book a chair car (CC) ticket on train BTB129 from Delhi to Jaipur on 9 October 2026 for Kavita Joshi."),
    "T48": ("booking", ["booking", "multi_passenger", "partial_allowed", "state_changing", "explicit_date"],
            "Book sleeper (SL) tickets on train BTB104 from Jaipur to New Delhi on 9 October 2026 for Leela Das, Arjun Das and Maya Das. "
            "If there aren't enough seats for everyone, book as many as possible, in the order I listed."),
    "T49": ("sequential", ["sequential", "route_property", "state_changing", "explicit_date"],
            "Book a 3A ticket from Mumbai to Pune on 9 October 2026 for Farah Khan, on the train that continues on to Bengaluru."),
    "T50": ("booking", ["booking", "state_dependent", "conditional", "multi_passenger", "state_changing", "explicit_date"],
            "Book a chair car (CC) ticket on train BTB117 from Mumbai to Pune on 9 October 2026 for Imran Sheikh. After that, if a CC seat "
            "is still available, book one for Zoya Ali as well. Then tell me how many CC seats are left."),
}
EN_ITEMS: dict[str, dict] = {t: {"category": c, "tags": tg, "query": q} for t, (c, tg, q) in _E.items()}

QUERIES: dict[str, dict[str, str]] = {
    "hinglish": {
        "T26": "Train BTB102 mein 3A ki kitni seats bachi hain?",
        "T27": "9 October 2026 ko Pune se Mumbai ke liye train BTB124 mein Aditi Rao ke naam par sleeper (SL) ticket book kar do.",
        "T28": "Train BTB150 kin-kin stations par rukti hai?",
        "T29": "9 October 2026 ko Kolkata se New Delhi ke liye train BTB110 mein Suresh Menon ke naam par First AC (1A) ticket book kar do.",
        "T30": "2 October 2026 ko Pune se Nagpur ke liye Rohit Pawar ke naam par sleeper (SL) ticket book kar do.",
        "T31": "9 October 2026 ko Bombay Central se Ahmedabad ki sabse pehli train kaun si hai?",
        "T32": "8 October 2026 ko Nagpur se Pune ke liye train BTB128 mein Kiran Rao ke naam par 2A ticket book kar do, agar 2A ka fare "
               "₹2,000 se kam ho; warna usi train mein 3A book kar do.",
        "T33": "9 October 2026 ko Mumbai se Pune ke liye Anil Joshi, Sunita Joshi aur Rohan Joshi ke tickets book kar do. Hum teeno ek hi "
               "train aur ek hi class mein saath travel karenge, isliye kisi bhi class mein sabse sasta option chuno jismein hum teeno ke liye seats hon.",
        "T34": "10 October 2026 ko Ahmedabad se Mumbai ki un trains mein se jinka 3A fare ₹3,000 ya usse kam hai, kis train ka safar sabse "
               "kam time ka hai? Kya usmein 3A seats available hain?",
        "T35": "Is Saturday ko New Delhi se Lucknow ke liye Deepak Yadav ke naam par sleeper (SL) ticket book kar do.",
        "T36": "9 October 2026 ko Kolkata se Lucknow ke liye train BTB112 mein Pooja Sen ke naam par AC ticket book kar do.",
        "T37": "Rahul Verma, BTB110, 2A, Kolkata se New Delhi, 9 October 2026.",
        "T38": "9 October 2026 ko Ahmedabad se Mumbai ke liye train BTB103 mein Nikhil Bose ke naam par 3A ticket book kar do. Agar woh full "
               "ho, to uski jagah usi din usi route ki sabse sasti dusri train mein 3A book kar do.",
        "T39": "7 October 2026 ko New Delhi se Lucknow ke liye train BTB111 mein Meera Nair ke naam par 2A ticket book kar do, lekin sirf "
               "tab jab train us din chalti ho.",
        "T40": "Lucknow se Jaipur ki koi direct train nahi hai, isliye 9 October 2026 ko New Delhi mein train badalni padegi. Train badalne "
               "ke liye kam se kam 1 ghanta chahiye, aur Jaipur jitni jaldi ho sake pahunchna hai. Kaun si do trains leni chahiye?",
        "T41": "Sameer Khan ke liye yeh do hisson wali yatra book kar do: 9 October 2026 ko Mumbai se Nagpur train BTB119 mein 3A, aur phir "
               "11 October 2026 ko Nagpur se Bengaluru train BTB121 mein 2A. Mujhe dono hisse chahiye, isliye agar koi bhi hissa book na "
               "ho sake, to kuch bhi book mat karna.",
        "T42": "9 October 2026 ko Bengaluru se Nagpur ke liye train BTB122 mein mere papa Ramesh Gupta ke liye 2A aur mere, Ajay Gupta, "
               "ke liye 3A book kar do.",
        "T43": "9 October 2026 ko Mumbai se Ahmedabad ke liye Tanvi Shah ke naam par 3A ticket book kar do. Train 10 October ko subah 7 "
               "baje tak Ahmedabad pahunch jaani chahiye, aur 3A ka fare ₹3,000 ya usse kam hona chahiye.",
        "T44": "Agar 9 October 2026 ko shaam 5:20 baje New Delhi se nikalne wali Kolkata ki train li jaye, to Kolkata kis tareekh ko aur "
               "kitne baje pahunchenge?",
        "T45": "Please meri booking ID BK0042 wali ticket cancel kar do.",
        "T46": "9 October 2026 ko Nagpur se Mumbai ke liye train BTB120 mein Asha Iyer aur Vikram Iyer ke liye teen sleeper (SL) tickets book kar do.",
        "T47": "9 October 2026 ko Delhi se Jaipur ke liye train BTB129 mein Kavita Joshi ke naam par chair car (CC) ticket book kar do.",
        "T48": "9 October 2026 ko Jaipur se New Delhi ke liye train BTB104 mein Leela Das, Arjun Das aur Maya Das ke liye sleeper (SL) "
               "tickets book kar do. Agar sabke liye seats na hon, to jitne ho sakein utne book kar dena, usi order mein jismein maine naam likhe hain.",
        "T49": "9 October 2026 ko Mumbai se Pune ke liye Farah Khan ke naam par 3A ticket book kar do, us train mein jo aage Bengaluru tak jaati hai.",
        "T50": "9 October 2026 ko Mumbai se Pune ke liye train BTB117 mein Imran Sheikh ke naam par chair car (CC) ticket book kar do. Uske "
               "baad, agar CC ki ek seat bhi bachi ho, to Zoya Ali ke liye bhi ek ticket book kar do. Phir batao ki CC ki kitni seats bachi hain.",
    },
    "hi": {
        "T26": "ट्रेन BTB102 में 3A की कितनी सीटें बची हैं?",
        "T27": "9 अक्टूबर 2026 को पुणे से मुंबई के लिए ट्रेन BTB124 में Aditi Rao के नाम से स्लीपर (SL) टिकट बुक कीजिए।",
        "T28": "ट्रेन BTB150 किन-किन स्टेशनों पर रुकती है?",
        "T29": "9 अक्टूबर 2026 को कोलकाता से नई दिल्ली के लिए ट्रेन BTB110 में Suresh Menon के नाम से फर्स्ट एसी (1A) टिकट बुक कीजिए।",
        "T30": "2 अक्टूबर 2026 को पुणे से नागपुर के लिए Rohit Pawar के नाम से स्लीपर (SL) टिकट बुक कीजिए।",
        "T31": "9 अक्टूबर 2026 को बॉम्बे सेंट्रल से अहमदाबाद की सबसे पहली ट्रेन कौन-सी है?",
        "T32": "8 अक्टूबर 2026 को नागपुर से पुणे के लिए ट्रेन BTB128 में Kiran Rao के नाम से 2A का टिकट बुक कीजिए, अगर 2A का किराया "
               "₹2,000 से कम हो; वरना उसी ट्रेन में 3A बुक कीजिए।",
        "T33": "9 अक्टूबर 2026 को मुंबई से पुणे के लिए Anil Joshi, Sunita Joshi और Rohan Joshi के टिकट बुक कीजिए। हम तीनों एक ही ट्रेन "
               "और एक ही क्लास में साथ यात्रा करेंगे, इसलिए किसी भी क्लास में सबसे सस्ता विकल्प चुनिए जिसमें हम तीनों के लिए सीटें हों।",
        "T34": "10 अक्टूबर 2026 को अहमदाबाद से मुंबई की उन ट्रेनों में से जिनका 3A किराया ₹3,000 या उससे कम है, किस ट्रेन का सफ़र "
               "सबसे कम समय का है? क्या उसमें 3A की सीटें उपलब्ध हैं?",
        "T35": "इस शनिवार को नई दिल्ली से लखनऊ के लिए Deepak Yadav के नाम से स्लीपर (SL) टिकट बुक कीजिए।",
        "T36": "9 अक्टूबर 2026 को कोलकाता से लखनऊ के लिए ट्रेन BTB112 में Pooja Sen के नाम से एसी टिकट बुक कीजिए।",
        "T37": "Rahul Verma, BTB110, 2A, कोलकाता से नई दिल्ली, 9 अक्टूबर 2026।",
        "T38": "9 अक्टूबर 2026 को अहमदाबाद से मुंबई के लिए ट्रेन BTB103 में Nikhil Bose के नाम से 3A का टिकट बुक कीजिए। अगर वह भरी "
               "हुई हो, तो उसकी जगह उसी दिन उसी रूट की सबसे सस्ती दूसरी ट्रेन में 3A बुक कीजिए।",
        "T39": "7 अक्टूबर 2026 को नई दिल्ली से लखनऊ के लिए ट्रेन BTB111 में Meera Nair के नाम से 2A का टिकट बुक कीजिए, लेकिन केवल "
               "तभी जब ट्रेन उस दिन चलती हो।",
        "T40": "लखनऊ से जयपुर की कोई सीधी ट्रेन नहीं है, इसलिए 9 अक्टूबर 2026 को नई दिल्ली में ट्रेन बदलनी पड़ेगी। ट्रेन बदलने के लिए "
               "कम से कम 1 घंटा चाहिए, और जयपुर जितनी जल्दी हो सके पहुँचना है। कौन-सी दो ट्रेनें लेनी चाहिए?",
        "T41": "Sameer Khan के लिए यह दो हिस्सों वाली यात्रा बुक कीजिए: 9 अक्टूबर 2026 को मुंबई से नागपुर ट्रेन BTB119 में 3A, और फिर "
               "11 अक्टूबर 2026 को नागपुर से बेंगलुरु ट्रेन BTB121 में 2A। मुझे दोनों हिस्से चाहिए, इसलिए अगर कोई भी हिस्सा बुक न हो "
               "सके, तो कुछ भी बुक मत कीजिए।",
        "T42": "9 अक्टूबर 2026 को बेंगलुरु से नागपुर के लिए ट्रेन BTB122 में मेरे पिताजी Ramesh Gupta के लिए 2A और मेरे, Ajay Gupta, "
               "के लिए 3A बुक कीजिए।",
        "T43": "9 अक्टूबर 2026 को मुंबई से अहमदाबाद के लिए Tanvi Shah के नाम से 3A का टिकट बुक कीजिए। ट्रेन 10 अक्टूबर को सुबह 7 बजे "
               "तक अहमदाबाद पहुँच जानी चाहिए, और 3A का किराया ₹3,000 या उससे कम होना चाहिए।",
        "T44": "अगर 9 अक्टूबर 2026 को शाम 5:20 बजे नई दिल्ली से निकलने वाली कोलकाता की ट्रेन ली जाए, तो कोलकाता किस तारीख़ को और "
               "कितने बजे पहुँचेंगे?",
        "T45": "कृपया बुकिंग आईडी BK0042 वाला मेरा टिकट रद्द कर दीजिए।",
        "T46": "9 अक्टूबर 2026 को नागपुर से मुंबई के लिए ट्रेन BTB120 में Asha Iyer और Vikram Iyer के लिए स्लीपर (SL) के तीन टिकट बुक कीजिए।",
        "T47": "9 अक्टूबर 2026 को दिल्ली से जयपुर के लिए ट्रेन BTB129 में Kavita Joshi के नाम से चेयर कार (CC) टिकट बुक कीजिए।",
        "T48": "9 अक्टूबर 2026 को जयपुर से नई दिल्ली के लिए ट्रेन BTB104 में Leela Das, Arjun Das और Maya Das के लिए स्लीपर (SL) टिकट "
               "बुक कीजिए। अगर सबके लिए सीटें न हों, तो जितने हो सकें उतने टिकट बुक कीजिए, उसी क्रम में जिसमें मैंने नाम लिखे हैं।",
        "T49": "9 अक्टूबर 2026 को मुंबई से पुणे के लिए Farah Khan के नाम से 3A का टिकट बुक कीजिए, उस ट्रेन में जो आगे बेंगलुरु तक जाती है।",
        "T50": "9 अक्टूबर 2026 को मुंबई से पुणे के लिए ट्रेन BTB117 में Imran Sheikh के नाम से चेयर कार (CC) टिकट बुक कीजिए। उसके बाद, "
               "अगर CC की कोई सीट अब भी बची हो, तो Zoya Ali के लिए भी एक टिकट बुक कीजिए। फिर बताइए कि CC की कितनी सीटें बची हैं।",
    },
    "mr": {
        "T26": "ट्रेन BTB102 मध्ये 3A च्या किती सीट शिल्लक आहेत?",
        "T27": "9 ऑक्टोबर 2026 रोजी पुण्याहून मुंबईला जाण्यासाठी ट्रेन BTB124 मध्ये Aditi Rao यांच्या नावाने स्लीपर (SL) तिकीट बुक करा.",
        "T28": "ट्रेन BTB150 कोणकोणत्या स्टेशनांवर थांबते?",
        "T29": "9 ऑक्टोबर 2026 रोजी कोलकात्याहून नवी दिल्लीला जाण्यासाठी ट्रेन BTB110 मध्ये Suresh Menon यांच्या नावाने फर्स्ट एसी (1A) तिकीट बुक करा.",
        "T30": "2 ऑक्टोबर 2026 रोजी पुण्याहून नागपूरला जाण्यासाठी Rohit Pawar यांच्या नावाने स्लीपर (SL) तिकीट बुक करा.",
        "T31": "9 ऑक्टोबर 2026 रोजी बॉम्बे सेंट्रलहून अहमदाबादला जाणारी सर्वात आधी सुटणारी ट्रेन कोणती आहे?",
        "T32": "8 ऑक्टोबर 2026 रोजी नागपूरहून पुण्याला जाण्यासाठी ट्रेन BTB128 मध्ये Kiran Rao यांच्या नावाने 2A चे तिकीट बुक करा, पण 2A चे भाडे ₹2,000 पेक्षा कमी असेल तरच. अन्यथा त्याच ट्रेनमध्ये 3A बुक करा.",
        "T33": "9 ऑक्टोबर 2026 रोजी मुंबईहून पुण्याला जाण्यासाठी Anil Joshi, Sunita Joshi आणि Rohan Joshi यांची तिकिटे बुक करा. आम्ही तिघे एकाच ट्रेनमध्ये आणि एकाच क्लासमध्ये एकत्र प्रवास करणार आहोत. त्यामुळे आम्हा तिघांसाठी सीट उपलब्ध असलेला, कोणत्याही क्लासमधील सर्वात स्वस्त पर्याय निवडा.",
        "T34": "10 ऑक्टोबर 2026 रोजी अहमदाबादहून मुंबईला जाणाऱ्या, ज्यांचे 3A भाडे ₹3,000 किंवा त्यापेक्षा कमी आहे अशा ट्रेनपैकी सर्वात कमी प्रवासाचा वेळ असलेली ट्रेन कोणती? त्या ट्रेनमध्ये 3A सीट उपलब्ध आहेत का?",
        "T35": "या शनिवारी नवी दिल्लीहून लखनौला जाण्यासाठी Deepak Yadav यांच्या नावाने स्लीपर (SL) तिकीट बुक करा.",
        "T36": "9 ऑक्टोबर 2026 रोजी कोलकात्याहून लखनौला जाण्यासाठी ट्रेन BTB112 मध्ये Pooja Sen यांच्या नावाने AC तिकीट बुक करा.",
        "T37": "Rahul Verma, BTB110, 2A, कोलकाता ते नवी दिल्ली, 9 ऑक्टोबर 2026.",
        "T38": "9 ऑक्टोबर 2026 रोजी अहमदाबादहून मुंबईला जाण्यासाठी ट्रेन BTB103 मध्ये Nikhil Bose यांच्या नावाने 3A चे तिकीट बुक करा. त्या ट्रेनमध्ये 3A सीट उपलब्ध नसतील, तर त्याच दिवशी त्याच मार्गावरील इतर ट्रेनपैकी सर्वात स्वस्त ट्रेनमध्ये 3A तिकीट बुक करा.",
        "T39": "7 ऑक्टोबर 2026 रोजी नवी दिल्लीहून लखनौला जाण्यासाठी ट्रेन BTB111 मध्ये Meera Nair यांच्या नावाने 2A चे तिकीट बुक करा, पण ती ट्रेन त्या दिवशी धावत असेल तरच.",
        "T40": "लखनौहून जयपूरला थेट ट्रेन नाही, त्यामुळे 9 ऑक्टोबर 2026 रोजी नवी दिल्लीत ट्रेन बदलावी लागेल. ट्रेन बदलण्यासाठी किमान 1 तास हवा आहे आणि मला जयपूरला शक्य तितक्या लवकर पोहोचायचे आहे. मी कोणत्या दोन ट्रेन घ्याव्यात?",
        "T41": "Sameer Khan यांच्यासाठी हा दोन टप्प्यांचा प्रवास बुक करा: 9 ऑक्टोबर 2026 रोजी मुंबईहून नागपूरला ट्रेन BTB119 मध्ये 3A आणि नंतर 11 ऑक्टोबर 2026 रोजी नागपूरहून बेंगळुरूला ट्रेन BTB121 मध्ये 2A. मला दोन्ही टप्पे हवे आहेत, त्यामुळे दोन्हीपैकी कोणताही एक टप्पा बुक करता येत नसेल तर काहीही बुक करू नका.",
        "T42": "9 ऑक्टोबर 2026 रोजी बेंगळुरूहून नागपूरला जाण्यासाठी ट्रेन BTB122 मध्ये माझ्या वडिलांसाठी, Ramesh Gupta, 2A आणि माझ्यासाठी, Ajay Gupta, 3A बुक करा.",
        "T43": "9 ऑक्टोबर 2026 रोजी मुंबईहून अहमदाबादला जाण्यासाठी Tanvi Shah यांच्या नावाने 3A चे तिकीट बुक करा. ट्रेन 10 ऑक्टोबर रोजी सकाळी 7 वाजेपर्यंत अहमदाबादला पोहोचली पाहिजे आणि 3A चे भाडे ₹3,000 किंवा त्यापेक्षा कमी असावे.",
        "T44": "9 ऑक्टोबर 2026 रोजी संध्याकाळी 5:20 वाजता नवी दिल्लीहून कोलकात्याला जाणारी ट्रेन घेतली, तर मी कोलकात्याला कोणत्या तारखेला आणि किती वाजता पोहोचेन?",
        "T45": "कृपया बुकिंग आयडी BK0042 असलेले माझे तिकीट रद्द करा.",
        "T46": "9 ऑक्टोबर 2026 रोजी नागपूरहून मुंबईला जाण्यासाठी ट्रेन BTB120 मध्ये Asha Iyer आणि Vikram Iyer यांच्यासाठी स्लीपर (SL) ची तीन तिकिटे बुक करा.",
        "T47": "9 ऑक्टोबर 2026 रोजी दिल्लीहून जयपूरला जाण्यासाठी ट्रेन BTB129 मध्ये Kavita Joshi यांच्या नावाने चेअर कार (CC) तिकीट बुक करा.",
        "T48": "9 ऑक्टोबर 2026 रोजी जयपूरहून नवी दिल्लीला जाण्यासाठी ट्रेन BTB104 मध्ये Leela Das, Arjun Das आणि Maya Das यांच्यासाठी स्लीपर (SL) तिकिटे बुक करा. सर्वांसाठी पुरेशा सीट उपलब्ध नसतील, तर मी नावे दिलेल्या क्रमाने जितकी तिकिटे शक्य असतील तितकी बुक करा.",
        "T49": "9 ऑक्टोबर 2026 रोजी मुंबईहून पुण्याला जाण्यासाठी Farah Khan यांच्या नावाने, पुढे बेंगळुरूपर्यंत जाणाऱ्या ट्रेनमध्ये 3A चे तिकीट बुक करा.",
        "T50": "9 ऑक्टोबर 2026 रोजी मुंबईहून पुण्याला जाण्यासाठी ट्रेन BTB117 मध्ये Imran Sheikh यांच्या नावाने चेअर कार (CC) तिकीट बुक करा. त्यानंतर CC ची किमान एक सीट शिल्लक असेल, तर Zoya Ali यांच्यासाठीही एक तिकीट बुक करा. मग CC च्या किती सीट शिल्लक आहेत ते सांगा.",
    },
}

_BOOKV = _m([r"^book\b"], [r"book kar do"], ["बुक कीजिए"], ["बुक करा"])
MARKERS: dict[str, dict] = {
    "T26": {"intent": _m([r"how many", r"seats are left"], [r"kitni seats bachi"], ["कितनी सीटें बची"], ["किती सीट शिल्लक"]), "booking": "ABSENT"},
    "T27": {"intent": _m([r"\bsleeper\b"], [r"\bsleeper\b"], ["स्लीपर"], ["स्लीपर"]), "booking": _BOOKV},
    "T28": {"intent": _m([r"which stations", r"stop at"], [r"kin-kin stations", r"rukti"], ["किन-किन स्टेशनों", "रुकती"], ["कोणकोणत्या स्टेशनांवर", "थांबते"]),
            "booking": "ABSENT"},
    "T29": {"intent": _m([r"First AC \(1A\)"], [r"First AC \(1A\)"], [r"फर्स्ट एसी \(1A\)"], [r"फर्स्ट एसी \(1A\)"]), "booking": _BOOKV},
    "T30": {"intent": _m([r"\bsleeper\b"], [r"\bsleeper\b"], ["स्लीपर"], ["स्लीपर"]), "booking": _BOOKV},
    "T31": {"intent": _m([r"Bombay Central", r"first train"], [r"Bombay Central", r"sabse pehli train"], ["बॉम्बे सेंट्रल", "सबसे पहली ट्रेन"],
                         ["बॉम्बे सेंट्रल", "सर्वात आधी सुटणारी ट्रेन"]), "booking": "ABSENT"},
    "T32": {"fare": _m([r"if the 2A fare is under ₹2,000"], [r"agar 2A ka fare ₹2,000 se kam"], ["अगर 2A का किराया ₹2,000 से कम"], ["2A चे भाडे ₹2,000 पेक्षा कमी"]),
            "fallback": _m([r"otherwise book 3A on the same train"], [r"warna usi train mein 3A"], ["वरना उसी ट्रेन में 3A"], ["अन्यथा त्याच ट्रेनमध्ये 3A"]),
            "booking": _BOOKV},
    "T33": {"fare": _m([r"cheapest option"], [r"sabse sasta option"], ["सबसे सस्ता विकल्प"], ["सर्वात स्वस्त पर्याय"]),
            "availability": _m([r"seats for all three of us"], [r"hum teeno ke liye seats"], ["हम तीनों के लिए सीटें"], ["आम्हा तिघांसाठी सीट"]),
            "intent": _m([r"same train in the same class"], [r"ek hi train aur ek hi class"], ["एक ही ट्रेन और एक ही क्लास"], ["एकाच ट्रेनमध्ये आणि एकाच क्लासमध्ये"]),
            "booking": _m([r"^book\b"], [r"book kar do"], ["बुक कीजिए"], ["बुक करा"])},
    "T34": {"intent": _m([r"shortest journey time"], [r"sabse kam time"], ["सबसे कम समय"], ["सर्वात कमी प्रवासाचा वेळ"]),
            "fare": _m([r"at most ₹3,000"], [r"₹3,000 ya usse kam"], ["₹3,000 या उससे कम"], ["₹3,000 किंवा त्यापेक्षा कमी"]),
            "availability": _m([r"3A seats available"], [r"3A seats available"], ["3A की सीटें उपलब्ध"], ["3A सीट उपलब्ध"]), "booking": "ABSENT"},
    "T35": {"intent": _m([r"this Saturday"], [r"Is Saturday"], ["इस शनिवार"], ["या शनिवारी"]), "booking": _BOOKV},
    "T36": {"intent": _m([r"\bAC ticket\b"], [r"\bAC ticket\b"], ["एसी टिकट"], ["AC तिकीट"]), "booking": _BOOKV},
    "T37": {"intent": _m([r"^Rahul Verma, BTB110, 2A"], [r"^Rahul Verma, BTB110, 2A"], [r"^Rahul Verma, BTB110, 2A"], [r"^Rahul Verma, BTB110, 2A"]), "booking": "ABSENT"},
    "T38": {"availability": _m([r"If it is full"], [r"Agar woh full"], ["अगर वह भरी हुई"], ["3A सीट उपलब्ध नसतील"]),
            "fallback": _m([r"cheapest other train on that route that day"], [r"usi din usi route ki sabse sasti dusri train"], ["उसी दिन उसी रूट की सबसे सस्ती दूसरी ट्रेन"],
                           ["त्याच दिवशी त्याच मार्गावरील इतर ट्रेनपैकी सर्वात स्वस्त ट्रेनमध्ये"]), "booking": _BOOKV},
    "T39": {"forbidden": _m([r"but only if the train runs on that day"], [r"sirf tab jab train us din chalti ho"], ["केवल तभी जब ट्रेन उस दिन चलती हो"],
                            ["ट्रेन त्या दिवशी धावत असेल तरच"]), "booking": _BOOKV},
    "T40": {"time_constraint": _m([r"at least 1 hour"], [r"kam se kam 1 ghanta"], ["कम से कम 1 घंटा"], ["किमान 1 तास"]),
            "intent": _m([r"as early as possible", r"which two trains"], [r"jitni jaldi ho sake", r"do trains"], ["जितनी जल्दी हो सके", "दो ट्रेनें"],
                         ["शक्य तितक्या लवकर", "दोन ट्रेन"]), "booking": "ABSENT"},
    "T41": {"forbidden": _m([r"if either leg can't be booked, don't book anything"], [r"agar koi bhi hissa book na ho sake, to kuch bhi book mat karna"],
                            ["अगर कोई भी हिस्सा बुक न हो सके, तो कुछ भी बुक मत कीजिए"], ["दोन्हीपैकी कोणताही एक टप्पा बुक करता येत नसेल", "काहीही बुक करू नका"]),
            "intent": _m([r"3A on train BTB119", r"2A on train BTB121"], [r"BTB119 mein 3A", r"BTB121 mein 2A"], ["BTB119 में 3A", "BTB121 में 2A"],
                         ["BTB119 मध्ये 3A", "BTB121 मध्ये 2A"]), "booking": _m([r"^book\b"], [r"book kar do"], ["बुक कीजिए"], ["बुक करा"])},
    "T42": {"intent": _m([r"2A for my father, Ramesh Gupta", r"3A for me, Ajay Gupta"], [r"Ramesh Gupta ke liye 2A", r"Ajay Gupta, ke liye 3A"],
                         ["Ramesh Gupta के लिए 2A", "Ajay Gupta, के लिए 3A"], ["Ramesh Gupta, 2A", "Ajay Gupta, 3A"]), "booking": _BOOKV},
    "T43": {"time_constraint": _m([r"by 7 AM on 10 October"], [r"10 October ko subah 7 baje tak"], ["10 अक्टूबर को सुबह 7 बजे तक"], ["10 ऑक्टोबर रोजी सकाळी 7 वाजेपर्यंत"]),
            "fare": _m([r"at most ₹3,000"], [r"₹3,000 ya usse kam"], ["₹3,000 या उससे कम"], ["₹3,000 किंवा त्यापेक्षा कमी"]), "booking": _BOOKV},
    "T44": {"time": _m([r"5:20 PM"], [r"shaam 5:20 baje"], ["शाम 5:20 बजे"], ["संध्याकाळी 5:20"]),
            "intent": _m([r"on what date", r"what time"], [r"kis tareekh", r"kitne baje"], ["किस तारीख़", "कितने बजे"], ["कोणत्या तारखेला", "किती वाजता"]), "booking": "ABSENT"},
    "T45": {"intent": _m([r"\bcancel\b", r"BK0042"], [r"\bcancel\b", r"BK0042"], ["रद्द", "BK0042"], ["रद्द", "BK0042"])},
    "T46": {"intent": _m([r"\bthree\b"], [r"\bteen\b"], ["तीन टिकट"], ["तीन तिकिटे"]), "booking": _BOOKV},
    "T47": {"intent": _m([r"chair car"], [r"chair car"], ["चेयर कार"], ["चेअर कार"]), "booking": _BOOKV},
    "T48": {"fallback": _m([r"book as many as possible, in the order I listed"], [r"jitne ho sakein utne book kar dena, usi order mein"],
                           ["जितने हो सकें उतने टिकट बुक कीजिए, उसी क्रम में"], ["सर्वांसाठी पुरेशा सीट उपलब्ध नसतील", "मी नावे दिलेल्या क्रमाने", "जितकी तिकिटे शक्य असतील तितकी बुक करा"]),
            "availability": _m([r"aren't enough seats for everyone"], [r"sabke liye seats na hon"], ["सबके लिए सीटें न हों"], ["सर्वांसाठी पुरेशा सीट उपलब्ध नसतील"]), "booking": _BOOKV},
    "T49": {"intent": _m([r"continues on to Bengaluru"], [r"aage Bengaluru tak jaati"], ["आगे बेंगलुरु तक जाती"], ["पुढे बेंगळुरूपर्यंत जाणाऱ्या"]), "booking": _BOOKV},
    "T50": {"availability": _m([r"if a CC seat is still available"], [r"agar CC ki ek seat bhi bachi ho"], ["अगर CC की कोई सीट अब भी बची हो"], ["CC ची किमान एक सीट शिल्लक असेल"]),
            "intent": _m([r"how many CC seats are left"], [r"CC ki kitni seats bachi"], ["CC की कितनी सीटें बची"], ["CC च्या किती सीट शिल्लक"]), "booking": _BOOKV},
}

# ------------------------------------------------------------------ translation-risk flags (draft author's notes, NOT human judgement)
_RISK = {  # constraint the reviewer must check in every non-English variant
    "T26": None, "T27": None, "T28": "Train id BTB150 must stay unchanged (it is intentionally invalid).",
    "T29": "'1A' must not be rendered as an existing class (e.g. 2A); 'First AC' is the intended unsupported class.",
    "T30": "The past date (2 October) must be kept; a reviewer must not 'fix' it.",
    "T31": "'Bombay Central' must stay as the user's (unresolvable) name; replacing it with Mumbai Central removes the recovery step.",
    "T32": "Strict 'under/less than ₹2,000' and the else-branch ('otherwise 3A on the same train') must both survive.",
    "T33": "Three passengers, same train AND same class, cheapest option in ANY class with seats for all three: four coupled conditions.",
    "T34": "Fare ceiling (at most ₹3,000, inclusive) + shortest-journey objective + seat question must all survive.",
    "T35": "'this Saturday' must stay relative (no explicit date added); with 'now' = Monday 5 Oct it means 10 Oct.",
    "T36": "'AC' must stay unspecific (not 3A/2A/'AC 3 tier'); the ambiguity is the task.",
    "T37": "No verb may be added (no 'book', no 'check'); the intent ambiguity is the task.",
    "T38": "Fallback = cheapest OTHER train, same route, same day, same class; each qualifier must survive.",
    "T39": "'only if the train runs on that day' is the binding condition.",
    "T40": "At least 1 hour to change (inclusive) + earliest arrival + change at New Delhi; no booking verb.",
    "T41": "All-or-nothing over both legs ('if either ... can't be booked, don't book anything').",
    "T42": "Class-to-passenger binding (father 2A, speaker 3A) must not be swapped.",
    "T43": "Arrival deadline (by 7 AM on 10 October, inclusive) and fare ceiling (at most ₹3,000) both binding.",
    "T44": "Departure 5:20 PM on 9 October; the question asks for the arrival DATE and time.",
    "T45": "Cancellation must stay a cancellation request; booking id BK0042 unchanged.",
    "T46": "'three' tickets vs two names: the count must not be corrected during review.",
    "T47": "'Delhi' must stay generic (as in T09); the train id resolves it.",
    "T48": "Partial booking explicitly allowed, in listed order; order of names must be preserved.",
    "T49": "'continues on to Bengaluru' = the train's route goes beyond Pune to Bengaluru.",
    "T50": "Order (book Imran, then conditionally Zoya) and the final 'seats left' question.",
}
_NOTE = {  # (task, lang) -> specific wording note
    ("T26", "mr"): "'शिल्लक' (remaining) chosen; 'उरलेल्या' is an equally natural alternative.",
    ("T28", "hinglish"): "'kin-kin stations par rukti hai' = which stations does it stop at.",
    ("T29", "hi"): "'फर्स्ट एसी' transliteration; 'प्रथम श्रेणी वातानुकूलित' would be formal.",
    ("T31", "mr"): "'बॉम्बे सेंट्रलहून' attaches the ablative to the unresolvable name; the bare form also appears in the marker check.",
    ("T32", "mr"): "'जर ... तर; नाहीतर ...' conditional; slightly long sentence.",
    ("T33", "mr"): "Relative clause 'असा ... पर्याय ... ज्यात' scopes the seat condition onto the option (intended).",
    ("T34", "hinglish"): "'safar sabse kam time ka' = shortest journey time (not shortest distance).",
    ("T34", "mr"): "Correlative 'ज्या ट्रेनचे ... त्यांपैकी' scopes the fare filter before the ranking (intended).",
    ("T35", "hinglish"): "'Is Saturday' = this Saturday; 'agle Saturday' would be ambiguous (could mean the 17th).",
    ("T35", "mr"): "'या शनिवारी' = this Saturday (not 'पुढच्या शनिवारी').",
    ("T36", "hi"): "'एसी टिकट' is how users colloquially ask; deliberately unspecific.",
    ("T37", "hi"): "Terse comma list kept identical in structure; only the route words are translated.",
    ("T38", "hi"): "'भरी हुई' (full) for 'sold out'; 'सोल्ड आउट' would match earlier tasks but English here says 'full'.",
    ("T40", "hinglish"): "Impersonal 'train badalni padegi' keeps the speaker gender-neutral.",
    ("T41", "hinglish"): "'hisse' (parts) for legs; 'legs' is also common in Hinglish.",
    ("T41", "mr"): "'टप्पे' (stages) for legs.",
    ("T42", "mr"): "Appositive commas around the names mirror English; a reviewer may prefer 'माझे वडील Ramesh Gupta यांच्यासाठी'.",
    ("T44", "hinglish"): "Passive 'train li jaye ... pahunchenge' keeps gender neutral.",
    ("T44", "mr"): "'पोहोचू' (1st person plural/neutral) used to avoid gendered 'पोहोचेन' ambiguity.",
    ("T45", "hinglish"): "'cancel' kept as a loanword.",
    ("T48", "mr"): "'मी नावे दिलेल्या क्रमानेच' = in exactly the order I gave the names.",
    ("T49", "mr"): "Correlative 'जी ट्रेन ... त्या ट्रेनमध्ये' is natural but long.",
    ("T50", "hinglish"): "'agar CC ki ek seat bhi bachi ho' = if even one CC seat remains (= 'still available').",
}
FLAGS: dict[tuple[str, str], dict[str, dict]] = {}
for _t in BATCH_IDS:
    for _l in ("hinglish", "hi", "mr"):
        _r = _RISK[_t]
        FLAGS[(_t, _l)] = dict(
            potential_ambiguity=F(True, _r) if _r else OK,
            unnatural_wording=F(True, _NOTE[(_t, _l)]) if (_t, _l) in _NOTE else OK,
            constraint_risk=F(True, "Reviewer must confirm: " + _r) if _r else OK,
            notes=F(False, "Passenger names, train ids, class codes and amounts kept identical to English."))
