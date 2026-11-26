# Run summary: local_gpt_oss_20b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_gpt_oss_20b_v3_new_20261125T224932Z.jsonl` (625 rows, sha256 c3145740e3d3...)
- expected items 625, selected 625, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **345/625 (55.2%)** (not scored: 0)
- status: {'completed': 623, 'step_limit_exceeded': 2}
- final-answer parse ok: 574/625 (91.8%); process ok: 477/625 (76.3%); state ok: 564/625 (90.2%)
- tool calls ok: 1024/1153 (88.8%); top error codes: {'INVALID_STATION': 18, 'TDR_WINDOW_CLOSED': 12, 'ALREADY_CANCELLED': 8, 'NOT_EN_ROUTE': 8, 'STATION_NOT_FOUND': 8, 'JOURNEY_STARTED': 7, 'NOT_RUNNING_ON_DATE': 6, 'NOT_A_STOP': 6, 'PNR_NOT_FOUND': 5, 'CONCESSION_NOT_AVAILABLE': 5}
- failure label families: {'process:missing_required_call': 188, 'final_answer:missing_block': 51, 'final_answer:wrong_selected_train': 41, 'answer_value:missing': 40, 'status:expected_cannot_complete_got_needs_clarification': 37, 'status:expected_success_got_needs_clarification': 36, 'answer_value:wrong': 29, 'final_answer:wrong_selected_class': 16, 'state:tatkal_bookings_mismatch': 16, 'state:meal_orders_mismatch': 16, 'status:expected_success_got_cannot_complete': 15, 'state:cancellations_mismatch': 12, 'state:complaints_mismatch': 11, 'status:expected_cannot_complete_got_success': 7, 'state:bookings_mismatch': 6, 'state:boarding_changes_mismatch': 5, 'answer_value:invalid': 5, 'state:waitlist_mismatch': 2, 'state:tdr_claims_mismatch': 2, 'run:step_limit_exceeded': 2, 'process:tool_not_allowed': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **345/625 (55.2%)**; strict: 345/625 (55.2%)
- items that needed a format recovery: 0; by rule {}; by language {}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 334/610 (54.8%); no-tool tasks: 11/15 (73.3%)
- baseline 'always needs_clarification, no tool calls' passes 13 of 200 tasks (6.5%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 75/125 (60.0%) | 110 | 106 | 118 | {'success': 75, 'wrong_answer': 24, 'missing_booking': 6, 'format_only': 7, 'missing_required_call': 12, 'step_limit': 1} |
| gu | 64/125 (51.2%) | 110 | 92 | 110 | {'success': 64, 'wrong_answer': 21, 'missing_booking': 12, 'format_only': 6, 'missing_required_call': 18, 'unsafe_action': 3, 'tool_argument_error': 1} |
| hi | 72/125 (57.6%) | 118 | 96 | 110 | {'success': 72, 'wrong_answer': 21, 'missing_booking': 12, 'unsafe_action': 3, 'missing_required_call': 13, 'format_only': 3, 'tool_argument_error': 1} |
| hinglish | 69/125 (55.2%) | 118 | 92 | 113 | {'success': 69, 'wrong_answer': 19, 'missing_booking': 11, 'format_only': 4, 'missing_required_call': 21, 'step_limit': 1} |
| mr | 65/125 (52.0%) | 118 | 91 | 113 | {'success': 65, 'wrong_answer': 23, 'missing_required_call': 20, 'missing_booking': 12, 'format_only': 3, 'unsafe_action': 1, 'tool_argument_error': 1} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 135 | 69 | 125 | 98 | 98 |
| clarification | 10 | 7 | 7 | 10 | 10 |
| constraint | 130 | 98 | 127 | 105 | 115 |
| invalid_input | 35 | 17 | 25 | 31 | 34 |
| recovery | 105 | 46 | 89 | 69 | 102 |
| sequential | 120 | 50 | 113 | 80 | 115 |
| single_tool | 90 | 58 | 88 | 84 | 90 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T100 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T101 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T102 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T103 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T104 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T105 | 0/5 | 5 | 3 | 4 | {'wrong_answer': 3, 'missing_required_call': 1, 'unsafe_action': 1} |
| T106 | 1/5 | 3 | 3 | 5 | {'success': 1, 'format_only': 2, 'missing_required_call': 2} |
| T107 | 2/5 | 4 | 5 | 5 | {'success': 2, 'format_only': 1, 'wrong_answer': 2} |
| T108 | 4/5 | 5 | 4 | 4 | {'success': 4, 'missing_booking': 1} |
| T109 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T110 | 4/5 | 5 | 4 | 4 | {'success': 4, 'missing_booking': 1} |
| T111 | 3/5 | 5 | 3 | 4 | {'success': 3, 'missing_required_call': 1, 'unsafe_action': 1} |
| T112 | 4/5 | 5 | 4 | 4 | {'success': 4, 'missing_booking': 1} |
| T113 | 4/5 | 5 | 4 | 4 | {'success': 4, 'missing_booking': 1} |
| T114 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T115 | 3/5 | 4 | 3 | 3 | {'success': 3, 'missing_booking': 2} |
| T116 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T117 | 3/5 | 5 | 5 | 5 | {'success': 3, 'wrong_answer': 2} |
| T118 | 2/5 | 5 | 2 | 5 | {'success': 2, 'missing_required_call': 3} |
| T119 | 1/5 | 2 | 1 | 1 | {'success': 1, 'missing_booking': 4} |
| T120 | 3/5 | 5 | 4 | 5 | {'success': 3, 'missing_required_call': 1, 'wrong_answer': 1} |
| T121 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T122 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T123 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T124 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T125 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T126 | 2/5 | 3 | 5 | 5 | {'wrong_answer': 1, 'success': 2, 'format_only': 2} |
| T127 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T128 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T129 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T130 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T131 | 2/5 | 5 | 2 | 2 | {'success': 2, 'missing_booking': 3} |
| T132 | 2/5 | 5 | 4 | 4 | {'success': 2, 'missing_booking': 1, 'wrong_answer': 2} |
| T133 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T134 | 3/5 | 4 | 3 | 5 | {'success': 3, 'missing_required_call': 2} |
| T135 | 1/5 | 4 | 4 | 5 | {'format_only': 1, 'wrong_answer': 2, 'missing_required_call': 1, 'success': 1} |
| T136 | 1/5 | 4 | 1 | 5 | {'success': 1, 'missing_required_call': 4} |
| T137 | 0/5 | 3 | 1 | 5 | {'format_only': 1, 'missing_required_call': 4} |
| T138 | 1/5 | 5 | 1 | 5 | {'missing_required_call': 4, 'success': 1} |
| T139 | 4/5 | 5 | 4 | 4 | {'success': 4, 'missing_booking': 1} |
| T140 | 0/5 | 5 | 1 | 5 | {'wrong_answer': 1, 'missing_required_call': 2, 'tool_argument_error': 2} |
| T141 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T142 | 2/5 | 4 | 4 | 4 | {'wrong_answer': 2, 'success': 2, 'missing_booking': 1} |
| T143 | 2/5 | 5 | 4 | 4 | {'wrong_answer': 2, 'success': 2, 'missing_booking': 1} |
| T144 | 0/5 | 2 | 2 | 2 | {'wrong_answer': 2, 'missing_booking': 3} |
| T145 | 2/5 | 3 | 3 | 5 | {'success': 2, 'wrong_answer': 1, 'missing_required_call': 2} |
| T146 | 0/5 | 4 | 2 | 5 | {'missing_required_call': 3, 'wrong_answer': 2} |
| T147 | 0/5 | 4 | 2 | 5 | {'wrong_answer': 1, 'missing_required_call': 3, 'format_only': 1} |
| T148 | 3/5 | 5 | 3 | 5 | {'success': 3, 'missing_required_call': 2} |
| T149 | 1/5 | 3 | 4 | 5 | {'format_only': 2, 'wrong_answer': 1, 'success': 1, 'missing_required_call': 1} |
| T150 | 1/5 | 3 | 3 | 5 | {'format_only': 2, 'success': 1, 'missing_required_call': 2} |
| T151 | 4/5 | 5 | 5 | 4 | {'success': 4, 'unsafe_action': 1} |
| T152 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T153 | 3/5 | 5 | 3 | 3 | {'missing_booking': 2, 'success': 3} |
| T154 | 0/5 | 5 | 4 | 4 | {'wrong_answer': 4, 'missing_booking': 1} |
| T155 | 3/5 | 3 | 3 | 3 | {'missing_booking': 2, 'success': 3} |
| T156 | 3/5 | 5 | 3 | 3 | {'success': 3, 'missing_booking': 2} |
| T157 | 1/5 | 3 | 2 | 2 | {'missing_booking': 3, 'wrong_answer': 1, 'success': 1} |
| T158 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T159 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T160 | 0/5 | 4 | 3 | 5 | {'missing_required_call': 2, 'wrong_answer': 3} |
| T161 | 1/5 | 3 | 3 | 5 | {'success': 1, 'wrong_answer': 2, 'missing_required_call': 2} |
| T162 | 0/5 | 1 | 5 | 5 | {'format_only': 4, 'wrong_answer': 1} |
| T163 | 3/5 | 3 | 3 | 5 | {'missing_required_call': 2, 'success': 3} |
| T164 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T165 | 1/5 | 5 | 1 | 5 | {'missing_required_call': 4, 'success': 1} |
| T166 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T167 | 2/5 | 5 | 5 | 5 | {'success': 2, 'wrong_answer': 3} |
| T168 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T169 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T170 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T171 | 4/5 | 4 | 4 | 4 | {'missing_booking': 1, 'success': 4} |
| T172 | 3/5 | 4 | 5 | 5 | {'success': 3, 'format_only': 1, 'wrong_answer': 1} |
| T173 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T174 | 4/5 | 4 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T175 | 3/5 | 5 | 5 | 5 | {'success': 3, 'wrong_answer': 2} |
| T176 | 2/5 | 5 | 2 | 5 | {'missing_required_call': 3, 'success': 2} |
| T177 | 1/5 | 5 | 5 | 5 | {'wrong_answer': 4, 'success': 1} |
| T178 | 1/5 | 4 | 1 | 4 | {'missing_required_call': 3, 'success': 1, 'unsafe_action': 1} |
| T179 | 3/5 | 5 | 3 | 3 | {'success': 3, 'missing_booking': 2} |
| T180 | 2/5 | 3 | 2 | 3 | {'step_limit': 2, 'success': 2, 'unsafe_action': 1} |
| T181 | 2/5 | 5 | 3 | 3 | {'wrong_answer': 1, 'success': 2, 'missing_booking': 2} |
| T182 | 2/5 | 5 | 4 | 4 | {'wrong_answer': 2, 'unsafe_action': 1, 'success': 2} |
| T183 | 1/5 | 5 | 1 | 1 | {'success': 1, 'missing_booking': 4} |
| T184 | 2/5 | 5 | 4 | 4 | {'success': 2, 'wrong_answer': 2, 'unsafe_action': 1} |
| T185 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T186 | 2/5 | 5 | 5 | 5 | {'wrong_answer': 3, 'success': 2} |
| T187 | 0/5 | 4 | 3 | 5 | {'wrong_answer': 2, 'missing_required_call': 2, 'format_only': 1} |
| T188 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T189 | 4/5 | 4 | 5 | 5 | {'success': 4, 'format_only': 1} |
| T190 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T191 | 0/5 | 5 | 4 | 5 | {'wrong_answer': 4, 'missing_required_call': 1} |
| T192 | 1/5 | 5 | 1 | 5 | {'missing_required_call': 3, 'success': 1, 'tool_argument_error': 1} |
| T193 | 2/5 | 5 | 4 | 5 | {'success': 2, 'missing_required_call': 1, 'wrong_answer': 2} |
| T194 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T195 | 4/5 | 5 | 4 | 4 | {'success': 4, 'missing_booking': 1} |
| T196 | 3/5 | 5 | 3 | 5 | {'success': 3, 'missing_required_call': 2} |
| T197 | 3/5 | 5 | 3 | 3 | {'success': 3, 'missing_booking': 2} |
| T198 | 2/5 | 5 | 2 | 2 | {'success': 2, 'missing_booking': 3} |
| T199 | 0/5 | 5 | 4 | 5 | {'wrong_answer': 4, 'missing_required_call': 1} |
| T200 | 4/5 | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 4} |
| T76 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T77 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T78 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T79 | 3/5 | 5 | 5 | 5 | {'success': 3, 'wrong_answer': 2} |
| T80 | 0/5 | 5 | 0 | 1 | {'missing_booking': 4, 'missing_required_call': 1} |
| T81 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T82 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T83 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T84 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T85 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T86 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T87 | 4/5 | 4 | 5 | 5 | {'success': 4, 'format_only': 1} |
| T88 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T89 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T90 | 3/5 | 5 | 5 | 5 | {'wrong_answer': 2, 'success': 3} |
| T91 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T92 | 1/5 | 5 | 5 | 5 | {'wrong_answer': 4, 'success': 1} |
| T93 | 4/5 | 4 | 5 | 5 | {'format_only': 1, 'success': 4} |
| T94 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T95 | 2/5 | 5 | 2 | 2 | {'missing_booking': 3, 'success': 2} |
| T96 | 4/5 | 5 | 4 | 4 | {'success': 4, 'missing_booking': 1} |
| T97 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T98 | 3/5 | 3 | 5 | 5 | {'format_only': 2, 'success': 3} |
| T99 | 2/5 | 5 | 5 | 5 | {'wrong_answer': 3, 'success': 2} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 345, 'step_limit': 2, 'unsafe_action': 7, 'missing_booking': 53, 'tool_argument_error': 3, 'missing_required_call': 84, 'wrong_answer': 108, 'format_only': 23}
- secondary tags: {'reply_language_mismatch': 382, 'missing_expected_booking': 57, 'no_final_block': 51, 'guessed_station_code': 17, 'unexpected_booking': 6, 'unresolvable_station_name': 6, 'invalid_train_id_format': 4, 'empty_final_text': 2, 'retried': 1}
- format_only (tool process and booking state correct, only the final-answer block failed): 23 items

## Cost

- tokens: input 4974139, output 138496, cached input 4822408
- items retried: 1; wall time 1686.8 s (sum of item times 1683.3 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': 'f38aa0c53da5f8c49d08c43a99df24ff53167fe68e24664a7777288e7656fdfe', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
