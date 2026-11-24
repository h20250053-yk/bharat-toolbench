# Format robustness: judging what models DO, not how they format it

Status: **implemented in benchmark 2.1.0** (see section 7 for what was built and the F-23 live results). The text below is the analysis that was approved. Everything below was found by
reading `agents/ollama_adapter.py`, `evaluation/runner.py`, `evaluation/final_answer.py`, `evaluation/scorer.py`,
`evaluation/canonical.py`, `environment/railway_env.py`, by probing the current code with synthetic inputs (scratchpad scripts,
nothing written to the repo), and by reading the two historical full runs in `runs/` (read only):
`local_qwen25_3b_full_20261013T222957Z.jsonl` and `local_llama32_3b_full_20261014T001534Z.jsonl` (200 items each, en/hinglish/hi/mr).
The existing offline audit `analysis/format_recovery.py` (outputs in `analysis/results/format_recovery_audit_*`) was used for the
prose-extraction numbers; I did not re-generate it.

## 0. The size of the problem in the old runs

| | Qwen 2.5 3B | Llama 3.2 3B |
|---|---|---|
| task_success (official, strict) | 3/199 scored (1.5%) | 3/200 (1.5%) |
| final answer parsed (`final_answer_parse == ok`) | 13 | 22 |
| `missing_block` | 186 | 173 |
| scored items whose tool process AND booking state were correct but that failed | **54** (53 `missing_block`, 1 other) | **49** (47 `missing_block`, 2 `missing_keys:notes`) |
| reply discarded by Ollama (`unparsed_model_output`, status `malformed_output`) | **43** (en 11, hinglish 9, **hi 16**, mr 7) | 0 |
| tool call written as text instead of a native call (final text) | 1 | **40** |
| `<FINAL_ANSWER_JSON>` opened but never closed | 0 | **30** |
| both tags present but JSON invalid (`Extra data`) / required key missing (`notes`) | 0 | 2 / 3 |
| bare JSON (no tags) | 0 | 2 (one is the echoed template, which must stay invalid) |

So roughly a quarter of all items in each run failed although the model's actions (tool calls and bookings) were already right:
those items are failures of **format**, not of decisions. Existing audit (`analysis/format_recovery.py`, analysis only, not a score):
Qwen strict wrapper repair adds +0 (3 -> 3/199), conservative 9/199 (4.5%), extended (prose extraction) 11/199 (5.5%);
Llama strict wrapper repair +7 (10/200 = 5.0%), conservative 12/200, extended 21/200 (10.5%). So the format layer moves the
headline number of a weak model by up to 9 percentage points; for stronger models the effect will be smaller but it will not be zero,
and it will differ by model family, which is the bias to remove.

## 1. Principles for every fix (the fairness contract)

1. **One shared implementation**, used by every adapter and every language (a new module, e.g. `evaluation/tolerance.py`, called from
   the runner and the parser; adapters stay thin). No model-name or language-specific branches.
2. **Value-preserving only.** A rule may change representation (wrapper, case, whitespace, digits script, list vs single string,
   quoting) and may never change a decision (tool, argument value, train, class, status, passenger, booking). Every rule has a guard
   ("accept only if exactly one candidate and it is unambiguous") and a counter-example test that must still fail.
3. **Always recorded.** Each recovery appends to `row["format_recoveries"]`: `{stage, rule, turn, before, after}`; the row gets
   `lenient_used: true/false`. Raw text and raw arguments are never overwritten (`raw_log` keeps what the model produced).
4. **Two scores from the same run.** `score` (lenient, with the rules) and `score_strict` (today's behaviour, byte-identical on old
   runs). See section 4 for how the strict score is defined honestly.
5. **No rule accepts a wrong action.** The scorer's process/state/status/train/class/passenger checks are untouched; only the way
   the model's answer is read changes.
6. **Prose extraction stays out of the scorer** (it infers intent from free text). It remains the analysis-only "extended" number in
   `analysis/format_recovery.py`, reported as a third, clearly labelled column.

Tiers used below: **L1** = in the harness, lenient score (deterministic, value-preserving); **L2** = analysis only (existing
`format_recovery`); **NO** = deliberately not recovered (would accept a wrong decision or guess).

## 2. Problems found

Numbering is stable for the approval step. "Seen" = how often in the old runs; "probe" = confirmed on synthetic input, not seen in the
old runs (these matter for other model families: Mistral, Phi, Granite, Llama 3.1, Qwen3, gpt-oss).

