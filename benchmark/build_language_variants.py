"""Writes the DRAFT Hinglish / Hindi / Marathi variants (pilot T01-T05 + batch T06-T15), and the English batch rows.
Run: python -m benchmark.build_language_variants

Only `query` (+ a script tag) differs from the English item; every other field is copied from en.jsonl, and the
shared gold is untouched. The frozen pilot English rows (T01-T05) are never rewritten: they are copied byte-for-byte;
only the batch English rows (from benchmark/batch_t06_t15.py) are (re)written after them. All non-English items are
Claude-generated drafts. Review fields come from benchmark/human_review.py (reviewed items), all other rows stay "draft".
"""
from __future__ import annotations

import json
from pathlib import Path

from . import human_review as _hr
from . import batch_t06_t15 as _b1
from . import batch_t16_t25 as _b2
from . import batch_t26_t50 as _b3
from . import batch_t51_t75 as _b4
from . import batch_gujarati as _gu
from .batch_t06_t15 import BATCH_IDS, EN_AUTHOR as BATCH_EN_AUTHOR, EN_ITEMS as BATCH_EN_ITEMS, QUERIES as BATCH_QUERIES

BATCHES = [_b1, _b2, _b3, _b4]  # appended in this order after the frozen pilot rows

LANG_DIR = Path(__file__).resolve().parent / "languages"
PILOT_IDS = ["T01", "T02", "T03", "T04", "T05"]
ALL_TOOLS = ["resolve_station", "search_trains", "get_train_details", "check_availability", "get_fare", "book_ticket"]
AUTHOR = "Claude-generated draft"
SCRIPT_TAG = {"hinglish": "romanized", "hi": "devanagari", "mr": "devanagari", "gu": "gujarati"}

QUERIES: dict[str, dict[str, str]] = {
    "hinglish": {
        "T01": "Train BTB103 mein 2A class ka fare kitna hai?",
        "T02": "7 October 2026 ko Nagpur se Pune jaane wali ek hi train mein 3A ki seat available hai kya? Saath hi 3A ka fare bhi bata dijiye.",
        "T03": "Mujhe 8 October 2026 ko Jaipur se Ahmedabad ka 3A ticket chahiye. Mujhe shaam 6 baje ya uske baad nikalna hai, ₹3,000 se zyada nahi lagna chahiye, aur seats available honi chahiye. Kaun si train sahi rahegi? Kuch bhi book mat karna, bas train bata do.",
        "T04": "7 October 2026 ko Mumbai se Pune ke liye sabse sasta sleeper (SL) ticket Ananya Kulkarni ke naam par book kar do.",
        "T05": "Train BTB103 mein Vikram Singh ke liye 3A ticket book karo, lekin sirf tab jab seats available hon. "
               "Agar 3A sold out ho, to kisi aur class ya kisi aur train mein book mat karna, bas mujhe bata dena.",
    },
    "hi": {
        "T01": "ट्रेन BTB103 में 2A क्लास का किराया कितना है?",
        "T02": "7 अक्टूबर 2026 को नागपुर से पुणे जाने वाली एकमात्र ट्रेन में 3A की सीट उपलब्ध है या नहीं? साथ ही 3A का किराया भी बताइए।",
        "T03": "मुझे 8 अक्टूबर 2026 को जयपुर से अहमदाबाद के लिए 3A का टिकट चाहिए। मुझे शाम 6 बजे या उसके बाद निकलना है, किराया ₹3,000 से ज़्यादा नहीं होना चाहिए, और सीटें उपलब्ध होनी चाहिए। कौन-सी ट्रेन ठीक रहेगी? कुछ भी बुक मत कीजिए, बस ट्रेन बता दीजिए।",
        "T04": "7 अक्टूबर 2026 को मुंबई से पुणे के लिए सबसे सस्ता स्लीपर (SL) टिकट Ananya Kulkarni के नाम से बुक कीजिए।",
        "T05": "ट्रेन BTB103 में Vikram Singh के लिए 3A का टिकट बुक कीजिए, लेकिन केवल तभी जब सीटें उपलब्ध हों। "
               "अगर 3A सोल्ड आउट हो, तो किसी दूसरी क्लास या दूसरी ट्रेन में बुक मत कीजिए, बस मुझे बता दीजिए।",
    },
    "mr": {
        "T01": "ट्रेन BTB103 मध्ये 2A क्लासचे भाडे किती आहे?",
        "T02": "7 ऑक्टोबर 2026 रोजी नागपूरहून पुण्याला जाणाऱ्या एकमेव ट्रेनमध्ये 3A सीट उपलब्ध आहे का? भाडेही सांगा.",
        "T03": "मला 8 ऑक्टोबर 2026 रोजी जयपूरहून अहमदाबादला जाण्यासाठी 3A चे तिकीट हवे आहे. मला संध्याकाळी 6 वाजता किंवा त्यानंतर निघायचे आहे, भाडे ₹3,000 पेक्षा जास्त नसावे आणि सीट उपलब्ध असावी. या अटी पूर्ण करणारी ट्रेन कोणती? काहीही बुक करू नका; फक्त ट्रेन सांगा.",
        "T04": "7 ऑक्टोबर 2026 रोजी मुंबईहून पुण्याला जाणारे सर्वात स्वस्त स्लीपर (SL) तिकीट Ananya Kulkarni यांच्या नावाने बुक करा.",
        "T05": "ट्रेन BTB103 मध्ये Vikram Singh यांच्यासाठी 3A चे तिकीट फक्त सीट उपलब्ध असेल तरच बुक करा. 3A सीट उपलब्ध नसतील, तर दुसऱ्या कोणत्याही क्लासमध्ये किंवा दुसऱ्या ट्रेनमध्ये तिकीट बुक करू नका; फक्त मला सांगा.",
    },
}


