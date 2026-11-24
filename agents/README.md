# agents

Model adapters that normalize provider tool calls into canonical `{tool_name, arguments}` for `RailwayEnv.call`:
`groq_adapter`, `gemini_adapter`, `openrouter_adapter` (experimental), `nvidia_adapter` (experimental; not wired into
`registry.py`) and `ollama_adapter` (local models; see `LOCAL_MODELS.md`). Model IDs come only from `config/models.yaml`.