### A. Final-answer wrapper

| ID | Problem | Evidence | Seen | Tier / proposed fix |
|---|---|---|---|---|
| F-01 | **Closing tag missing.** `split_answer` needs both tags (`final_answer.py:71-79`, regex `OPEN(.*?)CLOSE`). | Llama `T01_mr`: `...\n<FINAL_ANSWER_JSON>\n{"status": "success", ...}` and the text ends there. | Llama 30, Qwen 0 | L1: open tag + one complete JSON object that runs to the end of the text (use `json.JSONDecoder.raw_decode`). Recorded as `closing_tag_missing`. |
| F-02 | **Tag spelling.** Lowercase `<final_answer_json>`, spaces `< FINAL_ANSWER_JSON >`, brackets. | probe: all `missing_block`. | not seen | L1: case-insensitive match, optional inner spaces. Not brackets/other names. |
| F-03 | **JSON without tags / in a code fence without tags.** | probe: bare JSON and a ```` ```json ```` fence outside the tags are `missing_block`; Llama had 2 bare-JSON replies (one is the echoed template `"status": "success \| cannot_complete \| needs_clarification"`, which must stay invalid). | Llama 2 | L1: accept only if the object has ALL contract keys and a valid (or normalisable) status; the template echo stays invalid. Recorded `untagged_json`. |
| F-04 | **Wrapper object.** `{"FINAL_ANSWER_JSON": {...}}` / `{"answer": {...}}`. | not probed in code; plausible for instruction-tuned models that mimic API envelopes. | not seen | L1: unwrap when the object has exactly one key and its value holds the contract keys. |
| F-05 | **Trailing text / extra closing brace.** `json.loads` fails with `Extra data`. | Llama `T13_en`, `T50_mr`: valid object followed by an extra `}`. | Llama 2 | L1: `raw_decode` the first object; ignore trailing whitespace and stray `}`/`]`. |
| F-06 | **Draft block inside `<think>` counts as the answer.** If a model puts a draft block inside `<think>...</think>` and never writes a final one, the draft is scored (probe: OK). The opposite leak exists for value checks (G-02). | probe: `<think>draft <OPEN>{...}<CLOSE></think>` parses OK. | not seen (thinking is off by default now) | L1: strip `<think>...</think>` (and a leading unterminated `...</think>`) BEFORE looking for a block or checking values; recorded `think_stripped`. Makes the strict score stricter for thinking models, so apply it to both scores. |

### B. JSON syntax inside the block

| ID | Problem | Evidence | Seen | Tier / fix |
|---|---|---|---|---|
| F-07 | Trailing comma, single quotes, Python `None/True/False`, `//` comments. | probe: trailing comma, single quotes, comments -> `malformed_json`. (My Python-`None` probe contained no `None`, so it proves nothing; real `None`/`True` are invalid JSON.) | not seen | L1: try strict JSON, then a value-preserving repair (remove trailing commas, `ast.literal_eval` for a pure-literal dict with single quotes / `None/True/False`). Never `eval`; only literals. Recorded `json_repaired`. |
| F-08 | A required key that carries no information is missing: `notes` (never scored, `final_answer.py:36`). | Llama `T10_en`, `T12_hinglish`, ... `missing_keys:notes`. | Llama 3 (2 of them had correct process+state) | L1: `notes` defaults to `""`. Do NOT default `status`, `selected_train`, `selected_class`, `booking_ids`, `requested_passengers` (they carry decisions). |

### C. Field value formats (parser + scorer, `scorer.py:354-386`)

