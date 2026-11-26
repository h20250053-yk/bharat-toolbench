# Run summary: local_llama32_3b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_llama32_3b_v3_new_20261125T224932Z.jsonl` (625 rows, sha256 fd464c6132c0...)
- expected items 625, selected 625, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **9/625 (1.4%)** (not scored: 0)
- status: {'completed': 597, 'output_truncated': 27, 'step_limit_exceeded': 1}
- final-answer parse ok: 96/625 (15.4%); process ok: 212/625 (33.9%); state ok: 450/625 (72.0%)
- tool calls ok: 343/719 (47.7%); top error codes: {'INVALID_STATION': 122, 'INVALID_TRAIN': 53, 'SOLD_OUT': 34, 'TATKAL_NOT_OPEN': 28, 'ALREADY_CANCELLED': 24, 'INVALID_CATEGORY': 14, 'INVALID_ARGUMENTS': 13, 'INVALID_PNR': 12, 'JOURNEY_STARTED': 10, 'TDR_WINDOW_CLOSED': 10}
- failure label families: {'process:missing_required_call': 578, 'final_answer:missing_block': 493, 'state:tatkal_bookings_mismatch': 46, 'state:meal_orders_mismatch': 45, 'status:expected_success_got_needs_clarification': 36, 'state:bookings_mismatch': 28, 'run:output_truncated': 27, 'state:boarding_changes_mismatch': 23, 'state:complaints_mismatch': 21, 'final_answer:missing_keys': 20, 'final_answer:malformed_json': 15, 'status:expected_cannot_complete_got_needs_clarification': 14, 'final_answer:booking_ids_do_not_match_state': 13, 'state:cancellations_mismatch': 12, 'state:waitlist_mismatch': 7, 'final_answer:wrong_selected_train': 5, 'final_answer:booking_ids_invalid': 4, 'status:expected_cannot_complete_got_success': 4, 'answer_value:wrong': 4, 'state:tdr_claims_mismatch': 4, 'final_answer:wrong_selected_class': 3, 'answer_value:missing': 3, 'final_answer:selected_train_invalid': 3, 'status:expected_success_got_cannot_complete': 2, 'process:prohibited_action': 1, 'final_answer:invalid_status': 1, 'final_answer:wrong_requested_passengers': 1, 'run:step_limit_exceeded': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **9/625 (1.4%)**; strict: 2/625 (0.3%)
- items that needed a format recovery: 120; by rule {'extra_args_dropped': 58, 'closing_tag_missing': 31, 'trailing_text_ignored': 30, 'requested_passengers_shape': 8, 'untagged_json': 8, 'booking_ids_shape': 7, 'integer_form': 2, 'closing_braces_appended': 1, 'key_spelling': 1}; by language {'gu': 32, 'en': 23, 'hinglish': 21, 'hi': 19, 'mr': 25}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 9/610 (1.5%); no-tool tasks: 0/15 (0.0%)
- baseline 'always needs_clarification, no tool calls' passes 13 of 200 tasks (6.5%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 2/125 (1.6%) | 10 | 55 | 96 | {'format_only': 53, 'unsafe_action': 4, 'missing_required_call': 26, 'missing_booking': 25, 'success': 2, 'tool_argument_error': 15} |
| gu | 5/125 (4.0%) | 35 | 34 | 87 | {'format_only': 22, 'unsafe_action': 3, 'missing_required_call': 32, 'wrong_answer': 5, 'success': 5, 'missing_booking': 27, 'output_truncated': 17, 'step_limit': 1, 'tool_argument_error': 13} |
| hi | 0/125 (0.0%) | 11 | 42 | 90 | {'format_only': 38, 'unsafe_action': 4, 'missing_required_call': 28, 'wrong_answer': 4, 'tool_argument_error': 20, 'missing_booking': 31} |
| hinglish | 1/125 (0.8%) | 18 | 42 | 91 | {'format_only': 40, 'unsafe_action': 6, 'missing_required_call': 31, 'wrong_answer': 1, 'tool_argument_error': 18, 'missing_booking': 28, 'success': 1} |
| mr | 1/125 (0.8%) | 22 | 39 | 86 | {'format_only': 31, 'unsafe_action': 5, 'missing_required_call': 27, 'output_truncated': 10, 'wrong_answer': 6, 'success': 1, 'missing_booking': 29, 'tool_argument_error': 16} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 135 | 1 | 22 | 43 | 46 |
| clarification | 10 | 0 | 0 | 10 | 10 |
| constraint | 130 | 4 | 41 | 22 | 60 |
| invalid_input | 35 | 2 | 3 | 25 | 35 |
| recovery | 105 | 1 | 14 | 39 | 100 |
| sequential | 120 | 0 | 10 | 20 | 110 |
| single_tool | 90 | 1 | 6 | 53 | 89 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T100 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'missing_required_call': 2} |
| T101 | 0/5 | 1 | 1 | 5 | {'format_only': 1, 'missing_required_call': 4} |
| T102 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 5} |
| T103 | 1/5 | 4 | 1 | 1 | {'success': 1, 'missing_booking': 4} |
| T104 | 0/5 | 1 | 1 | 1 | {'format_only': 1, 'missing_booking': 3, 'output_truncated': 1} |
| T105 | 0/5 | 2 | 1 | 5 | {'format_only': 1, 'missing_required_call': 4} |
| T106 | 0/5 | 1 | 1 | 5 | {'format_only': 1, 'missing_required_call': 4} |
| T107 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T108 | 0/5 | 3 | 0 | 0 | {'missing_booking': 4, 'unsafe_action': 1} |
| T109 | 0/5 | 2 | 0 | 5 | {'missing_required_call': 5} |
| T110 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T111 | 0/5 | 3 | 0 | 5 | {'missing_required_call': 5} |
| T112 | 0/5 | 2 | 0 | 1 | {'missing_required_call': 1, 'missing_booking': 4} |
| T113 | 0/5 | 1 | 0 | 0 | {'missing_booking': 5} |
| T114 | 0/5 | 1 | 1 | 5 | {'format_only': 1, 'missing_required_call': 4} |
| T115 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T116 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 3, 'output_truncated': 1, 'missing_required_call': 1} |
| T117 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 5} |
| T118 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 5} |
| T119 | 0/5 | 0 | 0 | 0 | {'missing_booking': 3, 'output_truncated': 2} |
| T120 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 2, 'tool_argument_error': 2, 'output_truncated': 1} |
| T121 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T122 | 0/5 | 4 | 1 | 3 | {'missing_booking': 1, 'unsafe_action': 1, 'format_only': 1, 'missing_required_call': 2} |
| T123 | 0/5 | 4 | 1 | 0 | {'unsafe_action': 5} |
| T124 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'step_limit': 1} |
| T125 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T126 | 1/5 | 1 | 5 | 5 | {'format_only': 4, 'success': 1} |
| T127 | 0/5 | 1 | 0 | 5 | {'missing_required_call': 4, 'tool_argument_error': 1} |
| T128 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'missing_required_call': 2} |
| T129 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T130 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 5} |
| T131 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T132 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T133 | 0/5 | 0 | 0 | 2 | {'missing_required_call': 2, 'missing_booking': 3} |
| T134 | 0/5 | 1 | 1 | 5 | {'format_only': 1, 'tool_argument_error': 3, 'output_truncated': 1} |
| T135 | 0/5 | 2 | 0 | 5 | {'tool_argument_error': 5} |
| T136 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T137 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T138 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T139 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T140 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'missing_required_call': 1} |
| T141 | 0/5 | 4 | 0 | 0 | {'unsafe_action': 5} |
| T142 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T143 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T144 | 0/5 | 1 | 0 | 0 | {'missing_booking': 5} |
| T145 | 0/5 | 0 | 3 | 5 | {'format_only': 3, 'tool_argument_error': 2} |
| T146 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T147 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T148 | 0/5 | 1 | 0 | 5 | {'missing_required_call': 5} |
| T149 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T150 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T151 | 0/5 | 0 | 5 | 5 | {'format_only': 4, 'output_truncated': 1} |
| T152 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T153 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T154 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T155 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T156 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T157 | 0/5 | 0 | 0 | 0 | {'missing_booking': 5} |
| T158 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'tool_argument_error': 3} |
| T159 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 2, 'tool_argument_error': 3} |
| T160 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T161 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T162 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T163 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T164 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T165 | 0/5 | 1 | 0 | 5 | {'missing_required_call': 5} |
| T166 | 0/5 | 1 | 0 | 5 | {'missing_required_call': 5} |
| T167 | 0/5 | 0 | 1 | 5 | {'format_only': 1, 'missing_required_call': 4} |
| T168 | 1/5 | 1 | 5 | 5 | {'format_only': 4, 'success': 1} |
| T169 | 0/5 | 1 | 5 | 5 | {'format_only': 4, 'wrong_answer': 1} |
| T170 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T171 | 0/5 | 1 | 1 | 1 | {'missing_booking': 3, 'unsafe_action': 1, 'format_only': 1} |
| T172 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T173 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T174 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T175 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 5} |
| T176 | 0/5 | 3 | 0 | 5 | {'missing_required_call': 5} |
| T177 | 0/5 | 1 | 2 | 5 | {'format_only': 1, 'missing_required_call': 3, 'wrong_answer': 1} |
| T178 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 5} |
| T179 | 0/5 | 1 | 0 | 0 | {'missing_booking': 5} |
| T180 | 2/5 | 2 | 4 | 5 | {'success': 2, 'format_only': 2, 'output_truncated': 1} |
| T181 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T182 | 0/5 | 2 | 5 | 5 | {'format_only': 3, 'wrong_answer': 2} |
| T183 | 0/5 | 0 | 3 | 3 | {'format_only': 3, 'missing_booking': 2} |
| T184 | 0/5 | 0 | 2 | 2 | {'format_only': 2, 'missing_booking': 3} |
| T185 | 0/5 | 0 | 2 | 2 | {'format_only': 2, 'missing_booking': 2, 'output_truncated': 1} |
| T186 | 0/5 | 0 | 3 | 3 | {'format_only': 3, 'missing_booking': 2} |
| T187 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T188 | 0/5 | 1 | 4 | 5 | {'format_only': 3, 'wrong_answer': 1, 'output_truncated': 1} |
| T189 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T190 | 0/5 | 0 | 0 | 3 | {'missing_required_call': 3, 'missing_booking': 2} |
| T191 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T192 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T193 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 5} |
| T194 | 0/5 | 1 | 5 | 5 | {'format_only': 4, 'wrong_answer': 1} |
| T195 | 0/5 | 3 | 0 | 1 | {'missing_required_call': 1, 'missing_booking': 4} |
| T196 | 0/5 | 2 | 0 | 5 | {'missing_required_call': 5} |
| T197 | 0/5 | 0 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T198 | 0/5 | 3 | 0 | 1 | {'tool_argument_error': 1, 'missing_booking': 3, 'output_truncated': 1} |
| T199 | 0/5 | 1 | 0 | 5 | {'missing_required_call': 5} |
| T200 | 0/5 | 3 | 0 | 0 | {'unsafe_action': 3, 'missing_booking': 2} |
| T76 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T77 | 0/5 | 0 | 4 | 4 | {'format_only': 4, 'unsafe_action': 1} |
| T78 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T79 | 0/5 | 0 | 0 | 0 | {'unsafe_action': 5} |
| T80 | 0/5 | 0 | 0 | 5 | {'missing_required_call': 5} |
| T81 | 0/5 | 1 | 5 | 5 | {'format_only': 4, 'wrong_answer': 1} |
| T82 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'output_truncated': 1} |
| T83 | 1/5 | 1 | 5 | 5 | {'format_only': 4, 'success': 1} |
| T84 | 0/5 | 4 | 3 | 3 | {'missing_booking': 2, 'wrong_answer': 3} |
| T85 | 1/5 | 1 | 4 | 5 | {'format_only': 3, 'success': 1, 'missing_required_call': 1} |
| T86 | 0/5 | 3 | 4 | 4 | {'format_only': 2, 'wrong_answer': 2, 'missing_booking': 1} |
| T87 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T88 | 0/5 | 0 | 4 | 5 | {'format_only': 4, 'output_truncated': 1} |
| T89 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T90 | 0/5 | 2 | 4 | 5 | {'format_only': 2, 'tool_argument_error': 1, 'wrong_answer': 2} |
| T91 | 0/5 | 0 | 2 | 5 | {'format_only': 2, 'missing_required_call': 3} |
| T92 | 0/5 | 0 | 1 | 5 | {'format_only': 1, 'tool_argument_error': 2, 'missing_required_call': 2} |
| T93 | 1/5 | 1 | 5 | 5 | {'format_only': 4, 'success': 1} |
| T94 | 1/5 | 1 | 5 | 5 | {'format_only': 4, 'success': 1} |
| T95 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T96 | 0/5 | 0 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T97 | 0/5 | 2 | 5 | 5 | {'format_only': 3, 'wrong_answer': 2} |
| T98 | 0/5 | 0 | 5 | 5 | {'format_only': 4, 'output_truncated': 1} |
| T99 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 9, 'output_truncated': 27, 'step_limit': 1, 'unsafe_action': 22, 'missing_booking': 140, 'tool_argument_error': 82, 'missing_required_call': 144, 'wrong_answer': 16, 'format_only': 184}
- secondary tags: {'no_final_block': 493, 'missing_expected_booking': 162, 'guessed_station_code': 119, 'reply_language_mismatch': 78, 'invalid_train_id_format': 46, 'empty_final_text': 28, 'unexpected_booking': 22, 'tool_call_as_text': 15, 'ungrounded_train_id': 5, 'parallel_dependent_calls': 2, 'unresolvable_station_name': 1}
- format_only (tool process and booking state correct, only the final-answer block failed): 184 items

## Cost

- tokens: input 2996689, output 110041, cached input 1755064
- items retried: 0; wall time 1446.4 s (sum of item times 1443.4 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': 'a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
