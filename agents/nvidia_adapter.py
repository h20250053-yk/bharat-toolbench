"""NVIDIA API Catalog (build.nvidia.com) adapter: OpenAI-compatible chat completions. EXPERIMENTAL models only.

Reuses OpenRouterAdapter unchanged (same ModelTurn/ToolCall normalisation, error taxonomy, malformed-argument handling,
usage normalisation, key redaction) with NVIDIA's endpoint and key variable:

- base URL https://integrate.api.nvidia.com/v1 (NVIDIA's documented OpenAI-compatible endpoint)
- API key read ONLY from NVIDIA_API_KEY; SDK retries disabled (max_retries=0)
- provider-specific request fields come only from config `extra_body` (e.g. Nemotron 3's
  `chat_template_kwargs: {enable_thinking: false}`); OpenRouter's `reasoning: {effort}` object is NOT supported here
Model ID and settings come ONLY from config/models.yaml.
"""
from __future__ import annotations

from typing import Any

from .openrouter_adapter import OpenRouterAdapter


class NvidiaAdapter(OpenRouterAdapter):
    BASE_URL = "https://integrate.api.nvidia.com/v1"
    API_KEY_ENV = "NVIDIA_API_KEY"
    PROVIDER = "nvidia"
    PROVIDER_LABEL = "NVIDIA"

    def __init__(self, *, reasoning: str | None = None, **kw: Any):
        if reasoning:
            raise ValueError("NVIDIA adapter: `reasoning` is an OpenRouter field; configure provider fields via `extra_body`")
        super().__init__(reasoning=None, **kw)