| ID | Problem | Evidence (probe on ideal answers) | Seen | Tier / fix |
|---|---|---|---|---|
| F-09 | **Status spelling**: `Success`, ` success `, `SUCCESS`, `needs clarification`, `needs-clarification`, `cannot_complete.` are `invalid_status` (`final_answer.py:108`). | probe: all FAIL. | not seen | L1: casefold, strip, trailing punctuation, `[ -]` -> `_`. NO: `needs_clarity` (Qwen wrote it three times, as tool arguments) - a typo is a guess. |
| F-10 | **`booking_ids` null** or a bare string `"BK0001"`: `booking_ids_invalid` (`scorer.py:359`). | T01 with `booking_ids: null` FAIL; T04 with `"BK0001"` FAIL. | not seen | L1: null -> `[]`; one string -> `[string]`; comma/space separated ids -> list when every item is a valid id. The ids must still equal the bookings in the final environment state. |
| F-11 | **`requested_passengers` as a string** instead of a list. | T04 `"Ananya Kulkarni"` FAIL. | not seen | L1: single string -> one-element list. NO: several names in one string (ambiguous). |
| F-12 | **`selected_train` / `selected_class` with decoration**: `"BTB103 (Saffron Arc)"`, `"3A (Third AC)"`, `"BTB103."`. `canon_train_id` returns None (`canonical.py:29`). | probe: `Train BTB103` and `BTB103.` -> None; `3A class` -> None. Lowercase, spaces, hyphens, one-element list, `3a`, `AC 2 Tier` already work. | not seen | L1: if the string contains exactly ONE token of the right form (`BTB\d{3}` / one class synonym) take it; two different tokens -> unchanged (fails). |
| F-13 | **Integers as floats or with units** in `answer_values`: `0.0`, `17.0`, `445.0`, `"0 seats"`. `canon_int` / `canon_duration_minutes` reject them (`canonical.py:272-300`). | T34 `seats_available: 0.0` -> `answer_value:invalid`; `duration_minutes: 445.0` invalid. | not seen | L1: float with integral value; string = one integer plus an optional unit word from a short explicit list per language. NO: `7.25` (hours or h:mm?), `about 7 hours`. |
| F-14 | **`answer_values` key spelling**: `OPERATING_DAYS`, `Operating Days`. | T06 upper-cased keys -> `answer_value:missing`. | not seen | L1: key = casefold, spaces/hyphens -> `_`; accepted only if it maps onto exactly one contract key. Same for the top-level contract keys. |

### D. Free-text values in the reply (`VALUE_CHECKS`: fare, times, dates, train lists)

| ID | Problem | Evidence | Seen | Tier / fix |
|---|---|---|---|---|
| F-15 | **Time with seconds** `17:20:00` (the `(?![\d:])` lookahead at `canonical.py:127-133` rejects it); `18h30`. | T08: `Departs at 17:20:00.` -> `value:departure=17:20_not_stated`. | not seen | L1: `H:MM:SS` with seconds `00`; `HHhMM` and `HH.MM hrs/बजे/વાગ્યે` (explicit hour marker). The I-11 rule "`.` only before AM/PM" stays for everything else (so "₹14.50" is not a time). |
| F-16 | **Date forms**: `10th October 2026`, `October 10, 2026`, `10-Oct-2026`, `10.10.2026`, `Oct 10` are not found by `dates_in` (`canonical.py:184`: only `D <month>` / ISO / `D/M/Y`). | T35: `10th October 2026` and `October 10, 2026` -> `value:resolved_date=2026-10-10_not_stated`. | not seen | L1: ordinal suffixes, month-first, `dd-Mon-yyyy`, `dd.mm.yyyy` (4-digit year; numeric forms are read day-first only when the day is > 12 or the month name is spelled out, otherwise they stay unrecognised as today). Same month tables for hi/mr/gu. |
| F-17 | **Currency forms**: `Rs 3565/-` -> not found; `3 565`, `3.565`. | T01 prose `Fare is Rs 3565/-` FAIL. Working: `3,565`, `3565.00 INR`, `₹३५६५`, `૩૫૬૫ રૂપિયા`. | not seen | L1: trailing `/-`. NO: space or `.` as thousands separator (ambiguous with decimals). |
| F-18 | **Thinking text mixed into the answer counts as the answer.** Value checks scan the whole `final_text`, thinking included. | T01: `natural="<think>fare is 3565</think> Done."` PASSES the fare check. | not seen (thinking off) | L1: strip `<think>` before value checks (see F-06). Makes the lenient AND strict score fairer. |

### E. Tool-call transport (adapter + runner)

