# MODEL_PLAN: which models to evaluate on BharatToolBench v2.1.0

Status: plan only (2026-11-24). Nothing was downloaded or run; `config/models.yaml` is unchanged (the YAML in section 6 is a proposal).
Benchmark: 75 tasks x 5 languages = 375 items; local Ollama 0.40.18; identical settings for every model (temperature 0, seed 42, `num_ctx` 16384,
`max_tokens` 2048, thinking off where the model allows it); lenient headline score + strict sensitivity score.

## 0. Facts that drive the choice

**Hardware (checked now with `nvidia-smi`):** one **NVIDIA A30, 24,576 MiB total, 24,150 MiB free** (not ~30 GB), 125 GB RAM, 4.0 TB free disk. A model
"fits" only if weights + KV cache at `num_ctx` 16384 are below about 22 GB (leave ~1.5 GB for the CUDA context and compute buffers) AND `ollama ps` shows
`100% GPU` (any CPU offload slows a model 5-20x and breaks the time budget). Dense 30B-class models therefore do not fit; MoE models with ~4 B active
parameters do, if their total weights are below about 19 GB.

**What exists in Ollama for each requested family (read from the ollama.com library and tag pages on 2026-11-24; blogs only where stated):**

| family | open-weight models that run locally | tools badge | notes |
|---|---|---|---|
| OpenAI | `gpt-oss:20b` (14 GB, 128K ctx, Apache 2.0); `gpt-oss:120b` (65 GB) | tools, thinking | reasoning cannot be switched off, only low/medium/high; 120b does not fit |
| Google | **Gemma 4** (not Gemma 3): `e2b`, `e4b`, `12b` (8.0 GB), `26b` (MoE, ~4 B active, 16-19 GB), `31b` (dense, 19-20 GB) | tools, thinking, vision | 128K-256K ctx; "native function-calling"; thinking is off when its token is absent (`think:false`); licence not stated on the Ollama page, secondary sources say Apache 2.0 (verify on the Hugging Face card before camera-ready) |
| Groq | none that is current. Groq is an inference provider; its own open weights are `llama3-groq-tool-use` 8b/70b (July 2024, Llama-3 fine-tunes) | tools | **8K context only**, 2 years old, licence not stated on the page: excluded (section 3) |
| DeepSeek | only the R1 *distills* run locally (`deepseek-r1` 1.5b-70b; `8b` = R1-0528 distilled into Qwen3-8B, 5.2 GB; `14b` = Qwen2.5-14B distill). V3.x/V4 are 404 GB (V3.1) or ~160 GB (V4-Flash) and V4 is cloud-only on Ollama | tools, thinking | MIT weights; the Ollama page is 1 year old; early R1 reports said tool calling was unreliable (HF discussion), so test before trusting |
| Qwen | `qwen2.5` 0.5b-72b (tools, 32K ctx), `qwen3.5` 0.8b-122b and `qwen3.6` 27b/35b-a3b (tools, thinking, vision, 256K ctx), `qwen3-coder:30b` (already on disk) | tools | qwen2.5: Apache 2.0 except the 3B and 72B (Qwen licence); qwen3.x licence not stated on the page |
| Meta | `llama3.2:3b`, `llama3.1:8b` (128K ctx); 70B/405B/Llama 4 do not fit | tools | Llama community licences (attribution; naming rules for derivatives) |
| Mistral | `mistral-small3.2:24b` (15 GB, 128K, vision, tools; "more robust function-calling template") | tools | `mistral-small:latest` still points to the older 3.0 (2501) build; Apache 2.0 per the `mistral-small` page |
| others checked | `granite4` (350m/1b/3b and hybrid 7b-a1b-h, 32b-a9b-h 19 GB; Apache 2.0; tools), `phi4-mini` 3.8B (2.5 GB, tools) | tools | candidates only |

## 1. The decision

Design: **two axes on the same 375 items**: (a) size within a family (Qwen 3B -> 14B; Llama 3B -> 8B), (b) family at comparable size (8B class: Llama 3.1 vs
DeepSeek-R1-0528-Qwen3; 20-26B class: gpt-oss, Gemma 4, Mistral Small). Eight models in run order (7 is possible, see the cut rule):

