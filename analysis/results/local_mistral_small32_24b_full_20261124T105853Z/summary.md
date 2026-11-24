# Run summary: local_mistral_small32_24b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_mistral_small32_24b_full_20261124T105853Z.jsonl` (375 rows, sha256 6f9344858672...)
- expected items 375, selected 375, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **19/375 (5.1%)** (not scored: 0)
- status: {'completed': 145, 'malformed_output': 229, 'output_truncated': 1}
- final-answer parse ok: 40/375 (10.7%); process ok: 97/375 (25.9%); state ok: 261/375 (69.6%)
- tool calls ok: 68/98 (69.4%); top error codes: {'INVALID_TRAIN': 9, 'CLASS_NOT_OFFERED': 8, 'SOLD_OUT': 6, 'INVALID_STATION': 4, 'INVALID_ARGUMENTS': 3}
- failure label families: {'process:missing_required_call': 1020, 'final_answer:missing_block': 316, 'run:malformed_output': 229, 'state:bookings_mismatch': 114, 'final_answer:missing_keys': 18, 'process:prohibited_action': 10, 'final_answer:booking_ids_do_not_match_state': 3, 'answer_value:wrong': 3, 'final_answer:wrong_selected_train': 3, 'final_answer:wrong_selected_class': 3, 'answer_value:missing': 2, 'status:expected_success_got_needs_clarification': 2, 'status:expected_needs_clarification_got_success': 2, 'run:output_truncated': 1, 'status:expected_cannot_complete_got_needs_clarification': 1, 'process:dependency_violation': 1, 'final_answer:malformed_json': 1, 'status:expected_success_got_cannot_complete': 1, 'status:expected_needs_clarification_got_cannot_complete': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **19/375 (5.1%)**; strict: 19/375 (5.1%)
- items that needed a format recovery: 1; by rule {'extra_args_dropped': 1}; by language {'hinglish': 1}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 229, 'by_language': {'en': 56, 'hi': 53, 'mr': 36, 'gu': 65, 'hinglish': 19}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 16/320 (5.0%); no-tool tasks: 3/55 (5.5%)
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 4/75 (5.3%) | 8 | 21 | 52 | {'format_only': 6, 'malformed_model_output': 56, 'success': 4, 'missing_required_call': 5, 'wrong_answer': 2, 'unsafe_action': 1, 'missing_booking': 1} |
| gu | 4/75 (5.3%) | 5 | 19 | 54 | {'format_only': 4, 'malformed_model_output': 65, 'success': 4, 'missing_required_call': 1, 'wrong_answer': 1} |
| hi | 3/75 (4.0%) | 9 | 18 | 51 | {'format_only': 4, 'malformed_model_output': 53, 'unsafe_action': 3, 'missing_required_call': 9, 'success': 3, 'missing_booking': 2, 'wrong_answer': 1} |
| hinglish | 5/75 (6.7%) | 11 | 21 | 52 | {'format_only': 12, 'missing_required_call': 18, 'malformed_model_output': 19, 'missing_booking': 17, 'success': 5, 'tool_argument_error': 1, 'unsafe_action': 2, 'wrong_answer': 1} |
| mr | 3/75 (4.0%) | 7 | 18 | 52 | {'format_only': 6, 'malformed_model_output': 36, 'output_truncated': 1, 'missing_booking': 15, 'wrong_answer': 2, 'missing_required_call': 11, 'success': 3, 'tool_argument_error': 1} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 75 | 2 | 7 | 6 | 9 |
| clarification | 45 | 0 | 3 | 40 | 43 |
| constraint | 90 | 1 | 5 | 6 | 67 |
| invalid_input | 30 | 11 | 13 | 23 | 30 |
| recovery | 40 | 3 | 6 | 4 | 22 |
| sequential | 65 | 0 | 1 | 3 | 60 |
| single_tool | 30 | 2 | 5 | 15 | 30 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T02 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 4, 'missing_required_call': 1} |
| T03 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 4, 'output_truncated': 1} |
| T04 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T05 | 1/5 | 3 | 2 | 5 | {'success': 1, 'missing_required_call': 1, 'unsafe_action': 1, 'wrong_answer': 1, 'malformed_model_output': 1} |
| T06 | 1/5 | 1 | 5 | 5 | {'format_only': 4, 'success': 1} |
| T07 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 4, 'malformed_model_output': 1} |
| T08 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 5} |
| T09 | 0/5 | 0 | 5 | 5 | {'malformed_model_output': 4, 'format_only': 1} |
| T10 | 2/5 | 2 | 2 | 2 | {'success': 2, 'missing_booking': 2, 'malformed_model_output': 1} |
| T11 | 3/5 | 5 | 3 | 5 | {'success': 3, 'missing_required_call': 2} |
| T12 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 5} |
| T13 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T14 | 0/5 | 1 | 1 | 5 | {'wrong_answer': 1, 'malformed_model_output': 4} |
| T15 | 1/5 | 2 | 1 | 4 | {'malformed_model_output': 2, 'success': 1, 'unsafe_action': 1, 'missing_required_call': 1} |
| T16 | 0/5 | 3 | 0 | 5 | {'missing_required_call': 4, 'malformed_model_output': 1} |
| T17 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 5} |
| T18 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 4, 'tool_argument_error': 1} |
| T19 | 0/5 | 1 | 5 | 4 | {'malformed_model_output': 4, 'unsafe_action': 1} |
| T20 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 3, 'missing_required_call': 2} |
| T21 | 0/5 | 1 | 0 | 4 | {'malformed_model_output': 4, 'unsafe_action': 1} |
| T22 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T23 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 4, 'missing_booking': 1} |
| T24 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 2, 'missing_required_call': 3} |
| T25 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 5} |
| T26 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'missing_required_call': 1} |
| T27 | 2/5 | 2 | 2 | 2 | {'malformed_model_output': 3, 'success': 2} |
| T28 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T29 | 0/5 | 0 | 5 | 5 | {'malformed_model_output': 4, 'format_only': 1} |
| T30 | 0/5 | 0 | 5 | 5 | {'malformed_model_output': 3, 'format_only': 2} |
| T31 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 4, 'missing_required_call': 1} |
| T32 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T33 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T34 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 2, 'malformed_model_output': 3} |
| T35 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T36 | 0/5 | 0 | 5 | 5 | {'malformed_model_output': 3, 'format_only': 2} |
| T37 | 0/5 | 0 | 5 | 5 | {'malformed_model_output': 5} |
| T38 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T39 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 5} |
| T40 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 3, 'missing_required_call': 2} |
| T41 | 0/5 | 2 | 1 | 3 | {'unsafe_action': 2, 'format_only': 1, 'malformed_model_output': 2} |
| T42 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 5} |
| T43 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T44 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 2, 'missing_required_call': 2, 'tool_argument_error': 1} |
| T45 | 3/5 | 3 | 5 | 5 | {'format_only': 2, 'success': 3} |
| T46 | 0/5 | 0 | 5 | 5 | {'malformed_model_output': 4, 'format_only': 1} |
| T47 | 0/5 | 1 | 0 | 1 | {'malformed_model_output': 4, 'missing_required_call': 1} |
| T48 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T49 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T50 | 0/5 | 1 | 0 | 2 | {'missing_required_call': 1, 'missing_booking': 3, 'malformed_model_output': 1} |
| T51 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 5} |
| T52 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 5} |
| T53 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 3, 'missing_required_call': 2} |
| T54 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 5} |
| T55 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'missing_required_call': 1, 'malformed_model_output': 2} |
| T56 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 5} |
| T57 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 5} |
| T58 | 0/5 | 3 | 4 | 4 | {'missing_booking': 1, 'wrong_answer': 3, 'format_only': 1} |
| T59 | 0/5 | 1 | 4 | 5 | {'format_only': 3, 'malformed_model_output': 1, 'wrong_answer': 1} |
| T60 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 4, 'missing_required_call': 1} |
| T61 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 3, 'missing_required_call': 2} |
| T62 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 4, 'missing_required_call': 1} |
| T63 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 3, 'missing_required_call': 2} |
| T64 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 5} |
| T65 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 4, 'missing_booking': 1} |
| T66 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 5} |
| T67 | 0/5 | 0 | 5 | 5 | {'malformed_model_output': 4, 'format_only': 1} |
| T68 | 1/5 | 1 | 1 | 5 | {'malformed_model_output': 3, 'success': 1, 'missing_required_call': 1} |
| T69 | 0/5 | 0 | 5 | 5 | {'malformed_model_output': 3, 'format_only': 2} |
| T70 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 4, 'missing_required_call': 1} |
| T71 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 4, 'missing_booking': 1} |
| T72 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T73 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T74 | 0/5 | 1 | 5 | 5 | {'wrong_answer': 1, 'malformed_model_output': 4} |
| T75 | 0/5 | 1 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 19, 'output_truncated': 1, 'malformed_model_output': 229, 'unsafe_action': 6, 'missing_booking': 35, 'tool_argument_error': 2, 'missing_required_call': 44, 'wrong_answer': 7, 'format_only': 32}
- secondary tags: {'no_final_block': 316, 'empty_final_text': 230, 'kind:unparsed_model_output': 229, 'missing_expected_booking': 109, 'reply_language_mismatch': 39, 'unexpected_booking': 5, 'guessed_station_code': 4, 'invalid_train_id_format': 4}
- format_only (tool process and booking state correct, only the final-answer block failed): 32 items

## Cost

- tokens: input 338099, output 18056, cached input 282477
- items retried: 0; wall time 947.7 s (sum of item times 947.4 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
