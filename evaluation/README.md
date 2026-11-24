# BharatToolBench evaluation pipeline

Provider-neutral agent runner, Groq and Gemini function-calling adapters, a structured-first programmatic scorer,
resumable JSONL runs, quota accounting and a pilot report. **No LLM judge.** Adapters: Groq, Gemini, OpenRouter
(experimental), NVIDIA (experimental, not wired into the registry) and local Ollama (`agents/ollama_adapter.py`, see
`LOCAL_MODELS.md`). Two local Qwen/Llama 3B runs exist in `runs/`; results are in `analysis/results/`.

## Final-answer contract (`evaluation/final_answer.py`)
The system prompt (plan section 9 + contract; its SHA-256 is stored in every row) requires a natural-language reply
followed by one block:

```
<FINAL_ANSWER_JSON>
{"status": "success | cannot_complete | needs_clarification", "selected_train": "BTBxxx" | [...] | null,
 "selected_class": "3A|2A|SL|CC" | null, "booking_ids": [...], "requested_passengers": [...], "notes": "...",
 "answer_values": {...}}   # optional: requested facts copied from tool results
</FINAL_ANSWER_JSON>
```
Fields map onto existing gold (`final_state.status`, `allowed_train_ids`, `travel_class`, bookings in the environment,
passengers in the request); no new task semantics. `answer_values` keys map 1:1 onto gold `final_answer` keys
(`operating_days`, `runs_on_requested_day`, `classes`, `station_code`, `station_name`, `duration_minutes`, `seats_available`)
and describe `selected_train` when one is selected.

## Scorer (`evaluation/scorer.py`, `evaluation/canonical.py`)
1. run status (provider_error / runner_error -> not scored, re-run; malformed_output / step_limit_exceeded -> model failure)
2. structured answer: status, selected train(s) (must be within gold `allowed_train_ids`), class, booking ids (must equal
   the bookings actually created), requested passengers
3. environment state: bookings as an order-independent multiset (train, class, passenger)
4. explicit free-text values only where a task's `must_state` needs a value with no structured field (table `VALUE_CHECKS`;
   numbers/times/dates canonicalized: `₹1,460` = 1460, `8:20 PM` = `रात्री 8:20` = 20:20, Devanagari digits)
5. process: required calls with canonical arguments, gold `arg_alternatives`, the spec's documented equivalent
   observations (table `EQUIVALENT_PATHS`), dependency order, prohibited actions

Structured value checks (table `STRUCTURED_VALUE_CHECKS`, values from gold): T06 operating weekdays (as a set, en/hi/mr/gu/
Hinglish names or codes) + Monday yes/no; T11 offered classes (as a set, order-free, class synonyms); T16 station code +
official name (case/punctuation/spacing only, compared with the station record); T34 journey duration (explicit
hour/minute forms incl. Hindi/Marathi units -> minutes) + 3A seats. Because these values sit in the structured block and
describe `selected_train`, a value is never credited because a number appears elsewhere in the prose, nor to the wrong train.

Yes/no answer values (T06) are read with ONE rule in en, hinglish, hi, mr and gu: the whole value is a yes/no word, or a yes/no word
is the FIRST word (followed by `,` `.` `!` or a space); a leading word decides, a yes/no word later in the sentence is never read.

`task_success = outcome_success AND process_success`.

## Format tolerance: lenient (headline) and strict (sensitivity) scores
`evaluation/tolerance.py` is shared by every adapter and language. It changes only the representation of what the model said (tag variants,
missing closing tag, untagged/fenced JSON, JSON repairs, status/field/key spelling, integer forms, thinking text, tool calls written as text,
argument formats, unknown extra argument keys, digit scripts, date/time/currency forms) and never a decision (no renamed keys, no repaired
values, no guessed train/class/status, no answer extracted from prose). Every recovery is recorded (`row["format_recoveries"]`,
`row["score"]["format_recoveries"]`, `lenient_used`). `row["score"]` is the lenient headline, `row["score_strict"]` the original scorer
(a lower bound when a run-time recovery was used). Details, evidence and the F-23 Ollama check: `FORMAT_ROBUSTNESS.md`.

## Runner (`evaluation/runner.py`)
* at most **8 model turns** per item (plan section 6); a model still calling tools on turn 8 -> `step_limit_exceeded`
* retries ONLY retryable provider failures (429, 5xx, timeout, connection): exponential backoff 2,4,8,16 s +-25 %
  (cap 60 s), honouring `Retry-After` / `x-ratelimit-reset-*` / Google `retryDelay` (cap 300 s), max 5 attempts;
  every retry recorded with reason and wait
* never retried: malformed model output, context overflow and output truncation (scored failures: `context_overflow`, `output_truncated`), invalid model arguments (deterministic tool errors), step-limit overruns,
  scorer or harness errors
* malformed tool calls -> `malformed_tool_call` trajectory event + error observation to the model (run continues)
* token usage summed over all turns (`usage`, plus `usage_per_turn`); raw model requests/responses, tool
  requests/responses, retries, timestamps and the parsed final answer in `raw_log`
* provenance per row: run_id, benchmark_version, task_id, language, model/provider/settings, system-prompt and
  tool-schema hashes, environment hash before/after

