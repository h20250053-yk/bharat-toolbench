# Run summary: local_deepseek_r1_8b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_deepseek_r1_8b_pilot_20261124T102758Z.jsonl` (25 rows, sha256 a51b86df4856...)
- expected items 25, selected 25, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **0/25 (0.0%)** (not scored: 0)
- status: {'completed': 20, 'output_truncated': 5}
- final-answer parse ok: 20/25 (80.0%); process ok: 0/25 (0.0%); state ok: 20/25 (80.0%)
- tool calls ok: 0/0; top error codes: {}
- failure label families: {'process:missing_required_call': 95, 'status:expected_success_got_needs_clarification': 6, 'final_answer:selected_train_invalid': 6, 'run:output_truncated': 5, 'final_answer:missing_block': 5, 'state:bookings_mismatch': 5, 'value:fare_inr=1035_not_stated': 3, 'final_answer:booking_ids_invalid': 3, 'value:fare_inr=450_not_stated': 3, 'status:expected_cannot_complete_got_needs_clarification': 3, 'value:fare_inr=3565_not_stated': 2, 'value:fare_inr=1540_not_stated': 1, 'answer_value:wrong': 1, 'final_answer:wrong_selected_train': 1, 'final_answer:wrong_selected_class': 1, 'final_answer:booking_ids_do_not_match_state': 1, 'status:expected_cannot_complete_got_success': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **0/25 (0.0%)**; strict: 0/25 (0.0%)
- items that needed a format recovery: 1; by rule {'trailing_text_ignored': 1}; by language {'mr': 1}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 0/25 (0.0%); no-tool tasks: 0/0
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 0/5 (0.0%) | 2 | 0 | 4 | {'missing_required_call': 2, 'output_truncated': 3} |
| gu | 0/5 (0.0%) | 4 | 0 | 4 | {'missing_required_call': 3, 'output_truncated': 1, 'missing_booking': 1} |
| hi | 0/5 (0.0%) | 5 | 0 | 4 | {'missing_required_call': 4, 'missing_booking': 1} |
| hinglish | 0/5 (0.0%) | 5 | 0 | 4 | {'missing_required_call': 4, 'missing_booking': 1} |
| mr | 0/5 (0.0%) | 4 | 0 | 4 | {'missing_required_call': 4, 'output_truncated': 1} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 5 | 0 | 3 | 0 | 0 |
| constraint | 5 | 0 | 3 | 0 | 5 |
| recovery | 5 | 0 | 5 | 0 | 5 |
| sequential | 5 | 0 | 4 | 0 | 5 |
| single_tool | 5 | 0 | 5 | 0 | 5 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T02 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T03 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T04 | 0/5 | 3 | 0 | 0 | {'output_truncated': 2, 'missing_booking': 3} |
| T05 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |

## Diagnostic classification (not an official score)

- primary_failure: {'output_truncated': 5, 'missing_booking': 3, 'missing_required_call': 17}
- secondary tags: {'reply_language_mismatch': 15, 'empty_final_text': 5, 'no_final_block': 5, 'missing_expected_booking': 5}
- format_only (tool process and booking state correct, only the final-answer block failed): 0 items

## Cost

- tokens: input 20223, output 13842, cached input 18164
- items retried: 0; wall time 290.0 s (sum of item times 290.0 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '6995872bfe4c521a67b32da386cd21d5c6e819b6e0d62f79f64ec83be99f5763', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
