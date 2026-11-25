"""Builds benchmark/languages/pilot_language_audit.json (T01-T05, 20 records) and
benchmark/languages/batch_T06_T15_language_audit.json (T06-T15, 40 records). Run: python -m benchmark.build_language_audit

Per item: automated surface checks (language_checks.py; keyword presence only, NOT human verification) + hand-written
translation-quality flags (potential_ambiguity / unnatural_wording / constraint_risk / notes) + review fields that stay
'pending_human_review'. Flags are deliberately raised rather than silently resolved.
"""
from __future__ import annotations

import json
from pathlib import Path

from environment.state import DATA_DIR

from . import batch_t16_t25 as _b2
from . import batch_t26_t50 as _b3
from . import batch_t51_t75 as _b4
from . import batch_t76_t100 as _b5
from . import batch_gujarati as _gu
from .batch_t06_t15 import BATCH_IDS, FLAGS as BATCH_FLAGS
from .build_gold import load_specs
from .language_checks import LANGS, run_checks
from .validate_tasks import RawOracle

LANG_DIR = Path(__file__).resolve().parent / "languages"
AUDIT_PATH = LANG_DIR / "pilot_language_audit.json"
BATCH_AUDIT_PATH = LANG_DIR / "batch_T06_T15_language_audit.json"
BATCH2_AUDIT_PATH = LANG_DIR / "batch_T16_T25_language_audit.json"
BATCH3_AUDIT_PATH = LANG_DIR / "batch_T26_T50_language_audit.json"
BATCH4_AUDIT_PATH = LANG_DIR / "batch_T51_T75_language_audit.json"
GU_AUDIT_PATH = LANG_DIR / "batch_gu_T01_T50_language_audit.json"
GU2_AUDIT_PATH = LANG_DIR / "batch_gu_T51_T75_language_audit.json"
BATCH5_AUDIT_PATH = LANG_DIR / "batch_T76_T100_language_audit.json"
GU3_AUDIT_PATH = LANG_DIR / "batch_gu_T76_T100_language_audit.json"
PILOT_IDS = ["T01", "T02", "T03", "T04", "T05"]
PENDING = "pending_human_review"
F = lambda flag, detail: {"flag": flag, "detail": detail}  # noqa: E731
OK = F(False, "none identified by the draft author (not a human judgement)")

_INHERIT = ("Availability (seats > 0) is stated explicitly in all four variants ('have seats available' and its equivalent), matching the gold constraint; "
            "a reviewer should confirm it reads as a requirement on the recommended train.")
_EVENING = ("The words shaam/शाम/संध्याकाळी ('evening') were added next to '6' only to make 6 PM unambiguous vs 6 AM; they are not a new constraint, "
            "but a reviewer should confirm they do not read as a window ('in the evening').")

