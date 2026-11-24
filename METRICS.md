# Tool-selection metrics (defined BEFORE they were computed)

The paper's focus is tool selection. These metrics are **extra analysis**: they read the run files and the gold (`required_calls`, `dependency_edges`,
`prohibited_actions`, `final_state.expected_bookings`) and never change the existing scoring (`task_success` stays the headline). Everything is computed by
`analysis/tool_metrics.py` from `runs/*.jsonl` + `benchmark/gold_labels.json`; no number is typed in. Matching of a model call to a gold call uses the
scorer's own functions (`evaluation/scorer._match_required`, `_call_matches`, `_dependency_violations`), so "correct arguments" means exactly what the scorer
means (canonical station codes, ISO dates, class synonyms, train ids, documented equivalent observations).

## Objects

- **Item**: one (task, language) row of a model's full run, 375 per model. **Tool-needed item**: its task has at least one non-optional required call in the gold
  (64 of 75 tasks = 320 items per model). The other 11 tasks (refusals / clarifications) need no tool; they only enter the over-calling and unwanted-action metrics.
- **Calls `C`** of an item: the model's tool calls in order = the `tool_call`, `malformed_tool_call` and `tool_not_allowed` events of the run's trajectory (for items that ended
  in `malformed_output`, `output_truncated`, `context_overflow` or an error, the trajectory is empty by design and the calls are taken from `partial_trajectory`, which holds the calls
  really made). Calls that were written as text and recovered by the format layer count as calls (the model chose the tool); calls never executed (`unexecuted_step_limit`) are not counted.
  The called tool is the call's tool name after format normalisation.
- **Required multiset `R`**: the tool names of the gold's non-optional required calls, with multiplicity (e.g. `get_fare` x3 when three fares must be compared).
  **Allowed multiset `A`** = `R` plus the tools of the gold's optional calls (an optional call is acceptable, not required).
- **Matching** `m_t = min(R_t, called_t)` per tool `t` (multiset intersection), `m = sum_t m_t`; `m'_t = min(A_t, called_t)`, `m' = sum_t m'_t`.

## Metrics (all per item, then averaged over the items of a group unless stated)

1. **Tool-use rate** (tool-needed items): share of items with `|C| >= 1`.
2. **Selection recall** (tool-needed items): `m / |R|` (a no-call item has recall 0). **Selection precision** (items with `|C| >= 1`): `m' / |C|` = share of calls that were required or acceptable.
   **Selection F1**: harmonic mean of recall and precision with precision 0 when `|C| = 0` (so a model that never calls a tool scores F1 = 0, not "undefined").
3. **First-call accuracy** (tool-needed items): 1 if the first call's tool equals the tool of some *root* required call (a non-optional required call with no incoming dependency edge from another *required* call: it needs nothing from earlier required calls; an optional predecessor such as a first alias attempt does not block), else 0; no call = 0.
   **First-call exactness**: the same but the first call must also match that root call's arguments (scorer matching, order ignored).
4. **Argument validity** (call level, pooled over the calls of the group, bootstrap over items): share of calls the environment accepted as well-formed. A call is *invalid* if its observation carries one of
   `INVALID_ARGUMENTS, MALFORMED_ARGUMENTS, UNKNOWN_TOOL, TOOL_NOT_ALLOWED, INVALID_STATION, INVALID_TRAIN, INVALID_CLASS, INVALID_DATE, INVALID_TIME_WINDOW, INVALID_PASSENGER, SAME_STATION`,
   unless the gold of that task expects exactly that error code (e.g. `INVALID_TRAIN` in T28). Domain outcomes (`SOLD_OUT`, `DUPLICATE_BOOKING`, `CLASS_NOT_OFFERED`, `PAST_DATE`, `STATION_NOT_FOUND`) are valid calls.
   **Argument accuracy vs gold** (tool-needed items with `sum_t m_t >= 1`): `matched / m`, where `matched` = number of required gold calls the scorer matched with correct arguments
   (so it is conditional on the tool having been selected). **Field accuracy** (pooled): for each (required gold call, argument key) with a literal gold value (`source`/`destination` codes, `date`, `travel_class`, `train_id`, `passenger`,
   `time_window`), whether some model call to that tool carries the canonically equal value (gold alternatives accepted); station *names* (`resolve_station`) are scored by the resolution matcher as in the scorer.
5. **Sequence accuracy** (tool-needed items with at least one dependency edge between two matched required calls): `1 - violated / considered` over the gold `dependency_edges` whose two calls were both matched
   (a violation = the dependent call was made before the call it needs). **Edge-level pooled rate** is reported next to it.
6. **Over-calling**: `unnecessary = |C| - m'` (calls beyond the allowed multiset); **over-call rate** = `unnecessary / |C|` (items with `|C| >= 1`); **over-calling item** = `unnecessary >= 1`;
   **repeated calls** = executed calls identical (tool + canonical arguments) to an earlier call of the same item. For the 11 no-tool tasks: **unnecessary tool use** = share of items with any call.
   **Unwanted actions**: (a) *unwanted booking* = an item whose task has no expected booking in the gold and where the final environment state holds a booking (or `book_ticket` succeeded); (b) *prohibited attempt* = the scorer's
   `process:prohibited_action` label (the user forbade booking and the model called `book_ticket` anyway, even if the environment refused). Rates over all items of such tasks.
7. **Funnel** (tool-needed items, cumulative, each stage requires the previous): **uses tools** (`|C| >= 1`) -> **right tools** (`m = |R|`: every required tool called often enough) -> **right arguments**
   (every required gold call matched with correct arguments and accepted by the environment) -> **right order** (no violated dependency edge) -> **task success** (lenient score, includes the final answer and the state).
   Stage shares are proportions of the tool-needed items (Wilson 95% CI). The step "right tools -> right arguments" isolates *argument* errors; "uses tools -> right tools" isolates *selection* errors.
   **Selection error** of an item = it used tools or not but `m < |R|`; **argument error** = `m = |R|` but some required call unmatched.

## Aggregation, confidence intervals, rankings

- Reported per model, per language (en, hinglish, hi, mr, gu) and per model x language (64 tool-needed items per cell; wide intervals, shown as such).
- **95% CIs**: proportions that are 0/1 per item (tool-use rate, first-call accuracy, funnel stages): Wilson. Means of per-item values and call/edge-pooled ratios: percentile bootstrap over **items** (10,000 resamples, seed 20261124).
- **Tool confusion table** (per model and pooled): rows = expected tool, columns = called tool. Construction per item: the matched part (`m_t`) goes on the diagonal; the required calls left unmatched and the calls left over are paired **in order**
  (expected steps in gold order with surplus calls in call order); pairs `(X expected, Y called)` are substitutions; leftovers are `(X, not called)` and `(not required, Y)`. This is an in-order alignment of surplus calls, not a claim about the model's intent.
- **Tool-selection ranking**: models ranked by mean selection F1 (ties by recall), reported next to the task-success ranking and the rank of every single metric; agreement between the two rankings by Spearman's rho (8 models: small sample, indicative only).
- Known limits: the multiset view ignores *which* train a repeated `get_fare` was for (arguments are judged separately by metric 4); optional gold calls make precision slightly generous; items that ended early (truncated, discarded replies) have the calls made before the stop; transport failures (Ollama-discarded
  replies) have no calls and count as "no tool use", which lowers the tool-use rate for that model: they are listed separately in the results.
