"""Tests for the Gemini embedding client adapter (P4 Part 1, Task 2).

Mocks the ``google-genai`` SDK so no test hits the real Gemini API.
"""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import httpx
import pytest
from google.genai import errors as genai_errors

from embedding.gemini_embedding_client import GeminiFishSniperEmbeddingClient
from embedding.port import (
    FishSniperEmbeddingMisconfiguredError,
    FishSniperEmbeddingUnavailableError,
)
from settings import FishSniperBackendSettings


def _build_settings(*, max_attempts: int = 2, dimensions: int = 1536) -> FishSniperBackendSettings:
    return FishSniperBackendSettings(
        gemini_api_key="test-key-not-real",
        gemini_embedding_model="gemini-embedding-001",
        gemini_embedding_dimensions=dimensions,
        gemini_embedding_timeout_seconds=1.0,
        gemini_embedding_max_attempts=max_attempts,
    )


def _make_gemini_api_error(code: int) -> genai_errors.APIError:
    """Build a real ``google-genai`` error instance with a given HTTP-like code."""

    response_json = {
        "error": {"message": f"simulated {code}", "status": "SIMULATED"},
    }
    if 500 <= code < 600:
        return genai_errors.ServerError(code, response_json)
    return genai_errors.ClientError(code, response_json)


def _embed_response_with_floats(vector: list[float]) -> MagicMock:
    """Mimic the SDK ``embed_content()`` result shape: ``.embeddings[0].values``."""

    response = MagicMock()
    embedding_obj = MagicMock()
    embedding_obj.values = vector
    response.embeddings = [embedding_obj]
    return response


def _client_with_mock_sdk(
    settings: FishSniperBackendSettings,
    *,
    side_effects: list,
) -> tuple[GeminiFishSniperEmbeddingClient, MagicMock]:
    """Construct the adapter with ``models.embed_content`` programmed to a sequence of outcomes."""

    sdk_client = MagicMock()
    sdk_client.models.embed_content.side_effect = side_effects
    adapter = GeminiFishSniperEmbeddingClient(
        fish_sniper_backend_settings=settings,
        genai_client_factory=lambda **_: sdk_client,
    )
    return adapter, sdk_client


def test_embed_returns_vector_on_success() -> None:
    settings = _build_settings()
    expected_vector = [0.0] * settings.gemini_embedding_dimensions
    expected_vector[0] = 0.5
    adapter, sdk_client = _client_with_mock_sdk(
        settings,
        side_effects=[_embed_response_with_floats(expected_vector)],
    )

    result = adapter.embed(text="hello")

    assert result == expected_vector
    sdk_client.models.embed_content.assert_called_once()


def test_embed_raises_misconfigured_when_dimensions_mismatch() -> None:
    settings = _build_settings(dimensions=1536)
    adapter, _ = _client_with_mock_sdk(
        settings,
        side_effects=[_embed_response_with_floats([0.0] * 768)],
    )

    with pytest.raises(FishSniperEmbeddingMisconfiguredError):
        adapter.embed(text="hello")


def test_embed_retries_on_rate_limit_and_succeeds() -> None:
    settings = _build_settings(max_attempts=2)
    expected_vector = [0.1] * settings.gemini_embedding_dimensions
    adapter, sdk_client = _client_with_mock_sdk(
        settings,
        side_effects=[
            _make_gemini_api_error(429),
            _embed_response_with_floats(expected_vector),
        ],
    )

    result = adapter.embed(text="hello")

    assert result == expected_vector
    assert sdk_client.models.embed_content.call_count == 2


@pytest.mark.parametrize(
    "transient_factory",
    [
        lambda: _make_gemini_api_error(429),
        lambda: _make_gemini_api_error(500),
        lambda: _make_gemini_api_error(503),
        lambda: httpx.TimeoutException("simulated timeout"),
        lambda: httpx.ConnectError("simulated connect error"),
    ],
)
def test_embed_raises_unavailable_after_exhausting_retries(
    transient_factory: Callable[[], Exception],
) -> None:
    settings = _build_settings(max_attempts=2)
    adapter, sdk_client = _client_with_mock_sdk(
        settings,
        side_effects=[transient_factory(), transient_factory()],
    )

    with pytest.raises(FishSniperEmbeddingUnavailableError):
        adapter.embed(text="hello")

    assert sdk_client.models.embed_content.call_count == 2


@pytest.mark.parametrize("permanent_code", [400, 401, 403, 404])
def test_embed_raises_misconfigured_immediately_on_permanent_error(
    permanent_code: int,
) -> None:
    settings = _build_settings(max_attempts=2)
    adapter, sdk_client = _client_with_mock_sdk(
        settings,
        side_effects=[_make_gemini_api_error(permanent_code)],
    )

    with pytest.raises(FishSniperEmbeddingMisconfiguredError):
        adapter.embed(text="hello")

    assert sdk_client.models.embed_content.call_count == 1


def test_embed_request_passes_model_dimensions_task_type_and_contents() -> None:
    settings = _build_settings()
    success_response = _embed_response_with_floats(
        [0.0] * settings.gemini_embedding_dimensions,
    )
    adapter, sdk_client = _client_with_mock_sdk(
        settings,
        side_effects=[success_response],
    )

    adapter.embed(text="quick brown fox")

    call_kwargs = sdk_client.models.embed_content.call_args.kwargs
    assert call_kwargs["model"] == settings.gemini_embedding_model
    assert call_kwargs["contents"] == "quick brown fox"
    config = call_kwargs["config"]
    assert config.output_dimensionality == settings.gemini_embedding_dimensions
    assert config.task_type == "RETRIEVAL_DOCUMENT"


def test_embed_request_passes_retrieval_query_task_when_task_is_query() -> None:
    settings = _build_settings()
    success_response = _embed_response_with_floats(
        [0.0] * settings.gemini_embedding_dimensions,
    )
    adapter, sdk_client = _client_with_mock_sdk(
        settings,
        side_effects=[success_response],
    )

    adapter.embed(text="rag query text", task="query")

    config = sdk_client.models.embed_content.call_args.kwargs["config"]
    assert config.task_type == "RETRIEVAL_QUERY"
    settings = FishSniperBackendSettings(
        gemini_api_key=None,
        gemini_embedding_model="gemini-embedding-001",
        gemini_embedding_dimensions=1536,
        gemini_embedding_timeout_seconds=1.0,
        gemini_embedding_max_attempts=2,
    )

    with pytest.raises(FishSniperEmbeddingMisconfiguredError):
        GeminiFishSniperEmbeddingClient(
            fish_sniper_backend_settings=settings,
            genai_client_factory=lambda **_: MagicMock(),
        )
