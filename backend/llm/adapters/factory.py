"""Construct provider-specific text-generation adapters from catalog config."""

from __future__ import annotations

from llm.adapters.gemini import GeminiTextAdapter
from llm.adapters.keys import resolve_api_key
from llm.adapters.openai import OpenAITextAdapter
from llm.models import ModelConfig
from llm.port import GenerationMisconfiguredError, LlmTextGenerationClient
from settings import AppSettings


def build_text_adapter(
    *,
    model_config: ModelConfig,
    backend_settings: AppSettings,
) -> LlmTextGenerationClient:
    """Return a provider adapter for ``model_config`` with API key resolved from settings/env."""

    api_key = resolve_api_key(model_config=model_config, backend_settings=backend_settings)
    if model_config.provider == "gemini":
        return GeminiTextAdapter(model_config=model_config, api_key=api_key)
    if model_config.provider == "openai":
        return OpenAITextAdapter(model_config=model_config, api_key=api_key)
    raise GenerationMisconfiguredError(
        f"Unsupported provider {model_config.provider!r} for model_id={model_config.model_id!r}",
    )
