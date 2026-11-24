# Run summary: local_gpt_oss_20b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_gpt_oss_20b_full_20261124T105853Z.jsonl` (375 rows, sha256 85df651e14ed...)
- expected items 375, selected 375, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **213/375 (56.8%)** (not scored: 0)
- status: {'completed': 348, 'step_limit_exceeded': 27}
- final-answer parse ok: 323/375 (86.1%); process ok: 293/375 (78.1%); state ok: 323/375 (86.1%)
- tool calls ok: 1450/1527 (95.0%); top error codes: {'STATION_NOT_FOUND': 36, 'INVALID_ARGUMENTS': 11, 'INVALID_TRAIN': 7, 'INVALID_PASSENGER': 6, 'DUPLICATE_BOOKING': 5, 'CLASS_NOT_OFFERED': 4, 'INVALID_STATION': 4, 'PAST_DATE': 3, 'INVALID_CLASS': 1}
- failure label families: {'process:missing_required_call': 146, 'state:bookings_mismatch': 52, 'final_answer:missing_block': 52, 'run:step_limit_exceeded': 27, 'status:expected_success_got_needs_clarification': 16, 'status:expected_needs_clarification_got_success': 15, 'status:expected_cannot_complete_got_success': 12, 'status:expected_cannot_complete_got_needs_clarification': 9, 'final_answer:wrong_selected_train': 8, 'status:expected_success_got_cannot_complete': 8, 'final_answer:booking_ids_do_not_match_state': 5, 'final_answer:selected_train_invalid': 5, 'process:dependency_violation': 5, 'status:expected_needs_clarification_got_cannot_complete': 4, 'process:prohibited_action': 3, 'value:fare_inr=2495_not_stated': 3, 'final_answer:booking_ids_invalid': 2, 'value:resolved_date=2026-10-10_not_stated': 2, 'value:fare_inr=1035_not_stated': 1, 'value:fare_inr=450_not_stated': 1, 'value:departure=17': 1, 'value:departure=20': 1, 'value:arrival=04': 1, 'value:segment_distance_km=838_not_stated': 1, 'final_answer:wrong_selected_class': 1, 'value:departure=23': 1, 'value:arrival=06': 1, 'value:fare_difference_inr=650_not_stated': 1, 'value:resolved_date=2026-10-07_not_stated': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **213/375 (56.8%)**; strict: 213/375 (56.8%)
- items that needed a format recovery: 0; by rule {}; by language {}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 189/320 (59.1%); no-tool tasks: 24/55 (43.6%)
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 42/75 (56.0%) | 59 | 60 | 67 | {'success': 42, 'wrong_answer': 8, 'format_only': 9, 'step_limit': 6, 'missing_required_call': 5, 'missing_booking': 2, 'unsafe_action': 2, 'tool_argument_error': 1} |
| gu | 47/75 (62.7%) | 69 | 58 | 66 | {'success': 47, 'wrong_answer': 8, 'unsafe_action': 4, 'step_limit': 3, 'missing_required_call': 8, 'missing_booking': 3, 'format_only': 1, 'tool_argument_error': 1} |
| hi | 43/75 (57.3%) | 64 | 58 | 61 | {'success': 43, 'step_limit': 6, 'unsafe_action': 7, 'wrong_answer': 6, 'missing_required_call': 6, 'format_only': 4, 'missing_booking': 3} |
| hinglish | 41/75 (54.7%) | 64 | 58 | 64 | {'success': 41, 'missing_required_call': 7, 'unsafe_action': 5, 'wrong_answer': 9, 'step_limit': 8, 'format_only': 3, 'tool_argument_error': 1, 'missing_booking': 1} |
| mr | 40/75 (53.3%) | 67 | 59 | 65 | {'success': 40, 'missing_required_call': 8, 'wrong_answer': 13, 'tool_argument_error': 1, 'format_only': 3, 'step_limit': 4, 'missing_booking': 3, 'unsafe_action': 3} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 75 | 40 | 65 | 46 | 58 |
| clarification | 45 | 17 | 38 | 42 | 29 |
| constraint | 90 | 53 | 80 | 64 | 76 |
| invalid_input | 30 | 7 | 18 | 30 | 30 |
| recovery | 40 | 32 | 36 | 36 | 36 |
| sequential | 65 | 39 | 59 | 49 | 64 |
| single_tool | 30 | 25 | 27 | 26 | 30 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T02 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T03 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T04 | 3/5 | 4 | 4 | 4 | {'wrong_answer': 1, 'success': 3, 'step_limit': 1} |
| T05 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T06 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T07 | 3/5 | 5 | 3 | 5 | {'success': 3, 'missing_required_call': 2} |
| T08 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T09 | 2/5 | 5 | 5 | 2 | {'success': 2, 'unsafe_action': 3} |
| T10 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T11 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T12 | 2/5 | 5 | 5 | 5 | {'wrong_answer': 3, 'success': 2} |
| T13 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T14 | 2/5 | 2 | 2 | 5 | {'success': 2, 'step_limit': 3} |
| T15 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T16 | 4/5 | 4 | 4 | 5 | {'success': 4, 'tool_argument_error': 1} |
| T17 | 1/5 | 3 | 2 | 5 | {'success': 1, 'missing_required_call': 3, 'wrong_answer': 1} |
| T18 | 0/5 | 1 | 5 | 5 | {'format_only': 4, 'wrong_answer': 1} |
| T19 | 3/5 | 4 | 5 | 4 | {'format_only': 1, 'success': 3, 'unsafe_action': 1} |
| T20 | 2/5 | 4 | 5 | 5 | {'wrong_answer': 2, 'success': 2, 'format_only': 1} |
| T21 | 0/5 | 5 | 2 | 3 | {'wrong_answer': 2, 'unsafe_action': 2, 'missing_required_call': 1} |
| T22 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T23 | 0/5 | 1 | 0 | 0 | {'step_limit': 4, 'missing_booking': 1} |
| T24 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T25 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 4, 'tool_argument_error': 1} |
| T26 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T27 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T28 | 0/5 | 3 | 5 | 5 | {'format_only': 2, 'wrong_answer': 3} |
| T29 | 2/5 | 3 | 5 | 5 | {'format_only': 2, 'wrong_answer': 1, 'success': 2} |
| T30 | 1/5 | 2 | 5 | 5 | {'format_only': 3, 'wrong_answer': 1, 'success': 1} |
| T31 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T32 | 4/5 | 4 | 4 | 4 | {'step_limit': 1, 'success': 4} |
| T33 | 0/5 | 1 | 0 | 0 | {'step_limit': 4, 'unsafe_action': 1} |
| T34 | 1/5 | 4 | 5 | 5 | {'success': 1, 'step_limit': 1, 'wrong_answer': 3} |
| T35 | 0/5 | 4 | 0 | 1 | {'missing_booking': 4, 'missing_required_call': 1} |
| T36 | 2/5 | 3 | 5 | 4 | {'format_only': 2, 'success': 2, 'unsafe_action': 1} |
| T37 | 1/5 | 5 | 5 | 1 | {'unsafe_action': 4, 'success': 1} |
| T38 | 1/5 | 2 | 1 | 1 | {'unsafe_action': 1, 'step_limit': 3, 'success': 1} |
| T39 | 2/5 | 5 | 2 | 2 | {'success': 2, 'unsafe_action': 3} |
| T40 | 0/5 | 4 | 4 | 5 | {'wrong_answer': 4, 'tool_argument_error': 1} |
| T41 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T42 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T43 | 0/5 | 5 | 0 | 4 | {'tool_argument_error': 1, 'missing_booking': 1, 'missing_required_call': 3} |
| T44 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T45 | 4/5 | 4 | 5 | 5 | {'format_only': 1, 'success': 4} |
| T46 | 2/5 | 5 | 5 | 2 | {'success': 2, 'unsafe_action': 3} |
| T47 | 1/5 | 5 | 1 | 2 | {'missing_booking': 3, 'success': 1, 'missing_required_call': 1} |
| T48 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T49 | 0/5 | 4 | 0 | 4 | {'missing_required_call': 4, 'step_limit': 1} |
| T50 | 0/5 | 3 | 0 | 5 | {'step_limit': 2, 'missing_required_call': 3} |
| T51 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T52 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T53 | 1/5 | 5 | 1 | 5 | {'missing_required_call': 4, 'success': 1} |
| T54 | 2/5 | 5 | 2 | 2 | {'success': 2, 'missing_booking': 3} |
| T55 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T56 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T57 | 3/5 | 5 | 4 | 5 | {'success': 3, 'missing_required_call': 1, 'wrong_answer': 1} |
| T58 | 4/5 | 4 | 4 | 5 | {'step_limit': 1, 'success': 4} |
| T59 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T60 | 4/5 | 4 | 5 | 5 | {'success': 4, 'step_limit': 1} |
| T61 | 4/5 | 5 | 5 | 5 | {'wrong_answer': 1, 'success': 4} |
| T62 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T63 | 2/5 | 5 | 2 | 5 | {'missing_required_call': 3, 'success': 2} |
| T64 | 2/5 | 5 | 5 | 5 | {'success': 2, 'wrong_answer': 3} |
| T65 | 0/5 | 0 | 0 | 0 | {'step_limit': 5} |
| T66 | 1/5 | 5 | 1 | 5 | {'missing_required_call': 4, 'success': 1} |
| T67 | 2/5 | 2 | 5 | 5 | {'format_only': 3, 'success': 2} |
| T68 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T69 | 4/5 | 4 | 5 | 5 | {'format_only': 1, 'success': 4} |
| T70 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T71 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T72 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T73 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T74 | 1/5 | 5 | 5 | 3 | {'success': 1, 'wrong_answer': 2, 'unsafe_action': 2} |
| T75 | 5/5 | 5 | 5 | 5 | {'success': 5} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 213, 'step_limit': 27, 'unsafe_action': 21, 'missing_booking': 12, 'tool_argument_error': 4, 'missing_required_call': 34, 'wrong_answer': 44, 'format_only': 20}
- secondary tags: {'reply_language_mismatch': 231, 'no_final_block': 52, 'missing_expected_booking': 33, 'empty_final_text': 27, 'unexpected_booking': 21, 'unresolvable_station_name': 8, 'guessed_station_code': 4, 'invalid_train_id_format': 2, 'ungrounded_train_id': 2}
- format_only (tool process and booking state correct, only the final-answer block failed): 20 items

## Cost

- tokens: input 3233458, output 123197, cached input 3063416
- items retried: 0; wall time 1542.0 s (sum of item times 1541.2 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': 'f38aa0c53da5f8c49d08c43a99df24ff53167fe68e24664a7777288e7656fdfe', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
