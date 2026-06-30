"""Resolve LLM catalog API keys from ``AppSettings`` only.

Environment variables are loaded once by pydantic-settings (``.env`` + process
env). Other modules must not call ``os.environ`` for secrets or config paths.
"""

from __future__ import annotations

from llm.models import ModelConfig
from llm.port import GenerationMisconfiguredError
from settings import AppSettings

# Catalog ``api_key_env`` values supported today (must match settings fields).
_API_KEY_ENV_TO_SETTINGS_ATTR: dict[str, str] = {
    "GEMINI_API_KEY": "gemini_api_key",
    "OPENAI_API_KEY": "openai_api_key",
}


def _api_key_from_settings(
    *,
    model_config: ModelConfig,
    backend_settings: AppSettings,
) -> str | None:
    settings_attr = _API_KEY_ENV_TO_SETTINGS_ATTR.get(model_config.api_key_env)
    if settings_attr is None:
        return None
    value = getattr(backend_settings, settings_attr, None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def has_api_key_for_model(
    *,
    model_config: ModelConfig,
    backend_settings: AppSettings,
) -> bool:
    """Return True when settings provides a non-empty key for ``model_config``."""

    return _api_key_from_settings(
        model_config=model_config,
        backend_settings=backend_settings,
    ) is not None


def resolve_api_key(
    *,
    model_config: ModelConfig,
    backend_settings: AppSettings,
) -> str:
    """Return the API key for ``model_config`` or raise ``GenerationMisconfiguredError``."""

    api_key = _api_key_from_settings(
        model_config=model_config,
        backend_settings=backend_settings,
    )
    if api_key is None:
        if model_config.api_key_env not in _API_KEY_ENV_TO_SETTINGS_ATTR:
            raise GenerationMisconfiguredError(
                f"Unsupported api_key_env={model_config.api_key_env!r} for "
                f"model_id={model_config.model_id!r}; add a settings field and mapping.",
            )
        raise GenerationMisconfiguredError(
            f"{model_config.api_key_env} is not configured for model_id={model_config.model_id!r}",
        )
    return api_key
