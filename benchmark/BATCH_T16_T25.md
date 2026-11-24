# Batch T16–T25 (10 semantic tasks × 4 languages = 40 DRAFT items)

Status: **implemented, gold generated, validated. NOT human-reviewed.** Every item is `review_status: "draft"`,
`reviewer: null`. English source: `claude-session-4 (draft, not human-authored)`; Hinglish/Hindi/Marathi:
`Claude-generated draft`. Running total: **25 semantic tasks, 100 items (25 per language).**
T01–T15 (specs, gold, language rows, both earlier audits) are hash-frozen in `validate_tasks.py`.

| ID | Category | What it tests | Gold (generated) | Nearest existing task and why it differs |
|---|---|---|---|---|
| T16 | single_tool | Station identity: code + official name via `resolve_station` alone (per-language alias) | HWH, Howrah Junction | All other tasks resolve stations only as a means; here the station fact IS the answer |
| T17 | single_tool | Segment distance = difference of cumulative stop distances | BTB115 Pune→Bengaluru 838 km (naive 1030) | T06/T07 read a field; this derives a quantity |
| T18 | invalid_input | Unknown station (`STATION_NOT_FOUND`) | `cannot_complete`; resolve with `{"resolves_to_none": true}` | T11 (invalid class), T09 (station matching too MANY entries) |
| T19 | clarification | Booking fully specified and bookable except the passenger name | `needs_clarification`, no booking, min_calls 0 | T09 (ambiguous station) |
| T20 | recovery | Booking on a route with no direct train on ANY day | `cannot_complete`, no booking | T18 (station invalid), T24 (candidates exist but fail budget), T08 (fallback authorised) |
| T21 | clarification | Contradiction: named train BTB107 runs Jaipur→Ahmedabad, user says Ahmedabad→Jaipur | `needs_clarification`; `get_train_details` | T11 (cannot_complete), T19 (missing info): here info is present but inconsistent |
| T22 | booking | Earliest-departing train that still has seats; earliest (BTB101) sold out | book BTB103 2A; 35→34 | T04 (cheapest), T10 (fallback class on same train), T13 (train fixed by time) |
| T23 | booking | Round trip: two routes, two dates, two trains, one passenger | 2 bookings BTB127/BTB128 SL | T13 (two passengers, one train) |
| T24 | constraint | Unsatisfiable budget: every 2A candidate > ₹3500 | `cannot_complete`; fares of both candidates | T03 (feasible constraints) |
| T25 | constraint | Window 23:00 9 Oct – 05:00 10 Oct spans two dates; a single same-date wrap search wrongly adds BTB111 (03:55 on the 9th) | BTB109 only; searches on both dates | T03/T08 (one-date windows), T12 (arrival deadline) |

## Design decision recorded: T20 was redesigned

The first T20 draft was a **missing-date** clarification. The semantic-overlap check flagged it as identical in
reasoning to T19 (missing passenger): both are "a required booking slot is absent → ask, don't book". Rather than
relaxing the checker, T20 was replaced by a **no-trains-on-route** recovery task. A regression test
(`test_overlap_flags_a_second_missing_slot_clarification`) keeps that clone failing.

Overlap result: 25 distinct solver kinds and reasoning fingerprints, 300 pairs, max Jaccard 0.67 (T25 vs T02/T07/T08/T12,
driven by shared resolve→search tools), threshold 0.75 (unchanged).

## Category distribution after this batch (Playbook targets for 50 tasks)

single_tool 4 [8] · sequential 3 [10] · constraint 5 [10] · booking 4 [7] · recovery 4 [7] · clarification 3 [6] · invalid_input 2 [2].
No new sequential task: candidates considered (fare difference on the only train, total group cost) were variants of T02/T14/T15.

## Infrastructure changes (minimal, backward compatible)

* `build_gold.py`: 10 solvers; matcher `{"resolves_to_none": true}` for an unknown station name.
* `validate_tasks.py`: batch-2 coverage, independent oracle for the 10 kinds, round-trip second date, freeze of T01–T15.
* `language_checks.py`: single-station, segment-order, unknown-source, round-trip-dates and missing-passenger checks.
* `build_language_variants.py` / `build_language_audit.py`: append batch 2; new `batch_T16_T25_language_audit.json`.

## Known limitations

1. No human review yet (all 40 items, incl. English). Risk flags are in the batch-2 audit file.
2. Scorer not built yet; it must honour `optional`, `expected_error`, `resolves_to_none`, `equivalent_observations`
   (T21, T22), multiset booking comparison (T23) and `min_calls = 0` (T19).
3. T17's surface form "kilometres" is not checked for a number (none is given); correctness is purely in the gold.
4. T25 lists departures with dates; a scorer must compare the set of (train, date), not train ids alone.
