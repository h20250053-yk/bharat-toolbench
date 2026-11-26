# Progress log: Benchmark 3.0 run 20261125T224932Z (v3_new, T76-T200, 8 local Ollama models)

Run timestamp: 20261125T224932Z (tmux session `bench`, started 2026-11-25 22:49 UTC).
Stage 1 = T01-T75, 6 tools (2.1.0 runs); stage 2 = T76-T100, 12 tools; stage 3 = T101-T200, 20 tools. Success = lenient scorer, %.
Language gap = English minus the mean of Hinglish/Hindi/Marathi/Gujarati on the same task (pp, 95% bootstrap interval).

## MORNING SUMMARY (written 2026-11-26 ~06:10 UTC, after the run finished)

**Status: all 8 models finished, all 625/625 items each, 0 unresolved.** One run, timestamp **20261125T224932Z**, 22:49 -> 06:01 UTC (7 h 12 min). No stall, no dead session, no bench2 needed, no model skipped. full_phase.py resumed Qwen2.5-3B twice on its own; no other resumes. Each model's run files are committed separately, and the final report is committed together with this log.

### Success per stage (lenient %, strict = lenient unless shown; 95% Wilson intervals in RESULTS_V3.md)

| model | 6 tools (T01-T75) | 12 tools (T76-T100) | 20 tools (T101-T200) | all 200 | S2-S1 | S3-S1 |
|---|---|---|---|---|---|---|
| Gemma-4-26B-A4B | 76.3 | 57.6 | 69.6 | **70.6** | -18.7 * | -6.7 * |
| gpt-oss-20B | 56.8 | 72.8 | 50.8 | 55.8 | +16.0 * | -6.0 |
| Qwen2.5-14B | 26.9 (25.9) | 24.8 (24.0) | 22.0 (21.8) | 24.2 | -2.1 | -4.9 |
| Llama-3.1-8B | 11.2 | 32.0 (31.2) | 17.2 (16.4) | 16.8 | +20.8 * | +6.0 * |
| Mistral-Small-3.2-24B ‡ | 5.1 | 24.8 | 9.2 | 9.6 | +19.7 * | +4.1 * |
| DeepSeek-R1-8B § | 6.9 (6.1) | 3.2 | 1.8 | 3.9 | -3.7 | -5.1 * |
| Llama-3.2-3B | 7.7 (4.0) | 3.2 (0.8) | 1.0 (0.2) | 3.8 | -4.5 | -6.7 * |
| Qwen2.5-3B | 3.5 | 0.0 | 0.8 | 1.7 | -3.5 * | -2.7 * |

\* = interval excludes zero. ‡ = 22% of v3 rows (61% of 6-tool rows) were discarded by Ollama's tool-call parser. § = never calls a tool. Do-nothing baseline: 10/75, 1/25, 2/100 tasks.

### Main findings: 6 vs 12 vs 20 tools

1. **More tools do not hurt in one uniform way.** With 20 tools vs 6, 5 models drop, clearly so for Gemma, Llama-3.2, DeepSeek and Qwen-3B (-3 to -7 pp); the drops for gpt-oss and Qwen-14B include zero. Llama-3.1-8B and Mistral gain. The ranking is stable at the top: Gemma > gpt-oss > Qwen-14B > Llama-3.1-8B, with the rest near the floor.
2. **The 12-tool stage swings both ways** (Llama-3.1 +21, gpt-oss +16, Mistral +20, Gemma -19). It has only 25 tasks, mostly single PNR/refund/waitlist lookups, so it reflects task mix more than toolset size. The difficulty table (section 2) is the fairer comparison.
3. **Where larger toolsets bite (tool-use metrics, section 4): choosing the first tool, not filling arguments.** With 20 tools, first call right falls for the strong models (Gemma 67 -> 40%, gpt-oss 66 -> 49%), and Qwen-14B and gpt-oss call tools less (Qwen-14B uses tools 84 -> 64%). Argument accuracy stays high (Gemma about 100%, gpt-oss 97%). check_tatkal_availability is over-called by almost every model (up to 55/425 items where it is not needed).
4. **Weakest services with 20 tools:** Platform & live, Meals and Complaints (Gemma 26% on Complaints, because raise_complaint is called in only 21/55 items that need it). Strongest: Tatkal and Berths.

