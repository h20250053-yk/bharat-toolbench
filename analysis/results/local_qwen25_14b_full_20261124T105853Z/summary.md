# Run summary: local_qwen25_14b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_qwen25_14b_full_20261124T105853Z.jsonl` (375 rows, sha256 7b23504feeca...)
- expected items 375, selected 375, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **101/375 (26.9%)** (not scored: 0)
- status: {'completed': 364, 'output_truncated': 8, 'step_limit_exceeded': 3}
- final-answer parse ok: 316/375 (84.3%); process ok: 186/375 (49.6%); state ok: 275/375 (73.3%)
- tool calls ok: 1150/2259 (50.9%); top error codes: {'INVALID_TRAIN': 773, 'INVALID_STATION': 160, 'DUPLICATE_BOOKING': 56, 'STATION_NOT_FOUND': 36, 'SOLD_OUT': 30, 'CLASS_NOT_OFFERED': 23, 'INVALID_ARGUMENTS': 9, 'SAME_STATION': 6, 'INVALID_CLASS': 6, 'INVALID_PASSENGER': 4}
- failure label families: {'process:missing_required_call': 508, 'state:bookings_mismatch': 100, 'final_answer:missing_block': 45, 'final_answer:wrong_selected_train': 33, 'status:expected_needs_clarification_got_success': 26, 'status:expected_success_got_cannot_complete': 25, 'status:expected_success_got_needs_clarification': 25, 'status:expected_cannot_complete_got_success': 25, 'final_answer:booking_ids_do_not_match_state': 19, 'final_answer:booking_ids_invalid': 19, 'process:prohibited_action': 18, 'final_answer:missing_keys': 14, 'final_answer:wrong_selected_class': 13, 'final_answer:selected_train_invalid': 9, 'status:expected_cannot_complete_got_needs_clarification': 9, 'answer_value:wrong': 8, 'run:output_truncated': 8, 'status:expected_needs_clarification_got_cannot_complete': 7, 'value:resolved_date=2026-10-10_not_stated': 4, 'value:fare_inr=305_not_stated': 4, 'value:fare_inr=1035_not_stated': 3, 'run:step_limit_exceeded': 3, 'final_answer:wrong_selected_trains': 3, "value:departure_times=['18": 3, 'answer_value:missing': 3, 'value:fare_inr=2495_not_stated': 3, 'value:fare_inr=450_not_stated': 2, 'value:departure=17': 2, 'process:dependency_violation': 2, 'value:fare_inr=3565_not_stated': 1, 'value:fare_inr=1540_not_stated': 1, 'value:departure=20': 1, 'value:arrival=04': 1, 'value:segment_distance_km=838_not_stated': 1, 'final_answer:wrong_requested_passengers': 1, 'value:arrival=06': 1, 'value:fare_difference_inr=650_not_stated': 1, "value:selected_train_ids=['BTB127', 'BTB116', 'BTB124']_not_stated": 1, 'value:resolved_date=2026-10-07_not_stated': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **101/375 (26.9%)**; strict: 97/375 (25.9%)
- items that needed a format recovery: 12; by rule {'extra_args_dropped': 12}; by language {'en': 4, 'gu': 4, 'hinglish': 1, 'hi': 2, 'mr': 1}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 86/320 (26.9%); no-tool tasks: 15/55 (27.3%)
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 25/75 (33.3%) | 67 | 47 | 58 | {'missing_required_call': 8, 'success': 25, 'unsafe_action': 17, 'wrong_answer': 10, 'format_only': 3, 'step_limit': 2, 'tool_argument_error': 9, 'missing_booking': 1} |
| gu | 15/75 (20.0%) | 58 | 29 | 52 | {'success': 15, 'tool_argument_error': 9, 'missing_booking': 14, 'format_only': 3, 'wrong_answer': 8, 'missing_required_call': 15, 'output_truncated': 2, 'unsafe_action': 9} |
| hi | 22/75 (29.3%) | 65 | 37 | 55 | {'success': 22, 'tool_argument_error': 10, 'unsafe_action': 8, 'output_truncated': 3, 'wrong_answer': 10, 'missing_required_call': 8, 'missing_booking': 12, 'format_only': 2} |
| hinglish | 24/75 (32.0%) | 63 | 40 | 58 | {'success': 24, 'tool_argument_error': 13, 'missing_required_call': 10, 'wrong_answer': 8, 'format_only': 2, 'missing_booking': 7, 'unsafe_action': 10, 'step_limit': 1} |
| mr | 15/75 (20.0%) | 63 | 33 | 52 | {'success': 15, 'tool_argument_error': 10, 'missing_required_call': 14, 'unsafe_action': 12, 'format_only': 3, 'wrong_answer': 8, 'missing_booking': 10, 'output_truncated': 3} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 75 | 25 | 69 | 35 | 41 |
| clarification | 45 | 7 | 40 | 41 | 26 |
| constraint | 90 | 12 | 76 | 24 | 58 |
| invalid_input | 30 | 12 | 26 | 28 | 30 |
| recovery | 40 | 15 | 37 | 16 | 28 |
| sequential | 65 | 14 | 46 | 22 | 62 |
| single_tool | 30 | 16 | 22 | 20 | 30 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 4/5 | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 4} |
| T02 | 2/5 | 4 | 2 | 5 | {'success': 2, 'tool_argument_error': 3} |
| T03 | 1/5 | 5 | 1 | 5 | {'success': 1, 'tool_argument_error': 3, 'missing_required_call': 1} |
| T04 | 2/5 | 4 | 2 | 2 | {'unsafe_action': 2, 'success': 2, 'missing_booking': 1} |
| T05 | 2/5 | 5 | 2 | 5 | {'unsafe_action': 2, 'success': 2, 'missing_required_call': 1} |
| T06 | 2/5 | 2 | 4 | 5 | {'missing_required_call': 1, 'success': 2, 'format_only': 2} |
| T07 | 0/5 | 1 | 0 | 5 | {'missing_required_call': 3, 'tool_argument_error': 2} |
| T08 | 0/5 | 3 | 1 | 5 | {'missing_required_call': 3, 'output_truncated': 1, 'wrong_answer': 1} |
| T09 | 3/5 | 4 | 5 | 4 | {'unsafe_action': 1, 'success': 3, 'format_only': 1} |
| T10 | 4/5 | 5 | 4 | 4 | {'success': 4, 'missing_booking': 1} |
| T11 | 0/5 | 4 | 4 | 5 | {'wrong_answer': 4, 'missing_required_call': 1} |
| T12 | 0/5 | 4 | 3 | 5 | {'wrong_answer': 2, 'format_only': 1, 'missing_required_call': 1, 'tool_argument_error': 1} |
| T13 | 1/5 | 4 | 1 | 1 | {'success': 1, 'missing_booking': 4} |
| T14 | 2/5 | 3 | 3 | 5 | {'success': 2, 'missing_required_call': 1, 'wrong_answer': 1, 'output_truncated': 1} |
| T15 | 4/5 | 5 | 4 | 4 | {'unsafe_action': 1, 'success': 4} |
| T16 | 2/5 | 5 | 2 | 5 | {'missing_required_call': 3, 'success': 2} |
| T17 | 1/5 | 2 | 3 | 5 | {'format_only': 2, 'success': 1, 'missing_required_call': 2} |
| T18 | 0/5 | 3 | 5 | 5 | {'step_limit': 1, 'wrong_answer': 3, 'format_only': 1} |
| T19 | 1/5 | 5 | 5 | 1 | {'unsafe_action': 4, 'success': 1} |
| T20 | 4/5 | 5 | 4 | 5 | {'success': 4, 'tool_argument_error': 1} |
| T21 | 0/5 | 5 | 1 | 1 | {'unsafe_action': 4, 'missing_required_call': 1} |
| T22 | 1/5 | 4 | 1 | 1 | {'success': 1, 'missing_booking': 4} |
| T23 | 0/5 | 5 | 0 | 2 | {'tool_argument_error': 2, 'missing_booking': 3} |
| T24 | 0/5 | 5 | 1 | 5 | {'wrong_answer': 1, 'missing_required_call': 1, 'tool_argument_error': 3} |
| T25 | 0/5 | 3 | 0 | 5 | {'tool_argument_error': 2, 'missing_required_call': 3} |
| T26 | 4/5 | 4 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T27 | 3/5 | 5 | 3 | 3 | {'success': 3, 'missing_booking': 2} |
| T28 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T29 | 3/5 | 5 | 5 | 5 | {'success': 3, 'wrong_answer': 2} |
| T30 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T31 | 1/5 | 5 | 1 | 5 | {'tool_argument_error': 3, 'success': 1, 'missing_required_call': 1} |
| T32 | 1/5 | 5 | 3 | 1 | {'success': 1, 'unsafe_action': 3, 'missing_booking': 1} |
| T33 | 1/5 | 5 | 1 | 1 | {'success': 1, 'unsafe_action': 4} |
| T34 | 0/5 | 4 | 2 | 5 | {'wrong_answer': 2, 'tool_argument_error': 2, 'missing_required_call': 1} |
| T35 | 0/5 | 4 | 0 | 1 | {'tool_argument_error': 1, 'missing_booking': 3, 'output_truncated': 1} |
| T36 | 0/5 | 5 | 5 | 4 | {'unsafe_action': 1, 'wrong_answer': 4} |
| T37 | 0/5 | 5 | 5 | 1 | {'unsafe_action': 4, 'wrong_answer': 1} |
| T38 | 0/5 | 4 | 0 | 0 | {'unsafe_action': 3, 'missing_booking': 2} |
| T39 | 0/5 | 5 | 0 | 2 | {'unsafe_action': 3, 'missing_required_call': 2} |
| T40 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T41 | 2/5 | 5 | 2 | 3 | {'unsafe_action': 2, 'success': 2, 'missing_required_call': 1} |
| T42 | 4/5 | 5 | 4 | 4 | {'success': 4, 'missing_booking': 1} |
| T43 | 0/5 | 3 | 0 | 0 | {'missing_booking': 5} |
| T44 | 0/5 | 2 | 2 | 5 | {'format_only': 2, 'tool_argument_error': 2, 'missing_required_call': 1} |
| T45 | 1/5 | 4 | 5 | 5 | {'wrong_answer': 3, 'success': 1, 'format_only': 1} |
| T46 | 1/5 | 5 | 5 | 1 | {'unsafe_action': 4, 'success': 1} |
| T47 | 0/5 | 5 | 0 | 3 | {'missing_required_call': 2, 'tool_argument_error': 1, 'missing_booking': 2} |
| T48 | 3/5 | 5 | 5 | 5 | {'wrong_answer': 2, 'success': 3} |
| T49 | 0/5 | 5 | 0 | 2 | {'tool_argument_error': 2, 'missing_booking': 3} |
| T50 | 4/5 | 5 | 4 | 4 | {'success': 4, 'missing_booking': 1} |
| T51 | 1/5 | 3 | 1 | 5 | {'tool_argument_error': 3, 'success': 1, 'missing_required_call': 1} |
| T52 | 0/5 | 2 | 1 | 5 | {'format_only': 1, 'missing_required_call': 2, 'tool_argument_error': 2} |
| T53 | 0/5 | 4 | 1 | 5 | {'wrong_answer': 1, 'tool_argument_error': 4} |
| T54 | 1/5 | 4 | 1 | 1 | {'success': 1, 'missing_booking': 4} |
| T55 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T56 | 1/5 | 5 | 3 | 5 | {'tool_argument_error': 2, 'wrong_answer': 2, 'success': 1} |
| T57 | 1/5 | 3 | 1 | 5 | {'success': 1, 'tool_argument_error': 3, 'missing_required_call': 1} |
| T58 | 0/5 | 5 | 3 | 5 | {'wrong_answer': 3, 'missing_required_call': 2} |
| T59 | 1/5 | 5 | 1 | 5 | {'missing_required_call': 4, 'success': 1} |
| T60 | 1/5 | 3 | 1 | 5 | {'success': 1, 'tool_argument_error': 2, 'missing_required_call': 1, 'output_truncated': 1} |
| T61 | 0/5 | 4 | 3 | 1 | {'unsafe_action': 4, 'missing_required_call': 1} |
| T62 | 2/5 | 3 | 2 | 5 | {'success': 2, 'output_truncated': 1, 'tool_argument_error': 1, 'missing_required_call': 1} |
| T63 | 0/5 | 4 | 0 | 5 | {'tool_argument_error': 3, 'missing_required_call': 2} |
| T64 | 0/5 | 4 | 0 | 5 | {'tool_argument_error': 3, 'missing_required_call': 2} |
| T65 | 0/5 | 4 | 0 | 0 | {'unsafe_action': 4, 'missing_booking': 1} |
| T66 | 1/5 | 4 | 3 | 3 | {'success': 1, 'wrong_answer': 2, 'output_truncated': 1, 'missing_booking': 1} |
| T67 | 0/5 | 5 | 5 | 4 | {'wrong_answer': 4, 'unsafe_action': 1} |
| T68 | 3/5 | 4 | 3 | 5 | {'success': 3, 'missing_required_call': 1, 'output_truncated': 1} |
| T69 | 2/5 | 3 | 5 | 5 | {'step_limit': 2, 'success': 2, 'wrong_answer': 1} |
| T70 | 1/5 | 5 | 5 | 1 | {'unsafe_action': 4, 'success': 1} |
| T71 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T72 | 1/5 | 5 | 1 | 1 | {'unsafe_action': 3, 'success': 1, 'missing_booking': 1} |
| T73 | 0/5 | 5 | 0 | 0 | {'unsafe_action': 2, 'missing_booking': 3} |
| T74 | 0/5 | 3 | 5 | 5 | {'wrong_answer': 3, 'format_only': 2} |
| T75 | 4/5 | 5 | 4 | 4 | {'success': 4, 'missing_booking': 1} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 101, 'output_truncated': 8, 'step_limit': 3, 'unsafe_action': 56, 'missing_booking': 44, 'tool_argument_error': 51, 'missing_required_call': 55, 'wrong_answer': 44, 'format_only': 13}
- secondary tags: {'reply_language_mismatch': 216, 'guessed_station_code': 112, 'invalid_train_id_format': 74, 'missing_expected_booking': 63, 'unexpected_booking': 54, 'no_final_block': 45, 'tool_call_as_text': 20, 'unresolvable_station_name': 13, 'empty_final_text': 8, 'ungrounded_train_id': 5, 'parallel_dependent_calls': 5}
- format_only (tool process and booking state correct, only the final-answer block failed): 13 items

## Cost

- tokens: input 1942724, output 237760, cached input 1699537
- items retried: 0; wall time 5645.4 s (sum of item times 5644.7 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
