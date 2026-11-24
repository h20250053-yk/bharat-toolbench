# Batch T06–T15 (10 semantic tasks × 4 languages = 40 DRAFT items)

Status: **implemented, gold generated, validated. NOT human-reviewed.** Every item is `review_status: "draft"`,
`reviewer: null`. The English source is a Claude draft (`claude-session-3 (draft, not human-authored)`); Hinglish,
Hindi and Marathi are `Claude-generated draft`. Running total: **15 semantic tasks, 60 items (15 per language).**

## Design rule: no data-swap duplicates

Every task uses a different reasoning procedure (its own `solver.kind`) and was compared against T01–T05 and the
rest of the batch. A task that only changes train/station/date/passenger/class/fare is a duplicate and is rejected by
`python -m benchmark.semantic_overlap` (also run inside `validate_tasks`). Each solver additionally *asserts the
property that makes its task meaningful*, so a fixture change that would trivialise a task fails gold generation.

| ID | Category | What it tests | Gold (generated) | Nearest existing task and why it differs |
|---|---|---|---|---|
| T06 | single_tool | Schedule fact: origin weekdays of BTB111, yes/no for Monday | `get_train_details`; TUE/THU/SAT, Monday = no | T01 (fare value): schedule fact + inference, different tool |
| T07 | sequential | resolve → search → **details**: arrival time at an *intermediate* stop (Nagpur, after midnight) | BTB121, NGP 00:30 | T02 (search → availability/fare): answer only exists in the stop list |
| T08 | recovery | **Empty** departure window (12:00–17:00) + user-authorised fallback (first train strictly after 17:00) | 2 searches, edge c3→c4; BTB109 17:20 | T03 (window *contains* the answer): recovery from an empty result |
| T09 | clarification | Ambiguous "Delhi" in a booking request; ambiguity is *material* (NDLS→BTB105 and NZM→BTB129 both bookable) | `needs_clarification`, no booking, resolve optional | none (first clarification task) |
| T10 | recovery | Sold-out preferred class + **allowed** fallback class on the same train → book fallback | check 2A → book 3A; BTB101\|3A 8→7 | T05 (fallback *forbidden*, no booking): opposite authorisation and end state |
| T11 | invalid_input | Request presupposes a class the train does not have (`CLASS_NOT_OFFERED`); list offered classes | `get_fare` expected error (optional) + `get_train_details`; [2A, 3A] | T01 (valid fare) / T05 (class exists but sold out) |
| T12 | constraint | **Next-day arrival deadline** + objective "leave as late as possible"; the naive latest train misses the deadline | BTB101 (dep 20:20, arr 04:00 on 10 Oct); BTB107 excluded | T03 (departure floor + budget + seats): arrival-side constraint, max-departure objective, needs `arrival_day_offset` |
| T13 | booking | Train identified by stated departure time; **two** bookings; exactly 2 seats exist | 2× `book_ticket`; BTB102\|3A 2→0 | T04 (one passenger, cheapest): identification by time, two state mutations |
| T14 | sequential | Enumerate a train's **classes**, minimise fare subject to seats; the cheapest class (SL) is sold out | minimal proof set: avail(3A), fare(3A), avail(SL), fare(2A); answer 3A ₹1460 | T03 chooses a *train*; T05/T10 fix the class |
| T15 | constraint | All-or-nothing **group** booking: status AVAILABLE but 1 seat for 2 passengers → book nothing | `check_availability` only; prohibitions from the prompt | T05: there the environment itself rejects the booking (SOLD_OUT); here it would accept a partial booking, so only the agent's quantity reasoning prevents it |

Overlap result (`python -m benchmark.semantic_overlap`): 15 distinct solver kinds, 15 distinct reasoning
fingerprints, 105 pairs, maximum Jaccard 0.62 (T05~T15, T01~T14, T01~T02), threshold 0.75. Negative tests show the
checker flags a data-swapped clone of T03 and a renamed-solver clone of T12.

## Category coverage after this batch (Playbook targets for 50 tasks in brackets)

single_tool 2 [8] · sequential 3 [10] · constraint 3 [10] · booking 2 [7] · recovery 3 [7] · clarification 1 [6] · invalid_input 1 [2].
Task IDs follow the repository's running numbering (already decoupled from the Playbook's category-ordered IDs at T01–T05).

## Gold conventions added in this batch (backward compatible)

* `RequiredCall.expected_error`: the call is expected to fail with that code (T11). Serialised only when set, so
  T01–T05 gold is byte-identical.
* resolve matcher `{"resolves_ambiguous": ["NDLS", "NZM"]}`: the name must resolve to exactly these candidates (T09).
* `optional: true` calls are helpful but not required (alternative grounding paths); `min_calls` counts only
  non-optional calls. T09 has `min_calls = 0`, so efficiency is undefined there.
* Multi-booking tasks carry `booking_ids` in replay order; booking ids are order-dependent, so the order-independent
  check is `final_state.expected_bookings` (a multiset of train/class/passenger).
* `final_answer_requirements.equivalent_observations` documents accepted alternative evidence (e.g. T10: a rejected
  `book_ticket(BTB101, 2A)` with `SOLD_OUT` grounds the fallback as well as `check_availability`).

## Files

* `benchmark/semantic_tasks.json` — T06–T15 specs appended (T01–T05 unchanged, hash-frozen in the validator)
* `benchmark/batch_t06_t15.py` — single source of all batch text: English source, 30 drafts, surface-check markers, translation flags
* `benchmark/build_gold.py` — 10 new solvers; `benchmark/gold_labels.json` regenerated (pilot entries byte-identical)
* `benchmark/languages/*.jsonl` — 10 rows appended per language (pilot rows byte-identical, hash-frozen)
* `benchmark/languages/batch_T06_T15_language_audit.json` — 40 records, all review fields `pending_human_review`
* `benchmark/semantic_overlap.py` — duplicate checker
* `tests/test_batch_t06_t15.py` — 35 tests (behaviour, determinism, preservation, duplicates, multilingual, negatives)

## Known limitations (to resolve before benchmark v1.0)

1. **No human review yet** for any T06–T15 variant, including the English source. Translation-risk flags are in the batch audit file.
2. The surface checks are keyword tests; they catch dropped/altered constraints but say nothing about naturalness.
3. The scorer does not exist yet. It must honour `optional`, `expected_error`, `resolves_ambiguous`,
   `equivalent_observations`, multiset booking comparison (T13) and `min_calls = 0` (T09).
4. T10, T14 and T15 state a date although `check_availability`/`book_ticket` take none (documented per-(train, class)
   simplification, as in T05). A careful model may still mention the date; that is not an error.
5. T07 asks for the clock time only: `get_train_details` exposes no day offsets, so the arrival *date* at Nagpur is not
   derivable from that tool alone.
6. The overlap threshold (0.75) was set by the batch author with the scores visible; it is a guard against data-swap
   duplicates, not a proof of semantic distinctness to a human reader.
