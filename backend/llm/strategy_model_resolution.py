"""Resolve and validate ``llm_model_id`` for POST /agent/strategy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from llm.adapters.keys import has_api_key_for_model
from llm.registry import ModelRegistry
from shared_infras.settings import AppSettings


@dataclass(frozen=True, slots=True)
class StrategyLlmModelResolution:
    """Outcome of allowlist + API-key checks before invoking the strategy graph."""

    model_id: str


@dataclass(frozen=True, slots=True)
class StrategyLlmModelResolutionError:
    """Route-level rejection (maps to HTTP 400 or 503)."""

    http_status: int
    envelope: dict[str, Any]


def resolve_strategy_llm_model_id(
    *,
    requested_llm_model_id: str | None,
    model_registry: ModelRegistry,
    backend_settings: AppSettings,
) -> StrategyLlmModelResolution | StrategyLlmModelResolutionError:
    """Resolve ``llm_model_id`` (default from catalog) and validate allowlist + configured keys."""

    if requested_llm_model_id is None:
        resolved_model_id = model_registry.default_model_id()
    else:
        resolved_model_id = requested_llm_model_id

    if not model_registry.has_model(resolved_model_id):
        return StrategyLlmModelResolutionError(
            http_status=400,
            envelope={
                "code": "INVALID_PAYLOAD",
                "message": f"Unknown llm_model_id: {resolved_model_id!r}",
            },
        )

    model_config = model_registry.get_config(resolved_model_id)
    if not has_api_key_for_model(
        model_config=model_config,
        backend_settings=backend_settings,
    ):
        return StrategyLlmModelResolutionError(
            http_status=503,
            envelope={
                "error": "Selected model is not configured for this environment",
            },
        )

    return StrategyLlmModelResolution(model_id=resolved_model_id)
