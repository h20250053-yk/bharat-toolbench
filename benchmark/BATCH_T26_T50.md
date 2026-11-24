# Batch T26–T50 (25 semantic tasks × 4 languages = 100 DRAFT items) — benchmark complete: 50 tasks, 200 items

Status: **implemented, gold generated, validated. NOT human-reviewed.** All 100 items are `review_status: "draft"`,
`reviewer: null` (English source `claude-session-5 (draft, not human-authored)`; others `Claude-generated draft`).
T01–T25 (specs, gold, first 25 rows of every language file, all three earlier audits) are hash-frozen in `validate_tasks.py`.
Metrics: `python -m benchmark.coverage_report` → `benchmark/COVERAGE_REPORT.md` (all numbers computed).

## Design process (three internal checkpoints, one global check)

**Coverage gaps found in T01–T25 (from gold):** `book_ticket` never the only call and never after `get_train_details`;
no failed-call-then-retry; no `INVALID_TRAIN`, `INVALID_CLASS`, `PAST_DATE`; no unsupported action; max sequence 6;
no fare-conditioned branching, partial-booking policy, connection planning, relative dates, duration ranking,
class/intent/count ambiguity, or "when NOT to clarify".

* **Phase A (T26–T35)** basic tool selection and missing error codes: T26 seat count, T27 direct booking, T28 invalid train,
  T29 invalid class (no substitution), T30 past date, T31 fail→retry recovery, T32 fare-conditioned branch, T33 group cheapest
  across trains×classes, T34 fastest within budget, T35 relative-date booking.
* **Phase B (T36–T45)** gaps left after A: T36 'AC' ambiguity, T37 check-or-book ambiguity, T38 sold-out → cheapest other train,
  T39 book only if the train runs that day, T40 two-leg connection planning, T41 two-leg all-or-nothing, T42 per-passenger classes,
  T43 three binding constraints + booking, T44 overnight arrival date, T45 unsupported cancellation (zero calls).
* **Phase C (T46–T50)** gaps left after A+B: T46 ticket-count conflict, T47 ambiguity resolved by the train (inverse of T09),
  T48 partial booking allowed (inverse of T15), T49 selection by a route property only visible in train details, T50 state-dependent
  second booking.

## Rejected / redesigned during the session

| Task | First design | Why rejected | Final design |
|---|---|---|---|
| (none) | "6 o'clock" AM/PM clarification | No route has departures 12 h apart: the ambiguity would be manufactured | not built |
| T43 | four constraints incl. "depart at or after 5 PM" | solver guard: the departure constraint pruned no 3A train (claim would be false) | three binding constraints (class, arrival, fare), each eliminating one train |
| T42 | first date with a train (date iteration) | global overlap 0.75 with T25 (two consecutive-date searches) and T08 | two passengers, different classes on one train |
| T34 | fastest train (search only) | global overlap 0.75 with T25/T35: one-step thin task | fastest among trains within a fare ceiling + seat question |
| T35 | relative-date information query | overlap 0.75 with T34/T25 | relative-date **booking** |
| T50 | book, then report seats | overlap 0.75 with T10 (same tools, reversed order) | book → re-check → conditional second booking → final count |

The duplicate threshold (0.75) was **not** changed; tasks were redesigned instead. A regression test keeps thin search-only variants failing.

## Closest remaining pairs (global, T01–T50) and why they stay distinct

| Pair | Jaccard | Distinction |
|---|---|---|
| T22 ~ T38 | 0.73 | T22: no named choice, earliest departure among trains with seats. T38: user's named train is sold out, explicit authorisation, cheapest alternative (needs fares). |
| T04 ~ T43 | 0.73 | T04: minimise fare. T43: satisfy class + arrival deadline + fare ceiling (no optimisation). |
| T04 ~ T38 | 0.73 | T38 adds a sold-out named first choice and an authorised fallback; T04 has neither. |
| T02 ~ T34 | 0.73 | T02: the only train, report seats+fare. T34: rank by duration after a fare filter that removes the fastest train. |
| T35 ~ T49 | 0.70 | T35: date built from 'this Saturday'. T49: train chosen by a route property from get_train_details. |

## Methodology check (does the distribution support the intended claim?)

Claim: *tasks vary in tool selection, multi-step sequencing, constraint satisfaction, conditional actions, clarification,
invalid-input handling, recovery, temporal reasoning, comparison/ranking and safe booking.* Computed support (COVERAGE_REPORT.md):
all 6 tools are required somewhere and each is first in at least 2 tasks except `search_trains` (always needs codes); 27 distinct
exact tool sequences (22 collapsed); 27 multi-tool tasks, max sequence 13; conditional 11; comparison 10; temporal 13;
clarification 6 (+8 tasks whose correct trajectory has zero tool calls); invalid input 6; recovery 6; booking withheld when
requested 12; explicit prohibitions 5. **Supported**, with these honest weak spots:

* **multi-leg**: only 3 tasks (T23, T40, T41) — the 10-station world has few connection-only routes;
* **genuine fail→retry recovery**: only T31; other recovery tasks recover by choosing an alternative, not by retrying a failed call;
* **difficulty skews Easy/Medium** (15/24/9/2 by the explicit rule); Very Hard = T33, T38 only;
* behaviour labels are hand-assigned (reporting only); categories are single labels although many tasks span several behaviours.

## Infrastructure changes (minimal, backward compatible)

* `build_gold.py`: 25 solvers, each asserting its design property; no schema change.
* `validate_tasks.py`: batch-3 coverage, independent raw-JSON oracle for all 25 kinds, hygiene exceptions for the deliberately
  invalid inputs (BTB150, 1A, past date, Bombay Central, ambiguous 'Delhi' in T47), freeze of T01–T25.
* `language_checks.py`: tasks with no stations (T45), ambiguous source + train (T47), via / continues-to stations, legs, second date.
* `coverage_report.py` + `COVERAGE_REPORT.md` (new); `build_language_variants.py` / `build_language_audit.py` append batch 3.
* Tests: `tests/test_batch_t26_t50.py` (new); count-based assertions in earlier test files rescoped to their own slices;
  the T16–T25 referential-integrity test now names every deliberately invalid entity instead of assuming none exist.

## Known limitations

1. No human review of any of the 100 items (incl. English); risk flags are in `batch_T26_T50_language_audit.json`.
2. Scorer not built: it must honour `optional`, `expected_error`, `resolves_to_none`/`resolves_ambiguous`, `equivalent_observations`,
   multiset booking comparison (T33, T42, T48, T50), `min_calls = 0` (eight tasks), and date-qualified answers (T25, T35, T44).
3. T30 gold status is `cannot_complete`; asking for a new date without booking is also safe and should be considered by the scorer.
4. T37 (check-or-book) is a judgement call: the system prompt allows booking only when asked, so gold is `needs_clarification`.
