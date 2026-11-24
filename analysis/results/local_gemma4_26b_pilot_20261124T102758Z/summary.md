# Run summary: local_gemma4_26b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_gemma4_26b_pilot_20261124T102758Z.jsonl` (25 rows, sha256 b39dfc29c49a...)
- expected items 25, selected 25, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **18/25 (72.0%)** (not scored: 0)
- status: {'completed': 25}
- final-answer parse ok: 25/25 (100.0%); process ok: 21/25 (84.0%); state ok: 25/25 (100.0%)
- tool calls ok: 101/106 (95.3%); top error codes: {'INVALID_ARGUMENTS': 5}
- failure label families: {'process:missing_required_call': 4, 'value:fare_inr=450_not_stated': 3, 'status:expected_success_got_needs_clarification': 2, 'value:fare_inr=3565_not_stated': 2}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **18/25 (72.0%)**; strict: 18/25 (72.0%)
- items that needed a format recovery: 0; by rule {}; by language {}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 18/25 (72.0%); no-tool tasks: 0/0
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 5/5 (100.0%) | 5 | 5 | 5 | {'success': 5} |
| gu | 3/5 (60.0%) | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 3, 'wrong_answer': 1} |
| hi | 4/5 (80.0%) | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 4} |
| hinglish | 3/5 (60.0%) | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 3, 'wrong_answer': 1} |
| mr | 3/5 (60.0%) | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 3, 'wrong_answer': 1} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 5 | 2 | 5 | 5 | 5 |
| constraint | 5 | 5 | 5 | 5 | 5 |
| recovery | 5 | 5 | 5 | 5 | 5 |
| sequential | 5 | 5 | 5 | 5 | 5 |
| single_tool | 5 | 1 | 5 | 1 | 5 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 1/5 | 5 | 1 | 5 | {'success': 1, 'missing_required_call': 4} |
| T02 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T03 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T04 | 2/5 | 5 | 5 | 5 | {'success': 2, 'wrong_answer': 3} |
| T05 | 5/5 | 5 | 5 | 5 | {'success': 5} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 18, 'missing_required_call': 4, 'wrong_answer': 3}
- secondary tags: {'reply_language_mismatch': 15}
- format_only (tool process and booking state correct, only the final-answer block failed): 0 items

## Cost

- tokens: input 172321, output 7517, cached input 158221
- items retried: 0; wall time 88.0 s (sum of item times 87.9 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '001e5dafc3c77684c2307ebc6ab8e336e10c9b18eca52acf547d72fc83c3ca8c', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
