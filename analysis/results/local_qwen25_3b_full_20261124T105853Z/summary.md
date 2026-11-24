# Run summary: local_qwen25_3b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_qwen25_3b_full_20261124T105853Z.jsonl` (375 rows, sha256 2d1025be6379...)
- expected items 375, selected 375, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **13/375 (3.5%)** (not scored: 0)
- status: {'completed': 311, 'malformed_output': 44, 'output_truncated': 19, 'step_limit_exceeded': 1}
- final-answer parse ok: 67/375 (17.9%); process ok: 126/375 (33.6%); state ok: 247/375 (65.9%)
- tool calls ok: 1158/2290 (50.6%); top error codes: {'INVALID_TRAIN': 359, 'INVALID_STATION': 316, 'STATION_NOT_FOUND': 287, 'SOLD_OUT': 69, 'DUPLICATE_BOOKING': 52, 'CLASS_NOT_OFFERED': 22, 'INVALID_ARGUMENTS': 16, 'INVALID_PASSENGER': 4, 'INVALID_DATE': 3, 'PAST_DATE': 2}
- failure label families: {'process:missing_required_call': 791, 'final_answer:missing_block': 307, 'process:prohibited_action': 170, 'state:bookings_mismatch': 128, 'run:malformed_output': 44, 'run:output_truncated': 19, 'status:expected_needs_clarification_got_success': 12, 'final_answer:booking_ids_do_not_match_state': 10, 'status:expected_success_got_cannot_complete': 9, 'status:expected_cannot_complete_got_success': 8, 'answer_value:missing': 5, 'final_answer:booking_ids_invalid': 5, 'final_answer:wrong_selected_train': 3, 'final_answer:wrong_selected_class': 2, 'final_answer:wrong_requested_passengers': 2, 'process:dependency_violation': 2, 'value:fare_inr=1460_not_stated': 1, 'value:segment_distance_km=838_not_stated': 1, 'status:expected_success_got_needs_clarification': 1, 'final_answer:malformed_json': 1, 'answer_value:wrong': 1, 'final_answer:selected_train_invalid': 1, 'value:resolved_date=2026-10-10_not_stated': 1, 'run:step_limit_exceeded': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **13/375 (3.5%)**; strict: 13/375 (3.5%)
- items that needed a format recovery: 3; by rule {'requested_passengers_shape': 1, 'closing_tag_missing': 1, 'extra_args_dropped': 1}; by language {'en': 2, 'gu': 1}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 44, 'by_language': {'hinglish': 13, 'hi': 9, 'mr': 10, 'gu': 7, 'en': 5}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 12/320 (3.8%); no-tool tasks: 1/55 (1.8%)
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 4/75 (5.3%) | 21 | 33 | 49 | {'format_only': 17, 'unsafe_action': 12, 'tool_argument_error': 18, 'missing_booking': 13, 'output_truncated': 1, 'malformed_model_output': 5, 'success': 4, 'wrong_answer': 5} |
| gu | 1/75 (1.3%) | 9 | 21 | 49 | {'missing_required_call': 1, 'tool_argument_error': 18, 'output_truncated': 11, 'unsafe_action': 6, 'malformed_model_output': 7, 'format_only': 14, 'missing_booking': 15, 'wrong_answer': 2, 'success': 1} |
| hi | 2/75 (2.7%) | 12 | 28 | 51 | {'format_only': 19, 'tool_argument_error': 14, 'malformed_model_output': 9, 'missing_booking': 15, 'unsafe_action': 7, 'wrong_answer': 3, 'output_truncated': 4, 'missing_required_call': 1, 'success': 2, 'step_limit': 1} |
| hinglish | 3/75 (4.0%) | 10 | 22 | 50 | {'format_only': 15, 'tool_argument_error': 23, 'malformed_model_output': 13, 'missing_booking': 14, 'success': 3, 'unsafe_action': 7} |
| mr | 3/75 (4.0%) | 15 | 22 | 48 | {'missing_required_call': 1, 'tool_argument_error': 19, 'missing_booking': 16, 'unsafe_action': 10, 'malformed_model_output': 10, 'success': 3, 'format_only': 12, 'output_truncated': 3, 'wrong_answer': 1} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 75 | 8 | 23 | 18 | 22 |
| clarification | 45 | 1 | 13 | 44 | 31 |
| constraint | 90 | 0 | 13 | 7 | 52 |
| invalid_input | 30 | 0 | 0 | 24 | 30 |
| recovery | 40 | 2 | 8 | 7 | 25 |
| sequential | 65 | 2 | 6 | 8 | 57 |
| single_tool | 30 | 0 | 4 | 18 | 30 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'missing_required_call': 2} |
| T02 | 0/5 | 1 | 1 | 4 | {'unsafe_action': 1, 'tool_argument_error': 4} |
| T03 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 2, 'malformed_model_output': 2, 'output_truncated': 1} |
| T04 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'unsafe_action': 1} |
| T05 | 0/5 | 1 | 0 | 3 | {'unsafe_action': 3, 'tool_argument_error': 2} |
| T06 | 0/5 | 1 | 2 | 5 | {'format_only': 1, 'malformed_model_output': 2, 'wrong_answer': 1, 'tool_argument_error': 1} |
| T07 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T08 | 0/5 | 0 | 0 | 5 | {'output_truncated': 1, 'malformed_model_output': 4} |
| T09 | 1/5 | 1 | 5 | 5 | {'format_only': 4, 'success': 1} |
| T10 | 1/5 | 2 | 2 | 4 | {'format_only': 1, 'success': 1, 'output_truncated': 1, 'tool_argument_error': 1, 'missing_booking': 1} |
| T11 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'output_truncated': 1} |
| T12 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 1, 'malformed_model_output': 4} |
| T13 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 1, 'missing_booking': 4} |
| T14 | 1/5 | 2 | 2 | 5 | {'success': 1, 'tool_argument_error': 3, 'format_only': 1} |
| T15 | 0/5 | 1 | 0 | 0 | {'unsafe_action': 5} |
| T16 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T17 | 0/5 | 1 | 3 | 5 | {'wrong_answer': 1, 'format_only': 2, 'output_truncated': 2} |
| T18 | 0/5 | 0 | 2 | 5 | {'tool_argument_error': 3, 'format_only': 2} |
| T19 | 0/5 | 3 | 5 | 2 | {'unsafe_action': 3, 'format_only': 2} |
| T20 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'tool_argument_error': 3} |
| T21 | 0/5 | 2 | 4 | 3 | {'format_only': 2, 'unsafe_action': 2, 'tool_argument_error': 1} |
| T22 | 0/5 | 1 | 0 | 0 | {'missing_booking': 5} |
| T23 | 0/5 | 0 | 0 | 0 | {'missing_booking': 4, 'malformed_model_output': 1} |
| T24 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T25 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 5} |
| T26 | 0/5 | 1 | 4 | 5 | {'format_only': 3, 'wrong_answer': 1, 'output_truncated': 1} |
| T27 | 2/5 | 2 | 2 | 3 | {'success': 2, 'output_truncated': 1, 'missing_booking': 2} |
| T28 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'tool_argument_error': 2} |
| T29 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T30 | 0/5 | 0 | 5 | 5 | {'malformed_model_output': 1, 'format_only': 4} |
| T31 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T32 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T33 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T34 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T35 | 0/5 | 0 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T36 | 0/5 | 2 | 5 | 3 | {'unsafe_action': 2, 'format_only': 3} |
| T37 | 0/5 | 2 | 5 | 2 | {'format_only': 2, 'unsafe_action': 3} |
| T38 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'unsafe_action': 1} |
| T39 | 0/5 | 4 | 1 | 1 | {'unsafe_action': 4, 'format_only': 1} |
| T40 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 3, 'malformed_model_output': 2} |
| T41 | 0/5 | 2 | 1 | 2 | {'unsafe_action': 2, 'tool_argument_error': 1, 'format_only': 1, 'output_truncated': 1} |
| T42 | 1/5 | 3 | 3 | 3 | {'success': 1, 'format_only': 1, 'missing_booking': 2, 'wrong_answer': 1} |
| T43 | 0/5 | 0 | 0 | 0 | {'unsafe_action': 1, 'missing_booking': 3, 'output_truncated': 1} |
| T44 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 1, 'malformed_model_output': 2, 'missing_required_call': 1, 'output_truncated': 1} |
| T45 | 0/5 | 0 | 5 | 5 | {'malformed_model_output': 1, 'format_only': 3, 'output_truncated': 1} |
| T46 | 0/5 | 3 | 5 | 1 | {'unsafe_action': 3, 'format_only': 1, 'output_truncated': 1} |
| T47 | 4/5 | 4 | 5 | 5 | {'format_only': 1, 'success': 4} |
| T48 | 0/5 | 2 | 2 | 2 | {'wrong_answer': 1, 'malformed_model_output': 1, 'missing_booking': 2, 'format_only': 1} |
| T49 | 0/5 | 0 | 0 | 0 | {'missing_booking': 4, 'malformed_model_output': 1} |
| T50 | 0/5 | 2 | 0 | 1 | {'missing_booking': 4, 'tool_argument_error': 1} |
| T51 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T52 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 3, 'malformed_model_output': 2} |
| T53 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 3, 'malformed_model_output': 2} |
| T54 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T55 | 1/5 | 3 | 5 | 3 | {'wrong_answer': 1, 'unsafe_action': 2, 'success': 1, 'format_only': 1} |
| T56 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 4, 'tool_argument_error': 1} |
| T57 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T58 | 0/5 | 2 | 2 | 4 | {'format_only': 1, 'tool_argument_error': 2, 'output_truncated': 1, 'wrong_answer': 1} |
| T59 | 0/5 | 2 | 1 | 3 | {'wrong_answer': 1, 'tool_argument_error': 1, 'output_truncated': 1, 'unsafe_action': 2} |
| T60 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 3, 'malformed_model_output': 2} |
| T61 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T62 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'malformed_model_output': 1} |
| T63 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 1, 'malformed_model_output': 4} |
| T64 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T65 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T66 | 0/5 | 1 | 1 | 1 | {'missing_booking': 4, 'wrong_answer': 1} |
| T67 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T68 | 0/5 | 1 | 1 | 5 | {'wrong_answer': 1, 'tool_argument_error': 4} |
| T69 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T70 | 0/5 | 3 | 4 | 1 | {'unsafe_action': 4, 'tool_argument_error': 1} |
| T71 | 1/5 | 2 | 3 | 3 | {'success': 1, 'missing_booking': 1, 'format_only': 1, 'wrong_answer': 1, 'output_truncated': 1} |
| T72 | 0/5 | 0 | 0 | 0 | {'unsafe_action': 1, 'missing_booking': 2, 'step_limit': 1, 'output_truncated': 1} |
| T73 | 0/5 | 3 | 0 | 0 | {'unsafe_action': 1, 'malformed_model_output': 1, 'missing_booking': 3} |
| T74 | 0/5 | 0 | 5 | 5 | {'format_only': 4, 'malformed_model_output': 1} |
| T75 | 1/5 | 1 | 3 | 3 | {'missing_booking': 1, 'unsafe_action': 1, 'format_only': 2, 'success': 1} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 13, 'output_truncated': 19, 'malformed_model_output': 44, 'step_limit': 1, 'unsafe_action': 42, 'missing_booking': 73, 'tool_argument_error': 92, 'missing_required_call': 3, 'wrong_answer': 11, 'format_only': 77}
- secondary tags: {'no_final_block': 307, 'guessed_station_code': 248, 'reply_language_mismatch': 172, 'missing_expected_booking': 90, 'invalid_train_id_format': 75, 'unresolvable_station_name': 73, 'empty_final_text': 63, 'unexpected_booking': 45, 'kind:unparsed_model_output': 44, 'repetition_or_truncation': 2, 'ungrounded_train_id': 1, 'parallel_dependent_calls': 1}
- format_only (tool process and booking state correct, only the final-answer block failed): 77 items

## Cost

- tokens: input 1991127, output 158313, cached input 1741346
- items retried: 0; wall time 1434.5 s (sum of item times 1434.1 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
