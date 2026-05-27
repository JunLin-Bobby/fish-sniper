"""Unit tests for POST /agent/strategy llm_model_id resolution."""

from __future__ import annotations

from llm.registry import load_registry
from llm.strategy_model_resolution import (
    StrategyLlmModelResolution,
    StrategyLlmModelResolutionError,
    resolve_strategy_llm_model_id,
)
from settings import FishSniperBackendSettings


def test_resolve_uses_catalog_default_when_omitted() -> None:
    registry = load_registry()
    settings = FishSniperBackendSettings(gemini_api_key="k")

    result = resolve_strategy_llm_model_id(
        requested_llm_model_id=None,
        model_registry=registry,
        backend_settings=settings,
    )

    assert isinstance(result, StrategyLlmModelResolution)
    assert result.model_id == registry.default_model_id()


def test_resolve_unknown_model_returns_400_envelope() -> None:
    registry = load_registry()
    settings = FishSniperBackendSettings(gemini_api_key="k")

    result = resolve_strategy_llm_model_id(
        requested_llm_model_id="unknown-model",
        model_registry=registry,
        backend_settings=settings,
    )

    assert isinstance(result, StrategyLlmModelResolutionError)
    assert result.http_status == 400
    assert result.envelope["code"] == "INVALID_PAYLOAD"
    assert "unknown-model" in result.envelope["message"]


def test_resolve_configured_model_without_key_returns_503() -> None:
    registry = load_registry()
    settings = FishSniperBackendSettings(gemini_api_key=None, openai_api_key=None)

    result = resolve_strategy_llm_model_id(
        requested_llm_model_id="gemini-flash",
        model_registry=registry,
        backend_settings=settings,
    )

    assert isinstance(result, StrategyLlmModelResolutionError)
    assert result.http_status == 503
    assert "error" in result.envelope
