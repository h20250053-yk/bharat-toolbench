# Run summary: local_mistral_small32_24b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_mistral_small32_24b_pilot_20261124T102758Z.jsonl` (25 rows, sha256 59e461af6b3f...)
- expected items 25, selected 25, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **1/25 (4.0%)** (not scored: 0)
- status: {'completed': 12, 'malformed_output': 12, 'output_truncated': 1}
- final-answer parse ok: 3/25 (12.0%); process ok: 7/25 (28.0%); state ok: 20/25 (80.0%)
- tool calls ok: 7/9 (77.8%); top error codes: {'SOLD_OUT': 1, 'INVALID_ARGUMENTS': 1}
- failure label families: {'process:missing_required_call': 88, 'final_answer:missing_block': 17, 'run:malformed_output': 12, 'final_answer:missing_keys': 5, 'state:bookings_mismatch': 5, 'process:prohibited_action': 2, 'run:output_truncated': 1, 'status:expected_cannot_complete_got_needs_clarification': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **1/25 (4.0%)**; strict: 1/25 (4.0%)
- items that needed a format recovery: 0; by rule {}; by language {}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 12, 'by_language': {'en': 3, 'hi': 3, 'mr': 1, 'gu': 4, 'hinglish': 1}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 1/25 (4.0%); no-tool tasks: 0/0
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 1/5 (20.0%) | 1 | 2 | 4 | {'format_only': 1, 'malformed_model_output': 3, 'success': 1} |
| gu | 0/5 (0.0%) | 0 | 1 | 4 | {'format_only': 1, 'malformed_model_output': 4} |
| hi | 0/5 (0.0%) | 1 | 1 | 4 | {'format_only': 1, 'malformed_model_output': 3, 'unsafe_action': 1} |
| hinglish | 0/5 (0.0%) | 0 | 1 | 4 | {'format_only': 1, 'missing_required_call': 2, 'malformed_model_output': 1, 'missing_booking': 1} |
| mr | 0/5 (0.0%) | 1 | 2 | 4 | {'format_only': 1, 'malformed_model_output': 1, 'output_truncated': 1, 'missing_booking': 1, 'wrong_answer': 1} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 5 | 0 | 0 | 0 | 0 |
| constraint | 5 | 0 | 0 | 0 | 5 |
| recovery | 5 | 1 | 3 | 2 | 5 |
| sequential | 5 | 0 | 0 | 0 | 5 |
| single_tool | 5 | 0 | 0 | 5 | 5 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T02 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 4, 'missing_required_call': 1} |
| T03 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 4, 'output_truncated': 1} |
| T04 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T05 | 1/5 | 3 | 2 | 5 | {'success': 1, 'missing_required_call': 1, 'unsafe_action': 1, 'wrong_answer': 1, 'malformed_model_output': 1} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 1, 'output_truncated': 1, 'malformed_model_output': 12, 'unsafe_action': 1, 'missing_booking': 2, 'missing_required_call': 2, 'wrong_answer': 1, 'format_only': 5}
- secondary tags: {'no_final_block': 17, 'empty_final_text': 13, 'kind:unparsed_model_output': 12, 'reply_language_mismatch': 5, 'missing_expected_booking': 5}
- format_only (tool process and booking state correct, only the final-answer block failed): 5 items

## Cost

- tokens: input 32904, output 1444, cached input 26006
- items retried: 0; wall time 125.3 s (sum of item times 125.3 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
