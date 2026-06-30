"""Route text-generation requests to the correct provider adapter."""

from __future__ import annotations

import logging

from llm.adapters.factory import build_text_adapter
from llm.models import LlmGenerationResult, ModelConfig
from llm.port import LlmTextGenerationClient
from llm.registry import ModelRegistry
from settings import AppSettings

logger = logging.getLogger(__name__)


class TextGenerationRouter:
    """Resolve a logical ``model_id`` to a provider adapter and run generation."""

    def __init__(self, *, model_registry: ModelRegistry) -> None:
        self._model_registry = model_registry
        self._adapter_cache_by_model_id: dict[str, LlmTextGenerationClient] = {}

    @property
    def model_registry(self) -> ModelRegistry:
        return self._model_registry

    async def generate_text(
        self,
        *,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        backend_settings: AppSettings,
    ) -> LlmGenerationResult:
        """Generate text using the model catalog entry for ``model_id``."""

        model_config = self._model_registry.get_config(model_id)
        adapter = self._get_adapter(
            model_config=model_config,
            backend_settings=backend_settings,
        )
        logger.debug(
            "TextGenerationRouter.generate_text model_id=%s provider=%s",
            model_id,
            model_config.provider,
        )
        return await adapter.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    def _get_adapter(
        self,
        *,
        model_config: ModelConfig,
        backend_settings: AppSettings,
    ) -> LlmTextGenerationClient:
        cached = self._adapter_cache_by_model_id.get(model_config.model_id)
        if cached is not None:
            return cached
        adapter = build_text_adapter(
            model_config=model_config,
            backend_settings=backend_settings,
        )
        self._adapter_cache_by_model_id[model_config.model_id] = adapter
        return adapter
