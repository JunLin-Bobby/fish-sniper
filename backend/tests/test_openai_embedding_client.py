"""Tests for the OpenAI embedding client adapter (P4 Part 1, Task 2)."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

from embedding.openai_embedding_client import OpenAiFishSniperEmbeddingClient
from embedding.port import (
    FishSniperEmbeddingMisconfiguredError,
    FishSniperEmbeddingUnavailableError,
)
from settings import FishSniperBackendSettings

_DUMMY_REQUEST = httpx.Request("POST", "https://api.openai.com/v1/embeddings")


def _build_settings(*, max_attempts: int = 2, dimensions: int = 1536) -> FishSniperBackendSettings:
    return FishSniperBackendSettings(
        openai_api_key="test-key-not-real",
        openai_embedding_model="text-embedding-3-small",
        openai_embedding_dimensions=dimensions,
        openai_embedding_timeout_seconds=1.0,
        openai_embedding_max_attempts=max_attempts,
    )


def _http_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code=status_code, request=_DUMMY_REQUEST)


def _embedding_response_with_floats(vector: list[float]) -> MagicMock:
    """Build an object that mimics OpenAI Embeddings.create() result shape."""

    response = MagicMock()
    response.data = [MagicMock(embedding=vector)]
    return response


def _client_with_mock_sdk(
    settings: FishSniperBackendSettings,
    *,
    side_effects: list,
) -> tuple[OpenAiFishSniperEmbeddingClient, MagicMock]:
    """Construct the adapter with `embeddings.create` programmed to a sequence of outcomes."""

    sdk_client = MagicMock()
    sdk_client.embeddings.create.side_effect = side_effects
    adapter = OpenAiFishSniperEmbeddingClient(
        fish_sniper_backend_settings=settings,
        openai_client_factory=lambda **_: sdk_client,
    )
    return adapter, sdk_client


def test_embed_returns_vector_on_success() -> None:
    settings = _build_settings()
    expected_vector = [0.0] * settings.openai_embedding_dimensions
    expected_vector[0] = 0.5
    adapter, sdk_client = _client_with_mock_sdk(
        settings,
        side_effects=[_embedding_response_with_floats(expected_vector)],
    )

    result = adapter.embed(text="hello")

    assert result == expected_vector
    sdk_client.embeddings.create.assert_called_once()


def test_embed_raises_misconfigured_when_dimensions_mismatch() -> None:
    settings = _build_settings(dimensions=1536)
    adapter, _ = _client_with_mock_sdk(
        settings,
        side_effects=[_embedding_response_with_floats([0.0] * 768)],
    )

    with pytest.raises(FishSniperEmbeddingMisconfiguredError):
        adapter.embed(text="hello")


def test_embed_retries_on_rate_limit_and_succeeds() -> None:
    settings = _build_settings(max_attempts=2)
    expected_vector = [0.1] * settings.openai_embedding_dimensions
    rate_limit = RateLimitError("rate limited", response=_http_response(429), body=None)
    adapter, sdk_client = _client_with_mock_sdk(
        settings,
        side_effects=[rate_limit, _embedding_response_with_floats(expected_vector)],
    )

    result = adapter.embed(text="hello")

    assert result == expected_vector
    assert sdk_client.embeddings.create.call_count == 2


@pytest.mark.parametrize(
    "transient_error",
    [
        RateLimitError("rate limited", response=_http_response(429), body=None),
        InternalServerError("server error", response=_http_response(500), body=None),
        APITimeoutError(request=_DUMMY_REQUEST),
        APIConnectionError(request=_DUMMY_REQUEST),
    ],
)
def test_embed_raises_unavailable_after_exhausting_retries(transient_error: Exception) -> None:
    settings = _build_settings(max_attempts=2)
    adapter, sdk_client = _client_with_mock_sdk(
        settings,
        side_effects=[transient_error, transient_error],
    )

    with pytest.raises(FishSniperEmbeddingUnavailableError):
        adapter.embed(text="hello")

    assert sdk_client.embeddings.create.call_count == 2


@pytest.mark.parametrize(
    "permanent_error",
    [
        AuthenticationError("bad key", response=_http_response(401), body=None),
        PermissionDeniedError("forbidden", response=_http_response(403), body=None),
        BadRequestError("bad request", response=_http_response(400), body=None),
        NotFoundError("not found", response=_http_response(404), body=None),
    ],
)
def test_embed_raises_misconfigured_immediately_on_permanent_error(
    permanent_error: Exception,
) -> None:
    settings = _build_settings(max_attempts=2)
    adapter, sdk_client = _client_with_mock_sdk(
        settings,
        side_effects=[permanent_error],
    )

    with pytest.raises(FishSniperEmbeddingMisconfiguredError):
        adapter.embed(text="hello")

    assert sdk_client.embeddings.create.call_count == 1


def test_embed_request_passes_model_dimensions_and_input() -> None:
    settings = _build_settings()
    success_response = _embedding_response_with_floats(
        [0.0] * settings.openai_embedding_dimensions,
    )
    adapter, sdk_client = _client_with_mock_sdk(
        settings,
        side_effects=[success_response],
    )

    adapter.embed(text="quick brown fox")

    call_kwargs = sdk_client.embeddings.create.call_args.kwargs
    assert call_kwargs["model"] == settings.openai_embedding_model
    assert call_kwargs["dimensions"] == settings.openai_embedding_dimensions
    assert call_kwargs["input"] == "quick brown fox"