| ID | Problem | Evidence | Seen | Tier / fix |
|---|---|---|---|---|
| F-19 | **Tool call written as plain text instead of a native call.** The adapter returns `content` as text when Ollama does not convert it (`ollama_adapter.py:290`), the runner sees `not turn.tool_calls` and ends the item (`runner.py:130`), the text has no block -> `missing_block`. | Llama final texts such as `{"name":"search_trains","parameters":{"source":"Nagpur",...}}; {"name":"check_availability",...}`. 40 rows (37 consist only of such objects, 24 hold several, 83 objects in total). Qwen 1. | Llama 40, Qwen 1 | L1 in the RUNNER (so Groq/Gemini/OpenRouter get it too): if a turn has no native calls and the whole text is one or more tool-call objects (optionally in `<tool_call>` tags or a code fence, separated by whitespace/`;`/newlines), keys `name` + `parameters`/`arguments`, `name` an exact known tool -> execute them like native calls. Recorded `text_tool_call`. Guard: any prose around the objects -> not recovered. |
| F-20 | **Unbalanced braces in those objects.** All 40 Llama rows are invalid JSON because the outer `}` is missing (`"parameters":{...}}` closes `parameters` but not the object). | after appending the missing closers 80 of 83 objects parse. | Llama 40 (every row) | L1: append missing closers only (never remove or alter content), recorded `braces_repaired`. |
| F-21 | **Recovery would NOT have rescued these items** (important for honesty): the first call of the 37 repairable rows is `INVALID_STATION` 30, `INVALID_ARGUMENTS` 5, `SAME_STATION` 1, `INVALID_TIME_WINDOW` 1; none executes OK (city names instead of codes, `"null"` placeholders). | computed by replaying the repaired first call against the environment. | - | Consequence: the rule only removes a transport failure; the wrong arguments are then judged normally (strict decision scoring). This is the intended behaviour. |
| F-22 | **Tool name variants**: `Get_Fare`, `functions.get_fare`, `get_fare()`, ` get_fare`, `get-fare` -> `UNKNOWN_TOOL`; the runner compares `call.name` case-sensitively (`runner.py:145`). | probe against `env.call`. | not seen | L1: strip whitespace, casefold, remove `functions.`/`tools.` prefix and trailing `()`; accept only if it then equals exactly one tool name. NO: `get-fare`, `getfare`, any edit-distance match. |
| F-23 | **Ollama discards the reply** (`unparsed_model_output`): the model produced tokens (a `<tool_call>` block Ollama could not convert), Ollama returns empty content and no tool calls (`ollama_adapter.py:262`). The old runs cannot be repaired because the text is gone. | Qwen 43 rows (21.5%): median 98 tokens discarded (min 25, max 241); **27 at the very first turn**, i.e. the model's first action is lost; by language en 11, hinglish 9, **hi 16**, mr 7. 36 of 43 still had a correct final environment state (they did nothing wrong), 5 already satisfied process+state with the calls executed. | Qwen 43 | Not recoverable post hoc. Proposal: (a) on a live server (needs your approval) test whether Ollama 0.40.13 still discards and whether `stream: true` or another request shape exposes the raw text; (b) if it persists, keep the status but make it a separate **transport** category (`unparsed_model_output`) reported next to strict and lenient (not hidden in "malformed output"), and break it down by language because Hindi is hit hardest (32% vs 22% English) - a language-dependent serving artefact, not a language-dependent ability. |

### F. Tool-argument formats (runner, before `env.call`; the environment and its contract stay untouched)

The scorer already canonicalises these forms when it MATCHES gold calls (`canon_tool_args`), but the environment executes the raw
arguments and rejects them, and `_call_matches` requires `ok: true` (`scorer.py`), so the model is punished for a format the scorer
itself considers equal. Aligning the two removes that inconsistency.

| ID | Problem | Evidence | Seen | Tier / fix |
|---|---|---|---|---|
| F-24 | `time_window` passed as a **JSON string** instead of an object. | Llama: `{"time_window": "{\"start\": \"18:00:00\", \"end\": \"23:59:59\"}"}` -> `INVALID_ARGUMENTS` (8 calls). | Llama 8 | L1: if the value is a string that parses to a JSON object, use the object. Recorded `args_json_string`. |
| F-25 | **Time formats** inside `time_window`: `9:00`, `18:00:00`, `23:59:59`, Devanagari digits. | probe: `9:00`, `09:00:00`, `९:००` -> `INVALID_TIME_WINDOW`. Llama used `18:00:00` / `23:59:59`. | Llama (with F-24) | L1: zero-pad the hour, drop seconds (the window has minute resolution; no departure has seconds), ASCII digits. NO: `"end": "null"` or `""` (Llama, 20 rows hold such placeholders): a missing end is not guessable. |
| F-26 | **Train id** case/space/digit script: `btb103`, `BTB 103`, `BTB-103`, `BTB१०३`, `BTB૧૦૩`, full-width, zero-width space. Only surrounding whitespace is tolerated (`railway_env.py:105`). | probe: all `INVALID_TRAIN`. `canon_train_id` even returns `BTB१०३` for the Devanagari id (Python `\d` matches Unicode digits). | not seen | L1: remove whitespace/hyphen/zero-width, upper-case, map digits of any script to ASCII, accept only if the result is `BTB\d{3}`. Same for booking ids in the final answer. NO: `BTB1033`, `BTB10`, `RESERVED_BY_SEARCH` (Qwen 272 `INVALID_TRAIN` are placeholders/invented ids, not formats). |
| F-27 | **Date** forms in tool arguments: `2026-10-9`, `2026/10/09`, Devanagari digits. | probe: `INVALID_DATE`. | not seen | L1: ISO order only (year first): pad parts, accept `/` and `.` as separators, ASCII digits. NO: `09-10-2026`, `10/9` (day/month ambiguity). |
| F-28 | **Class** synonyms the scorer already knows but the environment rejects: `3AC`, `AC3`, `Sleeper`, `3 A`, `३A`. | probe: `3AC`, `3 A`, `३A` -> `INVALID_CLASS`; `3a`, ` 3A ` are fine. | not seen | L1: map through the scorer's explicit table (`_CLASS_SYNONYMS`) after removing spaces and mapping digits. NO: `AC`, `1A` (Llama used both: not offered / ambiguous). |
| F-29 | **Passenger name** trailing punctuation: the environment stores `Ananya Kulkarni.` as given and the scorer compares case/space-folded names only, so state matching fails on the full stop. | probe: `Ananya  Kulkarni.` books, but `canon_passenger` of it != `canon_passenger` of the gold name (verified). | not seen | L1: strip trailing `.`/`,` and collapse spaces before the call. NO: honorifics (`Mr.`), parenthesised text, transliteration. |

