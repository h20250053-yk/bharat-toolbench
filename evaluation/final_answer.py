"""Structured final-answer contract (plan section 9) and its strict parser.

The model ends with a natural-language reply AND exactly one delimited JSON block:

<FINAL_ANSWER_JSON>
{"status": "success" | "cannot_complete" | "needs_clarification",
 "selected_train": "BTBxxx" | ["BTBxxx", ...] | null,
 "selected_class": "3A" | "2A" | "SL" | "CC" | null,
 "booking_ids": ["BKxxxx", ...],             # only ids returned by book_ticket
 "requested_passengers": ["Name", ...],
 "notes": "short free text",
 "answer_values": {...}}          # optional; only the keys the user asked about (see ANSWER_VALUE_KEYS)
</FINAL_ANSWER_JSON>

Field -> gold mapping (no new semantics):
  status               -> gold final_state.status (the same three values the plan's contract uses)
  selected_train       -> gold final_state.allowed_train_ids (a list only when the answer is several trains, e.g. two legs)
  selected_class       -> gold final_state.travel_class
  booking_ids          -> the bookings the agent actually created (checked against the environment state)
  requested_passengers -> the passenger names in the user's request
  notes                -> not scored
  answer_values        -> requested facts, copied from tool results; keys map 1:1 onto gold final_answer keys:
                          operating_days -> operating_days, runs_on_requested_day -> runs_on_requested_weekday,
                          classes -> offered_classes, station_code -> station_code, station_name -> station_name,
                          duration_minutes -> duration_minutes, seats_available -> seats_available,
                          seats_remaining_at_end -> seats_remaining_at_end, train_count -> train_count
                          (values describe selected_train when one is selected, except where the key says otherwise)
"""
from __future__ import annotations

import json
import re
from typing import Any

STATUSES = ("success", "cannot_complete", "needs_clarification")
REQUIRED_KEYS = ("status", "selected_train", "selected_class", "booking_ids", "requested_passengers", "notes")
ANSWER_VALUE_KEYS = ("operating_days", "runs_on_requested_day", "classes", "station_code", "station_name",
                     "duration_minutes", "seats_available", "seats_remaining_at_end", "train_count",
                     # benchmark 3.0 (booking status, cancellation, waitlist, live status, concession)
                     "booking_status", "waitlist_position", "refund_inr", "delay_minutes", "expected_arrival",
                     "concession_fare_inr", "total_fare_inr")
OPEN, CLOSE = "<FINAL_ANSWER_JSON>", "</FINAL_ANSWER_JSON>"

CONTRACT_PROMPT = f"""Final answer format (required):
First reply to the user in natural language, in the same language as the user's request.
Then end your reply with exactly one machine-readable block, with the tags on their own lines:
{OPEN}
{{"status": "success | cannot_complete | needs_clarification",
 "selected_train": "<train id>" or ["<train id>", ...] or null,
 "selected_class": "3A | 2A | SL | CC" or null,
 "booking_ids": ["<booking id returned by book_ticket>", ...],
 "requested_passengers": ["<passenger name as given by the user>", ...],
 "notes": "<one short sentence>",
 "answer_values": {{<only the keys below that the user asked about>}}}}
{CLOSE}
Rules for the block:
- status: "success" if you completed what the user asked (including a fallback the user explicitly allowed);
  "cannot_complete" if it cannot be done (invalid request, nothing satisfies the constraints, sold out with no allowed fallback, unsupported action);
  "needs_clarification" if you must ask the user before acting.
- selected_train: the train you recommend, report on, or booked; a list in travel order if the answer is several trains; null if none.
- selected_class: the travel class you recommend or booked; null if none.
- booking_ids: exactly the booking ids returned by successful book_ticket calls in this conversation; [] if you booked nothing.
  Waitlist entries and cancellations are not bookings: never put their ids or PNRs in booking_ids.
- requested_passengers: the passenger names given in the request ([] if none).
- answer_values: include ONLY the keys the user's question asks about, with values copied from tool results; values
  describe selected_train when one is selected. Keys: "operating_days" (list of weekdays the train departs, e.g. ["TUE"]),
  "runs_on_requested_day" (true/false), "classes" (list of classes, e.g. ["2A", "3A"]), "station_code",
  "station_name" (full official name), "duration_minutes" (journey time in minutes, integer),
  "seats_available" (integer: seats left on the train and class the user asked about),
  "seats_remaining_at_end" (integer: seats left in the booked class after all your bookings),
  "train_count" (integer: how many trains run on the requested route and day),
  "booking_status" ("CONFIRMED", "WAITLISTED" or "CANCELLED": the status of the booking the user asked about, after your actions),
  "waitlist_position" (integer), "refund_inr" (integer: refund for a cancellation, quoted or done; the sum if several),
  "delay_minutes" (integer: how late the train is running now), "expected_arrival" (HH:MM, 24-hour: expected arrival at the
  station the user asked about), "concession_fare_inr" (integer: one concession ticket),
  "total_fare_inr" (integer: total the user asked for). Omit answer_values or use {{}} if none apply.
- Use valid JSON (double quotes, no comments, no trailing commas).
- The block is plain text inside your reply, not a tool call: never call a tool to give the final answer and never wrap the block in <tool_call> tags.
Example of a complete reply (invented train, stations and values, only to show the shape; use the real facts from the tools and the user's language):
User: Book a 2A ticket on train BTB999 from Alpha Junction to Beta Road on 3 December 2026 for Zed Quill, then tell me how many 2A seats are left.
Reply:
The 2A ticket for Zed Quill on train BTB999 is booked (booking BK9999). 13 seats are left in 2A.
{OPEN}
{{"status": "success", "selected_train": "BTB999", "selected_class": "2A", "booking_ids": ["BK9999"], "requested_passengers": ["Zed Quill"], "notes": "booked, then counted the seats left", "answer_values": {{"seats_remaining_at_end": 13}}}}
{CLOSE}"""


def split_answer(final_text: str) -> tuple[str, str | None]:
    """(natural-language part, raw JSON text of the LAST complete block or None)."""
    text = final_text or ""
    blocks = list(re.finditer(re.escape(OPEN) + r"(.*?)" + re.escape(CLOSE), text, re.S))
    if not blocks:
        return text.strip(), None
    last = blocks[-1]
    natural = (text[:last.start()] + text[last.end():]).strip()
    return natural, last.group(1)


def parse_final_answer(final_text: str) -> dict[str, Any]:
    """Strict parse. Returns {"ok", "error", "answer", "natural_text"}.
    error in: missing_block | malformed_json | not_an_object | missing_keys:<k,..> | invalid_status"""
    natural, raw = split_answer(final_text)
    res: dict[str, Any] = {"ok": False, "error": None, "answer": None, "natural_text": natural, "raw_json": raw}
    if raw is None:
        res["error"] = "missing_block"
        return res
    body = raw.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.S)  # tolerate a markdown fence INSIDE the tags only
    if fence:
        body = fence.group(1)
    try:
        obj = json.loads(body)
    except json.JSONDecodeError as exc:
        res["error"] = f"malformed_json: {exc.msg}"
        return res
    if not isinstance(obj, dict):
        res["error"] = "not_an_object"
        return res
    missing = [k for k in REQUIRED_KEYS if k not in obj]
    if missing:
        res["error"] = "missing_keys:" + ",".join(missing)
        res["answer"] = obj
        return res
    if obj.get("status") not in STATUSES:
        res["error"] = "invalid_status"
        res["answer"] = obj
        return res
    res.update(ok=True, answer=obj)
    return res
