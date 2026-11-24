# Reproducible local-model comparison protocol (Qwen 2.5 3B / Qwen 2.5 7B / Llama)

Goal: every model is evaluated on the **same 375 items** (T01–T75 × en, hinglish, hi, mr, gu; the historical mid-sem runs used the 200-item `--split midsem --languages en hinglish hi mr` subset) with the **same benchmark
prompt, tool schema, scorer and decoding settings**, and every run can be traced to exact code, data and model
weights. Official success is always the unchanged scorer's `task_success`; failure categories
(`analysis/FAILURE_TAXONOMY.md`) are diagnostic.

## Fixed conditions for every model

| setting | value | source |
|---|---|---|
| decoding | temperature 0, seed 42 | `config/models.yaml` entry |
| context / output budget | num_ctx 16384, max_tokens 2048 | `config/models.yaml` entry |
| thinking | `think: false` (off where possible; `low` for gpt-oss; recorded as `think_effective`) | `config/models.yaml` entry |
| timeout / keep-alive | 300 s, 10m | `config/models.yaml` entry |
| retries | `--max-attempts 2` | CLI |
| prompt / tools / scorer | unchanged; hashes recorded per row and in the manifest | `evaluation/`, `environment/` |
| serving | local Ollama, native `/api/chat` | `agents/ollama_adapter.py` |

`compare_runs` refuses to compare runs whose item set, benchmark version, prompt hash, tool-schema hash or dataset
hashes differ, and warns when decoding settings differ.

## Per-model procedure

Replace `<key>` / `<model>` / `<TS>` (UTC timestamp `YYYYMMDDTHHMMSSZ`). Every file name must be NEW.

1. **Model availability (requires approval before any download).** `ollama pull <model>`; then `ollama show <model>`
   must list the `tools` capability. Record the digest from `ollama list`.
2. **Config (separate change, own commit).** Append a new entry to `config/models.yaml` (never edit existing ones),
   copying `local_qwen25_3b` and changing only the key and `model` (`--model` accepts any key of the file). Entries now
   present: `local_qwen25_7b`, `local_qwen25_14b`, `local_llama31_8b`.
3. **Pre-run record.** Capture git commit (tree must be clean), CLI command, SHA-256 of `semantic_tasks.json`,
   `gold_labels.json`, the five language files and `human_review.json`, `config/models.yaml`, runner/scorer/final-answer/adapter sources,
   prompt and tool-schema hashes, Ollama version and model digest into `runs/<stem>.prerun.json`
   (see `runs/local_qwen25_3b_full_20261013T222957Z.prerun.json` for the format).
4. **Gates.** 4-item diagnostic (T01 × 4 languages, one file per language, `--max-requests 1`), then the 20-item pilot
   (`--split pilot`). Both are informational for the comparison; the full run is the comparable result.
5. **Full run.**
   `python -m evaluation.run_pilot --model <key> --split full --max-attempts 2 --run-file runs/<key>_full_<TS>.jsonl`
6. **Recovery (only if provider/runner errors or missing items remain).** `--resume` works on ONE file only: it reads
   `--run-file`, skips items whose latest row is `completed` / `malformed_output` / `step_limit_exceeded`, re-runs the
   rest (including items absent from the file) and APPENDS to that same file and its `.quota.json`. Never resume the
   original: copy it byte-for-byte to `runs/<stem>_resume1.jsonl`, run `--resume --run-file` on the copy, and keep both.
7. **Manifest.** `python -m analysis.run_manifest --prerun runs/<stem>.prerun.json --run-file runs/<stem>.jsonl
   [--run-file runs/<stem>_resume1.jsonl] --out runs/<stem>.manifest.json` (exit 3 if benchmark files changed).
8. **Observations.** `python -m analysis.observe_run --run-file runs/<stem>.jsonl [--run-file runs/<stem>_resume1.jsonl]
   --split full --manifest runs/<stem>.manifest.json --out analysis/results/<stem>` (exit 2 if any item is missing).
   Files are given in chronological order; each task-language pair is counted once (latest row wins).
9. **Comparison.** `python -m analysis.compare_runs analysis/results/<stem_A> analysis/results/<stem_B> [...]
   --out analysis/results/comparison_<A>_vs_<B>` → `comparison.md` / `comparison.json`: success, parse, process,
   state, tool-call success, tokens and time overall / per language / per category / per task; paired item-level
   counts and a seeded 95 % bootstrap CI of the success difference.

## Known sources of variation (report them, do not hide them)

* GPU numerics: replays at temperature 0 / fixed seed were not always token-identical on this machine
  (GTX 1650 4 GB). To quantify run-to-run variance, re-run the 20-item pilot split twice per model into new files and
  compare the two with `compare_runs`.
* Hardware: 7B models (~4.7 GB at Q4) exceed 4 GB VRAM and run partly on CPU with 8 GB RAM; expect several times
  longer runs. Same settings must still be used.
* Ollama simplifies tool schemas (drops `title`, `additionalProperties`, `$defs`, `$ref`) for every model alike; see
  `LOCAL_MODELS.md`.