### G. Thinking (see F-06, F-18) and serving-layer details

| ID | Problem | Tier / fix |
|---|---|---|
| F-30 | `message.thinking` is separate from content in Ollama, but a model/template that inlines `<think>` in `content` is not stripped anywhere (`ollama_adapter.py:290` passes content through). Covered by F-06/F-18 in the shared module; the adapter should additionally record `thinking_chars` per turn so the paper can report how much thinking leaked (already in `raw_log`). | L1 |
| F-31 | `final_text = turn.text or final_text` (`runner.py:129`) keeps the text of an EARLIER turn when the last turn is empty: an old partial answer can be scored as the final answer (audit M-07, left as is by your decision). With F-19 the text of a recovered-tool-call turn must not become the final text. | Needs your decision; either keep and document, or make the final text the last turn's text only. |

### H. Language-specific checks (every language, not only English)

| ID | Problem | Evidence | Tier / fix |
|---|---|---|---|
| F-32 | **Digits of other scripts in tool arguments and ids** (Hindi/Marathi Devanagari, Gujarati): `BTB१०३`, `२०२६-१०-०९`, `९:००`, `३A` are rejected by the environment; the scorer's free-text readers already map them (`ascii_digits`), the id/date/class readers do not. | Covered by F-25..F-28 (shared `ascii_digits` step). Not seen in old runs; the Hindi/Marathi/Gujarati items are exactly where a model may copy a digit from the user's text. |
| F-33 | **Zero-width characters and Unicode normalisation** in Indic words (ZWJ/ZWNJ, NFC vs NFD): `मंगळवार` + ZWJ -> unknown weekday; NFD forms of weekdays already work. | probe: `canon_weekday("मंगळवार‍")` is None; NFD works. | L1: NFC-normalise and remove U+200B/200C/200D/FEFF in every canonicaliser that reads words (weekdays, yes/no, classes, months). |
| F-34 | **Date words**: month-first and ordinals (F-16) have no Hindi/Marathi/Gujarati counterparts for ordinal words (`१० तारीख`, `10મી`); month names with Marathi suffixes work only by accident (no end boundary). | not seen | L1: add `तारीख`, `મી`, `वा` style ordinals to the date reader, with tests per language. |
| F-35 | **Yes/no words** are one rule in all languages now (2.0.2); ambiguous cases (`हो सकता है` reads as yes, `नहीं तो` as no, English "No problem, ..." as no) are known and listed in AUDIT_REPORT.md section 10. | - | NO change proposed; mentioned for completeness. |
| F-36 | **Reply language is not scored** (correct), so a model answering in English to a Gujarati query is not penalised in the score; the `reply_language_mismatch` tag stays diagnostic. | - | no change. |

### I. Considered and deliberately NOT recovered (would accept a decision error)

- `passenger_name` instead of `passenger` (Qwen: 40 `book_ticket` calls) and other renamed/extra arguments such as `date` on
  `get_train_details` (Llama: 13): a wrong argument name is a tool-use error. Optional, off by default: dropping an *extra* key when
  every required key is valid and nothing is renamed (decision for you; see section 6).