| # | model (Ollama tag) | maker / family | params (active) | weights | role | licence |
|---|---|---|---|---|---|---|
| 1 | `qwen2.5:3b` | Alibaba / Qwen | 3.1 B dense | 1.9 GB | light, pilot baseline (re-run) | Qwen research licence (3B) |
| 2 | `llama3.2:3b` | Meta / Llama | 3.2 B dense | 2.0 GB | light, pilot baseline (re-run) | Llama 3.2 community |
| 3 | `llama3.1:8b` | Meta / Llama | 8 B dense | 4.9 GB | Llama size step | Llama 3.1 community |
| 4 | `deepseek-r1:8b` | DeepSeek (R1-0528 distilled into Qwen3-8B) | 8.2 B dense | 5.2 GB | DeepSeek slot, 8B class | MIT (base Qwen3: Apache 2.0) |
| 5 | `qwen2.5:14b` | Alibaba / Qwen | 14.8 B dense | 9.0 GB | Qwen size step, same generation as #1 | Apache 2.0 |
| 6 | `gpt-oss:20b` | OpenAI | 21 B MoE (3.6 B active) | 14 GB | GPT slot | Apache 2.0 |
| 7 | `gemma4:26b` | Google / Gemma 4 | 26 B MoE (~4 B active) | 16-19 GB | Gemini-family slot (Gemma is the open Gemini sibling) | Apache 2.0 (verify) |
| 8 | `mistral-small3.2:24b` | Mistral | 24 B dense | 15 GB | substitute for the "Groq" slot, strongest dense model that fits | Apache 2.0 (verify on the 3.2 card) |

