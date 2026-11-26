# Run summary: local_deepseek_r1_8b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_deepseek_r1_8b_v3_new_20261125T224932Z.jsonl` (625 rows, sha256 4f0a7a40508c...)
- expected items 625, selected 625, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **13/625 (2.1%)** (not scored: 0)
- status: {'completed': 548, 'output_truncated': 77}
- final-answer parse ok: 539/625 (86.2%); process ok: 15/625 (2.4%); state ok: 395/625 (63.2%)
- tool calls ok: 0/0; top error codes: {}
- failure label families: {'process:missing_required_call': 915, 'status:expected_success_got_needs_clarification': 259, 'status:expected_cannot_complete_got_needs_clarification': 110, 'final_answer:missing_block': 79, 'run:output_truncated': 77, 'answer_value:wrong': 74, 'state:tatkal_bookings_mismatch': 50, 'state:meal_orders_mismatch': 45, 'state:complaints_mismatch': 45, 'state:bookings_mismatch': 35, 'final_answer:wrong_selected_train': 33, 'final_answer:booking_ids_invalid': 32, 'answer_value:missing': 31, 'state:cancellations_mismatch': 30, 'state:boarding_changes_mismatch': 25, 'status:expected_cannot_complete_got_success': 23, 'final_answer:wrong_selected_class': 18, 'final_answer:selected_train_invalid': 16, 'state:tdr_claims_mismatch': 15, 'state:waitlist_mismatch': 10, 'status:expected_success_got_cannot_complete': 9, 'final_answer:malformed_json': 6, 'answer_value:invalid': 4, 'status:expected_needs_clarification_got_cannot_complete': 1, 'final_answer:missing_keys': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **13/625 (2.1%)**; strict: 13/625 (2.1%)
- items that needed a format recovery: 58; by rule {'notes_defaulted': 32, 'trailing_text_ignored': 20, 'requested_passengers_shape': 3, 'untagged_json': 2, 'booking_ids_shape': 2, 'integer_form': 1}; by language {'mr': 9, 'gu': 11, 'hinglish': 13, 'hi': 15, 'en': 10}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 0/610 (0.0%); no-tool tasks: 13/15 (86.7%)
- baseline 'always needs_clarification, no tool calls' passes 13 of 200 tasks (6.5%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 2/125 (1.6%) | 84 | 3 | 79 | {'missing_required_call': 51, 'output_truncated': 40, 'missing_booking': 31, 'wrong_answer': 1, 'success': 2} |
| gu | 3/125 (2.4%) | 118 | 3 | 79 | {'missing_required_call': 76, 'missing_booking': 42, 'success': 3, 'output_truncated': 4} |
| hi | 3/125 (2.4%) | 125 | 3 | 79 | {'missing_required_call': 76, 'missing_booking': 46, 'success': 3} |
| hinglish | 3/125 (2.4%) | 121 | 3 | 79 | {'missing_required_call': 76, 'missing_booking': 46, 'success': 3} |
| mr | 2/125 (1.6%) | 91 | 3 | 79 | {'output_truncated': 33, 'missing_required_call': 52, 'missing_booking': 38, 'success': 2} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 135 | 0 | 118 | 0 | 0 |
| clarification | 10 | 9 | 10 | 10 | 10 |
| constraint | 130 | 0 | 113 | 0 | 50 |
| invalid_input | 35 | 4 | 30 | 5 | 35 |
| recovery | 105 | 0 | 91 | 0 | 100 |
| sequential | 120 | 0 | 101 | 0 | 110 |
| single_tool | 90 | 0 | 76 | 0 | 90 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T100 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T101 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T102 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T103 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T104 | 0/5 | 4 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T105 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T106 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T107 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T108 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T109 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T110 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T111 | 0/5 | 3 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T112 | 0/5 | 4 | 0 | 0 | {'missing_booking': 5} |
| T113 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T114 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T115 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T116 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T117 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T118 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T119 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T120 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T121 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T122 | 0/5 | 4 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T123 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T124 | 0/5 | 4 | 0 | 0 | {'missing_booking': 5} |
| T125 | 0/5 | 3 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T126 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T127 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T128 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T129 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T130 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T131 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T132 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T133 | 0/5 | 3 | 0 | 0 | {'output_truncated': 2, 'missing_booking': 3} |
| T134 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T135 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T136 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T137 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T138 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T139 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T140 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T141 | 0/5 | 4 | 0 | 0 | {'missing_booking': 5} |
| T142 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T143 | 0/5 | 4 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T144 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T145 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T146 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T147 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T148 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T149 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T150 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T151 | 4/5 | 4 | 5 | 5 | {'success': 4, 'output_truncated': 1} |
| T152 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T153 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T154 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T155 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T156 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T157 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T158 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T159 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T160 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T161 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T162 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 5} |
| T163 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T164 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T165 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T166 | 0/5 | 3 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T167 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T168 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T169 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T170 | 0/5 | 4 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T171 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T172 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T173 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T174 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T175 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T176 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T177 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T178 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T179 | 0/5 | 2 | 0 | 0 | {'output_truncated': 3, 'missing_booking': 2} |
| T180 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T181 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T182 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T183 | 0/5 | 4 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T184 | 0/5 | 3 | 0 | 0 | {'missing_booking': 3, 'output_truncated': 2} |
| T185 | 0/5 | 4 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T186 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T187 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T188 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T189 | 5/5 | 5 | 5 | 5 | {'success': 5} |
| T190 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T191 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T192 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T193 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T194 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T195 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T196 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T197 | 0/5 | 4 | 0 | 0 | {'missing_booking': 4, 'output_truncated': 1} |
| T198 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T199 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T200 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T76 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T77 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T78 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T79 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T80 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T81 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T82 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T83 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T84 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T85 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T86 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T87 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T88 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T89 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T90 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T91 | 0/5 | 3 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T92 | 0/5 | 3 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T93 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T94 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T95 | 0/5 | 5 | 0 | 0 | {'missing_booking': 5} |
| T96 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T97 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T98 | 4/5 | 5 | 5 | 5 | {'wrong_answer': 1, 'success': 4} |
| T99 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 13, 'output_truncated': 77, 'missing_booking': 203, 'missing_required_call': 331, 'wrong_answer': 1}
- secondary tags: {'reply_language_mismatch': 334, 'missing_expected_booking': 230, 'no_final_block': 79, 'empty_final_text': 77}
- format_only (tool process and booking state correct, only the final-answer block failed): 0 items

## Cost

- tokens: input 775532, output 333142, cached input 729867
- items retried: 0; wall time 5953.6 s (sum of item times 5949.5 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '6995872bfe4c521a67b32da386cd21d5c6e819b6e0d62f79f64ec83be99f5763', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
