# Run summary: local_gpt_oss_20b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_gpt_oss_20b_pilot_20261124T102758Z.jsonl` (25 rows, sha256 c2d2a065cf52...)
- expected items 25, selected 25, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **22/25 (88.0%)** (not scored: 0)
- status: {'completed': 24, 'step_limit_exceeded': 1}
- final-answer parse ok: 24/25 (96.0%); process ok: 24/25 (96.0%); state ok: 24/25 (96.0%)
- tool calls ok: 104/106 (98.1%); top error codes: {'INVALID_ARGUMENTS': 2}
- failure label families: {'value:fare_inr=1035_not_stated': 1, 'value:fare_inr=450_not_stated': 1, 'run:step_limit_exceeded': 1, 'state:bookings_mismatch': 1, 'final_answer:missing_block': 1, 'process:missing_required_call': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **22/25 (88.0%)**; strict: 22/25 (88.0%)
- items that needed a format recovery: 0; by rule {}; by language {}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 22/25 (88.0%); no-tool tasks: 0/0
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 4/5 (80.0%) | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| gu | 4/5 (80.0%) | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| hi | 4/5 (80.0%) | 4 | 4 | 4 | {'success': 4, 'step_limit': 1} |
| hinglish | 5/5 (100.0%) | 5 | 5 | 5 | {'success': 5} |
| mr | 5/5 (100.0%) | 5 | 5 | 5 | {'success': 5} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 5 | 3 | 4 | 4 | 4 |
| constraint | 5 | 4 | 5 | 5 | 5 |
| recovery | 5 | 5 | 5 | 5 | 5 |
| sequential | 5 | 5 | 5 | 5 | 5 |
| single_tool | 5 | 5 | 5 | 5 | 5 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T02 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T03 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T04 | 3/5 | 4 | 4 | 4 | {'wrong_answer': 1, 'success': 3, 'step_limit': 1} |
| T05 | 5/5 | 5 | 5 | 5 | {'success': 5} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 22, 'step_limit': 1, 'wrong_answer': 2}
- secondary tags: {'reply_language_mismatch': 15, 'empty_final_text': 1, 'missing_expected_booking': 1, 'no_final_block': 1}
- format_only (tool process and booking state correct, only the final-answer block failed): 0 items

## Cost

- tokens: input 228667, output 7864, cached input 217509
- items retried: 0; wall time 103.3 s (sum of item times 103.2 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': 'f38aa0c53da5f8c49d08c43a99df24ff53167fe68e24664a7777288e7656fdfe', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