for _b in BATCHES:  # batch drafts appended after the pilot drafts (pilot entries unchanged)
    for _lang, _qs in _b.QUERIES.items():
        QUERIES[_lang].update(_qs)


def write_english() -> None:
    """Keep the 5 frozen pilot lines byte-identical; (re)write only the batch rows after them."""
    lines = (LANG_DIR / "en.jsonl").read_text(encoding="utf-8").splitlines(keepends=True)
    pilot = [l for l in lines if json.loads(l)["semantic_task_id"] in PILOT_IDS]
    assert [json.loads(l)["semantic_task_id"] for l in pilot] == PILOT_IDS
    batch = [json.dumps({"task_id": f"{t}_en", "semantic_task_id": t, "language": "en", "query": b.EN_ITEMS[t]["query"],
                         "category": b.EN_ITEMS[t]["category"], "allowed_tools": ALL_TOOLS, "tags": b.EN_ITEMS[t]["tags"],
                         "author": b.EN_AUTHOR, "reviewer": None, "review_status": "draft"}, ensure_ascii=False) + "\n"
             for b in BATCHES for t in b.BATCH_IDS]
    (LANG_DIR / "en.jsonl").write_text("".join(pilot + batch), encoding="utf-8")
    print(f"wrote en.jsonl ({len(pilot)} frozen pilot + {len(batch)} batch items)")


def main() -> None:
    write_english()
    en = [json.loads(l) for l in (LANG_DIR / "en.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    for lang, qs in QUERIES.items():
        rows = []
        for e in en:
            tid = e["semantic_task_id"]
            rows.append({"task_id": f"{tid}_{lang}", "semantic_task_id": tid, "language": lang, "query": qs[tid],
                         "category": e["category"], "allowed_tools": e["allowed_tools"],
                         "tags": [*e["tags"], SCRIPT_TAG[lang]], "author": AUTHOR,
                         "reviewer": _hr.expected_review(lang, tid)[0], "review_status": _hr.expected_review(lang, tid)[1]})
        (LANG_DIR / f"{lang}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
        print(f"wrote {lang}.jsonl ({len(rows)} items)")


def write_gujarati() -> None:
    """gu.jsonl: one row per task in batch_gujarati.GU_IDS (T01-T50 so far), in English order. Every field except the query and
    the script tag is copied from en.jsonl; the four existing language files are not read for text and never written here."""
    en = [json.loads(l) for l in (LANG_DIR / "en.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [{"task_id": f"{e['semantic_task_id']}_gu", "semantic_task_id": e["semantic_task_id"], "language": "gu",
             "query": _gu.QUERIES[e["semantic_task_id"]], "category": e["category"], "allowed_tools": e["allowed_tools"],
             "tags": [*e["tags"], SCRIPT_TAG["gu"]], "author": _gu.AUTHOR,
             "reviewer": _hr.expected_review("gu", e["semantic_task_id"])[0], "review_status": _hr.expected_review("gu", e["semantic_task_id"])[1]}
            for e in en if e["semantic_task_id"] in _gu.GU_IDS]
    (LANG_DIR / "gu.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"wrote gu.jsonl ({len(rows)} items)")


if __name__ == "__main__":
    main()
    write_gujarati()
