# Run summary: local_llama32_3b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_llama32_3b_pilot_20261124T102758Z.jsonl` (25 rows, sha256 64a88fd2a0c5...)
- expected items 25, selected 25, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **1/25 (4.0%)** (not scored: 0)
- status: {'completed': 24, 'output_truncated': 1}
- final-answer parse ok: 10/25 (40.0%); process ok: 4/25 (16.0%); state ok: 20/25 (80.0%)
- tool calls ok: 6/35 (17.1%); top error codes: {'INVALID_TRAIN': 15, 'INVALID_ARGUMENTS': 6, 'INVALID_STATION': 4, 'SOLD_OUT': 4}
- failure label families: {'process:missing_required_call': 91, 'final_answer:missing_block': 15, 'process:prohibited_action': 8, 'state:bookings_mismatch': 5, 'status:expected_success_got_needs_clarification': 4, 'status:expected_success_got_cannot_complete': 2, 'value:fare_inr=3565_not_stated': 1, 'run:output_truncated': 1, 'status:expected_cannot_complete_got_needs_clarification': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **1/25 (4.0%)**; strict: 0/25 (0.0%)
- items that needed a format recovery: 11; by rule {'extra_args_dropped': 6, 'trailing_text_ignored': 4, 'args_json_string': 4, 'time_format': 3, 'closing_tag_missing': 2}; by language {'hi': 2, 'mr': 3, 'en': 3, 'gu': 2, 'hinglish': 1}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 1/25 (4.0%); no-tool tasks: 0/0
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 0/5 (0.0%) | 2 | 1 | 4 | {'format_only': 1, 'tool_argument_error': 2, 'missing_booking': 1, 'unsafe_action': 1} |
| gu | 0/5 (0.0%) | 2 | 0 | 4 | {'missing_required_call': 1, 'tool_argument_error': 1, 'output_truncated': 1, 'missing_booking': 1, 'unsafe_action': 1} |
| hi | 1/5 (20.0%) | 3 | 1 | 4 | {'success': 1, 'tool_argument_error': 2, 'missing_booking': 1, 'unsafe_action': 1} |
| hinglish | 0/5 (0.0%) | 1 | 1 | 4 | {'format_only': 1, 'tool_argument_error': 2, 'missing_booking': 1, 'unsafe_action': 1} |
| mr | 0/5 (0.0%) | 2 | 1 | 4 | {'missing_required_call': 1, 'tool_argument_error': 2, 'missing_booking': 1, 'format_only': 1} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 5 | 0 | 3 | 0 | 0 |
| constraint | 5 | 0 | 0 | 0 | 5 |
| recovery | 5 | 0 | 2 | 1 | 5 |
| sequential | 5 | 0 | 3 | 0 | 5 |
| single_tool | 5 | 1 | 2 | 3 | 5 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 1/5 | 2 | 3 | 5 | {'format_only': 2, 'success': 1, 'missing_required_call': 2} |
| T02 | 0/5 | 3 | 0 | 5 | {'tool_argument_error': 5} |
| T03 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T04 | 0/5 | 3 | 0 | 0 | {'missing_booking': 5} |
| T05 | 0/5 | 2 | 1 | 5 | {'unsafe_action': 4, 'format_only': 1} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 1, 'output_truncated': 1, 'unsafe_action': 4, 'missing_booking': 5, 'tool_argument_error': 9, 'missing_required_call': 2, 'format_only': 3}
- secondary tags: {'no_final_block': 15, 'reply_language_mismatch': 10, 'invalid_train_id_format': 9, 'missing_expected_booking': 5, 'guessed_station_code': 4, 'empty_final_text': 1}
- format_only (tool process and booking state correct, only the final-answer block failed): 3 items

## Cost

- tokens: input 68271, output 4891, cached input 46568
- items retried: 0; wall time 50.9 s (sum of item times 50.9 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': 'a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
