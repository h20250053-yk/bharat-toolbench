# Run summary: local_gemma4_26b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_gemma4_26b_full_20261124T105853Z.jsonl` (375 rows, sha256 a6b1c89ac6ef...)
- expected items 375, selected 375, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **286/375 (76.3%)** (not scored: 0)
- status: {'completed': 368, 'step_limit_exceeded': 7}
- final-answer parse ok: 363/375 (96.8%); process ok: 344/375 (91.7%); state ok: 347/375 (92.5%)
- tool calls ok: 1577/1704 (92.5%); top error codes: {'STATION_NOT_FOUND': 51, 'INVALID_ARGUMENTS': 43, 'INVALID_TRAIN': 10, 'PAST_DATE': 5, 'SAME_STATION': 5, 'DUPLICATE_BOOKING': 5, 'CLASS_NOT_OFFERED': 3, 'INVALID_PASSENGER': 3, 'SOLD_OUT': 2}
- failure label families: {'process:missing_required_call': 41, 'state:bookings_mismatch': 28, 'status:expected_needs_clarification_got_success': 16, 'final_answer:missing_block': 12, 'status:expected_cannot_complete_got_success': 11, 'final_answer:wrong_selected_train': 9, 'run:step_limit_exceeded': 7, 'value:resolved_date=2026-10-10_not_stated': 7, 'status:expected_success_got_needs_clarification': 6, 'status:expected_needs_clarification_got_cannot_complete': 6, 'value:departure=20': 5, 'answer_value:missing': 4, 'value:fare_inr=450_not_stated': 3, 'status:expected_success_got_cannot_complete': 3, 'value:fare_inr=305_not_stated': 3, 'value:fare_inr=3565_not_stated': 2, 'final_answer:booking_ids_invalid': 1, 'value:fare_inr=2495_not_stated': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **286/375 (76.3%)**; strict: 286/375 (76.3%)
- items that needed a format recovery: 0; by rule {}; by language {}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 254/320 (79.4%); no-tool tasks: 32/55 (58.2%)
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 59/75 (78.7%) | 72 | 71 | 69 | {'success': 59, 'format_only': 1, 'step_limit': 1, 'unsafe_action': 5, 'missing_required_call': 2, 'missing_booking': 1, 'wrong_answer': 6} |
| gu | 54/75 (72.0%) | 71 | 68 | 69 | {'missing_required_call': 4, 'success': 54, 'wrong_answer': 8, 'format_only': 1, 'step_limit': 2, 'unsafe_action': 4, 'missing_booking': 2} |
| hi | 61/75 (81.3%) | 73 | 70 | 70 | {'missing_required_call': 3, 'success': 61, 'format_only': 1, 'step_limit': 1, 'unsafe_action': 4, 'wrong_answer': 4, 'missing_booking': 1} |
| hinglish | 56/75 (74.7%) | 74 | 68 | 70 | {'missing_required_call': 5, 'success': 56, 'wrong_answer': 7, 'step_limit': 1, 'unsafe_action': 5, 'tool_argument_error': 1} |
| mr | 56/75 (74.7%) | 73 | 67 | 69 | {'missing_required_call': 4, 'success': 56, 'wrong_answer': 6, 'step_limit': 2, 'unsafe_action': 4, 'missing_booking': 2, 'tool_argument_error': 1} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 75 | 54 | 73 | 68 | 69 |
| clarification | 45 | 17 | 40 | 40 | 28 |
| constraint | 90 | 65 | 90 | 77 | 85 |
| invalid_input | 30 | 25 | 25 | 30 | 30 |
| recovery | 40 | 40 | 40 | 40 | 40 |
| sequential | 65 | 59 | 65 | 63 | 65 |
| single_tool | 30 | 26 | 30 | 26 | 30 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 1/5 | 5 | 1 | 5 | {'success': 1, 'missing_required_call': 4} |
| T02 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T03 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T04 | 2/5 | 5 | 5 | 5 | {'success': 2, 'wrong_answer': 3} |
| T05 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T06 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T07 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T08 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T09 | 2/5 | 2 | 5 | 5 | {'format_only': 3, 'success': 2} |
| T10 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T11 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T12 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T13 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T14 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T15 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T16 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T17 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T18 | 0/5 | 0 | 5 | 5 | {'step_limit': 5} |
| T19 | 4/5 | 5 | 5 | 4 | {'unsafe_action': 1, 'success': 4} |
| T20 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T21 | 0/5 | 5 | 0 | 0 | {'unsafe_action': 5} |
| T22 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T23 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T24 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T25 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T26 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T27 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T28 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T29 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T30 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T31 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T32 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T33 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T34 | 2/5 | 5 | 5 | 5 | {'success': 2, 'wrong_answer': 3} |
| T35 | 3/5 | 5 | 5 | 5 | {'success': 3, 'wrong_answer': 2} |
| T36 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T37 | 0/5 | 5 | 5 | 0 | {'unsafe_action': 5} |
| T38 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T39 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T40 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T41 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T42 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T43 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T44 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T45 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T46 | 1/5 | 5 | 5 | 1 | {'success': 1, 'unsafe_action': 4} |
| T47 | 1/5 | 3 | 1 | 2 | {'missing_booking': 3, 'missing_required_call': 1, 'success': 1} |
| T48 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T49 | 4/5 | 5 | 4 | 5 | {'success': 4, 'tool_argument_error': 1} |
| T50 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T51 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T52 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T53 | 4/5 | 5 | 5 | 5 | {'wrong_answer': 1, 'success': 4} |
| T54 | 2/5 | 5 | 2 | 2 | {'success': 2, 'missing_booking': 3} |
| T55 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T56 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T57 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T58 | 3/5 | 5 | 5 | 5 | {'success': 3, 'wrong_answer': 2} |
| T59 | 2/5 | 5 | 2 | 5 | {'success': 2, 'missing_required_call': 3} |
| T60 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T61 | 0/5 | 5 | 5 | 0 | {'unsafe_action': 5} |
| T62 | 4/5 | 5 | 4 | 5 | {'success': 4, 'tool_argument_error': 1} |
| T63 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T64 | 4/5 | 5 | 5 | 5 | {'wrong_answer': 1, 'success': 4} |
| T65 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T66 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T67 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T68 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T69 | 3/5 | 3 | 5 | 5 | {'success': 3, 'step_limit': 2} |
| T70 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T71 | 3/5 | 5 | 5 | 5 | {'wrong_answer': 2, 'success': 3} |
| T72 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T73 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T74 | 2/5 | 5 | 5 | 3 | {'unsafe_action': 2, 'success': 2, 'wrong_answer': 1} |
| T75 | 5/5 | 5 | 5 | 5 | {'success': 5} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 286, 'step_limit': 7, 'unsafe_action': 22, 'missing_booking': 6, 'tool_argument_error': 2, 'missing_required_call': 18, 'wrong_answer': 31, 'format_only': 3}
- secondary tags: {'reply_language_mismatch': 217, 'unexpected_booking': 22, 'no_final_block': 12, 'empty_final_text': 7, 'unresolvable_station_name': 6, 'missing_expected_booking': 6, 'invalid_train_id_format': 5}
- format_only (tool process and booking state correct, only the final-answer block failed): 3 items

## Cost

- tokens: input 2827732, output 112072, cached input 2591964
- items retried: 0; wall time 1195.8 s (sum of item times 1194.9 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '001e5dafc3c77684c2307ebc6ab8e336e10c9b18eca52acf547d72fc83c3ca8c', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
