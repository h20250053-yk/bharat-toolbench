# Run summary: local_deepseek_r1_8b

Official numbers come from the unchanged scorer (`task_success`). `primary_failure` / tags are DIAGNOSTIC (analysis/FAILURE_TAXONOMY.md).

## Integrity

- inputs: `runs/local_deepseek_r1_8b_full_20261124T105853Z.jsonl` (375 rows, sha256 214a380688fe...)
- expected items 375, selected 375, missing 0, unexpected 0, items with >1 row 0, complete=True

## Official result

- task_success: **24/375 (6.4%)** (not scored: 0)
- status: {'completed': 291, 'output_truncated': 84}
- final-answer parse ok: 287/375 (76.5%); process ok: 55/375 (14.7%); state ok: 255/375 (68.0%)
- tool calls ok: 0/0; top error codes: {}
- failure label families: {'process:missing_required_call': 1080, 'state:bookings_mismatch': 120, 'status:expected_success_got_needs_clarification': 85, 'final_answer:missing_block': 85, 'run:output_truncated': 84, 'final_answer:booking_ids_invalid': 65, 'final_answer:selected_train_invalid': 59, 'status:expected_cannot_complete_got_needs_clarification': 33, 'status:expected_cannot_complete_got_success': 23, 'answer_value:wrong': 20, 'final_answer:booking_ids_do_not_match_state': 15, 'final_answer:wrong_selected_class': 14, 'status:expected_needs_clarification_got_success': 12, 'final_answer:wrong_selected_train': 10, 'value:departure=20': 4, 'value:arrival=06': 4, 'value:fare_inr=1035_not_stated': 3, 'value:fare_inr=450_not_stated': 3, 'value:fare_inr=1460_not_stated': 3, 'value:arrival=11': 3, 'final_answer:wrong_requested_passengers': 3, 'value:arrival=10': 3, 'value:seats_available=35_not_stated': 3, "value:selected_train_ids=['BTB127', 'BTB116', 'BTB124']_not_stated": 3, "value:departure_times=['18": 3, 'value:fare_inr=3565_not_stated': 2, 'value:stop_arrival_time=00': 2, 'final_answer:malformed_json': 2, 'value:segment_distance_km=838_not_stated': 2, 'value:departure=14': 2, 'answer_value:missing': 2, 'value:arrival_date=2026-10-10_not_stated': 2, 'status:expected_success_got_cannot_complete': 2, 'value:departure=23': 2, 'value:resolved_date=2026-10-10_not_stated': 2, 'value:fare_inr=1540_not_stated': 1, 'value:arrival=04': 1, 'final_answer:missing_keys': 1, 'final_answer:wrong_selected_trains': 1, 'value:fare_difference_inr=650_not_stated': 1, 'value:resolved_date=2026-10-07_not_stated': 1, 'value:departure=21': 1, 'value:fare_inr=1800_not_stated': 1, 'value:fare_inr=305_not_stated': 1, 'value:fare_inr=2495_not_stated': 1, 'value:total_fare_inr=3550_not_stated': 1}

## Lenient (headline) and strict (sensitivity)

- lenient task_success: **24/375 (6.4%)**; strict: 22/375 (5.9%)
- items that needed a format recovery: 20; by rule {'trailing_text_ignored': 20}; by language {'mr': 3, 'gu': 10, 'hinglish': 3, 'hi': 4}
- reply discarded by the serving layer (`unparsed_model_output`, transport category): {'total': 0, 'by_language': {}}

## Read against the null baseline (audit I-10)

- tool-required tasks: 0/320 (0.0%); no-tool tasks: 24/55 (43.6%)
- baseline 'always needs_clarification, no tool calls' passes 9 of 75 tasks (12.0%)

## By language

| language | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| en | 1/75 (1.3%) | 10 | 11 | 51 | {'missing_required_call': 8, 'output_truncated': 65, 'success': 1, 'wrong_answer': 1} |
| gu | 6/75 (8.0%) | 72 | 11 | 51 | {'missing_required_call': 38, 'output_truncated': 2, 'missing_booking': 24, 'success': 6, 'wrong_answer': 5} |
| hi | 6/75 (8.0%) | 72 | 11 | 51 | {'missing_required_call': 40, 'missing_booking': 22, 'success': 6, 'wrong_answer': 4, 'output_truncated': 3} |
| hinglish | 5/75 (6.7%) | 72 | 11 | 51 | {'missing_required_call': 39, 'missing_booking': 24, 'wrong_answer': 6, 'success': 5, 'output_truncated': 1} |
| mr | 6/75 (8.0%) | 61 | 11 | 51 | {'missing_required_call': 29, 'output_truncated': 13, 'success': 6, 'missing_booking': 22, 'wrong_answer': 5} |