### Language view (section 8)

- **Pooled over all 8 models**: with 6 tools the languages are flat (23.5-25.5%). With 12 tools English is lowest (23.5% vs 25.5-30%). **With 20 tools English is highest: 24.2% vs Hinglish 19.4, Marathi 20.2, Gujarati 20.9, Hindi 23.0.** A small English advantage appears only with the largest toolset.
- **English minus the 4 Indian languages, per model** (S1 / S2 / S3; ✓ = interval excludes zero):
  - Gemma +3.0 / -7.0 / -2.0, stays the same (all include zero; close to language-neutral, Hindi best in all stages).
  - gpt-oss -1.0 / -11.0 / **+10.2 ✓**, grows (the change +11.2 includes zero).
  - Qwen-14B +8.0 / +4.0 / +3.8, shrinks slightly (all include zero; Marathi lowest in every stage).
  - Llama-3.1-8B -5.7 / -15.0 / +6.0, **grows (change +11.7 ✓)**.
  - Mistral +0.3 / -1.0 / **+6.0 ✓**, grows (change includes zero).
  - DeepSeek -7.0 ✓ / -4.0 / +0.2 (no tool use, not meaningful).
  - Llama-3.2 -1.3 / -4.0 ✓ / +1.2, same.
  - Qwen-3B +2.3 / 0 / +1.5, same (floor).
- **Best / worst language per stage (pooled):** S1 Hindi 25.5 / Marathi 23.5; S2 Hindi 30.0 / English 23.5; S3 English 24.2 / Hinglish 19.4.
- **Station-name (word-ending) errors** mostly disappear with more tools. With 6 tools they are an Indic-script problem, above all Marathi (Qwen-3B mr 44/75, Llama-3.1 mr 13 and gu 10, Qwen-14B mr 8, gpt-oss gu 4 and mr 3). With 12 tools they are essentially 0. With 20 tools they are 0-5 per language (Marathi most often). The common station error with 20 tools is a different one: **sending a city name or made-up code instead of a resolved code** ("name, not code"). It is language-independent and shrinks with model size (Qwen-3B 24-31/100, Gemma 0-4). Since commit 4cfe68f the report splits these causes and does not count deliberate traps.
- **Models vs languages: yes, the gap between MODELS is still far bigger than the gap between LANGUAGES.** With 20 tools the models span 0.8-69.6% (69 pp), while the pooled languages span 19.4-24.2% (4.8 pp). Within single models the language spread is at most 15 pp (Gemma, gpt-oss).

### Problems and how I handled them

- **No run problems:** no stalls, no Ollama restarts needed, `bench` ended normally.
- **DeepSeek-R1-8B never calls a tool** (0% in every stage, also in 2.1.0). It writes answers with made-up tool results. The tool schema was sent and Ollama reports the tools capability, so this is model behaviour; left as is. Its scores are effectively a do-nothing baseline.
- **Mistral-Small-3.2-24B: Ollama's tool-call parser discarded 138/625 replies** (61% of its 2.1.0 stage-1 rows). These count as failures, and its stage gains are mostly this discard rate changing. Gemma had 2 such rows.
- **Qwen2.5-3B: 24% output_truncated** (runaway Indic-script text up to max_tokens=2048).
- **Report flags (added after the run, on request):** § = never calls a tool (DeepSeek-R1-8B), ‡ = more than 50% malformed in a stage (Mistral-Small-3.2-24B, 6-tool stage, 61%). Both stay in the per-model tables, marked. Pooled language numbers (RESULTS_V3.md sections 3 and 8) are now given three ways: all 8 models; without flagged model-stages; only models with no flag (without DeepSeek and Mistral). The English advantage with 20 tools holds in all three: +3.4 / +3.8 / +3.5 pp.
- **Code changes during the night (analysis only):** pulled bharat-v3-analysis (8fe136c) and bharat-v3-language (662ecf4), both checked to touch only the expected files. Committed my station-error split 4cfe68f (stage_comparison.py + its test, 5 tests pass). Nothing in evaluation/, environment/, agents/, benchmark/, config/ or scripts/ was touched. No run files were edited.