- `needs_clarity`, `cannot complete.`-style typos beyond case/separator/punctuation; any status synonym.
- Several train ids, several classes or several names in one field; `AC`, `1A`; city names where station codes are required
  (Llama: 30 first calls); placeholders (`<train_id_from_search>`, `RESERVED_BY_SEARCH`, `"null"`, `""`).
- Putting the final-answer JSON into the arguments of a tool call (Qwen, 4 calls, `status: needs_clarity`): not a final answer.
- **Prose extraction** (the answer is only in sentences; Llama ~101, Qwen ~100+ items): stays L2/analysis (`format_recovery`),
  reported as the "extended" column, never in the lenient score.

## 3. Estimated effect on the old runs (so you can judge the value before approving)

From the existing audit and my counts, not a new score:

- L1 final-answer rules (F-01, F-05, F-08, F-03): at most the audit's `wrapper_repair` gain: **Qwen +0, Llama +7 items** (3 -> 10 of
  200). Only items whose tool process and state were already correct can change.
- L1 tool-call rules (F-19/F-20/F-24/F-25): change what the environment sees in 40 + 8 Llama calls; the recovered calls are still
  wrong decisions (F-21), so the score effect on the 3B models is small; the value is for models whose text calls are well-formed.
- F-23 (Ollama discards): 43 Qwen items cannot be fixed; they should be reported as a separate transport category.
- L2 prose extraction: Qwen 11/199, Llama 21/200 at most (already measured).

## 4. Strict vs lenient score: definition

- `score_strict`: exactly today's scorer on today's inputs (byte-identical on the old runs; regression test).
- `score` (lenient, L1 rules): same scorer after the recorded recoveries.
- Both come from the same run when the recoveries only touch the **end** of an item (final-answer wrapper/format rules, free-text
  readers): the strict score is computed offline from the raw text. When a recovery changes what the model **sees** during the item
  (text tool calls executed, arguments normalised), the conversation would have continued differently in a strict harness, so the
  strict number is defined as `task_success AND no recovery used` (a **lower bound** of what a strict re-run would give; identical to
  it when no recovery happened). For the paper: report this lower bound for every model, and, for the final two or three models only,
  optionally a real strict re-run (`--strict`, one extra run each) to show the bound is tight.
- Report four columns per model: strict, lenient, lenient-with-recoveries-used (how many items needed any recovery, per rule and per
  language), and the L2 "extended" prose-extraction number from `analysis/format_recovery.py`. Also report the transport category
  `unparsed_model_output` separately (F-23).

## 5. Tests I would add (nothing written yet)

Shared: `tests/test_format_tolerance.py` (new), fixtures in `tests/fixtures/format_cases.jsonl` built from real old-run snippets
(copied, not linked to `runs/`, which is untracked).

1. **Regression:** `score_strict` equals the stored `score.task_success`/labels on the fixtures taken from both old runs.
2. **One test per rule, per language** (en, hinglish, hi, mr, gu where the rule is language-sensitive: digits, months, ordinals, zero-width):
   input -> recovered value + a `format_recoveries` entry with the rule name; the strict result is unchanged.
3. **Counter-example per rule** (must still FAIL, lenient and strict): wrong tool name (`get_fares`), wrong train (`BTB1033`, placeholder),
   class `AC`, status `needs_clarity`, two trains in one field, two names in one string, `end: "null"`, `passenger_name`, template
   echo, prose around text tool calls, a draft block inside `<think>`.
4. **Invariant test over all 75 gold tasks (x 5 languages for language-sensitive rules):** take the ideal row; apply each format
   perturbation -> lenient passes, strict fails (or passes if the perturbation is already tolerated); apply a decision perturbation
   (wrong train/class/status/booking) combined with each format perturbation -> lenient must still fail with the same decision label.
   This is the guarantee that "never accept a wrong action" holds.
5. **Runner tests with a scripted adapter:** text tool calls (`name`+`parameters`, `<tool_call>` tags, fenced, `;`-separated, missing
   closing brace) are executed with ids `recovered-<turn>-<n>`, recorded, and the run continues; text with prose around is not
   recovered; the same behaviour for a Groq-style/Gemini-style scripted adapter (shared code path); `lenient_used` and
   `format_recoveries` appear in the row; raw text and raw arguments are preserved in `raw_log`.
