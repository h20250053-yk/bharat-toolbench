# Run summary: local_qwen25_14b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_qwen25_14b_pilot_20261124T102758Z.jsonl` (25 rows, sha256 24fb33c3093b...)
- expected items 25, selected 25, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **11/25 (44.0%)** (not scored: 0)
- status: {'completed': 25}
- final-answer parse ok: 23/25 (92.0%); process ok: 11/25 (44.0%); state ok: 22/25 (88.0%)
- tool calls ok: 70/169 (41.4%); top error codes: {'INVALID_TRAIN': 90, 'INVALID_STATION': 7, 'SOLD_OUT': 2}
- failure label families: {'process:missing_required_call': 40, 'final_answer:wrong_selected_train': 4, 'process:prohibited_action': 4, 'value:fare_inr=1035_not_stated': 3, 'state:bookings_mismatch': 3, 'status:expected_success_got_cannot_complete': 2, 'final_answer:wrong_selected_class': 2, 'value:fare_inr=450_not_stated': 2, 'value:fare_inr=3565_not_stated': 1, 'final_answer:missing_block': 1, 'value:fare_inr=1540_not_stated': 1, 'answer_value:wrong': 1, 'final_answer:selected_train_invalid': 1, 'final_answer:missing_keys': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **11/25 (44.0%)**; strict: 11/25 (44.0%)
- items that needed a format recovery: 0; by rule {}; by language {}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 11/25 (44.0%); no-tool tasks: 0/0
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 2/5 (40.0%) | 5 | 2 | 4 | {'missing_required_call': 1, 'success': 2, 'unsafe_action': 2} |
| gu | 3/5 (60.0%) | 4 | 3 | 4 | {'success': 3, 'tool_argument_error': 1, 'missing_booking': 1} |
| hi | 2/5 (40.0%) | 5 | 2 | 5 | {'success': 2, 'tool_argument_error': 2, 'unsafe_action': 1} |
| hinglish | 3/5 (60.0%) | 4 | 3 | 5 | {'success': 3, 'tool_argument_error': 2} |
| mr | 1/5 (20.0%) | 5 | 1 | 4 | {'success': 1, 'tool_argument_error': 1, 'missing_required_call': 2, 'unsafe_action': 1} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 5 | 2 | 4 | 2 | 2 |
| constraint | 5 | 1 | 5 | 1 | 5 |
| recovery | 5 | 2 | 5 | 2 | 5 |
| sequential | 5 | 2 | 4 | 2 | 5 |
| single_tool | 5 | 4 | 5 | 4 | 5 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 4/5 | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 4} |
| T02 | 2/5 | 4 | 2 | 5 | {'success': 2, 'tool_argument_error': 3} |
| T03 | 1/5 | 5 | 1 | 5 | {'success': 1, 'tool_argument_error': 3, 'missing_required_call': 1} |
| T04 | 2/5 | 4 | 2 | 2 | {'unsafe_action': 2, 'success': 2, 'missing_booking': 1} |
| T05 | 2/5 | 5 | 2 | 5 | {'unsafe_action': 2, 'success': 2, 'missing_required_call': 1} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 11, 'unsafe_action': 4, 'missing_booking': 1, 'tool_argument_error': 6, 'missing_required_call': 3}
- secondary tags: {'reply_language_mismatch': 14, 'invalid_train_id_format': 11, 'guessed_station_code': 7, 'missing_expected_booking': 3, 'unexpected_booking': 2, 'no_final_block': 1}
- format_only (tool process and booking state correct, only the final-answer block failed): 0 items

## Cost

- tokens: input 126830, output 14573, cached input 111474
- items retried: 0; wall time 323.7 s (sum of item times 323.6 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