### Push (I did not push)

    cd ~/Agentic/bharat-toolbench-public && git push origin main

Charts: analysis/figures_v3/figS1-figS7 (.png + .pdf, captions in captions.md). Full report: RESULTS_V3.md.

## Per-model entries

### 2026-11-25 23:50 UTC: local_qwen25_3b (qwen2.5:3b), commit 4c0cb2d

- Complete: 625/625 items, 0 unresolved, 2 automatic resumes by full_phase.py, 58.7 min.
- Success: S1 (6 tools) 3.5% [2.0, 5.8]; S2 (12 tools) 0.0% [0.0, 3.0]; S3 (20 tools) 0.8% [0.3, 2.0]. Strict = lenient.
- Biggest change vs 6 tools: S2 - S1 = -3.5 pp [-5.8, -0.2]. The model was already near the floor (the do-nothing baseline gets 10/75, 1/25, 2/100 tasks), so a drop from 3.5% leaves little room. Tool *use* actually improved with more tools: selection recall 57 -> 79 -> 72%, first call right 34 -> 58 -> 64%. Argument accuracy rose at 12 tools (93%) and fell at 20 tools (54%).
- Unusual: **stage 2 is 0/125 items**. That is plausible for this model, not a pipeline fault: rescoring changed 0 items, and the stage-1 result matches round one. **output_truncated 152/625 (24%)**, against 19/375 (5%) in stage 1. These are replies that ran to max_tokens=2048 without a tool call (runaway text). They are mostly Indic-script items: gu 60, mr 48, hi 30, hinglish 12, en 2. malformed_output 7, context_overflow 2, step limit 0, no missing items.
- Language:
  - Gap S1 +2.3 [-3.0, +8.3]; S2 +0.0 [0, 0]; S3 +1.5 [-0.8, +4.8]. Change S3 - S1 = -0.8 [-7.1, +5.5]: **no clear change**, and every interval includes zero (floor effect).
  - Best/worst language: S1 English 5.3 / Gujarati 1.3. S2 all 0 (no best/worst). S3 English 2.0 / Marathi and Gujarati 0.0.
  - Station errors, split by cause since commit 4cfe68f (traps the gold expects are not counted). Each cell is not resolved / name, not code / placeholder, in items:

    | stage | en | hinglish | hi | mr | gu |
    |---|---|---|---|---|---|
    | S1 (of 75) | 8 / 55 / 0 | 5 / 48 / 0 | 8 / 50 / 1 | **44** / 52 / 1 | 9 / 53 / 0 |
    | S2 (of 25) | 0 / 2 / 0 | 0 / 3 / 0 | 0 / 5 / 0 | 3 / 4 / 0 | 0 / 3 / 0 |
    | S3 (of 100) | 3 / 29 / 3 | 1 / 24 / 0 | 1 / 24 / 0 | 5 / 31 / 0 | 3 / 25 / 0 |

  - The real word-ending problem ("not resolved") is a **Marathi** problem with 6 tools (44/75 items, against 5-9 in the other languages). With 12 and 20 tools it almost disappears: Marathi 3/25 and 5/100, others 0-3. Part of the reason is that the new tasks need fewer stations. In English S3 the 3 "not resolved" are passenger names sent to resolve_station (T108/T110/T111), not word endings.
  - The dominant station error in every stage and language is **name, not code**: the model skips resolve_station and sends a city name or a made-up code to search_trains / order_meal / change_boarding_point / get_platform_info. This happens at about the same rate in every language (S3: 24-31/100), so it is a tool-use failure, not a language one.
  - Placeholders (empty, "next_stop", unfilled templates) are rare: 3 English items in S3.
  - English S3 hand check of all 32 items: 0 traps were counted, and in 8 trap items the model failed earlier, before the trap, by sending a city name.
  - Models vs languages: not assessable with one model yet.

### 2026-11-26 00:14 UTC: local_llama32_3b (llama3.2:3b), commit b0f3c86

