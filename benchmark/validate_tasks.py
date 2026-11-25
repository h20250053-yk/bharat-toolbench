"""Validate the semantic tasks T01-T100 x 5 languages = 500 items (human review recorded in benchmark/human_review.py). Run:  python -m benchmark.validate_tasks

Checks (all model-independent):
  1. spec / language-file / gold coverage; spec and gold are language-independent (no language key)
  2. gold is reproducible (regenerated == committed file) and was not hand-edited
  3. initial-state assumptions hold on a fresh baseline environment
  4. gold calls replay against the environment; expected final env diff is reproduced exactly
  5. INDEPENDENT ORACLE: answers recomputed straight from the raw fixture JSON (no environment code, no solver)
     must equal the gold answer, and be unique
  6. prompts reference only stations / trains / classes / dates that exist in the fixtures; no tool-name hints
  7. multilingual draft layer (validate_languages): 20 items, 5x4, shared gold, English frozen, all non-English are drafts,
     T03/T04/T05 constraint wording present in every language, audit file consistent and all review fields pending
  8. batch T06-T15: expected tool errors and ambiguous-station matchers replayed; independent oracle per solver kind;
     pilot T01-T05 frozen (spec, gold, all four language-file prefixes hashed); batch audit consistent;
     semantic-overlap (duplicate) check over all 15 tasks (benchmark/semantic_overlap.py)
  9. batch T51-T75: independent oracle per new solver kind; T01-T50 frozen (spec, gold, first 50 lines of every language
     file, T26-T50 audit); language-feature exceptions are declared per task in the spec (T54: native-script passenger name)
 10. T51-T75 frozen too (benchmark 2.0.0): spec, gold, rows 51-75 of all five language files, both T51-T75 audits
 11. batch T76-T100 (benchmark 3.0, six new tools): independent oracle per new solver kind from the raw account/live/train JSON; cancellations
     and waitlist entries checked like bookings; T01-T75 keep the six tools they were written for in their rows
"""
from __future__ import annotations

import json
import re
from datetime import date as Date
from pathlib import Path
from typing import Any

from environment import TOOL_NAMES, RailwayEnv
from environment.state import DATA_DIR, normalize_name

from . import batch_t06_t15 as _b1
from . import human_review as _hr
from . import batch_t16_t25 as _b2
from . import batch_t26_t50 as _b3
from . import batch_t51_t75 as _b4
from . import batch_t76_t100 as _b5
from . import batch_t101_t200 as _b6
from .oracle_t101_t200 import Oracle6
from . import batch_gujarati as _gu
import hashlib
from .batch_t06_t15 import BATCH_IDS, EN_AUTHOR as BATCH_EN_AUTHOR, EN_ITEMS as BATCH_EN_ITEMS, QUERIES as BATCH_QUERIES
from .build_gold import EFFECT_FIELDS, GOLD_PATH, SPEC_PATH, build_all, env_diff, load_specs, render
from .language_checks import CHECKS, EXTRA_LANGS, LANGS, NA, numeric_signature, parse_dates as parse_dates_lang, run_checks
from .schemas import BenchmarkItem, GoldSpec

LANG_DIR = Path(__file__).resolve().parent / "languages"
V2_TOOLS = ("resolve_station", "search_trains", "get_train_details", "check_availability", "get_fare", "book_ticket")
V3_TOOLS = tuple(_b5.ALL_TOOLS_V3)  # T76-T100 (12 tools); T101-T200 list all 20 (TOOL_NAMES)
PILOT_IDS = ["T01", "T02", "T03", "T04", "T05"]
BATCHES = [_b1, _b2, _b3, _b4, _b5, _b6]
BATCH5_AUDIT_PATH = LANG_DIR / "batch_T76_T100_language_audit.json"
BATCH6_AUDIT_PATH = LANG_DIR / "batch_T101_T200_language_audit.json"
BATCH3_AUDIT_PATH = LANG_DIR / "batch_T26_T50_language_audit.json"
BATCH4_AUDIT_PATH = LANG_DIR / "batch_T51_T75_language_audit.json"
# Freeze of T01-T50 when T51-T75 were added (end-sem batch): spec, gold, first 50 lines of each language file, T26-T50 audit.
FROZEN_T01_T50_IDS = [f"T{i:02d}" for i in range(1, 51)]
FROZEN_T01_T50_GOLD_SHA256 = "019f909aa7bc1885a86052d45990e3ed726ee8438adb6e30c62f96a84be5aad6"
FROZEN_T01_T50_SPEC_SHA256 = "02eff38bd1c5d716b365550247861382b31e1cd8e7f59e9046639cf0542dbe3b"
# Updated on purpose 2026-11-24 for the T38_mr wording fix (audit I-08); the audit record of T38_mr carries the new query text.
FROZEN_T26_T50_AUDIT_SHA256 = "0bbe9143914b98882a38d39bde0683e163b4a1736cf27d180f60cd86d56c607b"
# Updated ON PURPOSE on 2026-11-24 (audit I-08, approved by the project author): the Marathi T38 wording
# "दुसऱ्या सर्वात स्वस्त" (reads as "second-cheapest") became "इतर ट्रेनपैकी सर्वात स्वस्त" (cheapest among the other trains),
# which is what the gold (BTB123) means. Only the mr hash and FROZEN_T26_T50_AUDIT_SHA256 changed; spec, gold, en/hinglish/hi/gu untouched.
FROZEN_T01_T50_LANG_SHA256 = {'en': '4e5a3d50652bf3a75875066f811c262b60a5f7d3a6ca2ebef23ba3d70aee37dd', 'hi': '220600d143ec7cded5cc8b04e53527de0c1a12485a16d2c9e66fe500cee0fc6c', 'hinglish': 'a2cef9143ef9bf310c7d0e17f1bbe56f4014b61afebb1f71de9453279e5cc223', 'mr': 'cc3e7970482d3cf560656d02a374f39c5c774b9ab4ca5d586e5d60de20f1ed67'}
# Freeze of T01-T25 after the final Marathi revision: updated derived hashes for the revised language layer.
FROZEN_T01_T25_IDS = [f"T{i:02d}" for i in range(1, 26)]
FROZEN_T01_T25_GOLD_SHA256 = "8758e1a7bf6ef5112b3debbf666a6b9d4dad7e7cee4a5c928271d4487f4c6440"
FROZEN_T01_T25_SPEC_SHA256 = "71c9cbd3e6e1ec933e73e178e86c3484ba1c1f8ce36a6f87bcf0fa8422329210"
FROZEN_T16_T25_AUDIT_SHA256 = "a315be99ece01203227493204cfcf959b831cfff1c9a95dfec731d3e28d82762"
FROZEN_T01_T25_LANG_SHA256 = {'en': 'dd4f663bc37d40e88db39bd443d22d8f060dd5e5095c8f2f3547f41380ee4a65', 'hi': '8f5af8a7afa66fce6b3c4e4b7b632aa094a07122279d79100435dc7193164e80', 'hinglish': 'fef5753263ef56f1c2b8eb916e97267df57b4d09ad6fab65fc6252a81bd7df9f', 'mr': '284a60316124c481a01be48ea309d52f5cc90681d12d384a0eb7f962258159d2'}
ALL_IDS = PILOT_IDS + [t for b in BATCHES for t in b.BATCH_IDS]
BATCH2_AUDIT_PATH = LANG_DIR / "batch_T16_T25_language_audit.json"
# Freeze of T01-T15 after the final Marathi revision: updated derived hashes for the revised language layer.
FROZEN_T01_T15_IDS = PILOT_IDS + BATCH_IDS
FROZEN_T01_T15_GOLD_SHA256 = "45799b61757f7ff5af7af1ee1d01e4817f2f0c6edb3ae1b51daa8cf23d2df875"
FROZEN_T01_T15_SPEC_SHA256 = "8d09a40ea099be46a0a9413aee930f3af96169e86949c6166b1a6294dd578a4c"
FROZEN_T06_T15_AUDIT_SHA256 = "36aa09d0bad253bf2d150a8fdabf25d12f14e4530babf058e26d9a15e82b364d"
FROZEN_T01_T15_LANG_SHA256 = {'en': '87f7a9d3931421d474655bc4903ee9b410a78958a9340b7a17eebc085effa80f', 'hi': '1b293075724efe816164e1fc6b0b1f8349a392d99b9ad13c997a386d76359cf7', 'hinglish': '3e5c7694d47d192036e8a4d18c53bcd06848419f94533335b6f3a51c0bb238e4', 'mr': 'ad0aef12f03b65fb8759593f49f46425991910dbab446492fbdf367ba34cb9d8'}
# Freeze of T51-T75 (audit M-08, benchmark version 2.0.0, git tag v2.0-data), the same way T01-T50 is frozen: spec and gold of the 25 tasks,
# rows 51-75 of all five language files (review fields reset to draft, so recording a review is not a change) and both T51-T75 audits.
# Change on purpose only: edit the source batch module, rebuild, update the constant with a comment, re-record the human review.
FROZEN_T51_T75_IDS = [f"T{i:02d}" for i in range(51, 76)]
FROZEN_T51_T75_GOLD_SHA256 = "501a0ce4880bd3d68a975db0f1b75547df98aa2264c9f88add03ddbfd0c622eb"
FROZEN_T51_T75_SPEC_SHA256 = "c689f1a7490fa3aebfa23e51d444e901498b890da1a142a59cee2126635f923c"
FROZEN_T51_T75_LANG_SHA256 = {'en': 'bcbc4605713b98e3c7ec7ee3fb5a5645505024b1c96fd2dcb558ee5c59abf8ea', 'hi': '1eceb745957cfe12e5477fe784f191e3f14de8a0b075bbbc2dfc3dcee7d8f0e9',
                              'hinglish': 'bc0a65cb3a7981df582dd0b0af9ff73b2055e0ea59a473a3e3fb9f097e12db76', 'mr': '67c7bdb0a124258223b75d1bc1f2a9c0df0deec8bc79a1e06be245ceac30f82a',
                              'gu': '3e6ebfc143330f2236460680a272e74f970b02f8540d6eeb08b249ff4708c80f'}
FROZEN_T51_T75_AUDIT_SHA256 = "458cebc466c9bd1307a0b93cace2d367149b63ac4c61561f7fb4713b41e7e793"
FROZEN_GU_T51_T75_AUDIT_SHA256 = "0fa82f314e80ab6932ca47960e95fd8482fd8480d1390c70fc27d53057aa232f"
AUDIT_PATH = LANG_DIR / "pilot_language_audit.json"
BATCH_AUDIT_PATH = LANG_DIR / "batch_T06_T15_language_audit.json"
# Current freeze: sha256 of the T01-T05 rows (first 5 lines) of each language file, and of the T01-T05 gold/spec entries.
FROZEN_PILOT_LANG_SHA256 = {
    "en": "f46be0ffa73ebf8048fe6caa1116cb8bd37698a69ed3db3317d48d1801a8e646",
    "hi": "c7ae884bd281b3f26e18cddc9c1980f714791301757b7eafddc48fc1651d0a80",
    "hinglish": "4efe7eeb2ce5efeecca1d16c1c75864a14325a240dc17244096e835dd814d46b",
    "mr": "8e2e356d5e45a22b501bf7ce2bbe165d87e84f6cc1001a41c21232f9e69fa32f",
}
FROZEN_PILOT_GOLD_SHA256 = "844b5df995b57d58f8dc876641349bde5e631204e74706c22a26a1cf3e002897"
FROZEN_PILOT_SPEC_SHA256 = "3710347e6d732e6d20f91cfc44702ce7250424a8e876aa748e491a2e94967d8d"
# English prompts are frozen: exact text + file hash. Any change must be a new benchmark version.
FROZEN_EN_SHA256 = "f46be0ffa73ebf8048fe6caa1116cb8bd37698a69ed3db3317d48d1801a8e646"
FROZEN_EN_QUERIES = {
    "T01": "What is the fare for 2A class on train BTB103?",
    "T02": "Is there a 3A seat available on the only train from Nagpur to Pune on 7 October 2026? Also tell me the fare.",
    "T03": "I need a 3A ticket from Jaipur to Ahmedabad on 8 October 2026. I want to leave at or after 6 PM, pay no more than \u20b93,000, and have seats available. Which train fits? Don't book anything, just tell me the train.",
    "T04": "Book the cheapest sleeper (SL) ticket from Mumbai to Pune on 7 October 2026 for Ananya Kulkarni.",
    "T05": "Please book a 3A ticket on train BTB103 for Vikram Singh, but only if seats are available. If it is sold out, don't book any other class or train, just tell me.",
}
NON_EN_AUTHOR = "Claude-generated draft"
BANNED_STATUS_WORDS = ("verified", "accepted", "approved", "human_verified")
EXPECTED_CATEGORY = {"T01": "single_tool", "T02": "sequential", "T03": "constraint", "T04": "booking", "T05": "recovery",
                     **{t: b.EN_ITEMS[t]["category"] for b in BATCHES for t in b.BATCH_IDS}}
WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}


# ------------------------------------------------------------------ independent oracle (raw JSON only)
class RawOracle:
    def __init__(self) -> None:
        self.stations = json.loads((DATA_DIR / "stations.json").read_text(encoding="utf-8"))["stations"]
        self.trains = json.loads((DATA_DIR / "trains.json").read_text(encoding="utf-8"))["trains"]

    def codes_for(self, name: str) -> set[str]:
        key = normalize_name(name)
        return {s["code"] for s in self.stations
                if key in {normalize_name(f) for f in [s["code"], s["name"], s["city"], *sum(s["aliases"].values(), [])]}}

    @staticmethod
    def _m(hhmm: str) -> int:
        return int(hhmm[:2]) * 60 + int(hhmm[3:])

    def serving(self, src: str, dst: str, date: str) -> list[dict[str, Any]]:
        d, out = Date.fromisoformat(date), []
        for t in self.trains:
            codes = [s["station"] for s in t["stops"]]
            if src not in codes or dst not in codes or codes.index(src) >= codes.index(dst):
                continue
            board, alight = t["stops"][codes.index(src)], t["stops"][codes.index(dst)]
            origin_weekday = WEEKDAYS[(d.toordinal() - (board["departure_day"] or 0) - 1) % 7]  # ordinal 1 = Monday
            if origin_weekday in t["operating_days"]:
                # arr = minutes after midnight of the BOARDING date (batch addition; pilot kinds never read it)
                arr = ((alight["arrival_day"] or 0) - (board["departure_day"] or 0)) * 1440 + self._m(alight["arrival"])
                out.append({"train_id": t["train_id"], "dep": self._m(board["departure"]), "arr": arr, "classes": t["classes"]})
        return out

    def answer_batch3(self, kind: str, p: dict[str, Any]) -> dict[str, Any]:
        """Batch T26-T50: recomputed from raw fixture JSON only (no environment code, no solver)."""
        T = {t["train_id"]: t for t in self.trains}
        one = lambda n: next(iter(self.codes_for(n))) if len(self.codes_for(n)) == 1 else None  # noqa: E731
        hm = lambda m: f"{m // 60:02d}:{m % 60:02d}"  # noqa: E731
        VALID = {"3A", "2A", "SL", "CC"}

        def serving(src, dst, date):
            return [c for c in self.serving(src, dst, date) if not (date == "2026-10-05" and c["dep"] <= 540)]

        def runs(tid, src, dst, date):
            return tid in [c["train_id"] for c in serving(src, dst, date)]
        g = lambda k: p.get(k)  # noqa: E731
        tid, cls, pax = g("train_id"), g("travel_class"), g("passenger")
        seats = (lambda t, c: T[t]["classes"][c]["seats"])
        fare = (lambda t, c: T[t]["classes"][c]["fare_inr"])
        if kind == "seat_count_lookup":
            return {"train_ids": {tid}, "answer": {"seats_available": seats(tid, cls)}}
        if kind == "direct_named_booking":
            assert runs(tid, one(g("source_name")), one(g("destination_name")), g("date")) and seats(tid, cls) > 0
            return {"train_ids": {tid}, "answer": {"fare_inr": fare(tid, cls)}, "bookings": [(tid, cls, pax)]}
        if kind == "invalid_train_id":
            assert tid not in T
            return {"answer": {"status": "cannot_complete", "reason": "INVALID_TRAIN"}, "bookings": []}
        if kind == "unsupported_class":
            assert cls not in VALID and runs(tid, one(g("source_name")), one(g("destination_name")), g("date"))
            return {"answer": {"status": "cannot_complete", "reason": "INVALID_CLASS", "classes_on_train": sorted(T[tid]["classes"])}, "bookings": []}
        if kind == "past_date_booking":
            assert g("date") < "2026-10-05"
            return {"answer": {"status": "cannot_complete", "reason": "PAST_DATE"}, "bookings": []}
        if kind == "alias_retry_earliest":
            assert not self.codes_for(g("source_name"))
            c = sorted(serving(one(g("recovered_station")), one(g("destination_name")), g("date")), key=lambda x: x["dep"])
            return {"train_ids": {c[0]["train_id"]}, "answer": {"departure": hm(c[0]["dep"])}}
        if kind == "fare_conditioned_branch":
            branch = cls if fare(tid, cls) < g("fare_below_inr") else g("fallback_class")
            return {"train_ids": {tid}, "answer": {"travel_class": branch, "condition_fare_inr": fare(tid, cls)}, "bookings": [(tid, branch, pax)]}
        if kind == "group_cheapest_any_class":
            n = len(g("passengers"))
            opts = [(c["classes"][k]["fare_inr"], c["train_id"], k) for c in serving(one(g("source_name")), one(g("destination_name")), g("date"))
                    for k in c["classes"] if c["classes"][k]["seats"] >= n]
            f, t, k = min(opts)
            return {"train_ids": {t}, "answer": {"travel_class": k, "fare_inr_per_ticket": f}, "bookings": [(t, k, x) for x in g("passengers")]}
        if kind == "fastest_within_budget":
            c = sorted((x for x in serving(one(g("source_name")), one(g("destination_name")), g("date")) if cls in x["classes"]
                        and x["classes"][cls]["fare_inr"] <= g("max_fare_inr")), key=lambda x: x["arr"] - x["dep"])
            return {"train_ids": {c[0]["train_id"]}, "answer": {"duration_minutes": c[0]["arr"] - c[0]["dep"], "seats_available": c[0]["classes"][cls]["seats"]}}
        if kind == "relative_weekday_booking":
            d = next(Date.fromordinal(Date(2026, 10, 5).toordinal() + i) for i in range(1, 8)
                     if WEEKDAYS[Date.fromordinal(Date(2026, 10, 5).toordinal() + i).weekday()] == g("relative_weekday"))
            c = [x for x in serving(one(g("source_name")), one(g("destination_name")), d.isoformat()) if cls in x["classes"]]
            assert len(c) == 1
            return {"train_ids": {c[0]["train_id"]}, "answer": {"resolved_date": d.isoformat()}, "bookings": [(c[0]["train_id"], cls, pax)]}
        if kind == "ambiguous_class_term":
            ac = sorted(k for k in T[tid]["classes"] if k in ("3A", "2A", "CC") and seats(tid, k) > 0)
            assert len(ac) >= 2
            return {"answer": {"status": "needs_clarification", "candidate_classes": ac}, "bookings": []}
        if kind == "ambiguous_intent":
            assert seats(tid, cls) > 0
            return {"answer": {"status": "needs_clarification", "clarification_needed": "check_or_book"}, "bookings": []}
        if kind == "sold_out_cheapest_alternative":
            assert seats(tid, cls) == 0
            alts = [(x["classes"][cls]["fare_inr"], x["train_id"]) for x in serving(one(g("source_name")), one(g("destination_name")), g("date"))
                    if x["train_id"] != tid and cls in x["classes"] and x["classes"][cls]["seats"] > 0]
            f, t = min(alts)
            return {"train_ids": {t}, "answer": {"fare_inr": f}, "bookings": [(t, cls, pax)]}
        if kind == "runs_on_date_conditional":
            wd = WEEKDAYS[Date.fromisoformat(g("date")).weekday()]
            assert T[tid]["stops"][0]["station"] == one(g("source_name")) and wd not in T[tid]["operating_days"]
            return {"answer": {"status": "cannot_complete", "requested_weekday": wd}, "bookings": []}
        if kind == "connection_planning":
            src, via, dst, d = one(g("source_name")), one(g("via_name")), one(g("destination_name")), g("date")
            assert not serving(src, dst, d)
            pairs = sorted((b["arr"], a["train_id"], b["train_id"]) for a in serving(src, via, d) for b in serving(via, dst, d)
                           if b["dep"] - a["arr"] >= g("min_connection_minutes"))
            return {"answer": {"first_leg_train_id": pairs[0][1], "second_leg_train_id": pairs[0][2], "final_arrival": hm(pairs[0][0] % 1440)}, "bookings": []}
        if kind == "multi_leg_all_or_nothing":
            s = [seats(lg["train_id"], lg["travel_class"]) for lg in g("legs")]
            assert s[0] > 0 and 0 in s
            return {"answer": {"status": "cannot_complete", "failing_leg": s.index(0) + 1}, "bookings": []}
        if kind == "mixed_class_pair_booking":
            assert all(seats(tid, a["travel_class"]) > 0 for a in g("assignments"))
            return {"train_ids": {tid}, "bookings": [(tid, a["travel_class"], a["passenger"]) for a in g("assignments")]}
        if kind == "multi_constraint_booking":
            d = g("date")
            dl = (Date.fromisoformat(g("arrive_by_date")) - Date.fromisoformat(d)).days * 1440 + self._m(g("arrive_by_time"))
            ok = [x for x in serving(one(g("source_name")), one(g("destination_name")), d) if cls in x["classes"] and x["arr"] <= dl
                  and x["classes"][cls]["fare_inr"] <= g("max_fare_inr") and x["classes"][cls]["seats"] > 0]
            assert len(ok) == 1
            return {"train_ids": {ok[0]["train_id"]}, "answer": {"fare_inr": ok[0]["classes"][cls]["fare_inr"]}, "bookings": [(ok[0]["train_id"], cls, pax)]}
        if kind == "overnight_arrival_date":
            c = [x for x in serving(one(g("source_name")), one(g("destination_name")), g("date")) if x["dep"] == self._m(g("departure_time"))]
            assert len(c) == 1
            return {"train_ids": {c[0]["train_id"]}, "answer": {"arrival": hm(c[0]["arr"] % 1440),
                    "arrival_date": Date.fromordinal(Date.fromisoformat(g("date")).toordinal() + c[0]["arr"] // 1440).isoformat()}}
        if kind == "unsupported_action":
            return {"answer": {"status": "cannot_complete", "reason": "unsupported_action"}, "bookings": []}
        if kind == "passenger_count_conflict":
            assert g("ticket_count") != len(g("passengers"))
            return {"answer": {"status": "needs_clarification", "clarification_needed": "passenger_count"}, "bookings": []}
        if kind == "disambiguation_by_train":
            cands = self.codes_for(g("source_name"))
            fits = [c for c in sorted(cands) if runs(tid, c, one(g("destination_name")), g("date"))]
            assert len(cands) >= 2 and len(fits) == 1
            return {"train_ids": {tid}, "answer": {"resolved_source": fits[0]}, "bookings": [(tid, cls, pax)]}
        if kind == "partial_allowed_group":
            n = seats(tid, cls)
            return {"train_ids": {tid}, "answer": {"booked_passengers": g("passengers")[:n]}, "bookings": [(tid, cls, x) for x in g("passengers")[:n]]}
        if kind == "route_property_booking":
            dst, goal = one(g("destination_name")), one(g("continues_to_name"))
            hit = []
            for x in serving(one(g("source_name")), dst, g("date")):
                st = [s["station"] for s in T[x["train_id"]]["stops"]]
                if cls in x["classes"] and goal in st and st.index(goal) > st.index(dst):
                    hit.append(x["train_id"])
            assert len(hit) == 1
            return {"train_ids": set(hit), "bookings": [(hit[0], cls, pax)]}
        if kind == "state_conditional_second_booking":
            n = seats(tid, cls)
            assert n >= 2
            return {"train_ids": {tid}, "answer": {"seats_remaining_at_end": n - 2}, "bookings": [(tid, cls, pax), (tid, cls, g("second_passenger"))]}
        raise KeyError(kind)

    def answer_batch4(self, kind: str, p: dict[str, Any]) -> dict[str, Any]:
        """Batch T51-T75: recomputed from raw fixture JSON only (no environment code, no solver)."""
        T = {t["train_id"]: t for t in self.trains}
        one = lambda n: next(iter(self.codes_for(n))) if len(self.codes_for(n)) == 1 else None  # noqa: E731
        hm = lambda m: f"{m // 60:02d}:{m % 60:02d}"  # noqa: E731
        day = lambda d, k: Date.fromordinal(Date.fromisoformat(d).toordinal() + k).isoformat()  # noqa: E731

        def serving(src, dst, date):  # excludes trains already departed at the pinned 'now' (2026-10-05 09:00)
            return [c for c in self.serving(src, dst, date) if not (date == "2026-10-05" and c["dep"] <= 540)]
        g = lambda k: p.get(k)  # noqa: E731
        tid, cls, pax, d = g("train_id"), g("travel_class"), g("passenger"), g("date")
        src = one(g("source_name")) if g("source_name") else None
        dst = one(g("destination_name")) if g("destination_name") else None
        seats = (lambda t, c: T[t]["classes"][c]["seats"])
        fare = (lambda t, c: T[t]["classes"][c]["fare_inr"])
        if kind == "route_count_latest_departure":
            c = serving(src, dst, d)
            last = max(c, key=lambda x: x["dep"])
            return {"train_ids": {last["train_id"]}, "answer": {"train_count": len(c), "departure": hm(last["dep"]),
                                                                  "seats_available": seats(last["train_id"], cls)}}
        if kind == "earliest_arrival_after_time":
            c = min((x for x in serving(src, dst, d) if x["dep"] >= self._m(g("departure_not_before"))), key=lambda x: x["arr"])
            return {"train_ids": {c["train_id"]}, "answer": {"arrival": hm(c["arr"] % 1440), "arrival_date": day(d, c["arr"] // 1440)}}
        if kind == "fare_difference_two_departures":
            f = {x["train_id"]: x["classes"][cls]["fare_inr"] for x in serving(src, dst, d) if hm(x["dep"]) in g("departure_times")}
            assert len(f) == 2
            return {"train_ids": {min(f, key=f.get)}, "answer": {"fare_difference_inr": max(f.values()) - min(f.values())}}
        if kind == "native_script_passenger_booking":
            c = [x for x in serving(src, dst, d) if cls in x["classes"]]
            assert len(c) == 1 and all(not re.match(r"^[A-Za-z]", f) for f in g("passenger_script_forms").values())
            return {"train_ids": {c[0]["train_id"]}, "answer": {"fare_inr": c[0]["classes"][cls]["fare_inr"]}, "bookings": [(c[0]["train_id"], cls, pax)]}
        if kind == "midroute_boarding_arrival":
            c = next(x for x in serving(src, dst, d) if x["train_id"] == tid)
            assert T[tid]["stops"][0]["station"] != src
            return {"train_ids": {tid}, "answer": {"arrival": hm(c["arr"] % 1440), "arrival_date": day(d, c["arr"] // 1440),
                                                   "seats_available": seats(tid, cls)}}
        if kind == "multi_destination_departures":
            got = sorted((x["dep"], x["train_id"]) for k in ("destination_name", "second_destination_name")
                         for x in serving(src, one(g(k)), d) if x["dep"] >= self._m(g("departure_not_before")))
            return {"answer": {"selected_train_ids": [t for _, t in got], "departure_times": [hm(m) for m, _ in got]}, "bookings": []}
        if kind == "relative_day_latest_with_class":
            dd = day("2026-10-05", {"tomorrow": 1, "day_after_tomorrow": 2}[g("relative_day")])
            c = max((x for x in serving(src, dst, dd) if cls in x["classes"]), key=lambda x: x["dep"])
            return {"train_ids": {c["train_id"]}, "answer": {"resolved_date": dd, "departure": hm(c["dep"])}, "bookings": []}
        if kind == "two_intent_count_and_booking":
            assert tid in [x["train_id"] for x in serving(src, dst, d)]
            return {"train_ids": {tid}, "answer": {"seats_available": seats(g("count_train_id"), g("count_class"))}, "bookings": [(tid, cls, pax)]}
        if kind == "retracted_booking_fare_only":
            assert seats(tid, cls) > 0
            return {"train_ids": {tid}, "answer": {"fare_inr": fare(tid, cls)}, "bookings": []}
        if kind == "cheaper_class_arrival_deadline":
            o = [(x["classes"][k]["fare_inr"], x["train_id"], k) for x in serving(src, dst, d) if x["arr"] < self._m(g("arrive_before_time"))
                 for k in g("classes") if k in x["classes"]]
            f, t, k = min(o)
            return {"train_ids": {t}, "answer": {"travel_class": k, "fare_inr": f}, "bookings": []}
        if kind == "group_total_budget_check":
            c = [x for x in serving(src, dst, d) if cls in x["classes"]]
            assert len(c) == 1
            total = c[0]["classes"][cls]["fare_inr"] * len(g("passengers"))
            assert total > g("max_total_fare_inr")
            return {"answer": {"status": "cannot_complete", "total_fare_inr": total}, "bookings": []}
        if kind == "spoken_time_train_fare":
            c = [x for x in serving(src, dst, d) if x["dep"] == self._m(g("departure_time"))]
            assert len(c) == 1
            return {"train_ids": {c[0]["train_id"]}, "answer": {"fare_inr": c[0]["classes"][cls]["fare_inr"]}, "bookings": []}
        if kind == "deadline_class_sold_out_infeasible":
            dl = (Date.fromisoformat(g("arrive_by_date")) - Date.fromisoformat(d)).days * 1440 + self._m(g("arrive_by_time"))
            c = [x for x in serving(src, dst, d) if cls in x["classes"] and x["arr"] <= dl]
            assert c and all(x["classes"][cls]["seats"] == 0 for x in c)
            return {"answer": {"status": "cannot_complete", "sold_out_train_ids": [x["train_id"] for x in c]}, "bookings": []}
        if kind == "spoken_amount_earliest_under_budget":
            c = sorted((x for x in serving(src, dst, d) if cls in x["classes"] and x["classes"][cls]["fare_inr"] < g("max_fare_exclusive_inr")),
                       key=lambda x: x["dep"])
            return {"train_ids": {c[0]["train_id"]}, "answer": {"departure": hm(c[0]["dep"]), "fare_inr": c[0]["classes"][cls]["fare_inr"]}, "bookings": []}
        if kind == "earliest_train_party_seats_booking":
            n = len(g("passengers"))
            c = sorted((x for x in serving(src, dst, d) if cls in x["classes"] and x["classes"][cls]["seats"] >= n), key=lambda x: x["dep"])
            return {"train_ids": {c[0]["train_id"]}, "answer": {"departure": hm(c[0]["dep"])}, "bookings": [(c[0]["train_id"], cls, x) for x in g("passengers")]}
        if kind == "next_running_day_booking":
            dd = next(day(d, k) for k in range(1, 8) if WEEKDAYS[Date.fromisoformat(day(d, k)).weekday()] in T[tid]["operating_days"])
            assert T[tid]["stops"][0]["station"] == src and tid in [x["train_id"] for x in serving(src, dst, dd)]
            return {"train_ids": {tid}, "answer": {"resolved_date": dd}, "bookings": [(tid, cls, pax)]}
        if kind == "impossible_date_clarification":
            y, m, dd = (int(x) for x in g("requested_date").split("-"))
            try:
                Date(y, m, dd)
                raise AssertionError("requested date must be impossible")
            except ValueError:
                pass
            return {"answer": {"status": "needs_clarification", "clarification_needed": "date"}, "bookings": []}
        if kind == "hypothetical_total_no_booking":
            return {"train_ids": {tid}, "answer": {"total_fare_inr": sum(fare(tid, a["travel_class"]) for a in g("hypothetical_tickets"))}, "bookings": []}
        if kind == "same_station_two_names":
            assert src == dst and src is not None
            return {"answer": {"status": "needs_clarification", "station_code": src}, "bookings": []}
        if kind == "seat_threshold_conditional_booking":
            assert 0 < seats(tid, cls) < g("min_seats")
            return {"answer": {"status": "cannot_complete", "seats_available": seats(tid, cls)}, "bookings": []}
        if kind == "duplicate_passenger_dedup":
            u = list(dict.fromkeys(g("passengers")))
            assert len(u) < len(g("passengers")) and seats(tid, cls) >= len(u)
            return {"train_ids": {tid}, "answer": {"booked_passengers": u}, "bookings": [(tid, cls, x) for x in u]}
        if kind == "excluded_train_booking":
            c = [x for x in serving(src, dst, d) if cls in x["classes"] and x["train_id"] != g("excluded_train_id") and x["classes"][cls]["seats"] > 0]
            assert len(c) == 1
            return {"train_ids": {c[0]["train_id"]}, "answer": {"fare_inr": c[0]["classes"][cls]["fare_inr"]}, "bookings": [(c[0]["train_id"], cls, pax)]}
        if kind == "sold_out_next_departure_booking":
            c = serving(src, dst, d)
            me = next(x for x in c if x["train_id"] == tid)
            assert me["classes"][cls]["seats"] == 0
            w = min((x for x in c if cls in x["classes"] and x["dep"] > me["dep"]), key=lambda x: x["dep"])
            assert w["classes"][cls]["seats"] > 0
            return {"train_ids": {w["train_id"]}, "answer": {"departure": hm(w["dep"])}, "bookings": [(w["train_id"], cls, pax)]}
        if kind == "typo_train_id_clarification":
            assert g("typed_train_id") not in T and g("likely_train_id") in [x["train_id"] for x in serving(src, dst, d)]
            return {"answer": {"status": "needs_clarification", "suggested_train_id": g("likely_train_id")}, "bookings": []}
        if kind == "class_not_offered_take_offered":
            off = sorted(T[tid]["classes"])
            assert cls not in off and len(off) == 1
            return {"train_ids": {tid}, "answer": {"travel_class": off[0], "fare_inr": fare(tid, off[0])}, "bookings": [(tid, off[0], pax)]}
        raise KeyError(kind)

    def answer_batch2(self, kind: str, p: dict[str, Any]) -> dict[str, Any]:
        """Batch T16-T25: recomputed from raw fixture JSON only."""
        T = {t["train_id"]: t for t in self.trains}
        S = {s["code"]: s for s in self.stations}
        one = lambda n: next(iter(self.codes_for(n))) if len(self.codes_for(n)) == 1 else None  # noqa: E731
        hm = lambda m: f"{m // 60:02d}:{m % 60:02d}"  # noqa: E731

        def serving(src, dst, date):  # excludes trains already departed at the pinned 'now' (2026-10-05 09:00)
            return [c for c in self.serving(src, dst, date) if not (date == "2026-10-05" and c["dep"] <= 540)]
        if kind == "station_identity":
            c = one(p["station_name"])
            return {"answer": {"station_code": c, "station_name": S[c]["name"], "city": S[c]["city"]}}
        if kind == "segment_distance":
            stops = {s["station"]: s["distance_km"] for s in T[p["train_id"]]["stops"]}
            a, b = one(p["from_name"]), one(p["to_name"])
            return {"train_ids": {p["train_id"]}, "answer": {"segment_distance_km": stops[b] - stops[a]}}
        if kind == "unknown_station":
            assert not self.codes_for(p["source_name"]) and one(p["destination_name"])
            return {"answer": {"status": "cannot_complete", "reason": "STATION_NOT_FOUND"}}
        if kind == "missing_passenger_clarification":
            assert p["train_id"] in [c["train_id"] for c in serving(one(p["source_name"]), one(p["destination_name"]), p["date"])]
            assert T[p["train_id"]]["classes"][p["travel_class"]]["seats"] > 0
            return {"answer": {"status": "needs_clarification", "clarification_needed": "passenger_name"}}
        if kind == "no_route_booking":
            src, dst = one(p["source_name"]), one(p["destination_name"])
            assert src and dst and not any(serving(src, dst, f"2026-10-{day:02d}") for day in range(5, 12))
            return {"answer": {"status": "cannot_complete", "reason": "no_direct_train"}, "bookings": []}
        if kind == "train_direction_conflict":
            codes = [s["station"] for s in T[p["train_id"]]["stops"]]
            src, dst = one(p["source_name"]), one(p["destination_name"])
            assert codes.index(dst) < codes.index(src) and serving(src, dst, p["date"])
            return {"answer": {"status": "needs_clarification", "train_runs": [codes[0], codes[-1]]}}
        src, dst, cls = one(p["source_name"]), one(p["destination_name"]), p.get("travel_class")
        if kind == "earliest_with_seats_booking":
            off = sorted((c for c in serving(src, dst, p["date"]) if cls in c["classes"]), key=lambda c: c["dep"])
            assert off and off[0]["classes"][cls]["seats"] == 0
            w = next(c for c in off if c["classes"][cls]["seats"] > 0)
            return {"train_ids": {w["train_id"]}, "answer": {"departure": hm(w["dep"]), "fare_inr": w["classes"][cls]["fare_inr"]},
                    "bookings": [(w["train_id"], cls, p["passenger"])]}
        if kind == "round_trip_booking":
            legs = []
            for a, b, d in ((src, dst, p["date"]), (dst, src, p["return_date"])):
                c = [x for x in serving(a, b, d) if cls in x["classes"]]
                assert len(c) == 1 and c[0]["classes"][cls]["seats"] > 0
                legs.append(c[0]["train_id"])
            return {"answer": {"outbound_train_id": legs[0], "return_train_id": legs[1]},
                    "bookings": [(legs[0], cls, p["passenger"]), (legs[1], cls, p["passenger"])]}
        if kind == "infeasible_budget":
            fares = [c["classes"][cls]["fare_inr"] for c in serving(src, dst, p["date"]) if cls in c["classes"]]
            assert len(fares) >= 2 and min(fares) > p["max_fare_inr"]
            return {"answer": {"status": "cannot_complete", "cheapest_fare_found": min(fares)}}
        if kind == "cross_midnight_window":
            d2 = Date.fromordinal(Date.fromisoformat(p["date"]).toordinal() + 1).isoformat()
            got = [{"train_id": c["train_id"], "departure_date": p["date"], "departure": hm(c["dep"])}
                   for c in sorted(serving(src, dst, p["date"]), key=lambda c: c["dep"]) if c["dep"] >= self._m(p["window_start"])]
            got += [{"train_id": c["train_id"], "departure_date": d2, "departure": hm(c["dep"])}
                    for c in sorted(serving(src, dst, d2), key=lambda c: c["dep"]) if c["dep"] <= self._m(p["window_end"])]
            return {"train_ids": {g["train_id"] for g in got}, "answer": {"departures": got}}
        raise KeyError(kind)

    def answer_batch5(self, kind: str, p: dict[str, Any]) -> dict[str, Any]:
        """Batch T76-T100 (benchmark 3.0): recomputed from the raw fixture JSON only (account.json, live_status.json, trains.json);
        no environment code and no solver. Rules restated here independently: refund = fare - charge (charge by class, or the
        WAITLISTED charge); no cancellation once the train has left its origin; waitlist position = people already waiting + 1;
        concession fare = fare * (100 - percent) / 100 rounded half up; a run's delay is constant; the run shown is the one in progress
        now, else today's run, else 'not running today'."""
        acct = json.loads((DATA_DIR / "account.json").read_text(encoding="utf-8"))
        live = json.loads((DATA_DIR / "live_status.json").read_text(encoding="utf-8"))
        A = {b["pnr"]: b for b in acct["account_bookings"]}
        T = {t["train_id"]: t for t in self.trains}
        now = (Date(2026, 10, 5).toordinal(), 9 * 60)  # pinned 'now' as (day ordinal, minutes)
        now_abs = now[0] * 1440 + now[1]
        refund = lambda b: b["fare_inr"] - acct["cancellation_charge_inr"]["WAITLISTED" if b["status"] == "WAITLISTED" else b["travel_class"]]  # noqa: E731
        conc = lambda tid, cls, con: (T[tid]["classes"][cls]["fare_inr"] * (100 - acct["concession_percent"][con][cls]) + 50) // 100  # noqa: E731

        def run_view(tid: str) -> dict[str, Any] | None:
            t = T[tid]
            best = None
            for back in (1, 0):
                start = now[0] - back
                if WEEKDAYS[(start - 1) % 7] not in t["operating_days"]:
                    continue
                d = next((r["delay_minutes"] for r in live["runs"] if r["train_id"] == tid
                          and Date.fromisoformat(r["run_start_date"]).toordinal() == start), 0)
                ab = lambda day, hm_: (start + (day or 0)) * 1440 + self._m(hm_) + d  # noqa: E731
                first = ab(t["stops"][0]["departure_day"], t["stops"][0]["departure"])
                last = ab(t["stops"][-1]["arrival_day"], t["stops"][-1]["arrival"])
                st = "NOT_STARTED" if now_abs < first else ("ARRIVED" if now_abs >= last else "RUNNING")
                arr = {s["station"]: ab(s["arrival_day"], s["arrival"]) for s in t["stops"] if s["arrival"]}
                if st == "RUNNING" or back == 0:
                    best = best if (best and best["status"] == "RUNNING") else {"status": st, "delay": d, "arr": arr}
            return best

        if kind == "pnr_status_lookup":
            b = A[p["pnr"]]
            return {"train_ids": {b["train_id"]}, "answer": {"booking_status": b["status"], "waitlist_position": b["waitlist_position"]}}
        if kind in ("refund_quote_no_cancel", "cancel_pnr"):
            b = A[p["pnr"]]
            assert b["status"] == "CONFIRMED"
            return {"train_ids": {b["train_id"]}, "answer": {"refund_inr": refund(b)}, "cancellations": [p["pnr"]] if kind == "cancel_pnr" else []}
        if kind in ("conditional_cancel_refund_too_low", "conditional_cancel_refund_enough"):
            b = A[p["pnr"]]
            ok = refund(b) >= p["min_refund_inr"]
            assert ok == (kind == "conditional_cancel_refund_enough")
            return {**({"train_ids": {b["train_id"]}} if ok else {}),
                    "answer": {"refund_inr": refund(b), "status": "success" if ok else "cannot_complete"}, "cancellations": [p["pnr"]] if ok else []}
        if kind == "pnr_not_found":
            assert p["pnr"] not in A
            return {"answer": {"status": "cannot_complete"}}
        if kind == "cancel_already_cancelled":
            assert A[p["pnr"]]["status"] == "CANCELLED"
            return {"answer": {"status": "cannot_complete", "booking_status": "CANCELLED"}}
        if kind == "cancel_after_departure":
            b = A[p["pnr"]]
            o = T[b["train_id"]]["stops"][0]
            assert Date.fromisoformat(b["journey_date"]).toordinal() * 1440 + self._m(o["departure"]) <= now_abs
            return {"answer": {"status": "cannot_complete"}}
        if kind in ("waitlist_fallback_booking", "sold_out_no_waitlist", "waitlist_not_needed_booking"):
            t = T[p["train_id"]]
            seats = t["classes"][p["travel_class"]]["seats"]
            if kind == "waitlist_not_needed_booking":
                assert seats > 0
                return {"train_ids": {t["train_id"]}, "answer": {"travel_class": p["travel_class"]},
                        "bookings": [(t["train_id"], p["travel_class"], p["passenger"])]}
            assert seats == 0
            if kind == "sold_out_no_waitlist":
                return {"answer": {"status": "cannot_complete"}}
            pos = acct["waitlist_baseline"].get(f"{t['train_id']}|{p['travel_class']}", 0) + 1
            return {"train_ids": {t["train_id"]}, "answer": {"waitlist_position": pos},
                    "waitlist": [(t["train_id"], p["travel_class"], p["passenger"])]}
        if kind in ("live_delay", "live_expected_arrival_intermediate", "live_connection_check", "live_running_today"):
            v = run_view(p["train_id"])
            if kind == "live_running_today":
                assert v is None
                return {"train_ids": {p["train_id"]}, "answer": {"runs_on_requested_weekday": False}}
            assert v["status"] == "RUNNING"
            if kind == "live_delay":
                return {"train_ids": {p["train_id"]}, "answer": {"delay_minutes": v["delay"]}}
            (code,) = self.codes_for(p["station_name"])
            a = v["arr"][code] % 1440
            out = {"expected_arrival": f"{a // 60:02d}:{a % 60:02d}", "delay_minutes": v["delay"]}
            if kind == "live_connection_check":
                out["makes_connection"] = a <= self._m(p["connection_time"])
            return {"train_ids": {p["train_id"]}, "answer": out}
        if kind in ("concession_fare", "concession_budget_check"):
            c = conc(p["train_id"], p["travel_class"], p["concession"])
            if kind == "concession_budget_check":
                assert c <= p["budget_inr"] < T[p["train_id"]]["classes"][p["travel_class"]]["fare_inr"]
            return {"train_ids": {p["train_id"]}, "answer": {"concession_fare_inr": c}}
        if kind == "concession_party_total":
            c = conc(p["train_id"], p["travel_class"], p["concession"])
            return {"train_ids": {p["train_id"]}, "answer": {"total_fare_inr": c + p["regular_tickets"] * T[p["train_id"]]["classes"][p["travel_class"]]["fare_inr"]}}
        if kind == "concession_not_available":
            assert p["travel_class"] not in acct["concession_percent"][p["concession"]]
            return {"answer": {"status": "cannot_complete"}}
        if kind in ("cancel_and_rebook_class", "conditional_waitlisted_cancel_rebook"):
            b = A[p["pnr"]]
            assert (b["status"] == "WAITLISTED") == (kind == "conditional_waitlisted_cancel_rebook")
            assert T[b["train_id"]]["classes"][p["new_class"]]["seats"] > 0
            return {"train_ids": {b["train_id"]}, "answer": {"refund_inr": refund(b), "travel_class": p["new_class"]},
                    "bookings": [(b["train_id"], p["new_class"], b["passenger"])], "cancellations": [p["pnr"]]}
        if kind == "conditional_waitlisted_noop":
            b = A[p["pnr"]]
            assert b["status"] == "CONFIRMED"
            return {"train_ids": {b["train_id"]}, "answer": {"booking_status": "CONFIRMED"}}
        if kind == "cancel_without_pnr_clarification":
            return {"answer": {"status": "needs_clarification"}}
        if kind == "cancel_multiple_total_refund":
            bs = [A[x] for x in p["pnrs"]]
            assert all(b["status"] == "CONFIRMED" for b in bs) and len({b["train_id"] for b in bs}) == 1
            return {"train_ids": {bs[0]["train_id"]}, "answer": {"refund_inr": sum(refund(b) for b in bs)}, "cancellations": list(p["pnrs"])}
        if kind == "availability_and_concession":
            return {"train_ids": {p["train_id"]}, "answer": {"seats_available": T[p["train_id"]]["classes"][p["travel_class"]]["seats"],
                                                            "concession_fare_inr": conc(p["train_id"], p["travel_class"], p["concession"])}}
        raise KeyError(kind)

    def answer_batch(self, kind: str, p: dict[str, Any]) -> dict[str, Any]:
        """Batch T06-T15: recomputed from raw fixture JSON only. `answer` = expected subset of the gold final_answer."""
        if kind in BATCH2_KINDS:
            return self.answer_batch2(kind, p)
        if kind in BATCH3_KINDS:
            return self.answer_batch3(kind, p)
        if kind in BATCH4_KINDS:
            return self.answer_batch4(kind, p)
        if kind in BATCH5_KINDS:
            return self.answer_batch5(kind, p)
        if kind in BATCH6_KINDS:  # T101-T200: benchmark/oracle_t101_t200.py (raw JSON only, rules restated there)
            return Oracle6().answer(kind, p)
        T = {t["train_id"]: t for t in self.trains}
        one = lambda n: next(iter(self.codes_for(n))) if len(self.codes_for(n)) == 1 else None  # noqa: E731
        if kind == "operating_days_lookup":
            t = T[p["train_id"]]
            assert t["stops"][0]["station"] == one(p["boarding_station_name"]), "boarding station must be the origin"
            return {"train_ids": {t["train_id"]}, "answer": {"operating_days": t["operating_days"],
                                                              "runs_on_requested_weekday": p["weekday"] in t["operating_days"]}}
        if kind == "class_not_offered":
            t = T[p["train_id"]]
            assert p["travel_class"] not in t["classes"]
            return {"answer": {"status": "cannot_complete", "offered_classes": sorted(t["classes"])}}
        if kind == "ambiguous_station_clarification":
            cands, dst, cls = sorted(self.codes_for(p["source_name"])), one(p["destination_name"]), p["travel_class"]
            viable = {c: [x["train_id"] for x in self.serving(c, dst, p["date"]) if cls in x["classes"] and x["classes"][cls]["seats"] > 0
                          and not (p["date"] == "2026-10-05" and x["dep"] <= 540)] for c in cands}
            assert len(cands) >= 2 and sum(1 for v in viable.values() if v) >= 2, f"ambiguity not material: {viable}"
            return {"answer": {"status": "needs_clarification", "candidate_station_codes": cands}}
        if kind in ("fallback_class_booking", "group_all_or_nothing", "cheapest_available_class"):
            t = T[p["train_id"]]
            assert p["train_id"] in [x["train_id"] for x in self.serving(one(p["source_name"]), one(p["destination_name"]), p["date"])]
            seats = {c: v["seats"] for c, v in t["classes"].items()}
            fares = {c: v["fare_inr"] for c, v in t["classes"].items()}
            if kind == "fallback_class_booking":
                assert seats[p["travel_class"]] == 0 and seats[p["fallback_class"]] > 0
                return {"train_ids": {t["train_id"]}, "answer": {"travel_class": p["fallback_class"], "fare_inr": fares[p["fallback_class"]]},
                        "bookings": [(t["train_id"], p["fallback_class"], p["passenger"])]}
            if kind == "group_all_or_nothing":
                assert 0 < seats[p["travel_class"]] < len(p["passengers"])
                return {"answer": {"status": "cannot_complete", "seats_available": seats[p["travel_class"]]}, "bookings": []}
            ok = {c: fares[c] for c in seats if seats[c] > 0}
            best = [c for c in ok if ok[c] == min(ok.values())]
            assert len(best) == 1
            return {"train_ids": {t["train_id"]}, "answer": {"travel_class": best[0], "fare_inr": ok[best[0]], "seats_available": seats[best[0]]}}
        src, dst = one(p["source_name"]), one(p["destination_name"])
        cands = self.serving(src, dst, p["date"])
        hm = lambda m: f"{m // 60:02d}:{m % 60:02d}"  # noqa: E731
        if kind == "intermediate_stop_time":
            assert len(cands) == 1
            stop = next(s for s in T[cands[0]["train_id"]]["stops"] if s["station"] == one(p["stop_name"]))
            return {"train_ids": {cands[0]["train_id"]}, "answer": {"stop_arrival_time": stop["arrival"], "stop_departure_time": stop["departure"]}}
        if kind == "empty_window_fallback":
            s, e, a = self._m(p["window_start"]), self._m(p["window_end"]), self._m(p["fallback_strictly_after"])
            assert not [c for c in cands if s <= c["dep"] <= e]
            later = sorted((c for c in cands if c["dep"] > a), key=lambda c: c["dep"])
            assert later and (len(later) == 1 or later[0]["dep"] < later[1]["dep"])
            return {"train_ids": {later[0]["train_id"]}, "answer": {"departure": hm(later[0]["dep"]), "requested_window_train_count": 0}}
        if kind == "arrival_deadline_latest_departure":
            deadline = (Date.fromisoformat(p["arrive_by_date"]) - Date.fromisoformat(p["date"])).days * 1440 + self._m(p["arrive_by_time"])
            ok = [c for c in cands if c["arr"] <= deadline]
            best = [c for c in ok if c["dep"] == max(x["dep"] for x in ok)]
            return {"train_ids": {c["train_id"] for c in best},
                    "answer": {"departure": hm(best[0]["dep"]), "arrival": hm(best[0]["arr"] % 1440),
                               "arrival_date": Date.fromordinal(Date.fromisoformat(p["date"]).toordinal() + best[0]["arr"] // 1440).isoformat()}}
        if kind == "timed_group_booking":
            m = [c for c in cands if c["dep"] == self._m(p["departure_time"])]
            assert len(m) == 1 and m[0]["classes"][p["travel_class"]]["seats"] >= len(p["passengers"])
            return {"train_ids": {m[0]["train_id"]}, "answer": {"fare_inr_per_ticket": m[0]["classes"][p["travel_class"]]["fare_inr"]},
                    "bookings": [(m[0]["train_id"], p["travel_class"], x) for x in p["passengers"]]}
        raise KeyError(kind)

    def answer(self, kind: str, p: dict[str, Any]) -> dict[str, Any]:
        if kind not in ("fare_lookup", "conditional_booking", "route_availability_fare", "constrained_choice", "cheapest_booking"):
            return self.answer_batch(kind, p)
        T = {t["train_id"]: t for t in self.trains}
        if kind == "fare_lookup":
            return {"train_ids": {p["train_id"]}, "fare_inr": T[p["train_id"]]["classes"][p["travel_class"]]["fare_inr"]}
        if kind == "conditional_booking":
            return {"seats_available": T[p["train_id"]]["classes"][p["travel_class"]]["seats"]}
        (src,), (dst,) = self.codes_for(p["source_name"]), self.codes_for(p["destination_name"])
        cands = self.serving(src, dst, p["date"])
        cls = p["travel_class"]
        if kind == "route_availability_fare":
            assert len(cands) == 1, f"expected one train, oracle found {len(cands)}"
            c = cands[0]["classes"][cls]
            return {"train_ids": {cands[0]["train_id"]}, "fare_inr": c["fare_inr"], "seats_available": c["seats"]}
        if kind == "constrained_choice":
            ok = [c for c in cands if cls in c["classes"] and c["dep"] >= self._m(p["departure_not_before"])
                  and c["classes"][cls]["fare_inr"] <= p["max_fare_inr"] and c["classes"][cls]["seats"] > 0]
            return {"train_ids": {c["train_id"] for c in ok}, "fare_inr": ok[0]["classes"][cls]["fare_inr"] if ok else None,
                    "seats_available": ok[0]["classes"][cls]["seats"] if ok else None}
        if kind == "cheapest_booking":
            offering = [c for c in cands if cls in c["classes"]]
            low = min(c["classes"][cls]["fare_inr"] for c in offering)
            best = [c for c in offering if c["classes"][cls]["fare_inr"] == low]
            return {"train_ids": {c["train_id"] for c in best}, "fare_inr": low,
                    "cheapest_has_seats": all(c["classes"][cls]["seats"] > 0 for c in best)}
        raise KeyError(kind)


BATCH2_KINDS = {"station_identity", "segment_distance", "unknown_station", "missing_passenger_clarification", "no_route_booking",
                "train_direction_conflict", "earliest_with_seats_booking", "round_trip_booking", "infeasible_budget", "cross_midnight_window"}


BATCH3_KINDS = {"seat_count_lookup", "direct_named_booking", "invalid_train_id", "unsupported_class", "past_date_booking", "alias_retry_earliest",
                "fare_conditioned_branch", "group_cheapest_any_class", "fastest_within_budget", "relative_weekday_booking", "ambiguous_class_term",
                "ambiguous_intent", "sold_out_cheapest_alternative", "runs_on_date_conditional", "connection_planning", "multi_leg_all_or_nothing",
                "mixed_class_pair_booking", "multi_constraint_booking", "overnight_arrival_date", "unsupported_action", "passenger_count_conflict",
                "disambiguation_by_train", "partial_allowed_group", "route_property_booking", "state_conditional_second_booking"}
BATCH4_KINDS = {"route_count_latest_departure", "earliest_arrival_after_time", "fare_difference_two_departures", "native_script_passenger_booking",
                "midroute_boarding_arrival", "multi_destination_departures", "relative_day_latest_with_class", "two_intent_count_and_booking",
                "retracted_booking_fare_only", "cheaper_class_arrival_deadline", "group_total_budget_check", "spoken_time_train_fare",
                "deadline_class_sold_out_infeasible", "spoken_amount_earliest_under_budget", "earliest_train_party_seats_booking",
                "next_running_day_booking", "impossible_date_clarification", "hypothetical_total_no_booking", "same_station_two_names",
                "seat_threshold_conditional_booking", "duplicate_passenger_dedup", "excluded_train_booking", "sold_out_next_departure_booking",
                "typo_train_id_clarification", "class_not_offered_take_offered"}
BATCH5_KINDS = {"pnr_status_lookup", "refund_quote_no_cancel", "cancel_pnr", "conditional_cancel_refund_too_low", "conditional_cancel_refund_enough",
                "pnr_not_found", "cancel_already_cancelled", "cancel_after_departure", "waitlist_fallback_booking", "sold_out_no_waitlist",
                "waitlist_not_needed_booking", "live_delay", "live_expected_arrival_intermediate", "live_connection_check",
                "live_running_today", "concession_fare", "concession_party_total", "concession_not_available", "concession_budget_check",
                "cancel_and_rebook_class", "conditional_waitlisted_cancel_rebook", "conditional_waitlisted_noop",
                "cancel_without_pnr_clarification", "cancel_multiple_total_refund", "availability_and_concession"}
BATCH6_KINDS = {s["solver"]["kind"] for s in _b6.SPECS}
INTENTIONALLY_INVALID_KINDS = {"invalid_train_id", "unsupported_class", "past_date_booking"}  # prompts that must contain invalid values


# ------------------------------------------------------------------ individual checks
def _check(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def _parse_dates(text: str) -> list[str]:
    """Real calendar dates written in the prompt. Impossible dates (T67: '31 November 2026') are not dates: they are skipped
    here and checked by that task's own solver/oracle (INVALID_DATE)."""
    out = []
    for d, m, y in re.findall(r"\b(\d{1,2})\s+(" + "|".join(m.title() for m in MONTHS) + r")\s+(\d{4})\b", text):
        try:
            out.append(Date(int(y), MONTHS[m.lower()], int(d)).isoformat())
        except ValueError:
            continue
    return out


def _tnum(tid: str) -> int:
    return int(tid[1:])


def validate() -> list[str]:
    errors: list[str] = []
    specs = {s.semantic_task_id: s for s in load_specs()}
    gold_file = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    oracle, ref_date = RawOracle(), RailwayEnv().reference_datetime.date()

    # 1. coverage
    _check(sorted(specs, key=_tnum) == ALL_IDS, f"spec ids {sorted(specs, key=_tnum)} != {ALL_IDS}", errors)
    _check(sorted((k for k in gold_file if not k.startswith("_")), key=_tnum) == ALL_IDS, "gold ids != task ids", errors)
    langs = sorted(p.name for p in LANG_DIR.glob("*.jsonl"))
    _check(langs == sorted(f"{l}.jsonl" for l in LANGS + EXTRA_LANGS), f"expected exactly {[l + '.jsonl' for l in LANGS + EXTRA_LANGS]}, found {langs}", errors)
    items = [BenchmarkItem(**json.loads(l)) for l in (LANG_DIR / "en.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    _check([i.semantic_task_id for i in items] == ALL_IDS, f"en.jsonl must hold exactly {ALL_IDS[0]}..{ALL_IDS[-1]} in order", errors)
    _check(all(i.task_id == f"{i.semantic_task_id}_en" and i.language == "en" for i in items), "bad task_id/language in en.jsonl", errors)
    for key in ("language", "query", "task_id"):
        _check(key not in json.loads(SPEC_PATH.read_text(encoding="utf-8"))["tasks"][0], f"spec must not contain '{key}'", errors)
        _check(all(key not in g for k, g in gold_file.items() if not k.startswith("_")), f"gold must not contain '{key}'", errors)

    # 2. gold reproducibility (no hand edits)
    _check(render(build_all()) == GOLD_PATH.read_text(encoding="utf-8"), "gold_labels.json != regenerated gold (hand-edited or stale)", errors)
    _check(render(build_all()) == render(build_all()), "gold generation is not deterministic", errors)
    # pilot freeze (T01-T05 spec + gold entries must never change)
    _check(_sha({t: gold_file.get(t) for t in PILOT_IDS}) == FROZEN_PILOT_GOLD_SHA256, "pilot T01-T05 gold changed (frozen)", errors)
    _check(_sha([t for t in json.loads(SPEC_PATH.read_text(encoding="utf-8"))["tasks"] if t["semantic_task_id"] in PILOT_IDS])
           == FROZEN_PILOT_SPEC_SHA256, "pilot T01-T05 specs changed (frozen)", errors)
    _check(_sha({t: gold_file.get(t) for t in FROZEN_T01_T15_IDS}) == FROZEN_T01_T15_GOLD_SHA256, "T01-T15 gold changed (frozen)", errors)
    _check(_sha({t: gold_file.get(t) for t in FROZEN_T01_T25_IDS}) == FROZEN_T01_T25_GOLD_SHA256, "T01-T25 gold changed (frozen)", errors)
    _check(_sha([t for t in json.loads(SPEC_PATH.read_text(encoding="utf-8"))["tasks"] if t["semantic_task_id"] in FROZEN_T01_T25_IDS])
           == FROZEN_T01_T25_SPEC_SHA256, "T01-T25 specs changed (frozen)", errors)
    _check(_sha([t for t in json.loads(SPEC_PATH.read_text(encoding="utf-8"))["tasks"] if t["semantic_task_id"] in FROZEN_T01_T15_IDS])
           == FROZEN_T01_T15_SPEC_SHA256, "T01-T15 specs changed (frozen)", errors)
    _check(_sha({t: gold_file.get(t) for t in FROZEN_T01_T50_IDS}) == FROZEN_T01_T50_GOLD_SHA256, "T01-T50 gold changed (frozen)", errors)
    _check(_sha([t for t in json.loads(SPEC_PATH.read_text(encoding="utf-8"))["tasks"] if t["semantic_task_id"] in FROZEN_T01_T50_IDS])
           == FROZEN_T01_T50_SPEC_SHA256, "T01-T50 specs changed (frozen)", errors)

    for item in items:
        tid, spec, gold = item.semantic_task_id, specs[item.semantic_task_id], gold_file[item.semantic_task_id]
        GoldSpec(**gold)  # schema-valid
        p, kind = spec.solver.params, spec.solver.kind
        _check(spec.category == item.category == EXPECTED_CATEGORY[tid], f"{tid}: category mismatch", errors)
        # Three tool stages, each offered only its own tools (evaluation/runner.offered_tools): T01-T75 the six tools of 2.x,
        # T76-T100 twelve, T101-T200 all twenty.
        want_tools = V2_TOOLS if int(tid[1:]) <= 75 else V3_TOOLS if int(tid[1:]) <= 100 else TOOL_NAMES
        _check(set(spec.allowed_tools) == set(want_tools) and item.allowed_tools == spec.allowed_tools, f"{tid}: allowed_tools", errors)

        # 3. initial state assumptions
        env = RailwayEnv()
        env.reset()
        for chk in spec.initial_state_checks:
            r = env.call(chk.tool, chk.args)
            _check(r["ok"] and all(r["data"].get(k) == v for k, v in chk.expect.items()),
                   f"{tid}: initial-state check failed {chk.tool}{chk.args} -> {r}", errors)
        _check(env.snapshot()["bookings"] == [], f"{tid}: baseline must have no bookings", errors)

        # 4. replay gold calls
        base = json.loads(json.dumps(env.snapshot()))
        ids = [c["call_id"] for c in gold["required_calls"]]
        _check(ids == [f"c{i}" for i in range(1, len(ids) + 1)], f"{tid}: call ids not sequential", errors)
        _check(gold["min_calls"] == sum(1 for c in gold["required_calls"] if not c.get("optional")), f"{tid}: min_calls", errors)
        for e in gold["dependency_edges"]:
            _check(ids.index(e["before"]) < ids.index(e["after"]), f"{tid}: edge {e} is not a forward edge", errors)
        names = [v for k, v in p.items() if (k.endswith("_name") or k == "recovered_station") and isinstance(v, str)]
        for c in gold["required_calls"]:
            args = dict(c["required_args"])
            target = None
            for k, v in c["required_args"].items():
                if isinstance(v, dict) and ("resolves_to" in v or "resolves_ambiguous" in v or "resolves_to_none" in v):  # name matcher
                    target = ({v["resolves_to"]} if "resolves_to" in v else set(v["resolves_ambiguous"]) if "resolves_ambiguous" in v else set())
                    cand = [n for n in names if oracle.codes_for(n) == target]
                    _check(bool(cand), f"{tid}: {c['call_id']} matcher {v} matches no spec station name", errors)
                    args[k] = cand[0] if cand else ""
            r = env.call(c["tool"], args)
            if c.get("expected_error"):
                _check(not r["ok"] and r["error"]["code"] == c["expected_error"],
                       f"{tid}: gold call {c['call_id']} should fail with {c['expected_error']}, got {r}", errors)
                continue
            _check(r["ok"], f"{tid}: gold call {c['call_id']} {c['tool']}{args} failed: {r.get('error')}", errors)
            if r["ok"] and target is not None:
                got = {x["code"] for x in r["data"]["candidates"]}
                _check(got == target and r["data"]["ambiguous"] == (len(target) > 1), f"{tid}: {c['call_id']} resolved to {got}, expected {target}", errors)
        diff = env_diff(base, env.snapshot())
        # state-changing gold calls must be only the ones in the expected diff (replay of ALL gold calls)
        _check(diff == gold["expected_env_diff"], f"{tid}: replayed env diff {diff} != gold {gold['expected_env_diff']}", errors)
        n_book = sum(1 for c in gold["required_calls"] if c["tool"] == "book_ticket" and not c.get("expected_error"))
        _check(len(gold["expected_env_diff"]["bookings"]) == n_book, f"{tid}: booking flag mismatch", errors)
        _check(len(gold["final_state"]["expected_bookings"]) == n_book, f"{tid}: expected_bookings count", errors)
        freed = sum(1 for c in gold["expected_env_diff"].get("cancellations", []) if c["previous_status"] == "CONFIRMED")  # 3.0
        _check(sum(-d for d in (b - a for a, b in gold["expected_env_diff"]["availability_changes"].values())) == n_book - freed,
               f"{tid}: seat change != bookings - freed seats of cancelled confirmed tickets", errors)

        # 5. independent oracle
        o, fa = oracle.answer(kind, p), gold["final_answer"]
        if "train_ids" in o:
            _check(len(o["train_ids"]) == 1, f"{tid}: answer not unique per oracle: {o['train_ids']}", errors)
            _check(o["train_ids"] == set(gold["final_state"]["allowed_train_ids"] or []), f"{tid}: oracle train {o['train_ids']} != gold", errors)
        for k in ("fare_inr", "seats_available"):
            if k in o and o[k] is not None and k in fa:
                _check(o[k] == fa[k], f"{tid}: oracle {k}={o[k]} != gold {fa[k]}", errors)
        if kind == "cheapest_booking":
            _check(o["cheapest_has_seats"], f"{tid}: cheapest train sold out -> not a plain booking task", errors)
        if kind == "conditional_booking":
            _check((o["seats_available"] == 0) == (fa["status"] == "cannot_complete"), f"{tid}: sold-out/status mismatch", errors)
        for k, v in o.get("answer", {}).items():  # batch kinds: every oracle-derived answer field must equal gold
            _check(fa.get(k) == v, f"{tid}: oracle {k}={v!r} != gold {fa.get(k)!r}", errors)
        if "cancellations" in o:  # 3.0
            _check(sorted(o["cancellations"]) == sorted(gold["final_state"].get("expected_cancellations") or []),
                   f"{tid}: oracle cancellations {o['cancellations']} != gold", errors)
        if "waitlist" in o:
            _check(sorted(o["waitlist"]) == sorted((w["train_id"], w["travel_class"], w["passenger"])
                                                   for w in gold["final_state"].get("expected_waitlist") or []), f"{tid}: oracle waitlist != gold", errors)
        want_eff = {k: sorted(v) for k, v in o.get("effects", {}).items()}  # 20-tool stage: Tatkal, boarding, meals, TDR, complaints
        got_eff = {k: sorted(tuple(e[f] for f in EFFECT_FIELDS[k]) for e in v) for k, v in (gold["final_state"].get("expected_effects") or {}).items()}
        _check(want_eff == got_eff, f"{tid}: oracle effects {want_eff} != gold {got_eff}", errors)
        if "bookings" in o:
            _check(sorted(o["bookings"]) == sorted((b["train_id"], b["travel_class"], b["passenger"]) for b in gold["final_state"]["expected_bookings"]),
                   f"{tid}: oracle bookings {o['bookings']} != gold", errors)
        if "train_ids" not in o:
            _check(gold["final_state"]["allowed_train_ids"] is None, f"{tid}: gold selects a train but the task has no selection", errors)

        # 6. prompt hygiene
        q = item.query
        for tr in re.findall(r"\bBTB\d{3}\b", q):
            _check(tr in oracle_train_ids(oracle) or (kind == "invalid_train_id" and tr == p["train_id"]), f"{tid}: prompt mentions unknown train {tr}", errors)
        for key, name in p.items():
            if key.endswith("_name") and name:
                n_codes = len(oracle.codes_for(name))
                want_ambiguous = kind in ("ambiguous_station_clarification", "disambiguation_by_train") and key == "source_name"
                want_unknown = kind in ("unknown_station", "alias_retry_earliest") and key == "source_name"
                _check((n_codes >= 2 if want_ambiguous else n_codes == 0 if want_unknown else n_codes == 1) and name.lower() in q.lower(),
                       f"{tid}: station {name!r} missing/ambiguous", errors)
        for d in _parse_dates(q):
            _check(d in (p.get("date"), p.get("return_date"), p.get("second_date"))
                   and (Date.fromisoformat(d) > ref_date or kind == "past_date_booking"), f"{tid}: prompt date {d} != spec date or not in the future", errors)
        if kind == "past_date_booking":
            _check(Date.fromisoformat(p["date"]) < ref_date, f"{tid}: past-date task must use a past date", errors)
        if "date" in p:
            _check(bool(_parse_dates(q)), f"{tid}: prompt has no explicit date", errors)
        for ck in ("travel_class", "fallback_class"):
            if ck in p:
                _check(re.search(rf"\b{p[ck]}\b", q) is not None, f"{tid}: class {p[ck]} not in prompt", errors)
        for pax in ([p["passenger"]] if "passenger" in p else []) + list(p.get("passengers", [])):
            _check(pax in q, f"{tid}: passenger name not in prompt", errors)
            _check(bool(re.match(r"^[A-Za-z][A-Za-z .'\-]{1,59}$", pax)),
                   f"{tid}: passenger name must be Latin letters (environment rule)", errors)
        _check(not any(t in q.lower() for t in TOOL_NAMES), f"{tid}: prompt leaks a tool name", errors)

        # 7. prohibited actions: only where the prompt explicitly says so, traceable, never contradicting gold
        _check(gold["prohibited_actions"] == json.loads(json.dumps([a.model_dump() for a in spec.prohibited_actions])),
               f"{tid}: gold prohibited_actions != spec", errors)
        _check(gold["forbidden_tools"] == sorted({a.tool for a in spec.prohibited_actions if not a.match}), f"{tid}: forbidden_tools", errors)
        _check(bool(spec.prohibited_actions) == (tid in EXPECT_PROHIBITIONS), f"{tid}: prohibitions present/absent unexpectedly", errors)
        for a in spec.prohibited_actions:
            _check(a.tool in TOOL_NAMES, f"{tid}: prohibited tool {a.tool} unknown", errors)
            _check(norm_quotes(a.prompt_phrase).lower() in norm_quotes(q).lower(), f"{tid}: prompt_phrase {a.prompt_phrase!r} not in prompt", errors)
            _check(all(not (c["tool"] == a.tool and all(c["required_args"].get(k) == v for k, v in a.match.items()))
                       for c in gold["required_calls"]), f"{tid}: gold call violates prohibition", errors)

        # 8. time-bound wording must agree with the gold constraint (T03: ">= 18:00" <=> "at or after 6 PM")
        if tid == "T03":
            ge = [c for c in spec.constraints if c["kind"] == "departure_time"]
            _check(len(ge) == 1 and ge[0]["op"] == ">=" and ge[0]["value"] == "18:00" == p["departure_not_before"], "T03: spec constraint != >= 18:00", errors)
            _check("at or after 6 PM" in q and "after 6 PM" not in q.replace("at or after 6 PM", ""), "T03: prompt must say 'at or after 6 PM' (inclusive)", errors)
            _check(gold["required_calls"][2]["required_args"]["time_window"]["start"] == "18:00", "T03: gold time_window start != 18:00", errors)

    validate_languages(specs, gold_file, oracle, ref_date, errors)
    validate_gujarati(specs, oracle, ref_date, errors)
    validate_human_review(errors)
    validate_t51_t75_freeze(gold_file, errors)
    from .semantic_overlap import overlap_errors  # duplicate / semantic-overlap check over every task
    errors += overlap_errors(specs, gold_file)
    return errors


def validate_t51_t75_freeze(gold_file: dict[str, Any], errors: list[str]) -> None:
    """T51-T75 are frozen like T01-T50: spec, gold, rows 51-75 of the five language files and the two audits."""
    spec_tasks = json.loads(SPEC_PATH.read_text(encoding="utf-8"))["tasks"]
    _check(_sha({t: gold_file.get(t) for t in FROZEN_T51_T75_IDS}) == FROZEN_T51_T75_GOLD_SHA256, "T51-T75 gold changed (frozen)", errors)
    _check(_sha([t for t in spec_tasks if t["semantic_task_id"] in FROZEN_T51_T75_IDS]) == FROZEN_T51_T75_SPEC_SHA256, "T51-T75 specs changed (frozen)", errors)
    for lang, want in FROZEN_T51_T75_LANG_SHA256.items():
        f = LANG_DIR / f"{lang}.jsonl"
        got = hashlib.sha256(_hr.draft_slice_bytes(f, 50, 75)).hexdigest() if f.exists() else None
        _check(got == want, f"{lang}.jsonl rows T51-T75 changed (frozen)", errors)
    for path, want, label in ((BATCH4_AUDIT_PATH, FROZEN_T51_T75_AUDIT_SHA256, "T51-T75 audit file"),
                              (GU2_AUDIT_PATH, FROZEN_GU_T51_T75_AUDIT_SHA256, "Gujarati T51-T75 audit file")):
        _check(path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == want, f"{label} changed (frozen)", errors)


def _sha(obj: Any) -> str:
    import hashlib
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ multilingual draft layer (T01-T05 x 4)
def _load_lang(lang: str, errors: list[str]) -> list[dict[str, Any]]:
    f = LANG_DIR / f"{lang}.jsonl"
    if not f.exists():
        errors.append(f"missing {f.name}")
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def validate_languages(specs: dict, gold_file: dict, oracle: "RawOracle", ref_date: Date, errors: list[str]) -> None:
    import hashlib

    rows: dict[str, list[dict[str, Any]]] = {l: _load_lang(l, errors) for l in LANGS}
    flat = [r for l in LANGS for r in rows[l]]
    # 1-3, 7: counts and uniqueness
    n_items = len(ALL_IDS) * len(LANGS)
    _check(len(flat) == n_items, f"expected exactly {n_items} language items, found {len(flat)}", errors)
    _check(len({r["task_id"] for r in flat}) == len(flat), "duplicate task_id among language items", errors)
    _check(len({r["semantic_task_id"] for r in flat}) == len(ALL_IDS) and {r["semantic_task_id"] for r in flat} == set(ALL_IDS),
           f"expected exactly the {len(ALL_IDS)} semantic tasks {ALL_IDS[0]}-{ALL_IDS[-1]}", errors)
    for tid in ALL_IDS:
        got = sorted(r["language"] for r in flat if r["semantic_task_id"] == tid)
        _check(got == sorted(LANGS), f"{tid}: variants {got} != {sorted(LANGS)}", errors)
    # 8: required fields / schema (extra keys rejected so nothing like a language-specific gold key sneaks in)
    fields = set(BenchmarkItem.model_fields)
    for r in flat:
        _check(set(r) == fields, f"{r.get('task_id')}: fields {sorted(set(r) ^ fields)} differ from BenchmarkItem schema", errors)
        try:
            BenchmarkItem(**r)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{r.get('task_id')}: schema error {e}")
            continue
        _check(bool(r["query"].strip()), f"{r['task_id']}: empty query", errors)
    # 4: id <-> language <-> file mapping
    for lang in LANGS:
        _check([r["semantic_task_id"] for r in rows[lang]] == ALL_IDS, f"{lang}.jsonl must hold {ALL_IDS[0]}..{ALL_IDS[-1]} in order", errors)
        for r in rows[lang]:
            _check(r["language"] == lang and r["task_id"] == f"{r['semantic_task_id']}_{lang}", f"{r['task_id']}: id/language mismatch in {lang}.jsonl", errors)
    # 6: pilot rows frozen (English pilot hash unchanged since the pilot; same for the 3 draft languages)
    for lang in LANGS:
        f = LANG_DIR / f"{lang}.jsonl"
        if f.exists():
            head = _hr.draft_head_bytes(f, len(PILOT_IDS))
            _check(hashlib.sha256(head).hexdigest() == FROZEN_PILOT_LANG_SHA256[lang],
                   f"{lang}.jsonl pilot rows T01-T05 changed (frozen)" + (" (en.jsonl hash changed (English is frozen))" if lang == "en" else ""), errors)
    _check(FROZEN_PILOT_LANG_SHA256["en"] == FROZEN_EN_SHA256, "frozen English hash constants disagree", errors)
    for lang in LANGS:  # T01-T15 rows (first 15 lines) frozen since the T06-T15 export
        f = LANG_DIR / f"{lang}.jsonl"
        if f.exists():
            head = _hr.draft_head_bytes(f, len(FROZEN_T01_T15_IDS))
            _check(hashlib.sha256(head).hexdigest() == FROZEN_T01_T15_LANG_SHA256[lang], f"{lang}.jsonl rows T01-T15 changed (frozen)", errors)
    for lang in LANGS:  # T01-T50 rows (first 50 lines) frozen since the T51-T75 export
        f = LANG_DIR / f"{lang}.jsonl"
        if f.exists():
            head = _hr.draft_head_bytes(f, len(FROZEN_T01_T50_IDS))
            _check(hashlib.sha256(head).hexdigest() == FROZEN_T01_T50_LANG_SHA256[lang], f"{lang}.jsonl rows T01-T50 changed (frozen)", errors)
    for lang in LANGS:  # T01-T25 rows (first 25 lines) frozen since the T16-T25 export
        f = LANG_DIR / f"{lang}.jsonl"
        if f.exists():
            head = _hr.draft_head_bytes(f, len(FROZEN_T01_T25_IDS))
            _check(hashlib.sha256(head).hexdigest() == FROZEN_T01_T25_LANG_SHA256[lang], f"{lang}.jsonl rows T01-T25 changed (frozen)", errors)
    batch_of = {t: b for b in BATCHES for t in b.BATCH_IDS}
    for r in rows["en"]:
        if r["semantic_task_id"] in PILOT_IDS:
            _check(r["query"] == FROZEN_EN_QUERIES.get(r["semantic_task_id"]), f"{r['task_id']}: English query changed", errors)
        else:  # batch English must equal its single source of truth
            b = batch_of.get(r["semantic_task_id"])
            src = f"{b.__name__.split('.')[-1]}.py" if b else "a batch module"
            _check(b is not None and r["query"] == b.EN_ITEMS[r["semantic_task_id"]]["query"], f"{r['task_id']}: English query out of sync with {src}", errors)
            _check(b is not None and r["author"] == b.EN_AUTHOR, f"{r['task_id']}: English batch author must be {getattr(b, 'EN_AUTHOR', '?')!r}", errors)
    for r in flat:
        b = batch_of.get(r["semantic_task_id"])
        if r["language"] != "en" and b is not None:
            _check(r["query"] == b.QUERIES[r["language"]].get(r["semantic_task_id"]),
                   f"{r['task_id']}: query out of sync with {b.__name__.split('.')[-1]}.py", errors)
    # 5: all variants of a task share ONE gold spec (no per-language gold; shared category/tools)
    en = {r["semantic_task_id"]: r for r in rows["en"]}
    for r in flat:
        tid = r["semantic_task_id"]
        _check(tid in gold_file and tid in specs, f"{r['task_id']}: no shared gold/spec for {tid}", errors)
        _check(r["category"] == en[tid]["category"] == specs[tid].category, f"{r['task_id']}: category differs from shared spec", errors)
        _check(r["allowed_tools"] == en[tid]["allowed_tools"] == specs[tid].allowed_tools, f"{r['task_id']}: allowed_tools differ", errors)
    _check(not any(l in k.lower() for k in gold_file for l in ("hinglish", "_hi", "_mr", "_en")), "gold has per-language keys", errors)
    # 9-10: review fields must match benchmark/human_review.py (reviewed items) - everything else stays an unreviewed draft
    for r in flat:
        exp_reviewer, exp_status = _hr.expected_review(r["language"], r["semantic_task_id"])
        _check(r["review_status"] == exp_status, f"{r['task_id']}: review_status must be '{exp_status}'", errors)
        _check(r["reviewer"] == exp_reviewer,
               f"{r['task_id']}: reviewer must be null before human review" if exp_reviewer is None
               else f"{r['task_id']}: reviewer must be {exp_reviewer!r} (human_review.py)", errors)
        _check(not any(w in json.dumps({k: v for k, v in r.items() if k not in ("query", "allowed_tools")}).lower() for w in BANNED_STATUS_WORDS),
               f"{r['task_id']}: item claims verification/acceptance", errors)
        if r["language"] != "en":
            _check(r["author"] == NON_EN_AUTHOR, f"{r['task_id']}: author must be {NON_EN_AUTHOR!r}", errors)
    # per-item semantic-equivalence surface checks + cross-variant invariants
    code_of = lambda n: next(iter(oracle.codes_for(n)))  # noqa: E731
    for tid in ALL_IDS:
        p = specs[tid].solver.params
        variants = {r["language"]: r["query"] for r in flat if r["semantic_task_id"] == tid}
        if sorted(variants) != sorted(LANGS):
            continue
        sigs = {l: numeric_signature(q) for l, q in variants.items()}
        _check(len({json.dumps(v) for v in sigs.values()}) == 1, f"{tid}: numbers differ across variants {sigs}", errors)
        for l, q in variants.items():
            _check(not any(t in q.lower() for t in TOOL_NAMES), f"{tid}_{l}: leaks a tool name", errors)
            _check("NDLS" not in q and not re.search(r"\b(JP|ADI|MMCT|NGP)\b", q), f"{tid}_{l}: exposes an internal station code", errors)
            for d in parse_dates_lang(q, l):
                _check(Date.fromisoformat(d) > ref_date or specs[tid].solver.kind == "past_date_booking", f"{tid}_{l}: date {d} not in the future", errors)
            res = run_checks(tid, l, q, p, code_of)
            for k, v in res.items():
                _check(v is not False, f"{tid}_{l}: surface check {k} FAILED", errors)
            native = p.get("passenger_script_forms", {}).get(l)
            for pax in ([p["passenger"]] if "passenger" in p else []) + list(p.get("passengers", [])):
                if native:  # declared language feature (T54 hi/mr): native-script name instead of the Latin one, by design
                    _check(native in q and pax not in q and not re.search(r"[A-Za-z]", native), f"{tid}_{l}: declared native-script passenger form missing", errors)
                    continue
                _check(re.search(r"[A-Za-z]", pax) is not None and pax in q, f"{tid}_{l}: passenger must stay Latin and identical", errors)
        # 11-14: the specific wording requirements, per language
        if tid == "T03":
            for l, q in variants.items():
                r = run_checks(tid, l, q, p, code_of)
                _check(r["time_constraint_preserved"] is True, f"T03_{l}: missing inclusive 'at or after 6 PM' equivalent", errors)       # 11
                _check(r["forbidden_action_preserved"] is True, f"T03_{l}: missing no-booking requirement", errors)                         # 12
                _check(r["fare_constraint_preserved"] is True and r["time_preserved"] is True, f"T03_{l}: budget/time missing", errors)
                _check(r["availability_constraint_preserved"] is True, f"T03_{l}: missing explicit seats-available requirement", errors)
        if tid == "T04":
            for l, q in variants.items():
                r = run_checks(tid, l, q, p, code_of)
                _check(r["booking_condition_preserved"] is True and r["fare_constraint_preserved"] is True, f"T04_{l}: booking/cheapest missing", errors)   # 13
        if tid == "T05":
            for l, q in variants.items():
                r = run_checks(tid, l, q, p, code_of)
                _check(r["availability_constraint_preserved"] is True and r["fallback_condition_preserved"] is True
                       and r["forbidden_action_preserved"] is True and r["booking_condition_preserved"] is True,
                       f"T05_{l}: sold-out / no-fallback / no-booking wording incomplete", errors)                                          # 14
    # audit files: the automated drafting audits (query text in sync with the language files; they record the draft stage and
    # stay review_status="draft" / pending_human_review - the human review itself is recorded in languages/human_review.json)
    for path, ids in ((AUDIT_PATH, PILOT_IDS), (LANG_DIR / BATCH_AUDIT_PATH.name, BATCH_IDS), (LANG_DIR / BATCH2_AUDIT_PATH.name, _b2.BATCH_IDS),
                       (LANG_DIR / BATCH3_AUDIT_PATH.name, _b3.BATCH_IDS), (LANG_DIR / BATCH4_AUDIT_PATH.name, _b4.BATCH_IDS),
                       (BATCH5_AUDIT_PATH, _b5.BATCH_IDS), (BATCH6_AUDIT_PATH, _b6.BATCH_IDS)):
        _validate_audit(path, ids, flat, errors)
    f = LANG_DIR / BATCH_AUDIT_PATH.name
    _check(f.exists() and hashlib.sha256(f.read_bytes()).hexdigest() == FROZEN_T06_T15_AUDIT_SHA256, "T06-T15 audit file changed (frozen)", errors)
    f2 = LANG_DIR / BATCH2_AUDIT_PATH.name
    _check(f2.exists() and hashlib.sha256(f2.read_bytes()).hexdigest() == FROZEN_T16_T25_AUDIT_SHA256, "T16-T25 audit file changed (frozen)", errors)
    f3 = LANG_DIR / BATCH3_AUDIT_PATH.name
    _check(f3.exists() and hashlib.sha256(f3.read_bytes()).hexdigest() == FROZEN_T26_T50_AUDIT_SHA256, "T26-T50 audit file changed (frozen)", errors)


GU_AUDIT_PATH = LANG_DIR / "batch_gu_T01_T50_language_audit.json"
GU2_AUDIT_PATH = LANG_DIR / "batch_gu_T51_T75_language_audit.json"
# Freeze of the Gujarati T01-T50 drafts when T51-T75 were added: first 50 lines of gu.jsonl and the T01-T50 Gujarati audit.
# (Update on purpose when the native Gujarati review edits a T01-T50 item.) Updated 2026-11-24 for the T02/T23 wording fixes.
FROZEN_GU_T01_T50_LANG_SHA256 = "e85e43d8df794e298729c2a044b5f781d5eb80ea840708e3e946aa4414dd502a"
FROZEN_GU_T01_T50_AUDIT_SHA256 = "d686ed10ed3908073d3b8c57915a2667d125bdf6083cb7aeca87227c7503bc29"


def validate_gujarati(specs: dict, oracle: "RawOracle", ref_date: Date, errors: list[str]) -> None:
    """Gujarati (gu.jsonl): covers batch_gujarati.GU_IDS (all 75 tasks). Same per-item rules as the other non-English
    languages (shared spec/gold, draft only, same numbers as English, surface checks, Latin passengers, future dates), plus:
    no Gujarati/Devanagari digits, and every marker the task has in the other languages has a Gujarati counterpart."""
    rows = _load_lang("gu", errors)
    ids = _gu.GU_IDS
    _check([r.get("semantic_task_id") for r in rows] == ids, f"gu.jsonl must hold exactly {ids[0]}..{ids[-1]} in order", errors)
    en = {r["semantic_task_id"]: r for r in _load_lang("en", errors)}
    fields = set(BenchmarkItem.model_fields)
    code_of = lambda n: next(iter(oracle.codes_for(n)))  # noqa: E731
    from .language_checks import _M
    for r in rows:
        tid = r.get("semantic_task_id")
        if tid not in en or tid not in specs:
            errors.append(f"gu: unknown task {tid}")
            continue
        _check(set(r) == fields, f"{tid}_gu: fields differ from BenchmarkItem schema", errors)
        try:
            BenchmarkItem(**r)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{tid}_gu: schema error {e}")
            continue
        q, p, e = r["query"], specs[tid].solver.params, en[tid]
        _check(r["task_id"] == f"{tid}_gu" and r["language"] == "gu", f"{tid}_gu: id/language mismatch", errors)
        _check(q == _gu.QUERIES.get(tid), f"{tid}_gu: query out of sync with batch_gujarati.py", errors)
        _check(r["category"] == e["category"] == specs[tid].category and r["allowed_tools"] == e["allowed_tools"] == specs[tid].allowed_tools,
               f"{tid}_gu: category/allowed_tools differ from the shared spec", errors)
        _check(r["tags"] == [*e["tags"], "gujarati"], f"{tid}_gu: tags must be the English tags + 'gujarati'", errors)
        _check((r["reviewer"], r["review_status"]) == _hr.expected_review("gu", tid) and r["author"] == NON_EN_AUTHOR,
               f"{tid}_gu: review fields must match human_review.py" if tid in _hr.REVIEWED.get("gu", []) else f"{tid}_gu: must be an unreviewed draft", errors)
        _check(numeric_signature(q) == numeric_signature(e["query"]), f"{tid}_gu: numbers differ from English", errors)
        _check(not re.search("[\u0AE6-\u0AEF\u0966-\u096F]", q), f"{tid}_gu: Gujarati/Devanagari digits are not used in the benchmark", errors)
        _check(re.search("[\u0A80-\u0AFF]", q) is not None, f"{tid}_gu: query is not in Gujarati script", errors)
        _check(not any(t in q.lower() for t in TOOL_NAMES), f"{tid}_gu: leaks a tool name", errors)
        _check("NDLS" not in q and not re.search(r"\b(JP|ADI|MMCT|NGP)\b", q), f"{tid}_gu: exposes an internal station code", errors)
        for d in parse_dates_lang(q, "gu"):
            _check(Date.fromisoformat(d) > ref_date or specs[tid].solver.kind == "past_date_booking", f"{tid}_gu: date {d} not in the future", errors)
        missing = [k for k, v in _M[tid].items() if isinstance(v, dict) and "gu" not in v]
        _check(not missing, f"{tid}_gu: no Gujarati marker for {missing}", errors)
        if missing:
            continue
        for k, v in run_checks(tid, "gu", q, p, code_of).items():
            _check(v is not False, f"{tid}_gu: surface check {k} FAILED", errors)
        native = p.get("passenger_script_forms", {}).get("gu")
        for pax in ([p["passenger"]] if "passenger" in p else []) + list(p.get("passengers", [])):
            if native:  # declared language feature (T54): the Gujarati-script name instead of the Latin one, by design
                _check(native in q and pax not in q and not re.search(r"[A-Za-z]", native), f"{tid}_gu: declared native-script passenger form missing", errors)
                continue
            _check(re.search(r"[A-Za-z]", pax) is not None and pax in q, f"{tid}_gu: passenger must stay Latin and identical", errors)
    f = LANG_DIR / "gu.jsonl"
    if f.exists():
        head = _hr.draft_head_bytes(f, 50)
        _check(hashlib.sha256(head).hexdigest() == FROZEN_GU_T01_T50_LANG_SHA256, "gu.jsonl rows T01-T50 changed (frozen)", errors)
    if GU_AUDIT_PATH.exists():
        _check(hashlib.sha256(GU_AUDIT_PATH.read_bytes()).hexdigest() == FROZEN_GU_T01_T50_AUDIT_SHA256, "Gujarati T01-T50 audit file changed (frozen)", errors)
    by_id = {r["task_id"]: r for r in rows}
    for path, part in ((GU_AUDIT_PATH, _gu.GU_IDS_T01_T50), (GU2_AUDIT_PATH, _gu.GU_IDS_T51_T75),
                       (LANG_DIR / "batch_gu_T76_T100_language_audit.json", _gu.GU_IDS_T76_T100),
                       (LANG_DIR / "batch_gu_T101_T200_language_audit.json", _gu.GU_IDS_T101_T200)):
        _validate_gu_audit(path, part, by_id, errors)


def _validate_gu_audit(path: Path, ids: list[str], by_id: dict[str, dict[str, Any]], errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"{path.name} missing")
        return
    audit = json.loads(path.read_text(encoding="utf-8"))["records"]
    _check([a["task_id"] for a in audit] == [f"{t}_gu" for t in ids], f"{path.name}: must cover {ids[0]}_gu..{ids[-1]}_gu in order", errors)
    for a in audit:
        r = by_id.get(a["task_id"])
        _check(r is not None and a["query"] == r["query"] and a["review_status"] == "draft" and a["language"] == "gu",
               f"audit record {a.get('task_id')} out of sync with gu.jsonl", errors)
        _check(list(a["checks"]) == CHECKS and all(v is not False for v in a["checks"].values()), f"audit {a['task_id']}: checks", errors)
        _check(all(a[k] == "pending_human_review" for k in ("human_review", "fluency_review", "equivalence_review")),
               f"audit {a['task_id']}: review fields must be pending_human_review", errors)
        _check(all(set(a["translation_flags"].get(k, {})) == {"flag", "detail"} for k in ("potential_ambiguity", "unnatural_wording", "constraint_risk", "notes")),
               f"audit {a['task_id']}: translation flags incomplete", errors)


def _validate_audit(path: Path, ids: list[str], flat: list[dict[str, Any]], errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"{path.name} missing")
        return
    audit = json.loads(path.read_text(encoding="utf-8"))["records"]
    n = len(ids) * len(LANGS)
    _check(len(audit) == n, f"audit must have {n} records, has {len(audit)} ({path.name})", errors)
    _check(sorted({a["semantic_task_id"] for a in audit}, key=_tnum) == ids, f"{path.name}: covers {sorted({a['semantic_task_id'] for a in audit})}, expected {ids}", errors)
    by_id = {r["task_id"]: r for r in flat}
    for a in audit:
        r = by_id.get(a["task_id"])
        _check(r is not None and a["query"] == r["query"] and a["review_status"] == "draft"
               and a["semantic_task_id"] == r["semantic_task_id"] and a["language"] == r["language"],
               f"audit record {a.get('task_id')} out of sync with language files", errors)
        _check(list(a["checks"]) == CHECKS, f"audit {a['task_id']}: check names", errors)
        _check(all(a[k] == "pending_human_review" for k in ("human_review", "fluency_review", "equivalence_review")),
               f"audit {a['task_id']}: review fields must be pending_human_review", errors)
        if a["language"] != "en":
            _check(all(set(a["translation_flags"].get(k, {})) == {"flag", "detail"} for k in ("potential_ambiguity", "unnatural_wording", "constraint_risk", "notes")),
                   f"audit {a['task_id']}: translation flags incomplete", errors)


EXPECT_PROHIBITIONS = {"T03", "T05", "T15", "T39", "T41",  # the only prompts (T01-T75) in which the user explicitly forbids something
                       "T59", "T60", "T72",
                       "T77", "T85", "T92",  # 3.0 batch: 'Don't cancel it yet', 'don't put him on the waitlist', 'Don't book anything yet'
                       "T104", "T109", "T140", "T175", "T196"}  # 20-tool batch: 'not the general quota', 'don't put her on the waitlist',
#                        "don't change the booking", "Don't file it yet", "Don't book anything"


def norm_quotes(t: str) -> str:
    return t.replace("\u2019", "'").replace("\u2018", "'")


def oracle_train_ids(o: RawOracle) -> set[str]:
    return {t["train_id"] for t in o.trains}


def validate_human_review(errors: list[str]) -> None:
    """languages/human_review.json must list exactly the items in human_review.REVIEWED, with the reviewer, date and the
    SHA-256 of the query text as it stands now (a reviewed query that was edited afterwards = stale review)."""
    if not _hr.RECORD_PATH.exists():
        errors.append(f"{_hr.RECORD_PATH.name} missing (run python -m benchmark.human_review)")
        return
    rec = json.loads(_hr.RECORD_PATH.read_text(encoding="utf-8"))
    want = [f"{t}_{l}" for l, ids in _hr.REVIEWED.items() for t in ids]
    _check([i["task_id"] for i in rec["items"]] == want, f"{_hr.RECORD_PATH.name}: items differ from human_review.REVIEWED", errors)
    rows = {}
    for lang in _hr.REVIEWED:
        f = LANG_DIR / f"{lang}.jsonl"
        if f.exists():
            rows.update({json.loads(l)["task_id"]: json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()})
    for i in rec["items"]:
        r = rows.get(i["task_id"])
        _check(r is not None and i["query_sha256"] == _hr.query_sha(r["query"]),
               f"{i['task_id']}: query changed after human review (stale review; re-review, then run python -m benchmark.human_review)", errors)
        _check(i["reviewer"] == _hr.REVIEWER and i["review_date"] == _hr.REVIEW_DATE and i["review_status"] == _hr.REVIEW_STATUS,
               f"{i['task_id']}: review record fields differ from human_review.py", errors)


def _review_summary() -> str:
    n = sum(len(v) for v in _hr.REVIEWED.values())
    parts = ", ".join(f"{l} {v[0]}-{v[-1]}" for l, v in _hr.REVIEWED.items())
    return f"{n} human-reviewed: {parts}; rest DRAFT"


def main() -> int:
    errors = validate()
    for e in errors:
        print("FAIL:", e)
    print(f"{'VALID' if not errors else 'INVALID'}: {len(ALL_IDS)} semantic tasks {ALL_IDS[0]}-{ALL_IDS[-1]} x {len(LANGS)} languages = "
          f"{len(ALL_IDS) * len(LANGS)} items + Gujarati {_gu.GU_IDS[0]}-{_gu.GU_IDS[-1]} = {len(_gu.GU_IDS)} items; "
          f"total {len(ALL_IDS) * len(LANGS) + len(_gu.GU_IDS)} ({_review_summary()}), {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
