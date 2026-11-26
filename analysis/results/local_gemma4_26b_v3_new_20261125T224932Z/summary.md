# Run summary: local_gemma4_26b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_gemma4_26b_v3_new_20261125T224932Z.jsonl` (625 rows, sha256 01563fa3b4e2...)
- expected items 625, selected 625, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **420/625 (67.2%)** (not scored: 0)
- status: {'completed': 623, 'malformed_output': 2}
- final-answer parse ok: 618/625 (98.9%); process ok: 545/625 (87.2%); state ok: 598/625 (95.7%)
- tool calls ok: 1321/1415 (93.4%); top error codes: {'TDR_WINDOW_CLOSED': 15, 'JOURNEY_STARTED': 10, 'INVALID_STATION': 10, 'NOT_EN_ROUTE': 9, 'NOT_A_STOP': 9, 'CONCESSION_NOT_AVAILABLE': 5, 'MEAL_NOT_SERVED_AT_THIS_TIME': 5, 'TDR_NOT_ELIGIBLE': 5, 'NOT_RUNNING_ON_DATE': 4, 'NO_BERTHS_IN_CLASS': 4}
- failure label families: {'process:missing_required_call': 84, 'final_answer:booking_ids_do_not_match_state': 71, 'final_answer:wrong_selected_train': 42, 'answer_value:missing': 36, 'status:expected_cannot_complete_got_success': 25, 'state:complaints_mismatch': 24, 'final_answer:wrong_selected_class': 22, 'answer_value:wrong': 14, 'status:expected_success_got_needs_clarification': 11, 'status:expected_success_got_cannot_complete': 7, 'final_answer:missing_block': 7, 'final_answer:booking_ids_invalid': 6, 'status:expected_cannot_complete_got_needs_clarification': 3, 'answer_value:invalid': 3, 'run:malformed_output': 2, 'state:meal_orders_mismatch': 1, 'state:tdr_claims_mismatch': 1, 'state:bookings_mismatch': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **420/625 (67.2%)**; strict: 420/625 (67.2%)
- items that needed a format recovery: 0; by rule {}; by language {}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 2, 'by_language': {'mr': 1, 'gu': 1}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 407/610 (66.7%); no-tool tasks: 13/15 (86.7%)
- baseline 'always needs_clarification, no tool calls' passes 13 of 200 tasks (6.5%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 81/125 (64.8%) | 123 | 108 | 118 | {'wrong_answer': 25, 'missing_required_call': 10, 'success': 81, 'format_only': 2, 'missing_booking': 7} |
| gu | 85/125 (68.0%) | 123 | 108 | 121 | {'wrong_answer': 22, 'missing_required_call': 13, 'success': 85, 'format_only': 1, 'missing_booking': 3, 'malformed_model_output': 1} |
| hi | 92/125 (73.6%) | 125 | 116 | 122 | {'wrong_answer': 24, 'missing_required_call': 6, 'success': 92, 'unsafe_action': 1, 'missing_booking': 2} |
| hinglish | 76/125 (60.8%) | 123 | 106 | 120 | {'missing_required_call': 14, 'wrong_answer': 28, 'success': 76, 'format_only': 2, 'missing_booking': 5} |
| mr | 86/125 (68.8%) | 124 | 107 | 117 | {'wrong_answer': 21, 'missing_required_call': 9, 'success': 86, 'malformed_model_output': 1, 'missing_booking': 7, 'unsafe_action': 1} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 135 | 75 | 135 | 113 | 113 |
| clarification | 10 | 8 | 8 | 10 | 10 |
| constraint | 130 | 106 | 129 | 126 | 127 |
| invalid_input | 35 | 23 | 32 | 29 | 35 |
| recovery | 105 | 81 | 104 | 82 | 105 |
| sequential | 120 | 81 | 120 | 115 | 118 |
| single_tool | 90 | 46 | 90 | 70 | 90 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T100 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T101 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T102 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T103 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T104 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T105 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T106 | 4/5 | 4 | 4 | 5 | {'success': 4, 'malformed_model_output': 1} |
| T107 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T108 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T109 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T110 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T111 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T112 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T113 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T114 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T115 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T116 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T117 | 4/5 | 5 | 5 | 5 | {'success': 4, 'wrong_answer': 1} |
| T118 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T119 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T120 | 3/5 | 5 | 5 | 5 | {'success': 3, 'wrong_answer': 2} |
| T121 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T122 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T123 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T124 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T125 | 3/5 | 5 | 3 | 5 | {'success': 3, 'missing_required_call': 2} |
| T126 | 1/5 | 2 | 4 | 5 | {'format_only': 3, 'success': 1, 'missing_required_call': 1} |
| T127 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T128 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T129 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T130 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T131 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T132 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T133 | 1/5 | 5 | 5 | 5 | {'success': 1, 'wrong_answer': 4} |
| T134 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T135 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T136 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T137 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T138 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T139 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T140 | 3/5 | 5 | 5 | 5 | {'success': 3, 'wrong_answer': 2} |
| T141 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T142 | 4/5 | 5 | 5 | 5 | {'wrong_answer': 1, 'success': 4} |
| T143 | 3/5 | 5 | 5 | 5 | {'wrong_answer': 2, 'success': 3} |
| T144 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T145 | 4/5 | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 4} |
| T146 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T147 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T148 | 3/5 | 5 | 3 | 5 | {'missing_required_call': 2, 'success': 3} |
| T149 | 4/5 | 5 | 4 | 5 | {'missing_required_call': 1, 'success': 4} |
| T150 | 3/5 | 5 | 3 | 5 | {'missing_required_call': 2, 'success': 3} |
| T151 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T152 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T153 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T154 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T155 | 4/5 | 5 | 4 | 4 | {'missing_booking': 1, 'success': 4} |
| T156 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T157 | 2/5 | 5 | 5 | 5 | {'wrong_answer': 3, 'success': 2} |
| T158 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T159 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T160 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T161 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T162 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T163 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T164 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T165 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T166 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T167 | 2/5 | 5 | 5 | 5 | {'success': 2, 'wrong_answer': 3} |
| T168 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T169 | 0/5 | 5 | 3 | 5 | {'wrong_answer': 3, 'missing_required_call': 2} |
| T170 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T171 | 2/5 | 5 | 5 | 5 | {'wrong_answer': 3, 'success': 2} |
| T172 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T173 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T174 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T175 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T176 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T177 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T178 | 0/5 | 5 | 2 | 4 | {'wrong_answer': 2, 'unsafe_action': 1, 'missing_required_call': 2} |
| T179 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T180 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T181 | 2/5 | 5 | 2 | 2 | {'missing_booking': 3, 'success': 2} |
| T182 | 2/5 | 5 | 3 | 3 | {'missing_booking': 2, 'wrong_answer': 1, 'success': 2} |
| T183 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T184 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T185 | 0/5 | 5 | 2 | 2 | {'missing_booking': 3, 'wrong_answer': 2} |
| T186 | 1/5 | 5 | 1 | 1 | {'missing_booking': 4, 'success': 1} |
| T187 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T188 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T189 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T190 | 3/5 | 4 | 3 | 3 | {'success': 3, 'missing_booking': 1, 'malformed_model_output': 1} |
| T191 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T192 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T193 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T194 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T195 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T196 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T197 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T198 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T199 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T200 | 4/5 | 5 | 4 | 4 | {'success': 4, 'unsafe_action': 1} |
| T76 | 0/5 | 5 | 4 | 5 | {'wrong_answer': 4, 'missing_required_call': 1} |
| T77 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T78 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T79 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T80 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |
| T81 | 1/5 | 5 | 1 | 5 | {'missing_required_call': 4, 'success': 1} |
| T82 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T83 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T84 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T85 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T86 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T87 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T88 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T89 | 0/5 | 5 | 4 | 5 | {'wrong_answer': 4, 'missing_required_call': 1} |
| T90 | 3/5 | 5 | 5 | 5 | {'wrong_answer': 2, 'success': 3} |
| T91 | 4/5 | 5 | 4 | 5 | {'success': 4, 'missing_required_call': 1} |
| T92 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T93 | 2/5 | 5 | 5 | 5 | {'success': 2, 'wrong_answer': 3} |
| T94 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T95 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T96 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T97 | 4/5 | 5 | 5 | 5 | {'wrong_answer': 1, 'success': 4} |
| T98 | 3/5 | 3 | 5 | 5 | {'format_only': 2, 'success': 3} |
| T99 | 0/5 | 5 | 5 | 5 | {'wrong_answer': 5} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 420, 'malformed_model_output': 2, 'unsafe_action': 2, 'missing_booking': 24, 'missing_required_call': 52, 'wrong_answer': 120, 'format_only': 5}
- secondary tags: {'reply_language_mismatch': 365, 'missing_expected_booking': 26, 'guessed_station_code': 8, 'no_final_block': 7, 'empty_final_text': 2, 'kind:unparsed_model_output': 2, 'unresolvable_station_name': 2, 'unexpected_booking': 2}
- format_only (tool process and booking state correct, only the final-answer block failed): 5 items

## Cost

- tokens: input 6640871, output 141822, cached input 6393240
- items retried: 0; wall time 1537.7 s (sum of item times 1533.9 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '001e5dafc3c77684c2307ebc6ab8e336e10c9b18eca52acf547d72fc83c3ca8c', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