- Complete: 625/625 items, 0 unresolved, no resumes, 24.1 min.
- Success (lenient, strict in brackets): S1 7.7% [5.4, 10.9] (strict 4.0); S2 3.2% [1.3, 7.9] (strict 0.8); S3 1.0% [0.4, 2.3] (strict 0.2).
- Biggest change vs 6 tools: S3 - S1 = **-6.7 pp [-9.9, -4.1]**, a clear drop. S2 - S1 = -4.5 [-8.2, +0.7] includes zero. The drop is largest on Easy tasks (18.9 -> 2.5 -> 1.2%).
- Tool use: as with Qwen, the mechanics *improve* with more tools: selection recall 38 -> 77 -> 67%, first call right 17 -> 70 -> 68%, forbidden action tried 45 -> 7 -> 0%, unwanted state change 5.3 -> 4.8 -> 2.4%. Argument accuracy is 24 -> 95 -> 47%. Calls happen but the outcomes are still wrong, so the failures sit in arguments and final answers, not tool choice. Weakest tool: check_tatkal_availability, called in only 28/75 items that need it.
- Unusual:
  - The lenient-strict gap is large: most successes need a format recovery (S2 4 vs 1, S3 5 vs 1; recoveries used in 21/125 and 37/500 items). Read this model's numbers as lenient-dependent.
  - output_truncated 27/625, only in Gujarati (17) and Marathi (10). malformed_output 0. step_limit_exceeded 1. No missing items.
  - Re-scoring changed 1 item, T45_gu: a 2.1.0 stage-1 row that the current scorer accepts. This is expected from the scorer updates, not a run problem.
- Language:
  - Gap S1 -1.3 [-7.3, +5.0]; S2 **-4.0 [-8.0, -1.0]**; S3 +1.2 [-0.8, +4.0]. Change S3 - S1 = +2.6 [-4.0, +9.2]: **no clear change**. S2 is the only interval that excludes zero, and there English is *below* the Indian languages: 0/25 English against 3/25 Gujarati and 1/25 Marathi (T83_gu, T85_mr, T93_gu, T94_gu). That is a tiny count, so read it as noise.
  - Best/worst language: S1 Gujarati 10.7 / Marathi 5.3. S2 Gujarati 12.0 / English, Hinglish and Hindi 0. S3 English and Gujarati 2.0 / Hindi and Marathi 0.
  - Station errors (not resolved / name, not code / placeholder): the word-ending problem is almost absent for Llama in every stage: S1 0-1 per language, S2 0, S3 0-2 (Marathi 2, Gujarati 1). "Name, not code" dominates again: S1 16-32/75, S2 0-3/25, S3 19-27/100, at a similar level across languages (English lowest in S1). Placeholders 0-2 per language in S3.
  - Models vs languages (2 models): both models are near the floor, so neither gap is large yet. In S1 the model gap (7.7 vs 3.5 = 4.2 pp) is bigger than the pooled language spread (4.7-6.0%, 1.3 pp). In S3 both are about 1-2 pp. Not decidable before the 8B+ models finish.

### 2026-11-26 00:50 UTC: local_llama31_8b (llama3.1:8b), commit 495a3ab

