# Run summary: local_llama32_3b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_llama32_3b_full_20261124T105853Z.jsonl` (375 rows, sha256 90638307294d...)
- expected items 375, selected 375, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **28/375 (7.5%)** (not scored: 0)
- status: {'completed': 355, 'output_truncated': 19, 'step_limit_exceeded': 1}
- final-answer parse ok: 148/375 (39.5%); process ok: 99/375 (26.4%); state ok: 258/375 (68.8%)
- tool calls ok: 140/604 (23.2%); top error codes: {'INVALID_TRAIN': 145, 'INVALID_STATION': 118, 'INVALID_ARGUMENTS': 102, 'STATION_NOT_FOUND': 56, 'INVALID_PASSENGER': 13, 'INVALID_CLASS': 11, 'SOLD_OUT': 10, 'CLASS_NOT_OFFERED': 9}
- failure label families: {'process:missing_required_call': 985, 'final_answer:missing_block': 222, 'state:bookings_mismatch': 117, 'status:expected_success_got_needs_clarification': 51, 'process:prohibited_action': 34, 'run:output_truncated': 19, 'status:expected_cannot_complete_got_needs_clarification': 18, 'final_answer:wrong_selected_class': 10, 'status:expected_needs_clarification_got_success': 9, 'final_answer:wrong_selected_train': 8, 'status:expected_cannot_complete_got_success': 6, 'final_answer:booking_ids_do_not_match_state': 6, 'status:expected_success_got_cannot_complete': 5, 'final_answer:selected_train_invalid': 4, 'final_answer:missing_keys': 4, 'final_answer:booking_ids_invalid': 2, 'process:dependency_violation': 2, 'value:resolved_date=2026-10-10_not_stated': 2, 'value:fare_inr=3565_not_stated': 1, 'final_answer:wrong_selected_trains': 1, 'status:expected_needs_clarification_got_cannot_complete': 1, 'final_answer:invalid_status': 1, 'run:step_limit_exceeded': 1, 'answer_value:missing': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **28/375 (7.5%)**; strict: 15/375 (4.0%)
- items that needed a format recovery: 162; by rule {'extra_args_dropped': 79, 'args_json_string': 51, 'trailing_text_ignored': 41, 'time_format': 14, 'closing_tag_missing': 13, 'requested_passengers_shape': 4, 'booking_ids_shape': 3, 'text_tool_call': 3, 'closing_braces_appended': 3, 'integer_form': 3, 'passenger_punctuation': 1, 'untagged_json': 1}; by language {'hi': 39, 'mr': 36, 'en': 31, 'gu': 27, 'hinglish': 29}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 12/320 (3.8%); no-tool tasks: 16/55 (29.1%)
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 5/75 (6.7%) | 26 | 24 | 53 | {'format_only': 17, 'tool_argument_error': 26, 'missing_booking': 17, 'unsafe_action': 6, 'success': 5, 'missing_required_call': 3, 'wrong_answer': 1} |
| gu | 7/75 (9.3%) | 38 | 18 | 51 | {'missing_required_call': 5, 'tool_argument_error': 20, 'output_truncated': 11, 'missing_booking': 15, 'unsafe_action': 6, 'success': 7, 'format_only': 6, 'wrong_answer': 4, 'step_limit': 1} |
| hi | 7/75 (9.3%) | 32 | 19 | 50 | {'success': 7, 'tool_argument_error': 27, 'missing_booking': 19, 'unsafe_action': 8, 'format_only': 8, 'missing_required_call': 3, 'wrong_answer': 3} |
| hinglish | 5/75 (6.7%) | 24 | 19 | 52 | {'format_only': 10, 'tool_argument_error': 30, 'missing_booking': 16, 'unsafe_action': 8, 'success': 5, 'wrong_answer': 3, 'output_truncated': 2, 'missing_required_call': 1} |
| mr | 4/75 (5.3%) | 28 | 19 | 52 | {'missing_required_call': 6, 'tool_argument_error': 24, 'missing_booking': 16, 'format_only': 11, 'unsafe_action': 6, 'output_truncated': 6, 'wrong_answer': 2, 'success': 4} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 75 | 8 | 45 | 14 | 22 |
| clarification | 45 | 16 | 26 | 40 | 36 |
| constraint | 90 | 0 | 29 | 1 | 60 |
| invalid_input | 30 | 0 | 9 | 20 | 30 |
| recovery | 40 | 1 | 16 | 2 | 21 |
| sequential | 65 | 0 | 15 | 2 | 60 |
| single_tool | 30 | 3 | 8 | 20 | 29 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 1/5 | 2 | 3 | 5 | {'format_only': 2, 'success': 1, 'missing_required_call': 2} |
| T02 | 0/5 | 3 | 0 | 5 | {'tool_argument_error': 5} |
| T03 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T04 | 0/5 | 3 | 0 | 0 | {'missing_booking': 5} |
| T05 | 0/5 | 2 | 1 | 5 | {'unsafe_action': 4, 'format_only': 1} |
| T06 | 0/5 | 1 | 2 | 5 | {'format_only': 2, 'tool_argument_error': 3} |
| T07 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T08 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T09 | 1/5 | 1 | 5 | 5 | {'format_only': 4, 'success': 1} |
| T10 | 1/5 | 2 | 1 | 1 | {'success': 1, 'missing_booking': 4} |
| T11 | 0/5 | 3 | 1 | 5 | {'missing_required_call': 4, 'format_only': 1} |
| T12 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T13 | 0/5 | 2 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T14 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T15 | 0/5 | 2 | 0 | 5 | {'tool_argument_error': 2, 'unsafe_action': 3} |
| T16 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'tool_argument_error': 2} |
| T17 | 0/5 | 2 | 2 | 5 | {'format_only': 2, 'tool_argument_error': 3} |
| T18 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T19 | 1/5 | 4 | 5 | 2 | {'unsafe_action': 3, 'success': 1, 'format_only': 1} |
| T20 | 0/5 | 2 | 0 | 5 | {'tool_argument_error': 5} |
| T21 | 0/5 | 5 | 0 | 0 | {'unsafe_action': 5} |
| T22 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T23 | 0/5 | 4 | 0 | 0 | {'missing_booking': 5} |
| T24 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T25 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 4, 'missing_required_call': 1} |
| T26 | 1/5 | 1 | 5 | 5 | {'success': 1, 'format_only': 4} |
| T27 | 3/5 | 4 | 3 | 3 | {'success': 3, 'missing_booking': 2} |
| T28 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'tool_argument_error': 1} |
| T29 | 0/5 | 2 | 5 | 5 | {'format_only': 2, 'wrong_answer': 2, 'output_truncated': 1} |
| T30 | 0/5 | 2 | 5 | 5 | {'format_only': 3, 'wrong_answer': 2} |
| T31 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T32 | 0/5 | 4 | 0 | 0 | {'unsafe_action': 4, 'missing_booking': 1} |
| T33 | 0/5 | 2 | 0 | 0 | {'missing_booking': 3, 'output_truncated': 2} |
| T34 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T35 | 0/5 | 1 | 0 | 0 | {'missing_booking': 5} |
| T36 | 2/5 | 3 | 5 | 5 | {'format_only': 2, 'wrong_answer': 1, 'success': 2} |
| T37 | 3/5 | 4 | 5 | 4 | {'success': 3, 'format_only': 1, 'unsafe_action': 1} |
| T38 | 0/5 | 2 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T39 | 0/5 | 2 | 0 | 4 | {'tool_argument_error': 4, 'unsafe_action': 1} |
| T40 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T41 | 0/5 | 2 | 0 | 3 | {'unsafe_action': 2, 'tool_argument_error': 1, 'missing_required_call': 1, 'step_limit': 1} |
| T42 | 2/5 | 3 | 2 | 2 | {'success': 2, 'missing_booking': 3} |
| T43 | 0/5 | 3 | 0 | 0 | {'missing_booking': 5} |
| T44 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'missing_required_call': 1} |
| T45 | 0/5 | 2 | 5 | 5 | {'wrong_answer': 2, 'format_only': 3} |
| T46 | 2/5 | 2 | 5 | 5 | {'format_only': 3, 'success': 2} |
| T47 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T48 | 0/5 | 2 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T49 | 0/5 | 1 | 0 | 0 | {'missing_booking': 5} |
| T50 | 0/5 | 4 | 1 | 3 | {'missing_required_call': 1, 'tool_argument_error': 1, 'missing_booking': 2, 'wrong_answer': 1} |
| T51 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T52 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T53 | 0/5 | 2 | 0 | 5 | {'tool_argument_error': 5} |
| T54 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T55 | 0/5 | 1 | 2 | 5 | {'format_only': 2, 'tool_argument_error': 2, 'output_truncated': 1} |
| T56 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 3, 'output_truncated': 2} |
| T57 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T58 | 0/5 | 4 | 4 | 4 | {'format_only': 1, 'wrong_answer': 3, 'missing_booking': 1} |
| T59 | 0/5 | 1 | 1 | 1 | {'format_only': 1, 'unsafe_action': 4} |
| T60 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 3, 'output_truncated': 1, 'missing_required_call': 1} |
| T61 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 3, 'output_truncated': 2} |
| T62 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T63 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 4, 'missing_required_call': 1} |
| T64 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T65 | 0/5 | 2 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T66 | 0/5 | 3 | 1 | 2 | {'missing_booking': 3, 'missing_required_call': 1, 'wrong_answer': 1} |
| T67 | 3/5 | 3 | 5 | 5 | {'format_only': 2, 'success': 3} |
| T68 | 1/5 | 2 | 5 | 4 | {'format_only': 2, 'unsafe_action': 1, 'wrong_answer': 1, 'success': 1} |
| T69 | 3/5 | 3 | 5 | 5 | {'format_only': 2, 'success': 3} |
| T70 | 0/5 | 4 | 0 | 2 | {'unsafe_action': 3, 'tool_argument_error': 2} |
| T71 | 3/5 | 3 | 3 | 3 | {'missing_booking': 2, 'success': 3} |
| T72 | 0/5 | 4 | 0 | 0 | {'missing_booking': 2, 'unsafe_action': 3} |
| T73 | 0/5 | 3 | 0 | 0 | {'missing_booking': 5} |
| T74 | 1/5 | 1 | 5 | 5 | {'format_only': 4, 'success': 1} |
| T75 | 0/5 | 4 | 0 | 0 | {'missing_booking': 5} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 28, 'output_truncated': 19, 'step_limit': 1, 'unsafe_action': 34, 'missing_booking': 83, 'tool_argument_error': 127, 'missing_required_call': 18, 'wrong_answer': 13, 'format_only': 52}
- secondary tags: {'no_final_block': 222, 'guessed_station_code': 117, 'reply_language_mismatch': 109, 'missing_expected_booking': 100, 'invalid_train_id_format': 83, 'unexpected_booking': 27, 'empty_final_text': 20, 'tool_call_as_text': 17, 'unresolvable_station_name': 4, 'repetition_or_truncation': 1}
- format_only (tool process and booking state correct, only the final-answer block failed): 52 items

## Cost

- tokens: input 1048595, output 101563, cached input 711761
- items retried: 0; wall time 993.5 s (sum of item times 993.1 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': 'a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
