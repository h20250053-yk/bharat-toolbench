# Diagnostic failure taxonomy (`analysis/observe_run.py`)

**Not an official score.** The official result of every item is the unchanged scorer's `task_success` and
`failure_labels`, copied verbatim into `observations.jsonl`. The categories below only explain *why* an item failed,
so that models (e.g. Qwen 2.5 3B / 7B / Llama) can be compared on failure profiles. They are derived deterministically
from fields already in each run row: `status`, `error_kind`, `score.*`, `trajectory`, `state_snapshot`, `raw_log`
finish reasons, plus `benchmark/gold_labels.json`. Nothing is re-scored.

## `primary_failure` — exactly one per item, first match wins

| # | category | rule |
|---|---|---|
| 0 | `success` | `score.task_success == true` |
| 1 | `infra_error` | status `provider_error` / `runner_error` (not scored; resolve by resume, never a model failure) |
| 2 | `context_overflow` | provider error kind `context_overflow` (prompt + max_tokens > num_ctx) |
| 3 | `malformed_model_output` | status `malformed_output` (e.g. `unparsed_model_output`: Ollama discarded a malformed `<tool_call>`) |
| 4 | `step_limit` | status `step_limit_exceeded` (still calling tools on turn 8) |
| 5 | `unsafe_action` | a `process:prohibited_action` / `process:tool_not_allowed` label (the scorer flags *attempted* prohibited calls, even if the environment rejected them), or a booking in the final state that gold does not expect |
| 6 | `missing_booking` | a booking gold expects is absent from the final state |
| 7 | `tool_argument_error` | required calls missing / dependency violated, AND the trajectory has tool calls rejected for bad arguments (`INVALID_*`, `STATION_NOT_FOUND`, `SAME_STATION`, `PAST_DATE`, `CLASS_NOT_OFFERED`, malformed or not-allowed calls) whose error code gold does NOT expect for that task |
| 8 | `missing_required_call` | other required-call / dependency failures |
| 9 | `wrong_answer` | final answer parsed, but status / train / class / passengers / values wrong |
| 10 | `format_only` | tool process and booking state correct; only the final-answer block failed to parse |
| 11 | `other` | none of the above (listed explicitly in the summary) |

Error codes that gold expects for a task (e.g. `INVALID_DATE` for a past-date request, `STATION_NOT_FOUND` for an
unknown city, `SOLD_OUT`) are never counted as argument errors.

## `secondary_tags` — any number, heuristic

| tag | rule |
|---|---|
| `invalid_train_id_format` | a tool call used a `train_id` not of the form `BTB` + 3 digits (placeholders such as `<train_id_from_search>`, `train_id1`) |
| `ungrounded_train_id` | a well-formed train id used before it appeared in the query or in any earlier tool observation |
| `parallel_dependent_calls` | an ungrounded id used in a turn that issued several calls at once (dependent calls sent before results) |
| `guessed_station_code` | an unexpected `INVALID_STATION` error (invented station code) |
| `unresolvable_station_name` | an unexpected `STATION_NOT_FOUND` error |
| `unexpected_booking` | the final state contains a booking gold does not expect — set regardless of the primary category, so unsafe state changes stay visible behind e.g. `step_limit` or `context_overflow` |
| `missing_expected_booking` | a booking gold expects is absent from the final state (any primary category) |
| `tool_call_as_text` | the reply's natural-language part contains a raw tool-call object for a benchmark tool (e.g. `{"name": "search_trains", ...}`) that the serving layer returned as text instead of a tool call |
| `empty_final_text` | no final text at all |
| `repetition_or_truncation` | last turn stopped on the token limit (`done_reason == "length"`) or ≥50 % repeated lines (≥6 lines) |
| `reply_language_mismatch` | reply script differs from the item language (en / hinglish: Latin; hi / mr: Devanagari; script share heuristic) |
| `no_final_block` | `final_answer_parse == "missing_block"` |
| `retried` | more than one attempt (retryable provider error) |
| `kind:<error_kind>` | added to `malformed_model_output` items |

## Item accounting

One logical run may span several files (an original run and a resume copy). Each expected task-language pair is
counted exactly once: the latest row across the files, in the order given, wins (the rule `run_pilot --resume` uses).
Missing items, unexpected items and items with several rows are reported in `summary.json` → `integrity`; the tool
exits with code 2 when the run is incomplete.
