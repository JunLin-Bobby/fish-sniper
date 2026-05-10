"""OpenAI-backed implementation of `FishSniperEmbeddingClient`.

The class is constructed with the application settings and an optional
factory for building the underlying OpenAI SDK client. Tests inject a
factory that returns a `MagicMock` to avoid network calls; production
uses the default factory which builds a real `openai.OpenAI` client.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from embedding.port import (
    FishSniperEmbeddingClient,
    FishSniperEmbeddingMisconfiguredError,
    FishSniperEmbeddingUnavailableError,
)
from settings import FishSniperBackendSettings

logger = logging.getLogger(__name__)

_TRANSIENT_OPENAI_ERRORS: tuple[type[Exception], ...] = (
    RateLimitError,
    InternalServerError,
    APITimeoutError,
    APIConnectionError,
)

_PERMANENT_OPENAI_ERRORS: tuple[type[Exception], ...] = (
    AuthenticationError,
    PermissionDeniedError,
    BadRequestError,
    NotFoundError,
)


def _default_openai_client_factory(**kwargs: Any) -> OpenAI:
    return OpenAI(**kwargs)


class OpenAiFishSniperEmbeddingClient(FishSniperEmbeddingClient):
    """Synchronous OpenAI Embeddings adapter with bounded retry."""

    def __init__(
        self,
        *,
        fish_sniper_backend_settings: FishSniperBackendSettings,
        openai_client_factory: Callable[..., Any] = _default_openai_client_factory,
    ) -> None:
        if not fish_sniper_backend_settings.openai_api_key:
            raise FishSniperEmbeddingMisconfiguredError(
                "OPENAI_API_KEY is not configured; refusing to silently degrade.",
            )
        self._model: str = fish_sniper_backend_settings.openai_embedding_model
        self._dimensions: int = fish_sniper_backend_settings.openai_embedding_dimensions
        self._max_attempts: int = max(1, fish_sniper_backend_settings.openai_embedding_max_attempts)
        self._sdk_client = openai_client_factory(
            api_key=fish_sniper_backend_settings.openai_api_key,
            timeout=fish_sniper_backend_settings.openai_embedding_timeout_seconds,
        )

    def embed(self, *, text: str) -> list[float]:
        last_transient_error: Exception | None = None

        for attempt_index in range(self._max_attempts):
            try:
                response = self._sdk_client.embeddings.create(
                    model=self._model,
                    input=text,
                    dimensions=self._dimensions,
                )
            except _PERMANENT_OPENAI_ERRORS as permanent_error:
                logger.error(
                    "openai_embedding_misconfigured",
                    extra={
                        "model": self._model,
                        "error_type": type(permanent_error).__name__,
                    },
                )
                raise FishSniperEmbeddingMisconfiguredError(
                    f"OpenAI permanent error: {type(permanent_error).__name__}",
                ) from permanent_error
            except _TRANSIENT_OPENAI_ERRORS as transient_error:
                last_transient_error = transient_error
                logger.warning(
                    "openai_embedding_transient_failure",
                    extra={
                        "model": self._model,
                        "error_type": type(transient_error).__name__,
                        "attempt": attempt_index + 1,
                        "max_attempts": self._max_attempts,
                    },
                )
                continue

            vector = list(response.data[0].embedding)
            if len(vector) != self._dimensions:
                raise FishSniperEmbeddingMisconfiguredError(
                    f"OpenAI returned {len(vector)} dims; expected {self._dimensions}.",
                )
            return vector

        raise FishSniperEmbeddingUnavailableError(
            f"OpenAI embedding failed after {self._max_attempts} attempts.",
        ) from last_transient_error
