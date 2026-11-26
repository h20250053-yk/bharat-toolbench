# Run summary: local_mistral_small32_24b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_mistral_small32_24b_v3_new_20261125T224932Z.jsonl` (625 rows, sha256 798b0551abf1...)
- expected items 625, selected 625, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **77/625 (12.3%)** (not scored: 0)
- status: {'completed': 481, 'malformed_output': 138, 'step_limit_exceeded': 4, 'output_truncated': 2}
- final-answer parse ok: 164/625 (26.2%); process ok: 314/625 (50.2%); state ok: 464/625 (74.2%)
- tool calls ok: 429/653 (65.7%); top error codes: {'INVALID_ARGUMENTS': 52, 'INVALID_TRAIN': 45, 'INVALID_STATION': 20, 'ALREADY_CANCELLED': 16, 'JOURNEY_STARTED': 14, 'SOLD_OUT': 12, 'NOT_RUNNING_ON_DATE': 11, 'TDR_WINDOW_CLOSED': 7, 'PNR_NOT_FOUND': 5, 'CONCESSION_NOT_AVAILABLE': 5}
- failure label families: {'process:missing_required_call': 489, 'final_answer:missing_block': 232, 'final_answer:missing_keys': 229, 'run:malformed_output': 138, 'state:tatkal_bookings_mismatch': 49, 'state:bookings_mismatch': 30, 'status:expected_success_got_cannot_complete': 28, 'final_answer:wrong_selected_train': 24, 'state:meal_orders_mismatch': 23, 'state:complaints_mismatch': 20, 'state:boarding_changes_mismatch': 15, 'final_answer:booking_ids_do_not_match_state': 13, 'state:cancellations_mismatch': 13, 'state:waitlist_mismatch': 10, 'status:expected_success_got_needs_clarification': 9, 'answer_value:missing': 9, 'state:tdr_claims_mismatch': 9, 'answer_value:wrong': 8, 'final_answer:wrong_selected_class': 6, 'run:step_limit_exceeded': 4, 'run:output_truncated': 2, 'process:prohibited_action': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **77/625 (12.3%)**; strict: 77/625 (12.3%)
- items that needed a format recovery: 5; by rule {'extra_args_dropped': 5}; by language {'en': 3, 'hinglish': 1, 'hi': 1}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 138, 'by_language': {'hi': 31, 'mr': 34, 'gu': 34, 'en': 23, 'hinglish': 16}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 76/610 (12.5%); no-tool tasks: 1/15 (6.7%)
- baseline 'always needs_clarification, no tool calls' passes 13 of 200 tasks (6.5%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 20/125 (16.0%) | 32 | 73 | 97 | {'wrong_answer': 9, 'format_only': 44, 'missing_booking': 18, 'success': 20, 'malformed_model_output': 23, 'tool_argument_error': 9, 'missing_required_call': 2} |
| gu | 16/125 (12.8%) | 31 | 67 | 95 | {'wrong_answer': 6, 'format_only': 45, 'success': 16, 'missing_booking': 8, 'malformed_model_output': 34, 'step_limit': 3, 'tool_argument_error': 5, 'missing_required_call': 5, 'output_truncated': 1, 'unsafe_action': 2} |
| hi | 18/125 (14.4%) | 40 | 68 | 95 | {'wrong_answer': 10, 'success': 18, 'missing_booking': 11, 'malformed_model_output': 31, 'format_only': 40, 'missing_required_call': 9, 'tool_argument_error': 4, 'unsafe_action': 2} |
| hinglish | 13/125 (10.4%) | 32 | 55 | 89 | {'wrong_answer': 8, 'success': 13, 'missing_booking': 24, 'missing_required_call': 22, 'format_only': 34, 'malformed_model_output': 16, 'tool_argument_error': 6, 'unsafe_action': 2} |
| mr | 10/125 (8.0%) | 29 | 51 | 88 | {'success': 10, 'wrong_answer': 6, 'format_only': 35, 'missing_booking': 17, 'malformed_model_output': 34, 'missing_required_call': 16, 'tool_argument_error': 5, 'step_limit': 1, 'output_truncated': 1} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 135 | 8 | 40 | 58 | 60 |
| clarification | 10 | 1 | 1 | 10 | 10 |
| constraint | 130 | 12 | 25 | 33 | 63 |
| invalid_input | 35 | 9 | 10 | 27 | 35 |
| recovery | 105 | 44 | 47 | 55 | 100 |
| sequential | 120 | 2 | 33 | 52 | 106 |
| single_tool | 90 | 1 | 8 | 79 | 90 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T100 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T101 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T102 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'missing_required_call': 3} |
| T103 | 1/5 | 1 | 1 | 1 | {'success': 1, 'malformed_model_output': 4} |
| T104 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 5} |
| T105 | 0/5 | 0 | 1 | 5 | {'format_only': 1, 'malformed_model_output': 4} |
| T106 | 1/5 | 1 | 4 | 5 | {'success': 1, 'missing_required_call': 1, 'format_only': 3} |
| T107 | 1/5 | 1 | 5 | 5 | {'format_only': 4, 'success': 1} |
| T108 | 0/5 | 0 | 0 | 0 | {'missing_booking': 2, 'malformed_model_output': 3} |
| T109 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 2, 'malformed_model_output': 2, 'step_limit': 1} |
| T110 | 0/5 | 0 | 0 | 0 | {'missing_booking': 1, 'malformed_model_output': 3, 'step_limit': 1} |
| T111 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 1, 'malformed_model_output': 4} |
| T112 | 0/5 | 0 | 0 | 0 | {'missing_booking': 2, 'malformed_model_output': 3} |
| T113 | 0/5 | 0 | 0 | 0 | {'missing_booking': 4, 'malformed_model_output': 1} |
| T114 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T115 | 0/5 | 0 | 0 | 0 | {'missing_booking': 1, 'malformed_model_output': 4} |
| T116 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 5} |
| T117 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T118 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T119 | 0/5 | 1 | 0 | 0 | {'malformed_model_output': 4, 'missing_booking': 1} |
| T120 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 3, 'malformed_model_output': 2} |
| T121 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T122 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T123 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 1, 'malformed_model_output': 4} |
| T124 | 0/5 | 0 | 0 | 0 | {'missing_booking': 2, 'malformed_model_output': 3} |
| T125 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T126 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T127 | 0/5 | 4 | 5 | 5 | {'wrong_answer': 4, 'format_only': 1} |
| T128 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T129 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'missing_required_call': 1} |
| T130 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T131 | 0/5 | 1 | 3 | 3 | {'wrong_answer': 1, 'format_only': 2, 'malformed_model_output': 2} |
| T132 | 1/5 | 2 | 1 | 1 | {'success': 1, 'malformed_model_output': 3, 'missing_booking': 1} |
| T133 | 0/5 | 5 | 0 | 2 | {'tool_argument_error': 2, 'missing_booking': 3} |
| T134 | 3/5 | 3 | 3 | 5 | {'malformed_model_output': 2, 'success': 3} |
| T135 | 1/5 | 2 | 1 | 5 | {'malformed_model_output': 3, 'success': 1, 'missing_required_call': 1} |
| T136 | 0/5 | 0 | 0 | 5 | {'malformed_model_output': 4, 'missing_required_call': 1} |
| T137 | 1/5 | 1 | 2 | 5 | {'malformed_model_output': 3, 'success': 1, 'format_only': 1} |
| T138 | 1/5 | 1 | 1 | 5 | {'malformed_model_output': 3, 'success': 1, 'missing_required_call': 1} |
| T139 | 1/5 | 3 | 1 | 1 | {'malformed_model_output': 1, 'success': 1, 'missing_booking': 3} |
| T140 | 0/5 | 2 | 0 | 5 | {'malformed_model_output': 3, 'missing_required_call': 1, 'tool_argument_error': 1} |
| T141 | 0/5 | 0 | 3 | 3 | {'malformed_model_output': 2, 'format_only': 3} |
| T142 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T143 | 0/5 | 0 | 4 | 4 | {'format_only': 4, 'missing_booking': 1} |
| T144 | 1/5 | 1 | 3 | 3 | {'format_only': 2, 'success': 1, 'malformed_model_output': 2} |
| T145 | 3/5 | 3 | 3 | 5 | {'success': 3, 'missing_required_call': 1, 'malformed_model_output': 1} |
| T146 | 2/5 | 2 | 2 | 5 | {'success': 2, 'missing_required_call': 3} |
| T147 | 3/5 | 3 | 3 | 5 | {'success': 3, 'missing_required_call': 1, 'malformed_model_output': 1} |
| T148 | 1/5 | 1 | 1 | 5 | {'success': 1, 'missing_required_call': 3, 'malformed_model_output': 1} |
| T149 | 1/5 | 1 | 2 | 5 | {'format_only': 1, 'missing_required_call': 1, 'success': 1, 'tool_argument_error': 2} |
| T150 | 4/5 | 4 | 4 | 5 | {'success': 4, 'malformed_model_output': 1} |
| T151 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T152 | 0/5 | 2 | 0 | 0 | {'malformed_model_output': 3, 'missing_booking': 2} |
| T153 | 0/5 | 3 | 0 | 2 | {'missing_booking': 3, 'missing_required_call': 2} |
| T154 | 0/5 | 0 | 4 | 4 | {'format_only': 4, 'missing_booking': 1} |
| T155 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'malformed_model_output': 1} |
| T156 | 0/5 | 2 | 0 | 0 | {'missing_booking': 4, 'step_limit': 1} |
| T157 | 0/5 | 2 | 4 | 4 | {'format_only': 2, 'wrong_answer': 2, 'missing_booking': 1} |
| T158 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'tool_argument_error': 1} |
| T159 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T160 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 1, 'missing_required_call': 2, 'malformed_model_output': 2} |
| T161 | 0/5 | 4 | 0 | 5 | {'tool_argument_error': 3, 'missing_required_call': 1, 'malformed_model_output': 1} |
| T162 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 4, 'malformed_model_output': 1} |
| T163 | 0/5 | 1 | 0 | 5 | {'malformed_model_output': 4, 'tool_argument_error': 1} |
| T164 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'missing_required_call': 2} |
| T165 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'missing_required_call': 2} |
| T166 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'missing_required_call': 2, 'tool_argument_error': 1} |
| T167 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'missing_required_call': 1} |
| T168 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T169 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T170 | 1/5 | 4 | 4 | 4 | {'wrong_answer': 3, 'success': 1, 'malformed_model_output': 1} |
| T171 | 0/5 | 1 | 2 | 2 | {'missing_booking': 1, 'malformed_model_output': 2, 'format_only': 1, 'wrong_answer': 1} |
| T172 | 3/5 | 3 | 3 | 5 | {'success': 3, 'missing_required_call': 1, 'output_truncated': 1} |
| T173 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T174 | 1/5 | 1 | 4 | 5 | {'format_only': 3, 'success': 1, 'output_truncated': 1} |
| T175 | 0/5 | 3 | 0 | 4 | {'malformed_model_output': 1, 'unsafe_action': 1, 'missing_required_call': 3} |
| T176 | 0/5 | 1 | 1 | 5 | {'missing_required_call': 3, 'format_only': 1, 'tool_argument_error': 1} |
| T177 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T178 | 0/5 | 1 | 0 | 2 | {'malformed_model_output': 2, 'unsafe_action': 3} |
| T179 | 0/5 | 1 | 0 | 0 | {'missing_booking': 1, 'malformed_model_output': 4} |
| T180 | 3/5 | 3 | 3 | 3 | {'success': 3, 'malformed_model_output': 2} |
| T181 | 0/5 | 1 | 3 | 3 | {'wrong_answer': 1, 'missing_booking': 2, 'format_only': 2} |
| T182 | 0/5 | 2 | 2 | 2 | {'wrong_answer': 1, 'missing_booking': 1, 'unsafe_action': 2, 'format_only': 1} |
| T183 | 0/5 | 4 | 4 | 4 | {'wrong_answer': 4, 'missing_booking': 1} |
| T184 | 0/5 | 3 | 4 | 4 | {'wrong_answer': 2, 'missing_booking': 1, 'format_only': 2} |
| T185 | 0/5 | 1 | 3 | 3 | {'format_only': 2, 'missing_booking': 2, 'wrong_answer': 1} |
| T186 | 0/5 | 1 | 3 | 3 | {'format_only': 3, 'missing_booking': 2} |
| T187 | 3/5 | 3 | 4 | 5 | {'success': 3, 'format_only': 1, 'missing_required_call': 1} |
| T188 | 2/5 | 2 | 3 | 5 | {'success': 2, 'missing_required_call': 2, 'format_only': 1} |
| T189 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T190 | 0/5 | 0 | 0 | 2 | {'malformed_model_output': 1, 'missing_booking': 2, 'missing_required_call': 2} |
| T191 | 0/5 | 3 | 3 | 5 | {'malformed_model_output': 2, 'wrong_answer': 3} |
| T192 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 1, 'malformed_model_output': 4} |
| T193 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'missing_required_call': 3} |
| T194 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T195 | 0/5 | 0 | 0 | 0 | {'missing_booking': 2, 'malformed_model_output': 3} |
| T196 | 0/5 | 4 | 0 | 5 | {'tool_argument_error': 5} |
| T197 | 0/5 | 0 | 0 | 0 | {'malformed_model_output': 4, 'missing_booking': 1} |
| T198 | 0/5 | 0 | 0 | 0 | {'missing_booking': 4, 'malformed_model_output': 1} |
| T199 | 2/5 | 5 | 2 | 5 | {'success': 2, 'missing_required_call': 3} |
| T200 | 0/5 | 0 | 0 | 0 | {'missing_booking': 3, 'malformed_model_output': 2} |
| T76 | 1/5 | 5 | 5 | 5 | {'wrong_answer': 4, 'success': 1} |
| T77 | 0/5 | 3 | 5 | 5 | {'format_only': 2, 'wrong_answer': 3} |
| T78 | 0/5 | 4 | 4 | 4 | {'missing_booking': 1, 'wrong_answer': 4} |
| T79 | 3/5 | 3 | 5 | 5 | {'format_only': 2, 'success': 3} |
| T80 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T81 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T82 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T83 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T84 | 0/5 | 0 | 0 | 0 | {'missing_booking': 2, 'malformed_model_output': 3} |
| T85 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'missing_required_call': 1} |
| T86 | 2/5 | 2 | 2 | 2 | {'success': 2, 'missing_booking': 1, 'malformed_model_output': 2} |
| T87 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T88 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T89 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T90 | 0/5 | 0 | 1 | 5 | {'malformed_model_output': 2, 'missing_required_call': 2, 'format_only': 1} |
| T91 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T92 | 0/5 | 0 | 2 | 5 | {'malformed_model_output': 2, 'missing_required_call': 1, 'format_only': 2} |
| T93 | 2/5 | 2 | 5 | 5 | {'success': 2, 'format_only': 3} |
| T94 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'missing_required_call': 1} |
| T95 | 0/5 | 2 | 0 | 0 | {'malformed_model_output': 1, 'missing_booking': 3, 'step_limit': 1} |
| T96 | 0/5 | 1 | 0 | 0 | {'malformed_model_output': 1, 'missing_booking': 4} |
| T97 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T98 | 1/5 | 1 | 5 | 5 | {'format_only': 4, 'success': 1} |
| T99 | 2/5 | 2 | 4 | 4 | {'missing_booking': 1, 'format_only': 2, 'success': 2} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 77, 'output_truncated': 2, 'malformed_model_output': 138, 'step_limit': 4, 'unsafe_action': 6, 'missing_booking': 78, 'tool_argument_error': 29, 'missing_required_call': 54, 'wrong_answer': 39, 'format_only': 198}
- secondary tags: {'reply_language_mismatch': 249, 'no_final_block': 232, 'missing_expected_booking': 157, 'empty_final_text': 144, 'kind:unparsed_model_output': 138, 'invalid_train_id_format': 36, 'guessed_station_code': 19, 'unexpected_booking': 6}
- format_only (tool process and booking state correct, only the final-answer block failed): 198 items

## Cost

- tokens: input 2827875, output 80775, cached input 1700071
- items retried: 0; wall time 4149.0 s (sum of item times 4145.6 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '5a408ab55df5c1b5cf46533c368813b30bf9e4d8fc39263bf2a3338cfa3b895b', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