## Adapters (`agents/`)
* Groq: timeout 60 s, SDK retries off, `parallel_tool_calls: false` for gpt-oss-120b (config), `tool_use_failed` = model output
* Gemini: timeout 90 s, SDK retries off, `ThinkingConfig(thinking_level=MINIMAL)`, tool results via
  `types.FunctionResponse(name, response, id)` (fixes the google-genai 2.x crash), MALFORMED_FUNCTION_CALL = model output

## Commands (do not run against real models until the pilot is approved)
```bash
python -m evaluation.smoke                         # offline: gold executable + scorer accepts ideal answers (75 tasks)
python -m pytest -q                                # includes tests/test_eval_*.py
export GROQ_API_KEY=...;   python -m evaluation.run_pilot --model primary_a --split pilot
export GEMINI_API_KEY=...; python -m evaluation.run_pilot --model primary_b --split pilot
python -m evaluation.run_pilot --model primary_a --split pilot --run-file runs/X.jsonl --resume   # re-runs provider errors only
python -m evaluation.run_pilot ... --max-requests 200 --max-total-tokens 180000   # stop cleanly at a quota cap
python -m analysis.pilot_report runs/X.jsonl
```
Keep `fallback_b` runs in separate files; never mix them into a `primary_b` run.

## Experimental model: `experimental_inkling` (OpenRouter) — NOT a primary or fallback model
* config: `config/models.yaml` -> `experimental_inkling` (provider `openrouter`, model `thinkingmachines/inkling:free`,
  temperature 0, max_tokens 1024, timeout 90 s). `primary_a`, `primary_b`, `fallback_b` are unchanged. No automatic
  fallback to or from this model; it runs only when named explicitly with `--model experimental_inkling`.
* adapter: `agents/openrouter_adapter.py` (OpenAI SDK, base URL `https://openrouter.ai/api/v1`, key ONLY from
  `OPENROUTER_API_KEY`, SDK retries off). Sends `max_tokens` (not `max_completion_tokens`); never sends Groq's
  `reasoning_effort`; sends `parallel_tool_calls` / `reasoning` only if configured (neither is, for this model).
  OpenRouter errors returned with HTTP 200 (`error` body, or `finish_reason: "error"`) are provider errors, not model output.
  401 / 402 / 403 / 404 / 400 and non-chat-completion 2xx bodies (HTML, invalid JSON: `invalid_response`) ->
  non-retryable `provider_error`; 408 / 429 / 5xx / timeout / connection -> retried. Odd tool-call shapes become
  `malformed_tool_call` events; the key value is redacted from adapter error messages.
* results go to their OWN files: `runs/experimental_inkling_pilot.jsonl` + `runs/experimental_inkling_pilot.quota.json`.
  Never merge them with primary or fallback runs, and never report them as primary results.
* known risk: third-party reports say the `:free` variant answers plain scripted API calls with HTTP 403
  "only available on agentic harnesses". This harness does not impersonate any other application; such a 403 is
  recorded as `provider_error` / `error_kind: forbidden` (not scored, not retried).

### Quota semantics (existing behaviour, unchanged — read before choosing caps)
* the quota file is per run file (`<run-file>.quota.json`) and is **cumulative**: it is loaded on every invocation,
  so `--max-requests` / `--max-total-tokens` are totals for that run file across resumes, not per invocation.
  To continue after a cap stop, resume with a HIGHER cap.
* caps are checked **only before starting an item**, never mid-item. One item may make up to 8 model requests per
  attempt and up to `--max-attempts` attempts, so a run can overshoot a cap by up to `8 x max_attempts` requests.
* `requests` / tokens count **successful model responses only**. Failed HTTP calls (429, 403, 5xx, ...) are counted in
  `retries` / `provider_errors`, not in `requests`, so a request cap does not bound failed calls; `--max-attempts`
  and the number of selected items do.
* without `--resume`, an existing `--run-file` is appended to and every item is run again; always pass `--resume`
  when continuing a run file.
* if the API key is missing, each item is recorded as `runner_error` (model_key null, not scored, re-run on `--resume`).

### One-request live smoke test (`evaluation/openrouter_smoke.py`) — run this BEFORE any pilot
```bash
python -m evaluation.openrouter_smoke            # dry run: shows the request, sends nothing, needs no key
python -m evaluation.openrouter_smoke --live     # sends AT MOST ONE HTTP request (needs OPENROUTER_API_KEY)
```
Do NOT use `run_pilot --max-requests 1` as a smoke test: caps are checked only between items and failed calls are not
counted, so it cannot guarantee one request. The smoke script enforces the limit itself (single adapter call, SDK
`max_retries=0`, and an HTTP request hook that blocks any 2nd request incl. redirects). It sends the benchmark system
prompt + the synthetic T01 English query + T01's tool schemas, never sends a tool result back, writes only a NEW
`runs/experimental_inkling_smoke_<UTC>.json` (exclusive create), and never touches run/quota/gold/task files.
Verdicts / exit codes: `OK_TOOL_CALL` 0, `OK_NO_TOOL_CALL` 10, `REJECTED` 20, `INCOMPATIBLE` 30, `NOT_SENT` 40, `HARNESS_ERROR` 50.
