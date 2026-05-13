"""Gemini-backed implementation of ``FishSniperEmbeddingClient``.

The class is constructed with the application settings and an optional
factory for building the underlying ``google-genai`` SDK client. Tests inject
a factory that returns a ``MagicMock`` to avoid network calls; production
uses the default factory which builds a real ``genai.Client``.

Reuses ``GEMINI_API_KEY`` (also used by the chat/strategy LLM stack) since
the project pivoted to a single Google provider for both embeddings and
generation. ``output_dimensionality`` is passed via Matryoshka so the
returned vector matches ``fishing_logs.embedding`` (vector(N)) exactly.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from embedding.port import (
    FishSniperEmbeddingClient,
    FishSniperEmbeddingMisconfiguredError,
    FishSniperEmbeddingTask,
    FishSniperEmbeddingUnavailableError,
)
from settings import FishSniperBackendSettings

logger = logging.getLogger(__name__)

_TRANSIENT_GEMINI_HTTP_CODES: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})

_PERMANENT_GEMINI_HTTP_CODES: frozenset[int] = frozenset({400, 401, 403, 404})

_GEMINI_TASK_TYPE_BY_ROLE: dict[FishSniperEmbeddingTask, str] = {
    "document": "RETRIEVAL_DOCUMENT",
    "query": "RETRIEVAL_QUERY",
}


def _default_genai_client_factory(**kwargs: Any) -> genai.Client:
    return genai.Client(**kwargs)


class GeminiFishSniperEmbeddingClient(FishSniperEmbeddingClient):
    """Synchronous Google Gemini Embeddings adapter with bounded retry."""

    def __init__(
        self,
        *,
        fish_sniper_backend_settings: FishSniperBackendSettings,
        genai_client_factory: Callable[..., Any] = _default_genai_client_factory,
    ) -> None:
        if not fish_sniper_backend_settings.gemini_api_key:
            raise FishSniperEmbeddingMisconfiguredError(
                "GEMINI_API_KEY is not configured; refusing to silently degrade.",
            )
        self._model: str = fish_sniper_backend_settings.gemini_embedding_model
        self._dimensions: int = fish_sniper_backend_settings.gemini_embedding_dimensions
        self._max_attempts: int = max(
            1, fish_sniper_backend_settings.gemini_embedding_max_attempts
        )
        self._sdk_client = genai_client_factory(
            api_key=fish_sniper_backend_settings.gemini_api_key,
        )

    def embed(
        self,
        *,
        text: str,
        task: FishSniperEmbeddingTask = "document",
    ) -> list[float]:
        last_transient_error: Exception | None = None
        gemini_task_type = _GEMINI_TASK_TYPE_BY_ROLE[task]

        for attempt_index in range(self._max_attempts):
            try:
                response = self._sdk_client.models.embed_content(
                    model=self._model,
                    contents=text,
                    config=types.EmbedContentConfig(
                        task_type=gemini_task_type,
                        output_dimensionality=self._dimensions,
                    ),
                )
            except genai_errors.APIError as gem_err:
                code = getattr(gem_err, "code", None)
                if code in _PERMANENT_GEMINI_HTTP_CODES:
                    logger.error(
                        "gemini_embedding_misconfigured",
                        extra={
                            "model": self._model,
                            "code": code,
                            "error_type": type(gem_err).__name__,
                        },
                    )
                    raise FishSniperEmbeddingMisconfiguredError(
                        f"Gemini permanent error code={code}: {type(gem_err).__name__}",
                    ) from gem_err
                last_transient_error = gem_err
                logger.warning(
                    "gemini_embedding_transient_failure",
                    extra={
                        "model": self._model,
                        "code": code,
                        "error_type": type(gem_err).__name__,
                        "attempt": attempt_index + 1,
                        "max_attempts": self._max_attempts,
                    },
                )
                continue
            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                last_transient_error = net_err
                logger.warning(
                    "gemini_embedding_network_failure",
                    extra={
                        "model": self._model,
                        "error_type": type(net_err).__name__,
                        "attempt": attempt_index + 1,
                        "max_attempts": self._max_attempts,
                    },
                )
                continue

            embeddings_list = response.embeddings or []
            if not embeddings_list:
                raise FishSniperEmbeddingMisconfiguredError(
                    "Gemini returned no embeddings in response.",
                )
            vector = list(embeddings_list[0].values or [])
            if len(vector) != self._dimensions:
                raise FishSniperEmbeddingMisconfiguredError(
                    f"Gemini returned {len(vector)} dims; expected {self._dimensions}.",
                )
            return vector

        raise FishSniperEmbeddingUnavailableError(
            f"Gemini embedding failed after {self._max_attempts} attempts.",
        ) from last_transient_error
