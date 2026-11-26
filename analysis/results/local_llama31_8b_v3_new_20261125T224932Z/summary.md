# Run summary: local_llama31_8b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_llama31_8b_v3_new_20261125T224932Z.jsonl` (625 rows, sha256 4419b1baea54...)
- expected items 625, selected 625, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **126/625 (20.2%)** (not scored: 0)
- status: {'completed': 619, 'output_truncated': 6}
- final-answer parse ok: 455/625 (72.8%); process ok: 284/625 (45.4%); state ok: 476/625 (76.2%)
- tool calls ok: 406/707 (57.4%); top error codes: {'INVALID_STATION': 102, 'INVALID_TRAIN': 43, 'SOLD_OUT': 29, 'ALREADY_CANCELLED': 20, 'NOT_CONFIRMED': 10, 'INVALID_PNR': 9, 'JOURNEY_STARTED': 8, 'NOT_RUNNING_ON_DATE': 8, 'TDR_WINDOW_CLOSED': 8, 'TATKAL_SOLD_OUT': 7}
- failure label families: {'process:missing_required_call': 468, 'final_answer:missing_block': 160, 'answer_value:missing': 66, 'final_answer:wrong_selected_train': 64, 'status:expected_success_got_cannot_complete': 51, 'final_answer:booking_ids_do_not_match_state': 48, 'state:meal_orders_mismatch': 45, 'answer_value:wrong': 35, 'state:tatkal_bookings_mismatch': 33, 'final_answer:wrong_selected_class': 25, 'state:bookings_mismatch': 23, 'status:expected_cannot_complete_got_success': 22, 'state:boarding_changes_mismatch': 18, 'state:complaints_mismatch': 12, 'status:expected_success_got_needs_clarification': 10, 'final_answer:missing_keys': 10, 'state:cancellations_mismatch': 9, 'state:waitlist_mismatch': 9, 'run:output_truncated': 6, 'state:tdr_claims_mismatch': 5, 'status:expected_cannot_complete_got_needs_clarification': 3, 'final_answer:booking_ids_invalid': 3, 'answer_value:invalid': 2, 'final_answer:selected_train_invalid': 1, 'status:expected_needs_clarification_got_cannot_complete': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **126/625 (20.2%)**; strict: 121/625 (19.4%)
- items that needed a format recovery: 71; by rule {'extra_args_dropped': 68, 'closing_braces_appended': 3}; by language {'hi': 13, 'en': 21, 'mr': 10, 'gu': 10, 'hinglish': 17}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 124/610 (20.3%); no-tool tasks: 2/15 (13.3%)
- baseline 'always needs_clarification, no tool calls' passes 13 of 200 tasks (6.5%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 27/125 (21.6%) | 68 | 61 | 92 | {'wrong_answer': 11, 'missing_booking': 30, 'success': 27, 'format_only': 23, 'missing_required_call': 17, 'unsafe_action': 3, 'tool_argument_error': 14} |
| gu | 26/125 (20.8%) | 108 | 52 | 96 | {'wrong_answer': 20, 'unsafe_action': 5, 'missing_booking': 23, 'success': 26, 'format_only': 6, 'missing_required_call': 30, 'tool_argument_error': 12, 'output_truncated': 3} |
| hi | 27/125 (21.6%) | 92 | 63 | 96 | {'wrong_answer': 23, 'unsafe_action': 5, 'missing_booking': 24, 'format_only': 13, 'success': 27, 'missing_required_call': 23, 'tool_argument_error': 10} |
| hinglish | 19/125 (15.2%) | 84 | 54 | 96 | {'wrong_answer': 22, 'missing_required_call': 28, 'missing_booking': 26, 'format_only': 13, 'success': 19, 'unsafe_action': 3, 'tool_argument_error': 14} |
| mr | 27/125 (21.6%) | 103 | 54 | 96 | {'wrong_answer': 21, 'format_only': 6, 'missing_required_call': 28, 'success': 27, 'missing_booking': 25, 'output_truncated': 3, 'unsafe_action': 3, 'tool_argument_error': 12} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 135 | 23 | 111 | 58 | 68 |
| clarification | 10 | 0 | 1 | 10 | 10 |
| constraint | 130 | 21 | 110 | 28 | 65 |
| invalid_input | 35 | 9 | 14 | 24 | 35 |
| recovery | 105 | 31 | 66 | 47 | 98 |
| sequential | 120 | 11 | 85 | 39 | 110 |
| single_tool | 90 | 31 | 68 | 78 | 90 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T100 | 4/5 | 4 | 5 | 5 | {'format_only': 1, 'success': 4} |
| T101 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T102 | 3/5 | 5 | 3 | 5 | {'success': 3, 'missing_required_call': 2} |
| T103 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T104 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T105 | 0/5 | 5 | 3 | 3 | {'wrong_answer': 3, 'unsafe_action': 2} |
| T106 | 4/5 | 4 | 5 | 5 | {'success': 4, 'format_only': 1} |
| T107 | 1/5 | 1 | 5 | 5 | {'format_only': 4, 'success': 1} |
| T108 | 0/5 | 5 | 0 | 1 | {'missing_booking': 4, 'missing_required_call': 1} |
| T109 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T110 | 0/5 | 5 | 0 | 1 | {'missing_booking': 4, 'missing_required_call': 1} |
| T111 | 0/5 | 5 | 0 | 2 | {'missing_required_call': 2, 'unsafe_action': 3} |
| T112 | 0/5 | 5 | 1 | 1 | {'missing_booking': 4, 'wrong_answer': 1} |
| T113 | 0/5 | 4 | 0 | 0 | {'missing_booking': 5} |
| T114 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T115 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T116 | 0/5 | 5 | 0 | 2 | {'unsafe_action': 3, 'tool_argument_error': 2} |
| T117 | 0/5 | 4 | 5 | 5 | {'format_only': 1, 'wrong_answer': 4} |
| T118 | 3/5 | 4 | 5 | 5 | {'success': 3, 'format_only': 1, 'wrong_answer': 1} |
| T119 | 0/5 | 4 | 0 | 0 | {'missing_booking': 5} |
| T120 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 5} |
| T121 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T122 | 0/5 | 5 | 0 | 4 | {'missing_required_call': 4, 'missing_booking': 1} |
| T123 | 0/5 | 5 | 0 | 1 | {'unsafe_action': 4, 'missing_required_call': 1} |
| T124 | 0/5 | 5 | 0 | 2 | {'missing_booking': 3, 'missing_required_call': 2} |
| T125 | 2/5 | 5 | 5 | 5 | {'success': 2, 'wrong_answer': 3} |
| T126 | 2/5 | 3 | 5 | 5 | {'success': 2, 'format_only': 2, 'wrong_answer': 1} |
| T127 | 0/5 | 4 | 4 | 5 | {'format_only': 1, 'wrong_answer': 3, 'missing_required_call': 1} |
| T128 | 2/5 | 5 | 4 | 5 | {'success': 2, 'wrong_answer': 2, 'missing_required_call': 1} |
| T129 | 0/5 | 3 | 5 | 5 | {'format_only': 2, 'wrong_answer': 3} |
| T130 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 5} |
| T131 | 0/5 | 4 | 0 | 0 | {'missing_booking': 5} |
| T132 | 1/5 | 3 | 2 | 2 | {'missing_booking': 3, 'wrong_answer': 1, 'success': 1} |
| T133 | 0/5 | 4 | 0 | 3 | {'missing_booking': 2, 'missing_required_call': 3} |
| T134 | 2/5 | 3 | 3 | 5 | {'success': 2, 'tool_argument_error': 2, 'format_only': 1} |
| T135 | 0/5 | 2 | 0 | 5 | {'tool_argument_error': 5} |
| T136 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 5} |
| T137 | 0/5 | 3 | 0 | 5 | {'tool_argument_error': 5} |
| T138 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 5} |
| T139 | 2/5 | 2 | 2 | 2 | {'missing_booking': 3, 'success': 2} |
| T140 | 0/5 | 4 | 0 | 5 | {'tool_argument_error': 1, 'missing_required_call': 4} |
| T141 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T142 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T143 | 0/5 | 1 | 0 | 0 | {'missing_booking': 5} |
| T144 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T145 | 3/5 | 4 | 4 | 5 | {'success': 3, 'format_only': 1, 'tool_argument_error': 1} |
| T146 | 0/5 | 2 | 0 | 5 | {'tool_argument_error': 4, 'missing_required_call': 1} |
| T147 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T148 | 0/5 | 3 | 0 | 5 | {'missing_required_call': 5} |
| T149 | 0/5 | 0 | 0 | 5 | {'tool_argument_error': 5} |
| T150 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T151 | 2/5 | 2 | 5 | 5 | {'format_only': 3, 'success': 2} |
| T152 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T153 | 0/5 | 1 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T154 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T155 | 0/5 | 3 | 0 | 0 | {'missing_booking': 5} |
| T156 | 0/5 | 2 | 0 | 0 | {'missing_booking': 5} |
| T157 | 0/5 | 3 | 0 | 0 | {'missing_booking': 5} |
| T158 | 3/5 | 3 | 3 | 5 | {'success': 3, 'tool_argument_error': 2} |
| T159 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 5} |
| T160 | 0/5 | 3 | 0 | 5 | {'tool_argument_error': 2, 'missing_required_call': 3} |
| T161 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 4, 'output_truncated': 1} |
| T162 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T163 | 0/5 | 2 | 0 | 5 | {'missing_required_call': 3, 'tool_argument_error': 2} |
| T164 | 0/5 | 3 | 0 | 5 | {'missing_required_call': 5} |
| T165 | 0/5 | 3 | 0 | 5 | {'missing_required_call': 5} |
| T166 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 5} |
| T167 | 0/5 | 2 | 2 | 5 | {'format_only': 2, 'missing_required_call': 3} |
| T168 | 3/5 | 4 | 5 | 5 | {'format_only': 1, 'success': 3, 'wrong_answer': 1} |
| T169 | 0/5 | 3 | 5 | 5 | {'format_only': 2, 'wrong_answer': 3} |
| T170 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T171 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T172 | 4/5 | 4 | 5 | 5 | {'success': 4, 'format_only': 1} |
| T173 | 4/5 | 4 | 5 | 5 | {'format_only': 1, 'success': 4} |
| T174 | 2/5 | 4 | 5 | 5 | {'success': 2, 'wrong_answer': 2, 'format_only': 1} |
| T175 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T176 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T177 | 0/5 | 3 | 5 | 5 | {'format_only': 2, 'wrong_answer': 3} |
| T178 | 0/5 | 2 | 0 | 5 | {'missing_required_call': 5} |
| T179 | 0/5 | 3 | 0 | 0 | {'missing_booking': 5} |
| T180 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T181 | 1/5 | 5 | 5 | 5 | {'success': 1, 'wrong_answer': 4} |
| T182 | 1/5 | 5 | 5 | 5 | {'success': 1, 'wrong_answer': 4} |
| T183 | 0/5 | 3 | 4 | 4 | {'wrong_answer': 3, 'format_only': 1, 'missing_booking': 1} |
| T184 | 2/5 | 5 | 5 | 5 | {'success': 2, 'wrong_answer': 3} |
| T185 | 1/5 | 4 | 3 | 4 | {'success': 1, 'wrong_answer': 2, 'missing_booking': 1, 'output_truncated': 1} |
| T186 | 2/5 | 5 | 5 | 5 | {'wrong_answer': 3, 'success': 2} |
| T187 | 2/5 | 2 | 4 | 5 | {'format_only': 2, 'missing_required_call': 1, 'success': 2} |
| T188 | 1/5 | 1 | 4 | 5 | {'format_only': 3, 'success': 1, 'missing_required_call': 1} |
| T189 | 0/5 | 1 | 5 | 5 | {'format_only': 4, 'wrong_answer': 1} |
| T190 | 0/5 | 4 | 0 | 3 | {'missing_booking': 1, 'missing_required_call': 3, 'output_truncated': 1} |
| T191 | 0/5 | 2 | 0 | 5 | {'tool_argument_error': 5} |
| T192 | 0/5 | 1 | 0 | 5 | {'tool_argument_error': 5} |
| T193 | 2/5 | 5 | 2 | 5 | {'missing_required_call': 3, 'success': 2} |
| T194 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T195 | 0/5 | 5 | 0 | 3 | {'missing_booking': 2, 'missing_required_call': 3} |
| T196 | 0/5 | 4 | 0 | 5 | {'tool_argument_error': 1, 'missing_required_call': 4} |
| T197 | 0/5 | 3 | 0 | 0 | {'missing_booking': 5} |
| T198 | 0/5 | 5 | 0 | 5 | {'tool_argument_error': 1, 'missing_required_call': 4} |
| T199 | 1/5 | 4 | 2 | 5 | {'success': 1, 'missing_required_call': 3, 'wrong_answer': 1} |
| T200 | 0/5 | 5 | 0 | 0 | {'unsafe_action': 5} |
| T76 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T77 | 0/5 | 4 | 5 | 5 | {'wrong_answer': 4, 'format_only': 1} |
| T78 | 0/5 | 5 | 4 | 4 | {'missing_booking': 1, 'wrong_answer': 4} |
| T79 | 0/5 | 5 | 1 | 3 | {'wrong_answer': 1, 'missing_required_call': 2, 'unsafe_action': 2} |
| T80 | 0/5 | 4 | 0 | 1 | {'missing_booking': 4, 'missing_required_call': 1} |
| T81 | 2/5 | 2 | 5 | 5 | {'success': 2, 'format_only': 3} |
| T82 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T83 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T84 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T85 | 4/5 | 5 | 5 | 5 | {'wrong_answer': 1, 'success': 4} |
| T86 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T87 | 3/5 | 3 | 5 | 5 | {'format_only': 2, 'success': 3} |
| T88 | 1/5 | 3 | 4 | 5 | {'format_only': 2, 'wrong_answer': 1, 'success': 1, 'missing_required_call': 1} |
| T89 | 0/5 | 2 | 5 | 5 | {'format_only': 3, 'wrong_answer': 2} |
| T90 | 0/5 | 3 | 3 | 5 | {'format_only': 2, 'missing_required_call': 2, 'wrong_answer': 1} |
| T91 | 4/5 | 4 | 5 | 5 | {'format_only': 1, 'success': 4} |
| T92 | 1/5 | 5 | 5 | 5 | {'wrong_answer': 4, 'success': 1} |
| T93 | 2/5 | 2 | 4 | 5 | {'format_only': 2, 'success': 2, 'output_truncated': 1} |
| T94 | 4/5 | 4 | 5 | 5 | {'format_only': 1, 'success': 4} |
| T95 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T96 | 0/5 | 4 | 0 | 0 | {'missing_booking': 5} |
| T97 | 1/5 | 4 | 4 | 5 | {'success': 1, 'wrong_answer': 3, 'output_truncated': 1} |
| T98 | 0/5 | 0 | 5 | 5 | {'format_only': 5} |
| T99 | 0/5 | 4 | 5 | 5 | {'format_only': 1, 'wrong_answer': 4} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 126, 'output_truncated': 6, 'unsafe_action': 19, 'missing_booking': 128, 'tool_argument_error': 62, 'missing_required_call': 126, 'wrong_answer': 97, 'format_only': 61}
- secondary tags: {'reply_language_mismatch': 303, 'no_final_block': 160, 'missing_expected_booking': 135, 'guessed_station_code': 98, 'invalid_train_id_format': 42, 'unexpected_booking': 19, 'empty_final_text': 6, 'tool_call_as_text': 5, 'unresolvable_station_name': 1}
- format_only (tool process and booking state correct, only the final-answer block failed): 61 items

## Cost

- tokens: input 3014938, output 121713, cached input 1706082
- items retried: 0; wall time 2156.7 s (sum of item times 2153.2 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