## By task category

| category | items | success | parse ok | process ok | state ok |
|---|---|---|---|---|---|
| booking | 75 | 0 | 56 | 0 | 0 |
| clarification | 45 | 21 | 35 | 40 | 45 |
| constraint | 90 | 0 | 66 | 0 | 70 |
| invalid_input | 30 | 3 | 24 | 15 | 30 |
| recovery | 40 | 0 | 31 | 0 | 20 |
| sequential | 65 | 0 | 51 | 0 | 60 |
| single_tool | 30 | 0 | 24 | 0 | 30 |

## By task

| task | success | parse ok | process ok | state ok | primary failures |
|---|---|---|---|---|---|
| T01 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T02 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T03 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T04 | 0/5 | 3 | 0 | 0 | {'output_truncated': 2, 'missing_booking': 3} |
| T05 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T06 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T07 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T08 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T09 | 3/5 | 4 | 5 | 5 | {'output_truncated': 1, 'wrong_answer': 1, 'success': 3} |
| T10 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T11 | 0/5 | 3 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T12 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T13 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T14 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T15 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T16 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 5} |
| T17 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T18 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T19 | 1/5 | 4 | 5 | 5 | {'output_truncated': 1, 'wrong_answer': 3, 'success': 1} |
| T20 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T21 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T22 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T23 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T24 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T25 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T26 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T27 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T28 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 5} |
| T29 | 0/5 | 4 | 5 | 5 | {'output_truncated': 1, 'wrong_answer': 4} |
| T30 | 1/5 | 5 | 5 | 5 | {'success': 1, 'wrong_answer': 4} |
| T31 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T32 | 0/5 | 3 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T33 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T34 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T35 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T36 | 2/5 | 3 | 5 | 5 | {'output_truncated': 2, 'success': 2, 'wrong_answer': 1} |
| T37 | 2/5 | 4 | 5 | 5 | {'output_truncated': 1, 'wrong_answer': 2, 'success': 2} |
| T38 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T39 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T40 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T41 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T42 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T43 | 0/5 | 3 | 0 | 0 | {'output_truncated': 2, 'missing_booking': 3} |
| T44 | 0/5 | 5 | 0 | 5 | {'missing_required_call': 5} |
| T45 | 2/5 | 5 | 5 | 5 | {'wrong_answer': 3, 'success': 2} |
| T46 | 3/5 | 4 | 5 | 5 | {'output_truncated': 1, 'wrong_answer': 1, 'success': 3} |
| T47 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T48 | 0/5 | 3 | 0 | 0 | {'output_truncated': 2, 'missing_booking': 3} |
| T49 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T50 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T51 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T52 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T53 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T54 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T55 | 0/5 | 4 | 0 | 5 | {'missing_required_call': 4, 'output_truncated': 1} |
| T56 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T57 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T58 | 0/5 | 3 | 0 | 0 | {'output_truncated': 2, 'missing_booking': 3} |
| T59 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T60 | 0/5 | 1 | 0 | 5 | {'output_truncated': 4, 'missing_required_call': 1} |
| T61 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T62 | 0/5 | 3 | 0 | 5 | {'output_truncated': 2, 'missing_required_call': 3} |
| T63 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T64 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T65 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T66 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T67 | 4/5 | 4 | 5 | 5 | {'output_truncated': 1, 'success': 4} |
| T68 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T69 | 3/5 | 4 | 5 | 5 | {'output_truncated': 1, 'success': 3, 'wrong_answer': 1} |
| T70 | 0/5 | 4 | 0 | 5 | {'output_truncated': 1, 'missing_required_call': 4} |
| T71 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T72 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T73 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |
| T74 | 3/5 | 4 | 5 | 5 | {'output_truncated': 1, 'success': 3, 'wrong_answer': 1} |
| T75 | 0/5 | 4 | 0 | 0 | {'output_truncated': 1, 'missing_booking': 4} |

## Diagnostic classification (not an official score)

- primary_failure: {'success': 24, 'output_truncated': 84, 'missing_booking': 92, 'missing_required_call': 154, 'wrong_answer': 21}
- secondary tags: {'reply_language_mismatch': 219, 'missing_expected_booking': 120, 'no_final_block': 85, 'empty_final_text': 84, 'repetition_or_truncation': 1}
- format_only (tool process and booking state correct, only the final-answer block failed): 0 items

## Cost

- tokens: input 297843, output 207231, cached input 263457
- items retried: 0; wall time 4562.2 s (sum of item times 4561.7 s)
- decoding settings: [{'max_tokens': 2048, 'model_digest': '6995872bfe4c521a67b32da386cd21d5c6e819b6e0d62f79f64ec83be99f5763', 'num_ctx': 16384, 'seed': 42, 'temperature': 0}]
