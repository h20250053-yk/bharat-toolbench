# Run summary: local_qwen25_14b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_qwen25_14b_v3_new_20261125T224932Z.jsonl` (625 rows, sha256 c594a044e011...)
- expected items 625, selected 625, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **141/625 (22.6%)** (not scored: 0)
- status: {'completed': 615, 'output_truncated': 9, 'step_limit_exceeded': 1}
- final-answer parse ok: 420/625 (67.2%); process ok: 291/625 (46.6%); state ok: 458/625 (73.3%)
- tool calls ok: 568/949 (59.9%); top error codes: {'INVALID_TRAIN': 146, 'INVALID_STATION': 49, 'SOLD_OUT': 27, 'DUPLICATE_BOOKING': 19, 'TATKAL_SOLD_OUT': 15, 'TDR_WINDOW_CLOSED': 13, 'ALREADY_CANCELLED': 11, 'INVALID_PNR': 10, 'STATION_NOT_FOUND': 10, 'INVALID_ARGUMENTS': 10}
- failure label families: {'process:missing_required_call': 455, 'final_answer:missing_keys': 178, 'final_answer:booking_ids_invalid': 51, 'final_answer:wrong_selected_train': 50, 'answer_value:wrong': 48, 'status:expected_cannot_complete_got_success': 47, 'status:expected_success_got_cannot_complete': 46, 'state:meal_orders_mismatch': 41, 'answer_value:missing': 32, 'state:tatkal_bookings_mismatch': 28, 'final_answer:missing_block': 27, 'state:bookings_mismatch': 24, 'state:complaints_mismatch': 24, 'final_answer:booking_ids_do_not_match_state': 23, 'state:cancellations_mismatch': 19, 'state:boarding_changes_mismatch': 16, 'final_answer:wrong_selected_class': 15, 'state:tdr_claims_mismatch': 15, 'status:expected_success_got_needs_clarification': 12, 'state:waitlist_mismatch': 10, 'run:output_truncated': 9, 'status:expected_needs_clarification_got_cannot_complete': 3, 'status:expected_cannot_complete_got_needs_clarification': 3, 'process:prohibited_action': 2, 'run:step_limit_exceeded': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **141/625 (22.6%)**; strict: 139/625 (22.2%)
- items that needed a format recovery: 6; by rule {'extra_args_dropped': 6}; by language {'hinglish': 4, 'en': 1, 'hi': 1}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 138/610 (22.6%); no-tool tasks: 3/15 (20.0%)
- baseline 'always needs_clarification, no tool calls' passes 13 of 200 tasks (6.5%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 32/125 (25.6%) | 81 | 62 | 101 | {'missing_required_call': 40, 'missing_booking': 18, 'unsafe_action': 6, 'wrong_answer': 11, 'success': 32, 'format_only': 13, 'step_limit': 1, 'tool_argument_error': 4} |
| gu | 26/125 (20.8%) | 87 | 59 | 92 | {'wrong_answer': 14, 'missing_booking': 29, 'missing_required_call': 19, 'success': 26, 'format_only': 18, 'unsafe_action': 4, 'output_truncated': 4, 'tool_argument_error': 11} |
| hi | 31/125 (24.8%) | 88 | 61 | 94 | {'wrong_answer': 12, 'missing_required_call': 25, 'success': 31, 'missing_booking': 23, 'format_only': 14, 'unsafe_action': 7, 'tool_argument_error': 12, 'output_truncated': 1} |
| hinglish | 30/125 (24.0%) | 88 | 57 | 82 | {'wrong_answer': 11, 'missing_booking': 36, 'unsafe_action': 7, 'success': 30, 'missing_required_call': 25, 'format_only': 12, 'tool_argument_error': 4} |
| mr | 22/125 (17.6%) | 76 | 52 | 89 | {'wrong_answer': 13, 'format_only': 16, 'missing_booking': 29, 'unsafe_action': 5, 'success': 22, 'missing_required_call': 27, 'output_truncated': 4, 'tool_argument_error': 9} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 135 | 17 | 76 | 39 | 43 |
| clarification | 10 | 3 | 6 | 10 | 10 |
| constraint | 130 | 27 | 109 | 58 | 74 |
| invalid_input | 35 | 14 | 27 | 25 | 34 |
| recovery | 105 | 30 | 66 | 48 | 103 |
| sequential | 120 | 26 | 83 | 52 | 104 |
| single_tool | 90 | 24 | 53 | 59 | 90 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T100 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T101 | 4/5 | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 4} |
| T102 | 3/5 | 5 | 3 | 5 | {'missing_required_call': 2, 'success': 3} |
| T103 | 1/5 | 5 | 1 | 1 | {'success': 1, 'missing_booking': 4} |
| T104 | 3/5 | 5 | 3 | 3 | {'success': 3, 'missing_booking': 2} |
| T105 | 0/5 | 4 | 2 | 4 | {'step_limit': 1, 'unsafe_action': 1, 'missing_required_call': 2, 'wrong_answer': 1} |
| T106 | 0/5 | 5 | 1 | 4 | {'unsafe_action': 1, 'missing_required_call': 4} |
| T107 | 2/5 | 3 | 2 | 5 | {'missing_required_call': 3, 'success': 2} |
| T108 | 3/5 | 4 | 4 | 3 | {'success': 3, 'unsafe_action': 1, 'missing_booking': 1} |
| T109 | 2/5 | 5 | 2 | 5 | {'success': 2, 'missing_required_call': 3} |
| T110 | 4/5 | 5 | 4 | 4 | {'success': 4, 'missing_booking': 1} |
| T111 | 2/5 | 5 | 3 | 4 | {'success': 2, 'unsafe_action': 1, 'missing_required_call': 2} |
| T112 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T113 | 1/5 | 5 | 2 | 1 | {'success': 1, 'unsafe_action': 4} |
| T114 | 2/5 | 4 | 3 | 5 | {'missing_required_call': 2, 'wrong_answer': 1, 'success': 2} |
| T115 | 3/5 | 5 | 3 | 3 | {'success': 3, 'missing_booking': 2} |
| T116 | 0/5 | 5 | 3 | 2 | {'unsafe_action': 3, 'missing_required_call': 2} |
| T117 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T118 | 2/5 | 4 | 3 | 5 | {'wrong_answer': 1, 'missing_required_call': 1, 'success': 2, 'output_truncated': 1} |
| T119 | 1/5 | 5 | 1 | 1 | {'success': 1, 'missing_booking': 4} |
| T120 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 1, 'tool_argument_error': 4} |
| T121 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T122 | 1/5 | 5 | 1 | 1 | {'success': 1, 'missing_booking': 4} |
| T123 | 2/5 | 5 | 2 | 5 | {'success': 2, 'missing_required_call': 3} |
| T124 | 2/5 | 5 | 2 | 2 | {'success': 2, 'missing_booking': 3} |
| T125 | 1/5 | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 1, 'wrong_answer': 3} |
| T126 | 1/5 | 5 | 4 | 5 | {'missing_required_call': 1, 'wrong_answer': 3, 'success': 1} |
| T127 | 2/5 | 5 | 4 | 5 | {'wrong_answer': 2, 'missing_required_call': 1, 'success': 2} |
| T128 | 4/5 | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 4} |
| T129 | 3/5 | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 3, 'wrong_answer': 1} |
| T130 | 3/5 | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 3, 'wrong_answer': 1} |
| T131 | 0/5 | 3 | 1 | 1 | {'format_only': 1, 'missing_booking': 4} |
| T132 | 0/5 | 4 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T133 | 0/5 | 2 | 0 | 4 | {'tool_argument_error': 3, 'missing_booking': 1, 'output_truncated': 1} |
| T134 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T135 | 3/5 | 5 | 3 | 5 | {'missing_required_call': 2, 'success': 3} |
| T136 | 1/5 | 2 | 1 | 5 | {'success': 1, 'missing_required_call': 4} |
| T137 | 3/5 | 5 | 3 | 5 | {'success': 3, 'missing_required_call': 2} |
| T138 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T139 | 1/5 | 4 | 1 | 1 | {'missing_booking': 4, 'success': 1} |
| T140 | 0/5 | 3 | 0 | 5 | {'missing_required_call': 3, 'tool_argument_error': 2} |
| T141 | 0/5 | 1 | 2 | 3 | {'format_only': 2, 'missing_booking': 2, 'missing_required_call': 1} |
| T142 | 0/5 | 1 | 1 | 1 | {'missing_booking': 4, 'wrong_answer': 1} |
| T143 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T144 | 0/5 | 2 | 3 | 3 | {'wrong_answer': 2, 'missing_booking': 2, 'format_only': 1} |
| T145 | 1/5 | 2 | 2 | 5 | {'missing_required_call': 2, 'success': 1, 'format_only': 1, 'tool_argument_error': 1} |
| T146 | 2/5 | 3 | 3 | 5 | {'success': 2, 'missing_required_call': 1, 'format_only': 1, 'tool_argument_error': 1} |
| T147 | 2/5 | 3 | 2 | 5 | {'success': 2, 'missing_required_call': 1, 'output_truncated': 1, 'tool_argument_error': 1} |
| T148 | 1/5 | 2 | 2 | 5 | {'missing_required_call': 3, 'format_only': 1, 'success': 1} |
| T149 | 1/5 | 2 | 2 | 5 | {'missing_required_call': 2, 'success': 1, 'tool_argument_error': 1, 'format_only': 1} |
| T150 | 0/5 | 1 | 2 | 5 | {'format_only': 2, 'tool_argument_error': 2, 'output_truncated': 1} |
| T151 | 0/5 | 1 | 5 | 4 | {'unsafe_action': 1, 'format_only': 3, 'output_truncated': 1} |
| T152 | 0/5 | 5 | 0 | 0 | {'unsafe_action': 4, 'missing_booking': 1} |
| T153 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T154 | 0/5 | 3 | 1 | 1 | {'format_only': 1, 'missing_booking': 4} |
| T155 | 0/5 | 3 | 0 | 0 | {'missing_booking': 5} |
| T156 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T157 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T158 | 1/5 | 1 | 1 | 5 | {'missing_required_call': 4, 'success': 1} |
| T159 | 0/5 | 0 | 2 | 5 | {'missing_required_call': 1, 'format_only': 2, 'tool_argument_error': 2} |
| T160 | 0/5 | 3 | 2 | 5 | {'wrong_answer': 2, 'missing_required_call': 3} |
| T161 | 0/5 | 4 | 1 | 5 | {'format_only': 1, 'tool_argument_error': 4} |
| T162 | 2/5 | 4 | 3 | 5 | {'wrong_answer': 1, 'success': 2, 'tool_argument_error': 1, 'missing_required_call': 1} |
| T163 | 0/5 | 3 | 0 | 5 | {'tool_argument_error': 3, 'missing_required_call': 2} |
| T164 | 0/5 | 0 | 3 | 5 | {'missing_required_call': 2, 'format_only': 3} |
| T165 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'missing_required_call': 2, 'tool_argument_error': 1} |
| T166 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 5} |
| T167 | 0/5 | 0 | 1 | 5 | {'missing_required_call': 4, 'format_only': 1} |
| T168 | 0/5 | 0 | 4 | 5 | {'missing_required_call': 1, 'format_only': 4} |
| T169 | 0/5 | 1 | 2 | 5 | {'format_only': 2, 'missing_required_call': 3} |
| T170 | 0/5 | 4 | 2 | 2 | {'missing_booking': 2, 'output_truncated': 1, 'wrong_answer': 2} |
| T171 | 0/5 | 4 | 2 | 1 | {'missing_booking': 3, 'unsafe_action': 1, 'wrong_answer': 1} |
| T172 | 1/5 | 4 | 1 | 5 | {'missing_required_call': 4, 'success': 1} |
| T173 | 2/5 | 5 | 2 | 5 | {'missing_required_call': 3, 'success': 2} |
| T174 | 3/5 | 5 | 3 | 5 | {'missing_required_call': 2, 'success': 3} |
| T175 | 0/5 | 5 | 0 | 3 | {'missing_required_call': 1, 'unsafe_action': 2, 'tool_argument_error': 2} |
| T176 | 4/5 | 5 | 4 | 5 | {'success': 4, 'tool_argument_error': 1} |
| T177 | 0/5 | 0 | 4 | 5 | {'missing_required_call': 1, 'format_only': 4} |
| T178 | 0/5 | 4 | 0 | 1 | {'tool_argument_error': 1, 'unsafe_action': 4} |
| T179 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T180 | 0/5 | 5 | 2 | 2 | {'wrong_answer': 2, 'missing_booking': 3} |
| T181 | 0/5 | 0 | 2 | 2 | {'missing_booking': 3, 'format_only': 2} |
| T182 | 0/5 | 0 | 3 | 3 | {'format_only': 3, 'missing_booking': 2} |
| T183 | 0/5 | 1 | 1 | 1 | {'missing_booking': 4, 'format_only': 1} |
| T184 | 0/5 | 0 | 3 | 3 | {'format_only': 3, 'missing_booking': 2} |
| T185 | 0/5 | 1 | 0 | 0 | {'missing_booking': 5} |
| T186 | 0/5 | 1 | 0 | 0 | {'missing_booking': 5} |
| T187 | 1/5 | 2 | 3 | 5 | {'success': 1, 'missing_required_call': 2, 'format_only': 2} |
| T188 | 1/5 | 1 | 3 | 5 | {'missing_required_call': 2, 'success': 1, 'format_only': 2} |
| T189 | 0/5 | 2 | 5 | 5 | {'wrong_answer': 2, 'format_only': 3} |
| T190 | 0/5 | 0 | 2 | 4 | {'format_only': 2, 'missing_booking': 1, 'missing_required_call': 2} |
| T191 | 0/5 | 5 | 1 | 5 | {'tool_argument_error': 4, 'wrong_answer': 1} |
| T192 | 1/5 | 4 | 1 | 5 | {'success': 1, 'tool_argument_error': 2, 'missing_required_call': 2} |
| T193 | 3/5 | 5 | 3 | 5 | {'missing_required_call': 2, 'success': 3} |
| T194 | 0/5 | 4 | 3 | 5 | {'missing_required_call': 2, 'wrong_answer': 3} |
| T195 | 2/5 | 4 | 2 | 2 | {'success': 2, 'missing_booking': 2, 'output_truncated': 1} |
| T196 | 0/5 | 5 | 2 | 5 | {'wrong_answer': 2, 'tool_argument_error': 3} |
| T197 | 3/5 | 4 | 3 | 3 | {'success': 3, 'missing_booking': 2} |
| T198 | 1/5 | 5 | 1 | 2 | {'missing_booking': 3, 'success': 1, 'tool_argument_error': 1} |
| T199 | 3/5 | 5 | 3 | 5 | {'missing_required_call': 2, 'success': 3} |
| T200 | 1/5 | 5 | 1 | 2 | {'success': 1, 'missing_booking': 3, 'missing_required_call': 1} |
| T76 | 0/5 | 5 | 4 | 5 | {'missing_required_call': 1, 'wrong_answer': 4} |
| T77 | 0/5 | 2 | 3 | 5 | {'missing_required_call': 2, 'wrong_answer': 2, 'format_only': 1} |
| T78 | 0/5 | 3 | 2 | 2 | {'missing_booking': 3, 'wrong_answer': 2} |
| T79 | 1/5 | 3 | 4 | 2 | {'unsafe_action': 3, 'success': 1, 'wrong_answer': 1} |
| T80 | 0/5 | 4 | 3 | 3 | {'wrong_answer': 3, 'missing_booking': 2} |
| T81 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T82 | 1/5 | 4 | 1 | 5 | {'missing_required_call': 4, 'success': 1} |
| T83 | 1/5 | 1 | 1 | 5 | {'missing_required_call': 4, 'success': 1} |
| T84 | 0/5 | 5 | 1 | 1 | {'wrong_answer': 1, 'missing_booking': 4} |
| T85 | 1/5 | 5 | 1 | 5 | {'missing_required_call': 4, 'success': 1} |
| T86 | 1/5 | 5 | 1 | 1 | {'missing_booking': 4, 'success': 1} |
| T87 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T88 | 0/5 | 0 | 4 | 5 | {'missing_required_call': 1, 'format_only': 4} |
| T89 | 0/5 | 3 | 4 | 5 | {'missing_required_call': 1, 'wrong_answer': 3, 'format_only': 1} |
| T90 | 0/5 | 1 | 5 | 5 | {'format_only': 4, 'wrong_answer': 1} |
| T91 | 3/5 | 5 | 3 | 5 | {'missing_required_call': 2, 'success': 3} |
| T92 | 2/5 | 5 | 4 | 5 | {'success': 2, 'wrong_answer': 2, 'missing_required_call': 1} |
| T93 | 2/5 | 4 | 4 | 5 | {'missing_required_call': 1, 'wrong_answer': 1, 'success': 2, 'format_only': 1} |
| T94 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T95 | 2/5 | 5 | 2 | 2 | {'success': 2, 'missing_booking': 3} |
| T96 | 2/5 | 5 | 2 | 2 | {'success': 2, 'missing_booking': 3} |
| T97 | 0/5 | 4 | 4 | 2 | {'unsafe_action': 3, 'output_truncated': 1, 'wrong_answer': 1} |
| T98 | 3/5 | 4 | 5 | 5 | {'success': 3, 'wrong_answer': 1, 'format_only': 1} |
| T99 | 0/5 | 1 | 1 | 1 | {'missing_booking': 4, 'wrong_answer': 1} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 141, 'output_truncated': 9, 'step_limit': 1, 'unsafe_action': 29, 'missing_booking': 135, 'tool_argument_error': 40, 'missing_required_call': 136, 'wrong_answer': 61, 'format_only': 73}
- secondary tags: {'reply_language_mismatch': 344, 'missing_expected_booking': 142, 'invalid_train_id_format': 84, 'guessed_station_code': 44, 'unexpected_booking': 29, 'no_final_block': 27, 'tool_call_as_text': 11, 'empty_final_text': 9, 'unresolvable_station_name': 6, 'retried': 1}
- format_only (tool process and booking state correct, only the final-answer block failed): 73 items

## Cost

- tokens: input 3846315, output 225288, cached input 3699108
- items retried: 1; wall time 5458.1 s (sum of item times 5454.7 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