- Complete: 625/625 items, 0 unresolved, no resumes, 36.0 min.
- Success (lenient, strict in brackets): S1 11.2% [8.4, 14.8] (11.2); S2 **32.0% [24.5, 40.6]** (31.2); S3 **17.2% [14.1, 20.8]** (16.4). Strict is almost the same as lenient (S2 40 vs 39, S3 86 vs 82), so it does not depend on format recovery.
- Biggest change vs 6 tools: S2 - S1 = **+20.8 pp [+12.5, +29.9]**. This is the first model that does *better* with more tools; S3 - S1 = +6.0 [+1.3, +10.5] is also clearly positive. Medium tasks rise most (6.8 -> 28.9 -> 14.5%). Read with care: S2/S3 are different tasks, and many are single-lookup service tasks (PNR, refunds, Tatkal 36%, TDR 27%) that suit an 8B model more than the multi-step booking tasks of S1. Hard tasks stay at 0 in every stage.
- Tool use: selection recall 32 -> 80 -> 71%, first call right 21 -> 80 -> 75%, argument accuracy 36 -> 96 -> 65%, forbidden action tried 38 -> 0 -> 0%. Weak spots in S3: get_platform_info is called in only 19/65 items that need it, and book_tatkal_ticket is called 14 times when not needed.
- Unusual: nothing serious. output_truncated 6 (mr 3, gu 3), malformed_output 0, step limit 0, no missing items, re-scoring 0 changes. The "order respected" column shows n/a for S1/S2 for this model (no qualifying items); minor.
- Language:
  - Gap S1 -5.7 [-12.3, +0.7]; S2 -15.0 [-35.0, +3.0]; S3 +6.0 [-0.2, +12.8]. All three intervals include zero (S3 only barely). The **change S3 - S1 = +11.7 [+2.5, +20.9] excludes zero**: the gap grows. With 6 and 12 tools English is the *lowest* language; with 20 tools it is the highest, so the gap shifts in English's favour.
  - Best/worst language: S1 Marathi 18.7 / English 6.7. S2 Hinglish, Hindi and Gujarati 36.0 / English 20.0. S3 English 22.0 / Hinglish 10.0.
  - Station errors (not resolved / name, not code / placeholder): the word-ending problem appears only with 6 tools and only in the Indic-script languages (Marathi 13, Gujarati 10, Hindi 5, Hinglish 2, English 0 of 75). With 12 tools there are none; with 20 tools only Marathi 1. "Name, not code" is the main error with 20 tools again (17-21/100, the same in every language). Placeholders: English 2 and Hindi 1 in S3.
  - Models vs languages (3 models): **the model gap is much bigger than the language gap.** With 20 tools Llama-3.1-8B reaches 17.2% against 0.8-1.0% for the 3B models (about 16 pp), while the pooled spread between languages is 4.7 pp (English 8.7, Hinglish 4.0). With 12 tools: 32.0% against 0-3.2% (about 29 pp) vs a 9.3 pp language spread.

### 2026-11-26 02:30 UTC: local_deepseek_r1_8b (deepseek-r1:8b), commit 9f10499

- Complete: 625/625 items, 0 unresolved, no resumes, 99.2 min (the slowest model so far, because of long thinking).
- Success (strict in brackets): S1 6.9% [4.8, 10.0] (6.1); S2 3.2% [1.3, 7.9] (3.2); S3 1.8% [0.9, 3.4] (1.8).
- Biggest change vs 6 tools: S3 - S1 = -5.1 pp [-8.3, -2.5]. S2 - S1 = -3.7 [-7.3, +1.5] includes zero.
- **Unusual: this model never calls a tool, in any stage** (uses tools 0.0% in S1, S2 and S3; no tool_call events at all in the 625 rows). This is not a pipeline fault:
  - the tool schema was sent (same sha as the other models);
  - Ollama reports the `tools` capability;
  - think_effective = False;
  - its 2.1.0 stage-1 run shows the same 0%.

  Instead it **writes made-up tool results** into a well-formed final answer. For example, T76_en answers "PNR status is WL/12" without calling get_pnr_status. All 13 successes come from three tasks (T98, T151, T189) that can be passed without a tool. So its success rate is effectively a do-nothing baseline, and the drop with more tools only reflects how many tasks can be passed without tools.
