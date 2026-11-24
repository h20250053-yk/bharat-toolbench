# Run summary: local_llama31_8b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_llama31_8b_pilot_20261124T102758Z.jsonl` (25 rows, sha256 4f0fdef0736e...)
- expected items 25, selected 25, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **6/25 (24.0%)** (not scored: 0)
- status: {'completed': 23, 'output_truncated': 2}
- final-answer parse ok: 14/25 (56.0%); process ok: 6/25 (24.0%); state ok: 20/25 (80.0%)
- tool calls ok: 7/38 (18.4%); top error codes: {'INVALID_TRAIN': 12, 'INVALID_STATION': 9, 'STATION_NOT_FOUND': 6, 'SOLD_OUT': 3, 'INVALID_ARGUMENTS': 1}
- failure label families: {'process:missing_required_call': 89, 'final_answer:missing_block': 10, 'process:prohibited_action': 6, 'state:bookings_mismatch': 5, 'status:expected_success_got_cannot_complete': 4, 'run:output_truncated': 2, 'value:fare_inr=3565_not_stated': 1, 'final_answer:missing_keys': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **6/25 (24.0%)**; strict: 6/25 (24.0%)
- items that needed a format recovery: 4; by rule {'extra_args_dropped': 4, 'text_tool_call': 1, 'closing_braces_appended': 1}; by language {'en': 2, 'hi': 1, 'gu': 1}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 6/25 (24.0%); no-tool tasks: 0/0
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 2/5 (40.0%) | 2 | 2 | 4 | {'success': 2, 'tool_argument_error': 2, 'missing_booking': 1} |
| gu | 1/5 (20.0%) | 3 | 1 | 4 | {'success': 1, 'output_truncated': 1, 'tool_argument_error': 1, 'missing_booking': 1, 'unsafe_action': 1} |
| hi | 1/5 (20.0%) | 2 | 1 | 4 | {'success': 1, 'tool_argument_error': 2, 'missing_booking': 1, 'unsafe_action': 1} |
| hinglish | 1/5 (20.0%) | 3 | 1 | 4 | {'success': 1, 'tool_argument_error': 2, 'missing_booking': 1, 'unsafe_action': 1} |
| mr | 1/5 (20.0%) | 4 | 1 | 4 | {'missing_required_call': 1, 'tool_argument_error': 1, 'output_truncated': 1, 'missing_booking': 1, 'success': 1} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 5 | 0 | 2 | 0 | 0 |
| constraint | 5 | 0 | 0 | 0 | 5 |
| recovery | 5 | 2 | 5 | 2 | 5 |
| sequential | 5 | 0 | 2 | 0 | 5 |
| single_tool | 5 | 4 | 5 | 4 | 5 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T02 | 0/5 | 2 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T03 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T04 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T05 | 2/5 | 5 | 2 | 5 | {'success': 2, 'unsafe_action': 3} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 6, 'output_truncated': 2, 'unsafe_action': 3, 'missing_booking': 5, 'tool_argument_error': 8, 'missing_required_call': 1}
- secondary tags: {'reply_language_mismatch': 10, 'no_final_block': 10, 'guessed_station_code': 9, 'invalid_train_id_format': 6, 'missing_expected_booking': 5, 'unresolvable_station_name': 3, 'empty_final_text': 2, 'tool_call_as_text': 1}
- format_only (tool process and booking state correct, only the final-answer block failed): 0 items

## Cost

- tokens: input 64790, output 4162, cached input 44366
- items retried: 0; wall time 103.7 s (sum of item times 103.7 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
