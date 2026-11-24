# Run summary: local_llama31_8b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_llama31_8b_full_20261124T105853Z.jsonl` (375 rows, sha256 c35f5fb4a0a6...)
- expected items 375, selected 375, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **42/375 (11.2%)** (not scored: 0)
- status: {'completed': 355, 'output_truncated': 20}
- final-answer parse ok: 200/375 (53.3%); process ok: 101/375 (26.9%); state ok: 252/375 (67.2%)
- tool calls ok: 145/476 (30.5%); top error codes: {'INVALID_TRAIN': 144, 'INVALID_STATION': 95, 'STATION_NOT_FOUND': 50, 'SOLD_OUT': 12, 'INVALID_ARGUMENTS': 9, 'CLASS_NOT_OFFERED': 6, 'INVALID_PASSENGER': 6, 'DUPLICATE_BOOKING': 5, 'INVALID_CLASS': 4}
- failure label families: {'process:missing_required_call': 984, 'final_answer:missing_block': 153, 'state:bookings_mismatch': 123, 'status:expected_success_got_cannot_complete': 39, 'process:prohibited_action': 27, 'final_answer:missing_keys': 22, 'status:expected_success_got_needs_clarification': 21, 'run:output_truncated': 20, 'status:expected_cannot_complete_got_success': 17, 'final_answer:booking_ids_do_not_match_state': 16, 'final_answer:wrong_selected_class': 12, 'status:expected_needs_clarification_got_success': 11, 'status:expected_needs_clarification_got_cannot_complete': 8, 'status:expected_cannot_complete_got_needs_clarification': 7, 'final_answer:wrong_selected_train': 7, 'final_answer:booking_ids_invalid': 5, 'final_answer:selected_train_invalid': 4, 'value:resolved_date=2026-10-10_not_stated': 3, 'value:fare_inr=1460_not_stated': 2, 'value:segment_distance_km=838_not_stated': 2, 'answer_value:wrong': 2, 'value:seats_available=35_not_stated': 2, 'value:fare_inr=3565_not_stated': 1, 'value:departure=17': 1, 'final_answer:wrong_selected_trains': 1, 'final_answer:wrong_requested_passengers': 1, 'value:arrival=10': 1, 'answer_value:missing': 1, 'value:fare_inr=305_not_stated': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **42/375 (11.2%)**; strict: 42/375 (11.2%)
- items that needed a format recovery: 65; by rule {'extra_args_dropped': 63, 'closing_braces_appended': 18, 'text_tool_call': 18}; by language {'en': 26, 'hi': 9, 'gu': 9, 'hinglish': 16, 'mr': 5}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 29/320 (9.1%); no-tool tasks: 13/55 (23.6%)
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 5/75 (6.7%) | 21 | 22 | 48 | {'success': 5, 'tool_argument_error': 23, 'missing_booking': 21, 'missing_required_call': 4, 'format_only': 13, 'unsafe_action': 5, 'wrong_answer': 3, 'output_truncated': 1} |
| gu | 9/75 (12.0%) | 49 | 19 | 50 | {'success': 9, 'output_truncated': 13, 'tool_argument_error': 14, 'missing_booking': 17, 'unsafe_action': 6, 'missing_required_call': 9, 'format_only': 1, 'wrong_answer': 6} |
| hi | 8/75 (10.7%) | 36 | 20 | 52 | {'success': 8, 'tool_argument_error': 20, 'missing_booking': 17, 'unsafe_action': 6, 'missing_required_call': 11, 'format_only': 7, 'wrong_answer': 4, 'output_truncated': 2} |
| hinglish | 6/75 (8.0%) | 36 | 19 | 50 | {'success': 6, 'tool_argument_error': 19, 'missing_booking': 21, 'unsafe_action': 4, 'format_only': 8, 'missing_required_call': 11, 'wrong_answer': 4, 'output_truncated': 2} |
| mr | 14/75 (18.7%) | 58 | 21 | 52 | {'missing_required_call': 10, 'tool_argument_error': 19, 'output_truncated': 2, 'missing_booking': 17, 'success': 14, 'wrong_answer': 6, 'unsafe_action': 7} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 75 | 8 | 44 | 9 | 15 |
| clarification | 45 | 6 | 25 | 40 | 38 |
| constraint | 90 | 3 | 42 | 4 | 59 |
| invalid_input | 30 | 9 | 18 | 23 | 30 |
| recovery | 40 | 2 | 30 | 2 | 21 |
| sequential | 65 | 0 | 19 | 0 | 60 |
| single_tool | 30 | 14 | 22 | 23 | 29 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T02 | 0/5 | 2 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T03 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T04 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T05 | 2/5 | 5 | 2 | 5 | {'success': 2, 'unsafe_action': 3} |
| T06 | 3/5 | 3 | 4 | 5 | {'success': 3, 'format_only': 1, 'output_truncated': 1} |
| T07 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T08 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T09 | 2/5 | 2 | 5 | 5 | {'success': 2, 'format_only': 3} |
| T10 | 0/5 | 4 | 0 | 0 | {'missing_booking': 5} |
| T11 | 0/5 | 3 | 4 | 5 | {'format_only': 1, 'wrong_answer': 3, 'missing_required_call': 1} |
| T12 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 3, 'output_truncated': 1, 'missing_required_call': 1} |
| T13 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T14 | 0/5 | 3 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T15 | 0/5 | 4 | 0 | 3 | {'unsafe_action': 2, 'missing_required_call': 3} |
| T16 | 1/5 | 4 | 2 | 5 | {'format_only': 1, 'success': 1, 'tool_argument_error': 3} |
| T17 | 0/5 | 3 | 4 | 5 | {'format_only': 2, 'missing_required_call': 1, 'wrong_answer': 2} |
| T18 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T19 | 3/5 | 4 | 5 | 4 | {'unsafe_action': 1, 'success': 3, 'format_only': 1} |
| T20 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 3, 'missing_required_call': 2} |
| T21 | 0/5 | 3 | 0 | 2 | {'unsafe_action': 3, 'missing_required_call': 2} |
| T22 | 0/5 | 4 | 0 | 0 | {'missing_booking': 5} |
| T23 | 0/5 | 3 | 0 | 0 | {'missing_booking': 5} |
| T24 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 3, 'missing_required_call': 1, 'output_truncated': 1} |
| T25 | 0/5 | 2 | 0 | 5 | {'tool_argument_error': 4, 'missing_required_call': 1} |
| T26 | 3/5 | 3 | 4 | 5 | {'format_only': 1, 'missing_required_call': 1, 'success': 3} |
| T27 | 3/5 | 4 | 3 | 3 | {'missing_booking': 2, 'success': 3} |
| T28 | 2/5 | 3 | 4 | 5 | {'format_only': 2, 'missing_required_call': 1, 'success': 2} |
| T29 | 1/5 | 3 | 5 | 5 | {'format_only': 1, 'wrong_answer': 2, 'success': 1, 'output_truncated': 1} |
| T30 | 3/5 | 5 | 5 | 5 | {'wrong_answer': 2, 'success': 3} |
| T31 | 0/5 | 2 | 0 | 5 | {'tool_argument_error': 5} |
| T32 | 0/5 | 5 | 0 | 0 | {'unsafe_action': 4, 'missing_booking': 1} |
| T33 | 0/5 | 3 | 0 | 0 | {'missing_booking': 5} |
| T34 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T35 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T36 | 0/5 | 3 | 5 | 5 | {'format_only': 2, 'wrong_answer': 3} |
| T37 | 1/5 | 1 | 5 | 5 | {'format_only': 3, 'success': 1, 'output_truncated': 1} |
| T38 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T39 | 0/5 | 4 | 0 | 2 | {'tool_argument_error': 1, 'missing_required_call': 1, 'unsafe_action': 3} |
| T40 | 0/5 | 2 | 0 | 5 | {'tool_argument_error': 3, 'missing_required_call': 2} |
| T41 | 0/5 | 4 | 0 | 3 | {'unsafe_action': 3, 'missing_required_call': 2} |
| T42 | 1/5 | 3 | 1 | 1 | {'missing_booking': 4, 'success': 1} |
| T43 | 0/5 | 1 | 0 | 0 | {'missing_booking': 3, 'output_truncated': 2} |
| T44 | 0/5 | 2 | 0 | 5 | {'missing_required_call': 2, 'tool_argument_error': 3} |
| T45 | 3/5 | 3 | 5 | 5 | {'format_only': 2, 'success': 3} |
| T46 | 0/5 | 3 | 5 | 2 | {'format_only': 2, 'unsafe_action': 3} |
| T47 | 0/5 | 3 | 0 | 2 | {'missing_booking': 3, 'missing_required_call': 2} |
| T48 | 1/5 | 4 | 1 | 1 | {'missing_booking': 3, 'output_truncated': 1, 'success': 1} |
| T49 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T50 | 0/5 | 2 | 0 | 1 | {'missing_booking': 4, 'missing_required_call': 1} |
| T51 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T52 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T53 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T54 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T55 | 0/5 | 3 | 0 | 5 | {'tool_argument_error': 2, 'missing_required_call': 3} |
| T56 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T57 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T58 | 1/5 | 3 | 2 | 2 | {'missing_booking': 2, 'success': 1, 'wrong_answer': 1, 'output_truncated': 1} |
| T59 | 2/5 | 5 | 2 | 2 | {'success': 2, 'unsafe_action': 3} |
| T60 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T61 | 0/5 | 4 | 0 | 5 | {'tool_argument_error': 5} |
| T62 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T63 | 0/5 | 2 | 0 | 5 | {'missing_required_call': 5} |
| T64 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T65 | 0/5 | 3 | 0 | 0 | {'missing_booking': 5} |
| T66 | 0/5 | 4 | 0 | 3 | {'missing_booking': 2, 'tool_argument_error': 2, 'missing_required_call': 1} |
| T67 | 0/5 | 3 | 5 | 5 | {'format_only': 2, 'wrong_answer': 3} |
| T68 | 3/5 | 4 | 5 | 4 | {'format_only': 1, 'unsafe_action': 1, 'success': 3} |
| T69 | 0/5 | 3 | 5 | 5 | {'wrong_answer': 3, 'format_only': 2} |
| T70 | 1/5 | 5 | 2 | 4 | {'wrong_answer': 1, 'success': 1, 'unsafe_action': 1, 'missing_required_call': 2} |
| T71 | 2/5 | 2 | 2 | 2 | {'missing_booking': 3, 'success': 2} |
| T72 | 0/5 | 2 | 0 | 0 | {'missing_booking': 4, 'unsafe_action': 1} |
| T73 | 0/5 | 4 | 0 | 0 | {'missing_booking': 5} |
| T74 | 0/5 | 3 | 5 | 5 | {'format_only': 2, 'wrong_answer': 3} |
| T75 | 0/5 | 5 | 0 | 1 | {'tool_argument_error': 1, 'missing_booking': 4} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 42, 'output_truncated': 20, 'unsafe_action': 28, 'missing_booking': 93, 'tool_argument_error': 95, 'missing_required_call': 45, 'wrong_answer': 23, 'format_only': 29}
- secondary tags: {'no_final_block': 153, 'reply_language_mismatch': 152, 'missing_expected_booking': 104, 'guessed_station_code': 94, 'tool_call_as_text': 50, 'invalid_train_id_format': 46, 'unresolvable_station_name': 30, 'unexpected_booking': 24, 'empty_final_text': 20}
- format_only (tool process and booking state correct, only the final-answer block failed): 29 items

## Cost

- tokens: input 919433, output 89023, cached input 658523
- items retried: 0; wall time 1607.1 s (sum of item times 1606.6 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