- Other unusual points:
  - output_truncated 77/625: en 40, mr 33, gu 4. The replies hit max_tokens=2048 while still *thinking* (0 characters of content, about 2.8k of thinking), even though think=false. English is the most affected here, unlike the other models.
  - Re-scoring changed 2 items: T45_hi and T45_gu, both 2.1.0 stage-1 rows the current scorer accepts (same task as Llama-3.2's T45_gu change).
  - No missing items, malformed_output 0, step limit 0.
  - **It is NOT flagged "unreliable"** by the report's rule (more than half malformed_output), so it is included in the pooled language rows. *Proposal (not applied):* also exclude models with uses-tools = 0% from the pooled language table, or mark them †. With it included, the pooled numbers are pulled toward the do-nothing level.
- Language:
  - Gap S1 **-7.0 [-13.3, -1.0]** (English lowest at 1.3%); S2 -4.0 [-12.0, 0.0]; S3 +0.2 [0.0, +0.8]. Change S3 - S1 = +7.3 [+1.1, +13.4]: it excludes zero, so formally the gap grows toward English. With no tool use, though, this reflects which language versions of the no-tool tasks it happens to answer, not a tool-use language effect.
  - Best/worst language: S1 Hindi and Gujarati 9.3 / English 1.3. S2 the four Indian languages 4.0 / English 0. S3 all 2.0 except Marathi 1.0.
  - Station errors: none in any stage or language, because it never calls a tool.
  - Models vs languages (4 models): still true. The model gap with 20 tools is about 16 pp (Llama-3.1-8B 17.2% against 0.8-1.8% for the others), while the pooled language spread is 3.5 pp (English 7.0, Hinglish 3.5).

### 2026-11-26 03:59 UTC: local_qwen25_14b (qwen2.5:14b), commit e53fe01

- Complete: 625/625 items, 0 unresolved, no resumes, 91.0 min.
- Success (strict in brackets): S1 26.9% [22.7, 31.6] (25.9); S2 24.8% [18.1, 33.0] (24.0); S3 22.0% [18.6, 25.8] (21.8). Strict is almost the same as lenient. This is the strongest model so far over all 200 tasks (24.2%).
- Biggest change vs 6 tools: **stable**. S2 - S1 = -2.1 [-10.4, +7.1] and S3 - S1 = -4.9 [-10.7, +0.8] both include zero, so there is no clear effect of more tools. By difficulty: Easy goes down (34 -> 29 -> 22%), Hard goes up (14 -> 24%, n=25 in S3).
- Tool use: **uses tools falls with more tools: 84 -> 69 -> 64%**, and selection recall falls 72 -> 65 -> 55%. Unlike the smaller models, the 14B increasingly answers without calling the tools it needs. Argument accuracy is high when it does call (81 -> 95 -> 82%). By service in S3: best Berths 48% and Tatkal 37%, weakest Complaints 4% and Platform & live 5%. New tools are under-used: change_boarding_point 25/50, file_tdr 21/40, raise_complaint 27/55, order_meal 41/75. check_tatkal_availability is over-called (24/425 when not needed).
- Unusual: nothing serious. output_truncated 9 (mr 4, gu 4, hi 1), step limit 1, malformed_output 0, no missing items, re-scoring 0 changes.
- Language:
  - Gap S1 +8.0 [-2.3, +18.3]; S2 +4.0 [-9.0, +18.0]; S3 +3.8 [-5.2, +12.8]. Change S3 - S1 = -4.2 [-18.0, +9.5]: **the gap shrinks slightly, but every interval includes zero**, so there is no clear difference.
  - **Marathi is the lowest language in all three stages.** Best/worst: S1 English 33.3 / Marathi and Gujarati 20.0; S2 Hinglish and Hindi 36.0 / Marathi and Gujarati 12.0; S3 English 25.0 / Marathi 19.0. With 20 tools the spread narrows to 6 pp.
  - Station errors (not resolved / name, not code / placeholder): the word-ending problem appears mainly in Marathi with 6 tools (8/75, others 0-2). With 12 tools there are none; with 20 tools it is 0-2 per language (Marathi 2). "Name, not code" falls from 18-28/75 with 6 tools to 7-10/100 with 20 tools, similar across languages. Placeholders: 1 English item.
  - Models vs languages (5 models): still clearly true. With 20 tools the models range from 0.8% to 22.0% (21 pp), while the pooled language spread is 3.6 pp (English 10.6, Hinglish 7.0). Within this model the language spread (6 pp) is also far below the gap to the weakest models.

### 2026-11-26 04:27 UTC: local_gpt_oss_20b (gpt-oss:20b), commit 0524d3d

- Complete: 625/625 items, 0 unresolved, no resumes, 28.1 min (fast for its size).
- Success (strict is identical): S1 56.8% [51.7, 61.7]; S2 **72.8% [64.4, 79.8]**; S3 50.8% [46.4, 55.2]. Over all 200 tasks 55.8%, **by far the strongest model so far** (more than twice Qwen2.5-14B's 24.2%).
- Biggest change vs 6 tools: S2 - S1 = **+16.0 pp [+6.3, +24.7]**, a clear rise (as with Llama-3.1-8B, the 12-tool tasks suit it). S3 - S1 = -6.0 [-12.6, +0.7] includes zero, so the drop is not clear. By difficulty in S3, Hard tasks reach 72% (n=25) while Easy and Medium are about 50%.
- Tool use: with 20 tools it **calls tools less and picks the first tool worse**: uses tools 98 -> 97 -> 86%, selection recall 90 -> 93 -> 76%, first call right 66 -> 73 -> 49%. Argument accuracy stays very high (97 -> 100 -> 97%). By service in S3: Berths 84% and Tatkal 66%, weakest Platform & live 28% and Meals 38%. check_tatkal_availability is over-called (36/425 when not needed), order_meal is under-called (50/75).
- Unusual: nothing serious. step_limit_exceeded 2 (T180_en, T180_hinglish); S1 had 27 step-limit rows in the 2.1.0 run, so this improved. output_truncated 0, malformed_output 0, no missing items, re-scoring 0 changes. Note: this model runs with think_effective = "low", because gpt-oss cannot switch thinking off. That is a config property, the same as in 2.1.0.
- Language:
  - Gap S1 -1.0 [-11.3, +9.3]; S2 -11.0 [-25.0, +1.0]; S3 **+10.2 [+1.8, +19.0]**. The S3 gap excludes zero: with 20 tools English is clearly ahead. Change S3 - S1 = +11.2 [-2.2, +24.7] includes zero, so the growth is suggestive but not clear.
  - Best/worst language: S1 Gujarati 62.7 / Marathi 53.3; S2 Hindi 80.0 / English 64.0; S3 English 59.0 / Gujarati 45.0.
  - Station errors (not resolved / name, not code / placeholder): rare overall. With 6 tools the word-ending problem appears only in Gujarati 4 and Marathi 3 (of 75). With 12 tools there are none. With 20 tools it is 1-2 per language; "name, not code" is 1-7 (English 7 is the highest); no placeholders.
  - Models vs languages (6 models): still clearly true. With 20 tools the models range from 0.8% to 50.8% (50 pp), while the pooled language spread is 4.5 pp (English 18.7, Hinglish 14.2). Within gpt-oss the spread is 14 pp, its largest language effect, yet still far below the gap between models.

### 2026-11-26 04:55 UTC: local_gemma4_26b (gemma4:26b), commit f4a8453

- Complete: 625/625 items, 0 unresolved, no resumes, 25.6 min.
- Success (strict is identical): S1 **76.3%** [71.7, 80.3]; S2 57.6% [48.8, 65.9]; S3 69.6% [65.4, 73.5]. Over all 200 tasks 70.6%, **the strongest model**, ahead of gpt-oss-20B (55.8%).
- Biggest change vs 6 tools: S2 - S1 = **-18.7 pp [-28.3, -9.2]**, a clear drop. S3 - S1 = -6.7 [-12.5, -0.7] is also clearly negative, but small. This is the opposite pattern to Llama-3.1-8B and gpt-oss, which peaked at 12 tools. The S2 dip is in Easy tasks (66 -> 46%) and goes with fewer tool calls (uses tools 98 -> 82%). By difficulty in S3: Hard 96% (n=25), Medium 77%, Easy 59%. Gemma does worse on "easy" tasks than on harder ones in every stage.
- Tool use: argument accuracy is about 100% in every stage. **First call right falls steadily: 67 -> 55 -> 40%**, and selection precision falls to 62% with 20 tools. The cause is mostly extra calls: check_tatkal_availability is called in 55/425 items where it is not needed. **Complaints is its weak service (26%)**: raise_complaint is called in only 21/55 items that need it. Best service Tatkal 91%.
- Unusual: malformed_output 2 (T106_mr, T190_gu). In both, Ollama returned no content and no tool call although the model generated tokens (144 and 26): the output was discarded by Ollama's parser. That is a serving-layer glitch on 2 rows, not a model format failure. Everything else is clean: output_truncated 0, step limit 0, no missing items, re-scoring 0 changes.
- Language:
  - Gap S1 +3.0 [-4.7, +11.0]; S2 -7.0 [-20.0, +5.0]; S3 -2.0 [-8.2, +4.0]. Change S3 - S1 = -5.0 [-14.9, +4.9]: **every interval includes zero, no clear language gap and no clear change.** Gemma is close to language-neutral.
  - Best/worst language: S1 Hindi 81.3 / Gujarati 72.0; S2 Hindi, Marathi and Gujarati 60.0 / English 52.0; S3 Hindi 77.0 / Hinglish 62.0. Hindi is the best language in all three stages; Hinglish (romanised Hindi) is the lowest with 20 tools.
  - Station errors (not resolved / name, not code / placeholder): almost none. The word-ending problem shows only in Marathi (3/75 with 6 tools, 2/100 with 20 tools) plus 1 each in English, Hinglish and Hindi with 6 tools. "Name, not code" is 0-4/100 with 20 tools.
  - Models vs languages (7 models): still clearly true. With 20 tools the models range from 0.8% to 69.6% (69 pp), while the pooled language spread is 4.7 pp (English 25.7, Hinglish 21.0). Within Gemma the spread is 15 pp (Hindi vs Hinglish).

### 2026-11-26 06:03 UTC: local_mistral_small32_24b (mistral-small3.2:24b), commit 4ff3787

- Complete: 625/625 items, 0 unresolved, no resumes, 69.2 min. The run finished at 06:01:49 UTC (DONE file written; tmux `bench` exited normally).
- Success (strict is identical): S1 5.1% [3.3, 7.8]; S2 24.8% [18.1, 33.0]; S3 9.2% [7.0, 12.1]. Over all 200 tasks 9.6%.
- Biggest change vs 6 tools: S2 - S1 = +19.7 pp [+12.5, +28.2] and S3 - S1 = +4.1 [+0.6, +7.5], both formally clear gains. **But the gains mostly reflect fewer discarded replies, not better tool use** (see below).
- **Unusual: malformed_output 138/625 (22%)**: S2 11/125, S3 127/500, spread over every language (mr 34, gu 34, hi 31, en 23, hinglish 16). **All 138 have the same cause:** the model generated 14-37 tokens, but Ollama returned no content and no tool call, because its tool-call parser discarded the output (a malformed tool-call block). Nothing reaches the scorer, so format tolerance cannot recover these rows, and they count as failures as specified. It is the same glitch as Gemma's 2 rows, at a much higher rate. In the 2.1.0 stage-1 run this was **229/375 (61%)**, so mistral's S1 score of 5.1% is mostly parser discards. Uses tools is 20% in S1 but 85% in S2/S3, and the S2 "gain" is largely the discard rate falling from 61% to 9%.
  - Flagging: the report flags a model "unreliable" when more than half of *all* its rows are malformed. Mistral has 367/1000 = 37%, so it is **not flagged** and stays in the pooled language table. *Proposal (not applied):* apply the 50% rule per stage as well (S1 alone is 61%), or mark mistral's S1 with †.
  - Other outcomes: step limit 4, output_truncated 2, no missing items, re-scoring 0 changes.
- Tool use when it does reply: argument accuracy 89 -> 98 -> 80%, first call right 13 -> 69 -> 56%. In S3 it rarely books Tatkal (book_tatkal_ticket 8/60, Tatkal service 3%) and under-uses change_boarding_point (18/50). Berths and Platform & live are 0%.
- Language:
  - Gap S1 +0.3 [-4.0, +4.7]; S2 -1.0 [-12.0, +11.0]; S3 **+6.0 [+0.8, +11.5]**, which excludes zero: English is ahead with 20 tools. Change S3 - S1 = +5.7 [-1.2, +12.6] includes zero: the gap grows, but not clearly.
  - Best/worst language: S1 Hinglish 6.7 / Hindi and Marathi 4.0; S2 Gujarati 32.0 / Hinglish 20.0; S3 English 14.0 / Marathi 4.0.
  - Station errors (not resolved / name, not code / placeholder): the word-ending problem never occurs (0 in every stage and language). "Name, not code" is 3-8/100 with 20 tools (Gujarati 8, Marathi 7).
  - Models vs languages (all 8 models): holds. With 20 tools the models range from 0.8% to 69.6%, while the pooled language spread is 4.8 pp.