6. **Adapter tests:** unchanged behaviour for native calls; `unparsed_model_output` still raised; `thinking_chars` recorded.
7. **Strict-lower-bound test:** a row with a recovery gets `task_success_strict == False` even when lenient passes; a row without
   recoveries has equal strict and lenient scores.
8. **Analysis tests:** `observe_run` / `compare_runs` carry both scores, the recoveries per rule/language, and the transport
   category; old runs without the new fields still load (fields default to "strict only").
9. **Environment untouched:** the existing tool tests plus a test that `env.call` still rejects `btb103`/`3AC`/`2026-10-9` directly
   (the tolerance lives in the runner layer, so the tool contract and `TOOL_SCHEMA_SHA256` do not change).

## 6. Decisions I need from you before any code

1. **Which score is primary in the paper:** lenient (L1) as headline with strict as sensitivity (my recommendation, because the goal is
   to judge decisions), or strict as headline.
2. **Prompt change (option P-1, not a recovery):** add one worked example of the final block, and one sentence "the block is plain
   text, not a tool call", to the contract prompt. Likely the single most effective fix for 3B-class models (it targets the 186 /
   173 `missing_block` cases and the Qwen "answer wrapped in `<tool_call>`" discards) and fair to every model, but it changes the
   system-prompt hash and needs a version bump (2.1.0) and freeze before the first run.
3. **Optional extra-argument rule** (drop unknown extra keys when all required keys are valid; Llama 13 calls): on or off.
4. **F-31** (carried-over text from an earlier turn): keep or change.
5. **F-23:** may I do a live Ollama check (one model, a handful of requests, no benchmark items) to see whether the discards still
   happen with 0.40.13 and whether another request shape exposes the raw text?
6. **Version/tag:** these changes alter the scorer and the runner (and possibly the prompt): I suggest 2.1.0 / `v2.1.0-data`.

I will not touch any code until you approve specific IDs.


---

## 7. Implementation status (benchmark 2.1.0, tag `v2.1.0-data`) and F-23 results

Decisions applied: (1) lenient = headline (format recovery only, never prose extraction), strict = sensitivity, both stored and reported;
(2) one worked example plus "the block is plain text, not a tool call" in the contract prompt, with invented values only (tested for
leakage); (3) unknown extra argument keys are dropped when every required key is valid and the drop is recorded; nothing is renamed or
repaired (`passenger_name`, `needs_clarity`, placeholders, city names stay failures); (4) the text of a tool-calling turn is never a final
answer, an earlier text counts only if every later turn was empty, recorded; (5) live F-23 check done (below); (6) version 2.1.0.

| ID | Status | Where |
|---|---|---|
| F-01..F-05, F-07, F-08 | done (L1) | `evaluation/tolerance.py` `parse_final_answer_lenient`, used by `score(lenient=True)` |
| F-06, F-18, F-30 | done | `strip_thinking` (final answer and value checks, strict and lenient readers of the lenient score) |
| F-09..F-14 | done | `normalize_answer` (status spelling, booking_ids/requested_passengers shapes, train/class decoration, integer forms, key spelling) |
| F-15..F-17, F-34 | done | `times_in_lenient`, `dates_in_lenient`, `numbers_in_lenient`; rescues are recorded as `value_format:<kind>` |
| F-19, F-20 | done | `extract_text_tool_calls` + runner (Ollama, Groq, OpenRouter/NVIDIA; Gemini cannot attach the call to its history, so it gets no text-call recovery) |
| F-22 | done | `normalize_tool_name` |
| F-24..F-29, extra keys | done | `normalize_arguments` in `execute_tool_call` (the environment is untouched) |
| F-31 | done (decision 4) | `final_text_from_turns` |
| F-32, F-33 | done | `digits_to_ascii` (any script) and `clean_text` (NFC, zero-width) in every reader |
| F-21, F-35, F-36 | no change (informational) | |
| F-23 | not recoverable post hoc; **fixed by the Ollama version** (below) | |
| prompt example (P-1) | done | `evaluation/final_answer.py` `CONTRACT_PROMPT`, `tests/test_prompt_example.py` |

Recording: every recovery is a record `{stage, rule, before, after, turn, tool_call_id}` in `row["format_recoveries"]` (run time) and
`row["score"]["format_recoveries"]` (run time + final answer); `row["lenient_used"]`; `raw_log` keeps the raw text/arguments and a
`format_recovery` entry per rule. `row["score"]` is the lenient headline, `row["score_strict"]` the strict sensitivity score (strict =
success AND no run-time recovery, a lower bound; exact when only the final answer was recovered).
Analysis: `observe_run` summary section "Lenient (headline) and strict (sensitivity)" (rule and language counts, transport category),
`compare_runs` columns `task_success_strict` and `items_with_recovery`.

