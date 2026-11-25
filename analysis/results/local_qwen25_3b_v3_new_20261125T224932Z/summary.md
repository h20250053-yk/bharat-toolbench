# Run summary: local_qwen25_3b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_qwen25_3b_v3_new_20261125T224932Z.jsonl` (625 rows, sha256 8e01baabdfa0...); `runs/local_qwen25_3b_v3_new_20261125T224932Z_resume1.jsonl` (626 rows, sha256 59bf405c80ac...); `runs/local_qwen25_3b_v3_new_20261125T224932Z_resume2.jsonl` (627 rows, sha256 6d09e69670fd...)
- expected items 625, selected 625, missing 0, unexpected 0, items with >1 row 625, complete=True

## Official result

- task_success: **4/625 (0.6%)** (not scored: 0)
- status: {'completed': 464, 'output_truncated': 152, 'context_overflow': 2, 'malformed_output': 7}
- final-answer parse ok: 27/625 (4.3%); process ok: 195/625 (31.2%); state ok: 434/625 (69.4%)
- tool calls ok: 519/1389 (37.4%); top error codes: {'INVALID_TRAIN': 403, 'INVALID_STATION': 174, 'INVALID_ARGUMENTS': 69, 'ALREADY_CANCELLED': 30, 'TDR_WINDOW_CLOSED': 30, 'INVALID_PNR': 23, 'SOLD_OUT': 21, 'STATION_NOT_FOUND': 19, 'PNR_NOT_FOUND': 16, 'JOURNEY_STARTED': 12}
- failure label families: {'process:missing_required_call': 614, 'final_answer:missing_block': 598, 'run:output_truncated': 152, 'state:meal_orders_mismatch': 45, 'state:tatkal_bookings_mismatch': 41, 'state:bookings_mismatch': 36, 'state:boarding_changes_mismatch': 23, 'state:cancellations_mismatch': 20, 'state:complaints_mismatch': 20, 'state:waitlist_mismatch': 16, 'process:prohibited_action': 12, 'state:tdr_claims_mismatch': 11, 'final_answer:booking_ids_do_not_match_state': 7, 'run:malformed_output': 7, 'status:expected_success_got_needs_clarification': 5, 'status:expected_cannot_complete_got_success': 4, 'answer_value:missing': 4, 'final_answer:wrong_selected_train': 4, 'final_answer:wrong_selected_class': 4, 'answer_value:wrong': 4, 'run:context_overflow': 2, 'status:expected_cannot_complete_got_needs_clarification': 1, 'status:expected_success_got_cannot_complete': 1, 'final_answer:booking_ids_invalid': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **4/625 (0.6%)**; strict: 4/625 (0.6%)
- items that needed a format recovery: 4; by rule {'extra_args_dropped': 2, 'booking_ids_shape': 1, 'passenger_punctuation': 1}; by language {'hinglish': 2, 'en': 1, 'mr': 1}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 7, 'by_language': {'mr': 2, 'hi': 3, 'gu': 1, 'hinglish': 1}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 4/610 (0.7%); no-tool tasks: 0/15 (0.0%)
- baseline 'always needs_clarification, no tool calls' passes 13 of 200 tasks (6.5%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 2/125 (1.6%) | 10 | 66 | 90 | {'format_only': 55, 'missing_booking': 25, 'unsafe_action': 9, 'wrong_answer': 5, 'missing_required_call': 9, 'tool_argument_error': 18, 'success': 2, 'output_truncated': 2} |
| gu | 0/125 (0.0%) | 2 | 19 | 81 | {'format_only': 16, 'output_truncated': 60, 'unsafe_action': 11, 'wrong_answer': 1, 'tool_argument_error': 20, 'missing_booking': 14, 'missing_required_call': 2, 'malformed_model_output': 1} |
| hi | 1/125 (0.8%) | 9 | 37 | 87 | {'format_only': 32, 'unsafe_action': 8, 'output_truncated': 30, 'wrong_answer': 3, 'missing_required_call': 9, 'missing_booking': 21, 'context_overflow': 1, 'tool_argument_error': 17, 'malformed_model_output': 3, 'success': 1} |
| hinglish | 1/125 (0.8%) | 6 | 52 | 93 | {'format_only': 46, 'missing_booking': 20, 'unsafe_action': 8, 'wrong_answer': 1, 'context_overflow': 1, 'output_truncated': 12, 'tool_argument_error': 24, 'missing_required_call': 11, 'success': 1, 'malformed_model_output': 1} |
| mr | 0/125 (0.0%) | 0 | 21 | 83 | {'format_only': 19, 'output_truncated': 48, 'unsafe_action': 7, 'missing_booking': 23, 'malformed_model_output': 2, 'tool_argument_error': 21, 'missing_required_call': 5} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 135 | 1 | 11 | 30 | 43 |
| clarification | 10 | 0 | 0 | 10 | 10 |
| constraint | 130 | 2 | 10 | 31 | 56 |
| invalid_input | 35 | 0 | 0 | 22 | 35 |
| recovery | 105 | 0 | 1 | 39 | 97 |
| sequential | 120 | 0 | 3 | 20 | 103 |
| single_tool | 90 | 1 | 2 | 43 | 90 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T100 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'missing_required_call': 1} |
| T101 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'tool_argument_error': 1, 'output_truncated': 1} |
| T102 | 0/5 | 0 | 1 | 5 | {'format_only': 1, 'tool_argument_error': 3, 'output_truncated': 1} |
| T103 | 0/5 | 0 | 0 | 1 | {'missing_booking': 2, 'output_truncated': 2, 'unsafe_action': 1} |
| T104 | 0/5 | 0 | 0 | 0 | {'missing_booking': 3, 'unsafe_action': 1, 'output_truncated': 1} |
| T105 | 0/5 | 0 | 1 | 4 | {'format_only': 1, 'missing_required_call': 1, 'output_truncated': 2, 'tool_argument_error': 1} |
| T106 | 0/5 | 0 | 1 | 2 | {'unsafe_action': 1, 'tool_argument_error': 2, 'output_truncated': 2} |
| T107 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'output_truncated': 2} |
| T108 | 0/5 | 0 | 2 | 2 | {'format_only': 2, 'missing_booking': 1, 'output_truncated': 2} |
| T109 | 0/5 | 0 | 2 | 2 | {'unsafe_action': 3, 'format_only': 2} |
| T110 | 1/5 | 1 | 2 | 2 | {'success': 1, 'format_only': 1, 'missing_booking': 2, 'output_truncated': 1} |
| T111 | 0/5 | 0 | 2 | 4 | {'unsafe_action': 1, 'format_only': 1, 'output_truncated': 2, 'missing_required_call': 1} |
| T112 | 0/5 | 0 | 0 | 4 | {'output_truncated': 4, 'missing_booking': 1} |
| T113 | 0/5 | 0 | 1 | 0 | {'unsafe_action': 4, 'output_truncated': 1} |
| T114 | 0/5 | 1 | 1 | 5 | {'format_only': 1, 'tool_argument_error': 2, 'missing_required_call': 1, 'output_truncated': 1} |
| T115 | 1/5 | 1 | 1 | 2 | {'missing_booking': 1, 'success': 1, 'output_truncated': 2, 'unsafe_action': 1} |
| T116 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'tool_argument_error': 2, 'output_truncated': 1} |
| T117 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'output_truncated': 2, 'tool_argument_error': 1} |
| T118 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'malformed_model_output': 2, 'output_truncated': 1} |
| T119 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T120 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T121 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'tool_argument_error': 3} |
| T122 | 1/5 | 1 | 2 | 4 | {'success': 1, 'format_only': 1, 'output_truncated': 1, 'tool_argument_error': 2} |
| T123 | 0/5 | 0 | 1 | 2 | {'output_truncated': 3, 'unsafe_action': 1, 'tool_argument_error': 1} |
| T124 | 0/5 | 1 | 1 | 1 | {'missing_booking': 3, 'format_only': 1, 'output_truncated': 1} |
| T125 | 1/5 | 1 | 5 | 5 | {'format_only': 4, 'success': 1} |
| T126 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T127 | 0/5 | 1 | 3 | 5 | {'wrong_answer': 1, 'format_only': 2, 'missing_required_call': 1, 'output_truncated': 1} |
| T128 | 0/5 | 0 | 1 | 5 | {'format_only': 1, 'output_truncated': 4} |
| T129 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T130 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 1, 'missing_required_call': 4} |
| T131 | 0/5 | 0 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T132 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T133 | 0/5 | 0 | 1 | 1 | {'format_only': 1, 'missing_booking': 4} |
| T134 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'output_truncated': 2} |
| T135 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T136 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 3, 'output_truncated': 2} |
| T137 | 0/5 | 0 | 1 | 5 | {'tool_argument_error': 3, 'format_only': 1, 'output_truncated': 1} |
| T138 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 3, 'output_truncated': 2} |
| T139 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T140 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T141 | 0/5 | 0 | 1 | 1 | {'format_only': 1, 'unsafe_action': 3, 'output_truncated': 1} |
| T142 | 0/5 | 0 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T143 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T144 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T145 | 0/5 | 0 | 4 | 4 | {'unsafe_action': 1, 'format_only': 3, 'tool_argument_error': 1} |
| T146 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T147 | 0/5 | 0 | 1 | 5 | {'tool_argument_error': 4, 'format_only': 1} |
| T148 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 2, 'output_truncated': 3} |
| T149 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T150 | 0/5 | 0 | 1 | 5 | {'tool_argument_error': 3, 'format_only': 1, 'output_truncated': 1} |
| T151 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T152 | 0/5 | 0 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T153 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T154 | 0/5 | 0 | 0 | 0 | {'missing_booking': 2, 'unsafe_action': 2, 'output_truncated': 1} |
| T155 | 0/5 | 0 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T156 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T157 | 0/5 | 1 | 0 | 0 | {'missing_booking': 5} |
| T158 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T159 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 3, 'tool_argument_error': 1, 'malformed_model_output': 1} |
| T160 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T161 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'malformed_model_output': 1} |
| T162 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T163 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T164 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 3, 'output_truncated': 1, 'tool_argument_error': 1} |
| T165 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'output_truncated': 2, 'missing_required_call': 1} |
| T166 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 2, 'output_truncated': 3} |
| T167 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 1, 'output_truncated': 4} |
| T168 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'output_truncated': 3} |
| T169 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'output_truncated': 1} |
| T170 | 0/5 | 1 | 4 | 5 | {'wrong_answer': 1, 'format_only': 3, 'output_truncated': 1} |
| T171 | 0/5 | 0 | 0 | 0 | {'missing_booking': 2, 'output_truncated': 2, 'unsafe_action': 1} |
| T172 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'tool_argument_error': 1, 'output_truncated': 2} |
| T173 | 0/5 | 0 | 3 | 4 | {'format_only': 2, 'unsafe_action': 1, 'output_truncated': 2} |
| T174 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'output_truncated': 2} |
| T175 | 0/5 | 0 | 0 | 2 | {'unsafe_action': 3, 'malformed_model_output': 1, 'output_truncated': 1} |
| T176 | 0/5 | 1 | 4 | 5 | {'wrong_answer': 1, 'format_only': 3, 'output_truncated': 1} |
| T177 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'output_truncated': 3} |
| T178 | 0/5 | 0 | 0 | 3 | {'unsafe_action': 2, 'missing_required_call': 1, 'output_truncated': 2} |
| T179 | 0/5 | 0 | 2 | 3 | {'format_only': 2, 'tool_argument_error': 1, 'missing_booking': 2} |
| T180 | 0/5 | 0 | 2 | 2 | {'format_only': 2, 'output_truncated': 2, 'missing_booking': 1} |
| T181 | 0/5 | 0 | 1 | 4 | {'format_only': 1, 'output_truncated': 4} |
| T182 | 0/5 | 1 | 3 | 4 | {'format_only': 2, 'wrong_answer': 1, 'output_truncated': 2} |
| T183 | 0/5 | 0 | 1 | 1 | {'format_only': 1, 'unsafe_action': 2, 'output_truncated': 2} |
| T184 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'output_truncated': 2} |
| T185 | 0/5 | 1 | 3 | 3 | {'format_only': 2, 'wrong_answer': 1, 'output_truncated': 2} |
| T186 | 0/5 | 0 | 2 | 3 | {'format_only': 2, 'output_truncated': 2, 'missing_booking': 1} |
| T187 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'output_truncated': 1} |
| T188 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'missing_required_call': 1, 'output_truncated': 1, 'tool_argument_error': 1} |
| T189 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T190 | 0/5 | 0 | 1 | 3 | {'format_only': 1, 'missing_required_call': 2, 'output_truncated': 2} |
| T191 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T192 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T193 | 0/5 | 1 | 1 | 5 | {'format_only': 1, 'missing_required_call': 2, 'malformed_model_output': 1, 'output_truncated': 1} |
| T194 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'output_truncated': 2} |
| T195 | 0/5 | 0 | 0 | 1 | {'missing_booking': 1, 'output_truncated': 4} |
| T196 | 0/5 | 0 | 0 | 3 | {'missing_required_call': 1, 'output_truncated': 3, 'unsafe_action': 1} |
| T197 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T198 | 0/5 | 0 | 0 | 2 | {'missing_required_call': 2, 'missing_booking': 3} |
| T199 | 0/5 | 0 | 1 | 5 | {'format_only': 1, 'tool_argument_error': 3, 'output_truncated': 1} |
| T200 | 0/5 | 0 | 0 | 0 | {'unsafe_action': 2, 'output_truncated': 1, 'missing_booking': 2} |
| T76 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T77 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'output_truncated': 2} |
| T78 | 0/5 | 0 | 1 | 1 | {'missing_booking': 2, 'format_only': 1, 'output_truncated': 2} |
| T79 | 0/5 | 4 | 4 | 0 | {'unsafe_action': 5} |
| T80 | 0/5 | 1 | 2 | 5 | {'wrong_answer': 1, 'format_only': 1, 'output_truncated': 3} |
| T81 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T82 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'output_truncated': 1} |
| T83 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'output_truncated': 1} |
| T84 | 0/5 | 2 | 2 | 3 | {'missing_booking': 1, 'wrong_answer': 2, 'output_truncated': 2} |
| T85 | 0/5 | 1 | 1 | 1 | {'format_only': 1, 'unsafe_action': 4} |
| T86 | 0/5 | 0 | 2 | 1 | {'missing_booking': 2, 'context_overflow': 1, 'format_only': 1, 'unsafe_action': 1} |
| T87 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'output_truncated': 3} |
| T88 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'output_truncated': 2} |
| T89 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T90 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'output_truncated': 2, 'malformed_model_output': 1} |
| T91 | 0/5 | 0 | 1 | 5 | {'missing_required_call': 2, 'format_only': 1, 'output_truncated': 2} |
| T92 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 2, 'output_truncated': 2, 'unsafe_action': 1} |
| T93 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'output_truncated': 2} |
| T94 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'output_truncated': 2} |
| T95 | 0/5 | 0 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T96 | 0/5 | 1 | 0 | 1 | {'missing_booking': 2, 'output_truncated': 2, 'context_overflow': 1} |
| T97 | 0/5 | 1 | 2 | 4 | {'wrong_answer': 1, 'unsafe_action': 1, 'output_truncated': 3} |
| T98 | 0/5 | 0 | 5 | 5 | {'format_only': 4, 'output_truncated': 1} |
| T99 | 0/5 | 2 | 4 | 4 | {'format_only': 3, 'missing_booking': 1, 'wrong_answer': 1} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 4, 'context_overflow': 2, 'output_truncated': 152, 'malformed_model_output': 7, 'unsafe_action': 43, 'missing_booking': 103, 'tool_argument_error': 100, 'missing_required_call': 36, 'wrong_answer': 10, 'format_only': 168}
- secondary tags: {'no_final_block': 598, 'empty_final_text': 161, 'reply_language_mismatch': 160, 'missing_expected_booking': 160, 'guessed_station_code': 135, 'invalid_train_id_format': 92, 'unexpected_booking': 55, 'unresolvable_station_name': 13, 'kind:unparsed_model_output': 7, 'ungrounded_train_id': 3, 'parallel_dependent_calls': 3}
- format_only (tool process and booking state correct, only the final-answer block failed): 168 items

## Cost

- tokens: input 4538824, output 189007, cached input 4332092
- items retried: 0; wall time 3518.0 s (sum of item times 3506.8 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
