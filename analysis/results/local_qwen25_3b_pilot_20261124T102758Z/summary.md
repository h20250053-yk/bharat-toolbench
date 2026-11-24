# Run summary: local_qwen25_3b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_qwen25_3b_pilot_20261124T102758Z.jsonl` (25 rows, sha256 57ded636c1f2...)
- expected items 25, selected 25, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **0/25 (0.0%)** (not scored: 0)
- status: {'completed': 22, 'malformed_output': 2, 'output_truncated': 1}
- final-answer parse ok: 3/25 (12.0%); process ok: 4/25 (16.0%); state ok: 17/25 (68.0%)
- tool calls ok: 124/219 (56.6%); top error codes: {'INVALID_TRAIN': 54, 'INVALID_STATION': 17, 'STATION_NOT_FOUND': 17, 'INVALID_ARGUMENTS': 3, 'SOLD_OUT': 2, 'CLASS_NOT_OFFERED': 2}
- failure label families: {'process:missing_required_call': 67, 'final_answer:missing_block': 22, 'process:prohibited_action': 14, 'state:bookings_mismatch': 8, 'run:malformed_output': 2, 'final_answer:booking_ids_do_not_match_state': 2, 'status:expected_success_got_cannot_complete': 1, 'run:output_truncated': 1, 'final_answer:wrong_selected_train': 1, 'final_answer:wrong_selected_class': 1, 'value:fare_inr=450_not_stated': 1, 'process:dependency_violation': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **0/25 (0.0%)**; strict: 0/25 (0.0%)
- items that needed a format recovery: 0; by rule {}; by language {}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 2, 'by_language': {'hinglish': 1, 'hi': 1}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 0/25 (0.0%); no-tool tasks: 0/0
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 0/5 (0.0%) | 2 | 2 | 2 | {'format_only': 1, 'unsafe_action': 3, 'tool_argument_error': 1} |
| gu | 0/5 (0.0%) | 1 | 0 | 4 | {'missing_required_call': 1, 'tool_argument_error': 2, 'output_truncated': 1, 'missing_booking': 1} |
| hi | 0/5 (0.0%) | 0 | 1 | 4 | {'format_only': 1, 'tool_argument_error': 1, 'malformed_model_output': 1, 'missing_booking': 1, 'unsafe_action': 1} |
| hinglish | 0/5 (0.0%) | 0 | 1 | 4 | {'format_only': 1, 'tool_argument_error': 2, 'malformed_model_output': 1, 'missing_booking': 1} |
| mr | 0/5 (0.0%) | 0 | 0 | 3 | {'missing_required_call': 1, 'tool_argument_error': 2, 'missing_booking': 1, 'unsafe_action': 1} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 5 | 0 | 1 | 0 | 0 |
| constraint | 5 | 0 | 0 | 0 | 5 |
| recovery | 5 | 0 | 1 | 0 | 3 |
| sequential | 5 | 0 | 1 | 1 | 4 |
| single_tool | 5 | 0 | 0 | 3 | 5 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'missing_required_call': 2} |
| T02 | 0/5 | 1 | 1 | 4 | {'unsafe_action': 1, 'tool_argument_error': 4} |
| T03 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 2, 'malformed_model_output': 2, 'output_truncated': 1} |
| T04 | 0/5 | 1 | 0 | 0 | {'unsafe_action': 1, 'missing_booking': 4} |
| T05 | 0/5 | 1 | 0 | 3 | {'unsafe_action': 3, 'tool_argument_error': 2} |

## Diagnostic classification (not an official score)

- primary_failure: {'output_truncated': 1, 'malformed_model_output': 2, 'unsafe_action': 5, 'missing_booking': 4, 'tool_argument_error': 8, 'missing_required_call': 2, 'format_only': 3}
- secondary tags: {'no_final_block': 22, 'reply_language_mismatch': 12, 'guessed_station_code': 12, 'invalid_train_id_format': 9, 'unresolvable_station_name': 6, 'unexpected_booking': 4, 'missing_expected_booking': 4, 'empty_final_text': 3, 'kind:unparsed_model_output': 2, 'repetition_or_truncation': 1}
- format_only (tool process and booking state correct, only the final-answer block failed): 3 items

## Cost

- tokens: input 145799, output 14679, cached input 127242
- items retried: 0; wall time 119.1 s (sum of item times 119.1 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