Tests: `tests/test_format_tolerance.py` (142: every rule, counter-examples, per language), `tests/test_format_invariants.py` (75 tasks x 5
languages x 19 format changes: correct answer passes and every rescue is recorded; the same changes plus a wrong train/class/status/
booking/value still fail; thinking text neither answers nor satisfies a value), `tests/test_format_runner.py` (runner integration and the
tool-call invariant over 75 tasks x 5 languages: format variants have the same environment effect, plus a wrong value is still an error),
`tests/test_prompt_example.py`, `tests/test_observe_run.py` (strict/lenient columns).

### F-23 live check (2026-11-24, one small model, no benchmark items)

Setup: `qwen2.5:3b` (digest `357c53fb659c...`, the same weights as the old Qwen run) pulled into a separate model directory
`~/FreeModel/f23/models`; Ollama 0.40.13 (the installed one) and 0.40.18 (latest release, downloaded to `~/FreeModel/f23/v0.40.18`, no sudo,
own port 11436). 34 invented queries (en 6, hinglish 6, hi 10, mr 6, gu 6) with the real system prompt, tool schemas, settings (temperature 0,
seed 42, num_ctx 16384, num_predict 2048) and the real environment for up to 6 turns; counts are replies whose content AND tool calls are
empty although tokens were generated (the `unparsed_model_output` condition).

| server | tool schema sent | replies | discarded |
|---|---|---|---|
| 0.40.13 | original (`$ref`/`$defs`, as in the old 3B runs) | 66 / 65 (two repeats) | **4 / 4** (all at turn 1) |
| 0.40.13 | `$ref` inlined (current adapter, `anyOf [object, null]`) | 74 / 74 | **1 / 1** |
| 0.40.13 | `time_window` as a plain object (no `anyOf`) | 72 / 72 | **0 / 0** |
| 0.40.18 | original | 76 | **0** |
| 0.40.18 | inlined | 77 | **0** |
| 0.40.18 | plain object | 75 | **0** |

Findings: (a) the discards reproduce on 0.40.13 and are deterministic across repeats; (b) the model's raw output for a discarded reply (raw
`/api/generate` with the Qwen template) is a well-formed `<tool_call>{"name": "search_trains", "arguments": {..., "time_window": {...}}}</tool_call>`,
so the discard is Ollama's tool-call parser rejecting a valid call, not a model failure; (c) it depends on how the schema reaches the parser
(original > inlined > plain object); (d) `stream: true` does not expose the text (one empty chunk); (e) **Ollama 0.40.18 produced no discard in
any of ~230 replies, with any of the three schema forms**; the adapter (`preflight`, `start`) works unchanged against 0.40.18 (capabilities
`completion, tools`, native tool call parsed).

Applied (approved): **Ollama 0.40.18 is the standard server** (installed in `~/FreeModel/ollama`, the previous 0.40.13 install kept in
`~/FreeModel/ollama-0.40.13-old`), started in tmux with `OLLAMA_MODELS=$HOME/FreeModel/models` (see `LOCAL_MODELS.md`). `OllamaAdapter.preflight()`
(also run by `start()`, `run_pilot` and the pre-run snapshot) **refuses** a server older than 0.40.18 or one without a usable version
(`ollama_too_old`, numeric comparison); the version is recorded in every run row (`adapter_settings.ollama_version`), the pre-run snapshot
(`ollama_version`, `ollama_min_version`) and the run manifest (`ollama_version`, `ollama_versions_in_rows`, `ollama_version_consistent`), and listed in
the `observe_run` summary. The adapter keeps the inlined `$ref` schema. Checked against the real servers: 0.40.18 accepted, 0.40.13 refused.

**Consequence for the existing results:** the old Qwen 2.5 3B run (and the Llama 3.2 3B run) were produced on Ollama 0.40.3 with 8192 context,
1024 output tokens, the flattened `time_window` schema and no format tolerance. The Qwen run is affected by the Ollama discard bug (43 of 200 replies,
21.5%, 27 of them the very first reply of the item); both runs are therefore **pilot-only** and **both 3B models will be re-run** on 0.40.18 with the
2.1.0 settings before any comparison with other models. The test files (`~/FreeModel/f23`) were removed after the new server was installed and checked.
