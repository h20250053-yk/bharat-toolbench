# Running BharatToolBench with local models (Ollama)

Local models run through [Ollama](https://ollama.com) on this machine: no API key, no cloud calls.
Adapter: `agents/ollama_adapter.py` (native `/api/chat`, non-streaming, via `httpx`). Model settings live only in
`config/models.yaml`.

## Configured local models

| Key | Ollama model |
|---|---|
The eight models of `MODEL_PLAN.md`, in run order (the optional `local_qwen25_7b` is also configured):

| Key | Ollama model |
|---|---|
| `local_qwen25_3b` | `qwen2.5:3b` |
| `local_llama32_3b` | `llama3.2:3b` |
| `local_llama31_8b` | `llama3.1:8b` |
| `local_deepseek_r1_8b` | `deepseek-r1:8b` (R1-0528 distilled into Qwen3-8B) |
| `local_qwen25_14b` | `qwen2.5:14b` |
| `local_gpt_oss_20b` | `gpt-oss:20b` (reasoning cannot be disabled: `low`) |
| `local_gemma4_26b` | `gemma4:26b` (must show 100% GPU; fallback `gemma4:12b`) |
| `local_mistral_small32_24b` | `mistral-small3.2:24b` |

Every `local_*` entry has the **same** settings (enforced by `tests/test_eval_ollama.py`): temperature 0, seed 42,
`num_ctx` 16384, `max_tokens` 2048, `think: false`, timeout 300 s, `keep_alive` 10m. `think: false` is a policy: thinking is
OFF for every model that can switch it off; a model that cannot (gpt-oss) gets the lowest level (`low`); a model without the
`thinking` capability gets no `think` field. The effective value is recorded in each row's `adapter_settings`, the pre-run
snapshot and the manifest. The two 3B results in `analysis/results/` were produced earlier with `num_ctx` 8192, `max_tokens`
1024 and no `think` setting, so they are not directly comparable to runs with the current settings.

## Prerequisites (this Linux server, no sudo)

**Standard server: Ollama 0.40.18**, installed in the home directory (`~/FreeModel/ollama/bin/ollama`, on `PATH`; the previous 0.40.13 install is
kept in `~/FreeModel/ollama-0.40.13-old` and must not be used: servers before 0.40.18 discard valid tool-call replies, see
`FORMAT_ROBUSTNESS.md` F-23). Models live in `~/FreeModel/models`. `run_pilot`, `OllamaAdapter.preflight()` and the pre-run snapshot
REFUSE to run against an older server (or one that reports no version) and the server version is recorded in every run row
(`adapter_settings.ollama_version`), the pre-run snapshot and the run manifest.

Start it in tmux (so it survives the terminal; one session called `ollama`). `OLLAMA_NUM_PARALLEL=1` and `OLLAMA_MAX_LOADED_MODELS=1` are part of the plan (one conversation, one model on the GPU); the pre-run snapshot reads them from the server's own start-up log (`~/FreeModel/ollama-serve.log`), records them, and REFUSES to run if they differ:

```bash
tmux new-session -d -s ollama 'OLLAMA_MODELS=$HOME/FreeModel/models OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 ollama serve 2>&1 | tee -a $HOME/FreeModel/ollama-serve.log'
tmux ls                         # shows the session; look at the server log with: tmux attach -t ollama   (detach with Ctrl-b d)
curl -s localhost:11434/api/version   # {"version":"0.40.18"}
ollama list                     # the model must be listed; otherwise (needs approval): ollama pull qwen2.5:7b
ollama show qwen2.5:7b          # capabilities must list `tools`; run_pilot and the pre-run snapshot refuse a model without it
tmux kill-session -t ollama     # stop the server
```

## Commands (run from this folder, with the project venv: `source .venv/bin/activate`)

```bash
# offline checks (no Ollama needed)
python -m pytest -q tests/test_eval_ollama.py
python -m evaluation.smoke
python -m benchmark.validate_tasks

# one-item smoke test: --max-requests is checked before each item, so this runs exactly T01_en
python -m evaluation.run_pilot --model local_qwen25_3b --split pilot --languages en --max-requests 1 --run-file runs/<new_name>.jsonl

# 25-item pilot (T01-T05 x en, hinglish, hi, mr, gu)
python -m evaluation.run_pilot --model local_qwen25_3b --split pilot --max-attempts 2 --run-file runs/<new_name>.jsonl

# full benchmark (T01-T75 x 5 languages = 375 items; the default --languages is all five)
python -m evaluation.run_pilot --model local_qwen25_3b --split full --max-attempts 2 --run-file runs/<new_name>.jsonl

# the historical 200-item mid-sem subset
python -m evaluation.run_pilot --model local_qwen25_3b --split midsem --languages en hinglish hi mr --max-attempts 2 --run-file runs/<new_name>.jsonl

# summary of a run
python -m analysis.pilot_report runs/<file>.jsonl
```

Rules:
* `--run-file` is opened in **append** mode. Always pass a NEW file name; run_pilot refuses an existing non-empty file unless
  `--resume` is given. To continue an interrupted run, add `--resume` with the SAME file (re-runs only provider/runner errors).
* `--max-attempts 2` is recommended locally: a retry restarts the whole conversation.

## How results should be read

* `status: completed` only means the model stopped calling tools. Success is `score.task_success`
  (structured final answer + environment state + tool process; see `evaluation/README.md`).
* A reply without the `<FINAL_ANSWER_JSON>` block is a model failure (`final_answer:missing_block`), as for every model.
* `provider_error` rows are not scored. Kinds specific to the local adapter:
  * `connection` / `timeout` (retryable): Ollama not running or too slow -> start Ollama, then `--resume`.
  * `not_found`: model not pulled.
  * `tools_unsupported`: the model does not list the `tools` capability; the run is refused before any item.
* Two further statuses are SCORED model failures (never re-run): `context_overflow` (prompt + `max_tokens` would exceed
  `num_ctx`, so Ollama could have truncated the prompt; label `run:context_overflow`) and `output_truncated` (the reply hit
  the `max_tokens` limit without a tool call; label `run:output_truncated`, kept apart from `malformed_output`).
* Provenance in every row's `adapter_settings`: Ollama version, model digest, quantization, parameter size,
  `num_ctx`, seed, temperature. Usage includes `cached_input_tokens` (Ollama prompt cache).

## Known behaviour (observed with Ollama 0.40.3 + qwen2.5:3b; the discard below is fixed in 0.40.18)

* When Ollama cannot convert a `<tool_call>` block the model emitted (observed: the final-answer JSON wrapped in
  `<tool_call>` tags, with no function name), it returns `content: ""` with no `tool_calls` although
  `eval_count > 0`, i.e. the whole output is discarded. Since commit "Classify Ollama-discarded output ..." the adapter
  raises `ModelOutputError('unparsed_model_output')` for this case: row status `malformed_output`
  (a scored model failure, never retried), with response metadata (token counts, durations) in `raw_log`.
  Rows written before that change (`runs/local_qwen25_3b_pilot.jsonl`, 4 of 58 responses, all T03 variants) show
  it as `completed` with an empty final text instead.
* Ollama re-serialises tool schemas into its own types and drops `title`, `additionalProperties`, `$defs` and
  `$ref`: in the 3B runs the model saw `time_window` only as `anyOf: [{}, {"type": "null"}]`. Since audit I-06 the adapter
  inlines every `$ref` before sending, so the `{start, end}` structure reaches the model (the benchmark schema and its
  hash are unchanged; the hash of what was sent is in `adapter_settings.tool_schema_sent_sha256`).
* qwen2.5:3b results so far: pilot (T01-T05 x 4 languages) 0/20 task_success; 4-item diagnostic
  (T01 x 4 languages, `runs/local_qwen25_3b_diag_20261013T215111Z_*.jsonl`) 0/4, although every item made the
  correct `get_fare` call and stated the correct fare. The `<FINAL_ANSWER_JSON>` block was never produced; replaying
  the 14 recorded final turns with the unchanged prompt gave 0/14 parseable blocks (5/14 when the `tools` field is
  removed, a diagnostic contrast only). This is a model output-format limitation, not an adapter defect.

## Adding another local model

1. `ollama pull <model>` (needs approval), then check `ollama show <model>` lists `tools`.
2. Append a new `local_*` entry to `config/models.yaml` copying an existing one (same settings) and changing key and `model`;
   do not edit existing entries. `run_pilot --model` accepts any key of `config/models.yaml`.
3. Run the one-item smoke test, then the pilot, into new run files.