Why each is in:
1. `qwen2.5:3b`, 2. `llama3.2:3b`: the pilot baselines. They must be re-run on Ollama 0.40.18 with the 2.1.0 settings and the new prompt/format layer (the old runs are pilot-only).
They are also the cheapest end-to-end test of the harness.
3. `llama3.1:8b`: the only Llama that fits above 3B and the Llama family's native tool-use generation; gives Llama a 3B -> 8B size step.
4. `deepseek-r1:8b`: the one DeepSeek model that really runs locally and is current (R1-0528 added function calling; DeepSeek's V3.x/V4 cannot run here).
It is a *distill* (a Qwen3-8B re-trained on R1 outputs): the paper must call it "DeepSeek-R1-0528-Qwen3-8B (distill)", not "DeepSeek". Tool calling through Ollama was unreliable for early R1 builds,
so it is gated by the smoke test; if it fails, report it as a negative result rather than silently replacing it.
5. `qwen2.5:14b`: the same Qwen generation and tool template as the 3B baseline, so 3B -> 14B (x4.7) is a clean size comparison; a 7B (below) fills the curve if time allows.
6. `gpt-oss:20b`: OpenAI's open model, trained for function calling, MoE so it is fast; the only family whose reasoning cannot be switched off (it runs at `low`, recorded in the manifest).
7. `gemma4:26b`: Google's current open family with native function calling; the MoE form (4 B active) is fast and fits the 24 GB card (largest of the three 20-26B models: needs `ollama ps` = 100% GPU,
fallback `gemma4:12b`). Multilingual coverage is its selling point (pre-trained on 140+ languages per Google's model card).
8. `mistral-small3.2:24b`: nothing from Groq qualifies, so this is the best substitute: a different (European) family, dense 24B, Apache 2.0, 128K context, a tool-call template Mistral itself describes as improved,
and 15 GB so it fits easily. It also lets the paper compare three architectures at ~20-26B (dense, MoE, MoE-reasoning).

**Cut rule if you want 7:** drop #8 (`mistral-small3.2:24b`, the substitute) before touching the families you named; if #4 fails its smoke test it becomes a reported negative result and the list is 7 anyway.

## 2. Why notable models are NOT in the main list

| model | decision | reason |
|---|---|---|
| `qwen3-coder:30b` (on disk, 18 GB) | **out of the main list; keep as reserve / optional extra** | fits and is fast (A3B MoE, native tools), Apache 2.0, but it is a code-specialised model: it would add a Qwen "large" point that is confounded by specialisation and generation, and it is not multilingual-oriented. Run it only as a labelled extra (e.g. "tool-use of a coder model"), costs no download |
| `llama3-groq-tool-use:8b` (the only "Groq" open model) | out | 8K context (our `num_ctx` is 16384: Ollama would clamp it silently and the adapter's overflow check, which uses the configured value, would not notice truncation), July 2024, superseded by Llama 3.1 native tool use, licence not stated on the page |
| `gpt-oss:120b`, `llama3.3:70b`, `llama4`, `deepseek-r1:70b` | out | 43-65 GB: do not fit 24 GB |
| `qwen2.5:32b`, `deepseek-r1:32b` | out | 20 GB weights + about 4 GB KV at 16K = over 24 GB: CPU offload |
| `gemma4:31b` (19-20 GB) | out (optional) | borderline with the KV cache at 16K; the 26B MoE is faster and safer |
| `qwen3.6:35b-a3b` (23-24 GB), DeepSeek V3.x/V4 | out | do not fit / not available locally |
| `qwen3.6:27b` (17 GB, thinking, 256K) | optional extra | newest Qwen that fits; licence not stated on the Ollama page; adds a current-generation Qwen point (confounds generation and size, so not core) |
| `qwen2.5:7b` (4.7 GB, Apache 2.0) | optional extra, cheap | fills the Qwen size curve 3B/7B/14B (entry already in `models.yaml`) |
| `gemma4:12b` (8 GB), `gemma4:e4b` | optional / fallback | gives Gemma a size step, or replaces `26b` if it does not fit |
| `granite4` small-h 32b-a9b, `phi4-mini`, `granite4:3b` | not selected | extra families in the light/mid tiers would dilute the size/family comparison; keep as future work |

## 3. Settings (identical for all, written into every manifest)

Per model (`config/models.yaml`, test-enforced): temperature 0, seed 42, `num_ctx` 16384, `max_tokens` 2048, `think: false`, timeout 300 s, `keep_alive` 10m.
`think: false` means off where possible; gpt-oss runs at `low` (recorded as `think_effective`); Gemma 4 and DeepSeek-R1 receive `think: false` and must be confirmed by the smoke test
(no `<think>`/thought text in the reply; any that leaks is stripped by the format layer and counted).
Server (fixed once, same for all runs, recorded in the plan): `OLLAMA_NUM_PARALLEL=1` (one conversation at a time; also gives deterministic prompt caching), `OLLAMA_MAX_LOADED_MODELS=1`,
default KV cache type (f16 for every model; no per-model quantised KV), flash attention left at the Ollama default. These server variables are not in the pre-run snapshot today: I suggest
adding them to the snapshot before the first run (small change, not done).
Gate for each model before its full run: (1) `ollama show` lists `tools` (enforced), (2) `ollama ps` shows `100% GPU` after loading with `num_ctx` 16384, (3) the 1-item smoke test, (4) the 25-item pilot with:
no `unparsed_model_output`, no think text in replies, finish reasons sane, time per item in line with section 5. Ordinary failures are results; only harness faults block a full run.

## 4. Fit check (weights + KV cache at 16K, f16) against 24 GB

KV per token = layers x 2 x kv_heads x head_dim x 2 bytes (from the published architectures; Gemma 4 is an estimate because I could not read its configuration):

| model | weights | KV at 16K | total (est.) | fits? |
|---|---|---|---|---|
| qwen2.5:3b | 1.9 | 0.6 | ~3 | yes |
| llama3.2:3b | 2.0 | 1.9 | ~4.5 | yes |
| llama3.1:8b | 4.9 | 2.1 | ~7.5 | yes |
| deepseek-r1:8b | 5.2 | 2.4 | ~8 | yes |
| qwen2.5:14b | 9.0 | 3.2 | ~13 | yes |
| gpt-oss:20b | 14 | ~0.5 (sliding-window layers) | ~15.5 | yes |
| mistral-small3.2:24b | 15 | 2.7 (+ vision tower ~0.8) | ~19 | yes |
| gemma4:26b (a4b) | 16-19 | ~1.5-4 (estimate) | ~18-23 | **tight: confirm with `ollama ps`; fallback `gemma4:12b`** |
| qwen3-coder:30b (reference) | 18 | ~1.5-3 | ~20-21 | fits |
| qwen2.5:32b (reference) | 20 | 4.3 | ~25 | no |

## 5. Time and disk (estimates: no model was run; calibrate with the 25-item pilot)

Method: the A30 has ~933 GB/s memory bandwidth; Ollama decode reaches roughly 60-70% of it, so tokens/s ~ 0.65 x 933 / (GB of weights read per token) for dense models and per *active* weights for MoE.
Old runs (read only) for workload: Llama 3B 1.8 requests and 166 output tokens per item, Qwen 3B 2.8 requests and 473 output tokens per item (it loops). A competent tool-using model needs about 4-6 requests
per item (resolve x2, search, fare/availability, book, final answer) and 400-600 output tokens (gpt-oss: 1,000-2,000 including low-level reasoning). The system prompt + tool schemas (~1.9k tokens) stay in the
prompt cache with `NUM_PARALLEL=1`, so only tool results and the first request are prefilled.

| # | model | decode t/s (est.) | s/item (est.) | 375 items | pilot (25) |
|---|---|---|---|---|---|
| 1 | qwen2.5:3b | ~150 | ~6 | ~40 min | ~3 min |
| 2 | llama3.2:3b | ~150 | ~6 | ~40 min | ~3 min |
| 3 | llama3.1:8b | ~100 | ~9 | ~55 min | ~4 min |
| 4 | deepseek-r1:8b | ~100 | ~9-12 | ~55-75 min | ~5 min |
| 5 | qwen2.5:14b | ~55 | ~15 | ~95 min | ~7 min |
| 6 | gpt-oss:20b | ~120 | ~18 | ~110 min | ~8 min |
| 7 | gemma4:26b | ~90 | ~12 | ~75 min | ~6 min |
| 8 | mistral-small3.2:24b | ~35 | ~22 | ~140 min | ~10 min |

Total about **10 h of GPU time** for the eight full runs (+ ~50 min of pilots and ~10 min of model loads); plan **12-16 h wall-clock** with margin. Per-item worst case is bounded by the 8-turn limit and
2048 output tokens per reply (a looping 24B model could take minutes on one item), which is why the pilot decides, and why a model that loops is a result, not a reason to raise a limit.
Everything runs sequentially (one model on the GPU at a time); `OLLAMA_MAX_LOADED_MODELS=1` avoids two models competing for VRAM.

Disk to download (Ollama page sizes): qwen2.5:3b 1.9 + llama3.2:3b 2.0 + llama3.1:8b 4.9 + deepseek-r1:8b 5.2 + qwen2.5:14b 9.0 + gpt-oss:20b 14 + gemma4:26b 16-19 + mistral-small3.2:24b 15 =
**about 68-71 GB**; optional extras: qwen2.5:7b 4.7, gemma4:12b 8.0, qwen3.6:27b 17-19. Free disk: 4.0 TB. `qwen3-coder:30b` (18 GB) is already on disk.
Run outputs are small (the two old runs are a few tens of MB each; budget < 1 GB per model).

## 6. `config/models.yaml` (PROPOSAL, not applied)

Existing entries stay as they are (`local_qwen25_3b`, `local_llama32_3b`, `local_qwen25_7b`, `local_qwen25_14b`, `local_llama31_8b`; the identical-settings test covers every `local_*` key).
Add four entries with the same settings (comments carry the digests after the pull):

```yaml
  local_deepseek_r1_8b:   # DeepSeek-R1-0528 distilled into Qwen3-8B (MIT). Report as a distill. think:false must be confirmed by the smoke test.
    provider: ollama
    model: "deepseek-r1:8b"
    base_url: "http://127.0.0.1:11434"
    temperature: 0
    seed: 42
    max_tokens: 2048
    num_ctx: 16384
    timeout_seconds: 300
    keep_alive: "10m"
    think: false
  local_gpt_oss_20b:      # OpenAI gpt-oss-20b (Apache 2.0). Reasoning cannot be disabled: think:false resolves to the lowest level ("low"), recorded as think_effective.
    provider: ollama
    model: "gpt-oss:20b"
    base_url: "http://127.0.0.1:11434"
    temperature: 0
    seed: 42
    max_tokens: 2048
    num_ctx: 16384
    timeout_seconds: 300
    keep_alive: "10m"
    think: false
  local_gemma4_26b:       # Google Gemma 4 26B-A4B (MoE). Needs `ollama ps` = 100% GPU at num_ctx 16384; fallback model: gemma4:12b.
    provider: ollama
    model: "gemma4:26b"
    base_url: "http://127.0.0.1:11434"
    temperature: 0
    seed: 42
    max_tokens: 2048
    num_ctx: 16384
    timeout_seconds: 300
    keep_alive: "10m"
    think: false
  local_mistral_small32_24b:   # Mistral Small 3.2 24B (substitute for the Groq slot).
    provider: ollama
    model: "mistral-small3.2:24b"
    base_url: "http://127.0.0.1:11434"
    temperature: 0
    seed: 42
    max_tokens: 2048
    num_ctx: 16384
    timeout_seconds: 300
    keep_alive: "10m"
    think: false
```

Optional extras (same settings, add only if you want them): `local_gemma4_12b` (`gemma4:12b`), `local_qwen36_27b` (`qwen3.6:27b`), `local_qwen3_coder_30b` (`qwen3-coder:30b`, already pulled).
The test `test_all_local_models_share_identical_decoding_settings` also needs the new keys' names to start with `local_` (they do) and nothing else.

## 7. Run order and procedure (when you approve)

1. Start the server in tmux (LOCAL_MODELS.md), pull the models one at a time (each pull needs approval), record digests.
2. Per model: pre-run snapshot -> `ollama ps` fit check -> 1-item smoke -> 25-item pilot -> full 375 items (`--split full`, all five languages, `--max-attempts 2`) -> manifest -> `observe_run`.
3. Order: qwen2.5:3b, llama3.2:3b (baselines and harness validation), llama3.1:8b, deepseek-r1:8b (early detection of a tool-calling problem), qwen2.5:14b, gpt-oss:20b, gemma4:26b, mistral-small3.2:24b.
4. Analysis for the paper: size axis (Qwen 3B/14B, Llama 3B/8B), family axis (8B class: Llama 3.1 vs DeepSeek-R1-Qwen3; 20-26B class: gpt-oss vs Gemma 4 vs Mistral), per-language success next to the model's published language coverage,
strict vs lenient, recoveries per rule, the null baseline, tool-required tasks only.

## 8. Risks and what I could not verify

- Gemma 4: tool calling was unreliable in early Ollama builds (April 2026) and fixed later (secondary sources: Ollama >= 0.32.1 and weight refresh in July 2026); 0.40.18 should be fine but the smoke test decides. Its Ollama page does not state the licence; the 26B tag range 16-19 GB means I cannot give an exact fit before pulling.
- DeepSeek-R1 distill: tool calling and `think:false` behaviour are unconfirmed for the 8b-0528 tag (the Ollama page is a year old and silent on both).
- gpt-oss: reasoning tokens count against `max_tokens` 2048 (a long reasoning at `low` can hit `output_truncated`, which is scored separately); harmony-format tool calls are converted by Ollama.
- Language coverage differs by model and will show up in the language results: Llama 3.x lists Hindi but not Marathi/Gujarati, Qwen3.x claims 119 languages, Gemma 4 claims 140+ (pretraining) and 35+ (out of the box), Mistral Small lists Hindi, gpt-oss is mostly English-centric.
These are published claims, not measured here; they are context for interpreting results, not a selection criterion.
- Licences marked "verify" come from third-party summaries; check the model cards before the camera-ready.
- Time numbers are estimates from memory bandwidth and the old runs; nothing was benchmarked on this card with these models.

## Sources

Fetched directly (Ollama library and tag pages, 2026-11-24): [gpt-oss](https://ollama.com/library/gpt-oss), [gemma4](https://ollama.com/library/gemma4), [deepseek-r1](https://ollama.com/library/deepseek-r1),
[llama3-groq-tool-use](https://ollama.com/library/llama3-groq-tool-use), [qwen3.6](https://ollama.com/library/qwen3.6), [qwen3.5](https://ollama.com/library/qwen3.5), [qwen2.5](https://ollama.com/library/qwen2.5),
[llama3.1](https://ollama.com/library/llama3.1), [llama3.2](https://ollama.com/library/llama3.2), [mistral-small3.2](https://ollama.com/library/mistral-small3.2), [mistral-small](https://ollama.com/library/mistral-small),
[granite4](https://ollama.com/library/granite4), [phi4-mini](https://ollama.com/library/phi4-mini).
Search results used for context (secondary): [Gemma 4 vs Llama 3 vs Mistral tool calling](https://machinelearningmastery.com/comparing-local-tool-calling-gemma-4-vs-llama-3-vs-mistral/),
[Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4.md), [Gemma 4 July 2026 weight refresh](https://runaihome.com/blog/gemma-4-july-2026-flash-attention-4-prefill-ollama-update/),
[Ollama thinking docs](https://docs.ollama.com/capabilities/thinking.md), [DeepSeek-R1 tool-calling discussion](https://huggingface.co/deepseek-ai/DeepSeek-R1/discussions/122),
[Ollama gpt-oss page](https://ollama.com/library/gpt-oss:20b), [OpenAI gpt-oss with Ollama](https://developers.openai.com/cookbook/articles/gpt-oss/run-locally-ollama),
[Llama 3 Groq 8B Tool Use](https://huggingface.co/Groq/Llama-3-Groq-8B-Tool-Use), [Qwen on Ollama guides](https://insiderllm.com/guides/qwen-models-guide/),
[BFCL v4 leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html) (no useful rows for these models).
