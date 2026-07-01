"""Unit tests for LLM text-generation adapters and router (mocked SDKs)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai import errors as genai_errors
from openai import APIStatusError

from llm.adapters.factory import build_text_adapter
from llm.adapters.gemini import GeminiTextAdapter
from llm.adapters.keys import resolve_api_key
from llm.adapters.openai import OpenAITextAdapter
from llm.models import ModelConfig
from llm.port import GenerationMisconfiguredError, GenerationUnavailableError
from llm.registry import load_registry
from llm.router import TextGenerationRouter
from shared_infras.settings import AppSettings


def _gemini_config() -> ModelConfig:
    return ModelConfig(
        model_id="gemini-flash",
        provider="gemini",
        provider_model="gemini-3-flash-preview",
        display_name="Gemini Flash",
        temperature=0.8,
        api_key_env="GEMINI_API_KEY",
        timeout_seconds=30.0,
    )


def _openai_config() -> ModelConfig:
    return ModelConfig(
        model_id="gpt-4o-mini",
        provider="openai",
        provider_model="gpt-4o-mini",
        display_name="GPT-4o Mini",
        temperature=0.8,
        api_key_env="OPENAI_API_KEY",
        timeout_seconds=30.0,
    )


def _make_gemini_api_error(code: int) -> genai_errors.APIError:
    response_json = {"error": {"message": f"simulated {code}", "status": "SIMULATED"}}
    if 500 <= code < 600:
        return genai_errors.ServerError(code, response_json)
    return genai_errors.ClientError(code, response_json)


def test_resolve_api_key_gemini_from_settings() -> None:
    settings = AppSettings(gemini_api_key="secret-gemini")
    assert (
        resolve_api_key(model_config=_gemini_config(), backend_settings=settings) == "secret-gemini"
    )


def test_resolve_api_key_openai_from_settings() -> None:
    settings = AppSettings(openai_api_key="secret-openai")
    assert (
        resolve_api_key(model_config=_openai_config(), backend_settings=settings) == "secret-openai"
    )


def test_resolve_api_key_missing_raises() -> None:
    settings = AppSettings(gemini_api_key=None)
    with pytest.raises(GenerationMisconfiguredError, match="GEMINI_API_KEY"):
        resolve_api_key(model_config=_gemini_config(), backend_settings=settings)


@pytest.mark.asyncio
async def test_gemini_adapter_returns_llm_generation_result() -> None:
    response = MagicMock()
    response.text = '{"strategy": "ok"}'
    sdk_client = MagicMock()
    sdk_client.aio.models.generate_content = AsyncMock(return_value=response)
    adapter = GeminiTextAdapter(
        model_config=_gemini_config(),
        api_key="test-key",
        genai_client_factory=lambda **_: sdk_client,
    )

    result = await adapter.generate_text(
        system_prompt="You are a bass coach.",
        user_prompt="Generate JSON.",
    )

    assert result.raw_text == '{"strategy": "ok"}'
    assert result.provider == "gemini"
    assert result.model_id == "gemini-flash"
    assert result.provider_model == "gemini-3-flash-preview"
    assert result.temperature == 0.8
    sdk_client.aio.models.generate_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_gemini_adapter_maps_429_to_unavailable() -> None:
    sdk_client = MagicMock()
    sdk_client.aio.models.generate_content = AsyncMock(
        side_effect=_make_gemini_api_error(429),
    )
    adapter = GeminiTextAdapter(
        model_config=_gemini_config(),
        api_key="test-key",
        genai_client_factory=lambda **_: sdk_client,
    )

    with pytest.raises(GenerationUnavailableError, match="429"):
        await adapter.generate_text(system_prompt="sys", user_prompt="user")


@pytest.mark.asyncio
async def test_gemini_adapter_maps_401_to_misconfigured() -> None:
    sdk_client = MagicMock()
    sdk_client.aio.models.generate_content = AsyncMock(
        side_effect=_make_gemini_api_error(401),
    )
    adapter = GeminiTextAdapter(
        model_config=_gemini_config(),
        api_key="test-key",
        genai_client_factory=lambda **_: sdk_client,
    )

    with pytest.raises(GenerationMisconfiguredError, match="401"):
        await adapter.generate_text(system_prompt="sys", user_prompt="user")


@pytest.mark.asyncio
async def test_openai_adapter_returns_llm_generation_result() -> None:
    choice = MagicMock()
    choice.message.content = '{"lure": "spinnerbait"}'
    completion = MagicMock()
    completion.choices = [choice]
    openai_client = MagicMock()
    openai_client.chat.completions.create = AsyncMock(return_value=completion)
    adapter = OpenAITextAdapter(
        model_config=_openai_config(),
        api_key="test-key",
        openai_client_factory=lambda **_: openai_client,
    )

    result = await adapter.generate_text(
        system_prompt="You are a bass coach.",
        user_prompt="Generate JSON.",
    )

    assert result.raw_text == '{"lure": "spinnerbait"}'
    assert result.provider == "openai"
    assert result.model_id == "gpt-4o-mini"
    openai_client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_openai_adapter_maps_503_to_unavailable() -> None:
    openai_client = MagicMock()
    openai_client.chat.completions.create = AsyncMock(
        side_effect=APIStatusError(
            message="overloaded",
            response=MagicMock(status_code=503),
            body=None,
        ),
    )
    adapter = OpenAITextAdapter(
        model_config=_openai_config(),
        api_key="test-key",
        openai_client_factory=lambda **_: openai_client,
    )

    with pytest.raises(GenerationUnavailableError, match="503"):
        await adapter.generate_text(system_prompt="sys", user_prompt="user")


@pytest.mark.asyncio
async def test_router_delegates_to_gemini_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = load_registry()
    settings = AppSettings(gemini_api_key="test-key")
    response = MagicMock()
    response.text = "router-ok"
    sdk_client = MagicMock()
    sdk_client.aio.models.generate_content = AsyncMock(return_value=response)

    def _fake_build(*, model_config: ModelConfig, backend_settings: AppSettings):
        _ = backend_settings
        return GeminiTextAdapter(
            model_config=model_config,
            api_key="test-key",
            genai_client_factory=lambda **_: sdk_client,
        )

    monkeypatch.setattr("llm.router.build_text_adapter", _fake_build)
    router = TextGenerationRouter(model_registry=registry)

    result = await router.generate_text(
        model_id="gemini-flash",
        system_prompt="sys",
        user_prompt="user",
        backend_settings=settings,
    )

    assert result.raw_text == "router-ok"
    assert result.model_id == "gemini-flash"


def test_build_text_adapter_unknown_provider_raises() -> None:
    bad_config = ModelConfig.model_construct(
        model_id="bad",
        provider="unknown",  # type: ignore[arg-type]
        provider_model="x",
        display_name="Bad",
        temperature=0.5,
        api_key_env="GEMINI_API_KEY",
    )
    settings = AppSettings(gemini_api_key="k")
    with pytest.raises(GenerationMisconfiguredError, match="Unsupported provider"):
        build_text_adapter(model_config=bad_config, backend_settings=settings)