FLAGS: dict[tuple[str, str], dict[str, dict]] = {
    ("T01", "hinglish"): dict(potential_ambiguity=OK, unnatural_wording=OK, constraint_risk=OK, notes=F(False, "'fare' and 'class' kept as English loanwords, as is typical in Hinglish.")),
    ("T01", "hi"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'ट्रेन BTB103' (loanword) chosen over the more formal 'गाड़ी संख्या BTB103'; 'क्लास' vs 'श्रेणी'. Reviewer to confirm register."), constraint_risk=OK, notes=F(False, "Train id and '2A' kept in Latin/digits.")),
    ("T01", "mr"): dict(potential_ambiguity=OK, unnatural_wording=F(True, "'ट्रेन' vs 'गाडी', 'भाडे' vs 'तिकीट दर': register choice for a native Marathi reviewer."), constraint_risk=OK, notes=F(False, "'2A क्लासचे' attaches a Marathi suffix to a Latin token; fine for readers, may tokenise oddly.")),
    ("T02", "hinglish"): dict(potential_ambiguity=F(True, "'ek hi train' renders English 'the only train'; gold relies on exactly one Nagpur->Pune train. Reviewer to confirm it reads as 'the only train' and not as an emphasis on 'just one'."), unnatural_wording=OK, constraint_risk=OK, notes=F(False, "Fare question is split into a second sentence ('Saath hi 3A ka fare...'), mirroring English.")),
    ("T02", "hi"): dict(potential_ambiguity=F(True, "'एकमात्र ट्रेन' = 'the only train' (matches English); reviewer to confirm the register is natural."), unnatural_wording=F(True, "'उपलब्ध है या नहीं?' is slightly formal; colloquial speakers may say 'मिल सकती है क्या?'."), constraint_risk=OK, notes=F(False, "'3A का किराया' used instead of a pronoun to avoid an ambiguous referent.")),
    ("T02", "mr"): dict(potential_ambiguity=F(True, "'एकमेव ट्रेन' = 'the only train' (matches English); reviewer to confirm the register is natural."), unnatural_wording=F(True, "'रोजी' (on the date) is formal/written register; 'ट्रेनमध्ये' fuses postposition."), constraint_risk=OK, notes=F(False, "'3A चे भाडे किती आहे ते सांगा' avoids a gendered pronoun for train/seat.")),
    ("T03", "hinglish"): dict(potential_ambiguity=F(True, "'₹3,000 se zyada nahi lagna chahiye' = fare <= 3000 (intended); confirm it is not read as 'around 3000'."), unnatural_wording=F(True, "'Kuch bhi book mat karna' is a casual imperative; fine for chat, informal for a service."), constraint_risk=F(True, "Inclusive bound rendered as 'shaam 6 baje ya uske baad' (= at or after 6 PM). " + _EVENING + " " + _INHERIT), notes=F(True, "Highest-risk item: time inclusivity, budget bound, seats-available requirement and no-booking all live in one query.")),
    ("T03", "hi"): dict(potential_ambiguity=F(True, "'किराया ₹3,000 से ज़्यादा नहीं होना चाहिए' = fare <= 3000 (intended)."), unnatural_wording=OK, constraint_risk=F(True, "'शाम 6 बजे या उसके बाद' = at or after 6 PM. " + _EVENING + " " + _INHERIT), notes=F(True, "'कौन-सी ट्रेन' singular, mirroring 'Which train'. 'कुछ भी बुक मत कीजिए' covers the no-booking prohibition.")),
    ("T03", "mr"): dict(potential_ambiguity=F(True, "'भाडे ₹3,000 पेक्षा जास्त नसावे' = fare <= 3000 (intended)."), unnatural_wording=F(True, "'प्रवासासाठी' and 'निघायचे आहे' are natural but the sentence is long; reviewer to confirm."), constraint_risk=F(True, "'संध्याकाळी 6 वाजता किंवा त्यानंतर' = at or after 6 PM. " + _EVENING + " " + _INHERIT), notes=F(True, "Highest-risk item (see Hinglish). 'काहीही बुक करू नका' covers the no-booking prohibition.")),
    ("T04", "hinglish"): dict(potential_ambiguity=F(True, "'sabse sasta' = lowest SL fare (intended), not 'best value'."), unnatural_wording=OK, constraint_risk=OK, notes=F(False, "Passenger name stays Latin; 'ke naam par book kar do'.")),
    ("T04", "hi"): dict(potential_ambiguity=F(True, "'सबसे सस्ता' = lowest SL fare (intended)."), unnatural_wording=F(True, "Latin-script name inside a Devanagari sentence (required by the environment's Latin-only passenger rule); 'के नाम से' is natural."), constraint_risk=OK, notes=F(False, "'स्लीपर (SL)' keeps both the word and the class code.")),
    ("T04", "mr"): dict(potential_ambiguity=F(True, "'सर्वात स्वस्त' = lowest SL fare (intended)."), unnatural_wording=F(True, "'यांच्या नावाने' adds an honorific absent in English; reviewer to confirm it is neutral."), constraint_risk=OK, notes=F(False, "Booking verb 'बुक करा' is an imperative request to book exactly one ticket.")),
    ("T05", "hinglish"): dict(potential_ambiguity=F(True, "English 'If it is sold out' became 'Agar 3A sold out ho' (referent made explicit)."), unnatural_wording=OK, constraint_risk=F(True, "Three coupled conditions: book only if seats; if sold out do not book another class/train; just tell me. 'kisi aur class ya kisi aur train' must be read as neither."), notes=F(True, "'sirf tab jab' encodes 'only if'.")),
    ("T05", "hi"): dict(potential_ambiguity=F(True, "'दूसरी क्लास या दूसरी ट्रेन में बुक मत कीजिए': 'या' must be read as neither (same as English 'any other class or train')."), unnatural_wording=F(True, "'सोल्ड आउट' is a transliterated loanword; 'केवल तभी जब' is slightly formal."), constraint_risk=F(True, "Three coupled conditions (see Hinglish). Referent '3A' made explicit vs English 'it'."), notes=F(True, "Highest-risk item with T03.")),
    ("T05", "mr"): dict(potential_ambiguity=F(True, "'दुसऱ्या क्लासमध्ये किंवा दुसऱ्या ट्रेनमध्ये बुक करू नका' must be read as neither class nor train."), unnatural_wording=F(True, "'सीट' (loanword) chosen over 'जागा' for consistency with T02; 'सोल्ड आउट' loanword vs 'संपले'."), constraint_risk=F(True, "Three coupled conditions (see Hinglish). 'तरच' strongly encodes 'only if'."), notes=F(True, "Highest-risk item with T03.")),
}


def _records(ids: list[str], flags: dict, langs: list[str] = LANGS) -> list[dict]:
    specs = {s.semantic_task_id: s for s in load_specs()}
    oracle = RawOracle()
    code_of = lambda n: next(iter(oracle.codes_for(n)))  # noqa: E731
    recs = []
    for tid in ids:
        for lang in langs:
            file = LANG_DIR / f"{lang}.jsonl"
            row = next(json.loads(l) for l in file.read_text(encoding="utf-8").splitlines() if json.loads(l)["task_id"] == f"{tid}_{lang}")
            rec = {"semantic_task_id": tid, "language": lang, "task_id": row["task_id"], "query": row["query"],
                   "review_status": "draft",  # drafting audit: records the draft stage (human review: languages/human_review.json)
                   "checks": run_checks(tid, lang, row["query"], specs[tid].solver.params, code_of),
                   "human_review": PENDING, "fluency_review": PENDING, "equivalence_review": PENDING}
            if lang == "en":
                rec["translation_flags"] = "not_applicable (frozen English source)"
            else:
                rec["translation_flags"] = flags[(tid, lang)]
            recs.append(rec)
    return recs


def build() -> dict:
    recs = _records(PILOT_IDS, FLAGS)
    return {"_meta": {"stage": "pilot_language_draft", "items": len(recs),
                      "note": "Checks are automated keyword presence tests, NOT human verification. All review fields are pending_human_review. "
                              "For fixed-train tasks (T01, T05) 'route_preserved' tests the explicit train id. 'not_applicable' = the task has no such constraint.",
                      "back_translation": "not used as evidence"},
            "records": recs}


def build_batch() -> dict:
    recs = _records(BATCH_IDS, BATCH_FLAGS)
    return {"_meta": {"stage": "batch_T06_T15_language_draft", "items": len(recs),
                      "note": "Checks are automated keyword presence tests, NOT human verification. All review fields are pending_human_review. "
                              "Non-English variants are Claude-generated drafts. 'route_preserved' also covers named trains, boarding/intermediate "
                              "stations and, for T09, that 'Delhi' stays ambiguous. 'not_applicable' = the task has no such constraint.",
                      "back_translation": "not used as evidence"},
            "records": recs}


def build_batch2() -> dict:
    recs = _records(_b2.BATCH_IDS, _b2.FLAGS)
    return {"_meta": {"stage": "batch_T16_T25_language_draft", "items": len(recs),
                      "note": "Checks are automated keyword presence tests, NOT human verification. All review fields are pending_human_review. "
                              "Non-English variants are Claude-generated drafts. For T19 'passenger_preserved' tests that the "
                              "missing passenger name stays ABSENT. 'not_applicable' = the task has no such constraint.",
                      "back_translation": "not used as evidence"},
            "records": recs}


def build_batch3() -> dict:
    recs = _records(_b3.BATCH_IDS, _b3.FLAGS)
    return {"_meta": {"stage": "batch_T26_T50_language_draft", "items": len(recs),
                      "note": "Checks are automated keyword presence tests, NOT human verification. All review fields are pending_human_review. "
                              "Non-English variants are Claude-generated drafts. Designed in three internal phases (T26-T35, T36-T45, T46-T50). "
                              "'not_applicable' = the task has no such constraint (T45 has no station, class, date or passenger at all).",
                      "back_translation": "not used as evidence"},
            "records": recs}


def build_batch4() -> dict:
    recs = _records(_b4.BATCH_IDS, _b4.FLAGS)
    return {"_meta": {"stage": "batch_T51_T75_language_draft", "items": len(recs),
                      "note": "Checks are automated keyword presence tests, NOT human verification. All review fields are pending_human_review. "
                              "Non-English variants are Claude-generated drafts. End-sem batch: 17 failure-targeted tasks + 8 language-feature tasks "
                              "(T54, T57, T62, T64, T67, T69, T71, T72). For T54 hi/mr 'passenger_preserved' tests the declared Devanagari name "
                              "(and that the Latin form is absent); for T69 'route_preserved' tests that both station names survive. "
                              "'not_applicable' = the task has no such constraint.",
                      "back_translation": "not used as evidence"},
            "records": recs}


def build_gujarati_t51_t75() -> dict:
    recs = _records(_gu.GU_IDS_T51_T75, _gu.FLAGS, ["gu"])
    return {"_meta": {"stage": "gujarati_T51_T75_language_draft", "items": len(recs),
                      "note": "Gujarati (5th language) for the end-sem batch T51-T75. Checks are automated keyword presence tests, NOT human "
                              "verification. All review fields are pending_human_review. For T54 'passenger_preserved' tests the declared "
                              "Gujarati-script name (and that the Latin form is absent); for T69 'route_preserved' tests that both station "
                              "names survive. 'not_applicable' = the task has no such constraint.",
                      "back_translation": "not used as evidence"},
            "records": recs}


def build_batch5() -> dict:
    recs = _records(_b5.BATCH_IDS, _b5.FLAGS)
    return {"_meta": {"stage": "batch_T76_T100_language_draft", "items": len(recs),
                      "note": "Benchmark 3.0 batch (the six new tools: booking status, refund quote, cancellation, waitlist, live status, "
                              "concession). Checks are automated keyword presence tests, NOT human verification. All review fields are "
                              "pending_human_review. Non-English variants are Claude-generated drafts. PNR digits are part of the intent "
                              "markers. 'not_applicable' = the task has no such constraint (most tasks have no route or date).",
                      "back_translation": "not used as evidence"},
            "records": recs}


def build_gujarati_t76_t100() -> dict:
    recs = _records(_gu.GU_IDS_T76_T100, _gu.FLAGS, ["gu"])
    return {"_meta": {"stage": "gujarati_T76_T100_language_draft", "items": len(recs),
                      "note": "Gujarati for the benchmark 3.0 batch T76-T100. Checks are automated keyword presence tests, NOT human "
                              "verification. All review fields are pending_human_review. 'not_applicable' = the task has no such constraint.",
                      "back_translation": "not used as evidence"},
            "records": recs}


def build_gujarati() -> dict:
    recs = _records(_gu.GU_IDS_T01_T50, _gu.FLAGS, ["gu"])
    return {"_meta": {"stage": "gujarati_T01_T50_language_draft", "items": len(recs),
                      "note": "Gujarati (5th language) for T01-T50. Checks are automated keyword presence tests, NOT human verification. "
                              "All review fields are pending_human_review. Variants are Claude-generated drafts; the English/Hinglish/"
                              "Hindi/Marathi records live in the earlier audit files, which are unchanged. 'not_applicable' = the task "
                              "has no such constraint.",
                      "back_translation": "not used as evidence"},
            "records": recs}


def main() -> None:
    AUDIT_PATH.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", AUDIT_PATH)
    BATCH_AUDIT_PATH.write_text(json.dumps(build_batch(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", BATCH_AUDIT_PATH)
    BATCH2_AUDIT_PATH.write_text(json.dumps(build_batch2(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", BATCH2_AUDIT_PATH)
    BATCH3_AUDIT_PATH.write_text(json.dumps(build_batch3(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", BATCH3_AUDIT_PATH)
    BATCH4_AUDIT_PATH.write_text(json.dumps(build_batch4(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", BATCH4_AUDIT_PATH)
    GU_AUDIT_PATH.write_text(json.dumps(build_gujarati(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", GU_AUDIT_PATH)
    GU2_AUDIT_PATH.write_text(json.dumps(build_gujarati_t51_t75(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", GU2_AUDIT_PATH)
    BATCH5_AUDIT_PATH.write_text(json.dumps(build_batch5(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", BATCH5_AUDIT_PATH)
    GU3_AUDIT_PATH.write_text(json.dumps(build_gujarati_t76_t100(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", GU3_AUDIT_PATH)


if __name__ == "__main__":
    main()
