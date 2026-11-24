"""Instantiate configured model adapters. Model IDs and settings come ONLY from config/models.yaml."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

MODELS_PATH = Path(__file__).resolve().parent.parent / "config" / "models.yaml"


def load_model_config(path: Path = MODELS_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["models"]


def build_adapter(model_key: str, path: Path = MODELS_PATH, client: Any = None):
    cfg = load_model_config(path)
    if model_key not in cfg:
        raise KeyError(f"Unknown model key: {model_key}")
    m = cfg[model_key]
    common = dict(model_key=model_key, model=m["model"], temperature=m.get("temperature", 0), max_tokens=m.get("max_tokens", 1024),
                  reasoning=m.get("reasoning"), parallel_tool_calls=m.get("parallel_tool_calls"), client=client)
    provider = m["provider"]
    if provider == "groq":
        from .groq_adapter import GroqAdapter
        return GroqAdapter(timeout_seconds=m.get("timeout_seconds", 60), **common)
    if provider == "google":
        from .gemini_adapter import GeminiAdapter
        return GeminiAdapter(timeout_seconds=m.get("timeout_seconds", 90), **common)
    if provider == "openrouter":  # experimental models only; never an automatic fallback for anything
        from .openrouter_adapter import OpenRouterAdapter
        return OpenRouterAdapter(timeout_seconds=m.get("timeout_seconds", 60), **common)
    if provider == "ollama":  # local models served by Ollama (no API key)
        from .ollama_adapter import OllamaAdapter
        return OllamaAdapter(timeout_seconds=m.get("timeout_seconds", 300), num_ctx=m.get("num_ctx", 16384), seed=m.get("seed", 0),
                             base_url=m.get("base_url"), keep_alive=m.get("keep_alive"), think=m.get("think"), **common)
    raise ValueError(f"Unsupported provider: {provider}")
