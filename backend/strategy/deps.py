"""Strategy domain FastAPI dependency providers (LLM catalog + router)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from llm.registry import ModelRegistry, load_registry
from llm.router import TextGenerationRouter
from shared_infras.settings import get_settings

_model_registry_singleton: ModelRegistry | None = None
_text_generation_router_singleton: TextGenerationRouter | None = None


def get_model_registry() -> ModelRegistry:
    """Return the process-wide LLM model catalog (loaded from ``llm_models.yaml``)."""

    global _model_registry_singleton

    if _model_registry_singleton is None:
        _model_registry_singleton = load_registry(
            backend_settings=get_settings(),
        )
    return _model_registry_singleton


def get_text_generation_router() -> TextGenerationRouter:
    """Return the process-wide text-generation router (registry + provider adapters)."""

    global _text_generation_router_singleton

    if _text_generation_router_singleton is None:
        _text_generation_router_singleton = TextGenerationRouter(
            model_registry=get_model_registry(),
        )
    return _text_generation_router_singleton


ModelRegistryDep = Annotated[
    ModelRegistry,
    Depends(get_model_registry),
]
TextGenerationRouterDep = Annotated[
    TextGenerationRouter,
    Depends(get_text_generation_router),
]
