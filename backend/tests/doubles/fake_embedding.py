"""Fake embedding client for tests."""

from __future__ import annotations

from collections.abc import Callable

from embedding.port import FishSniperEmbeddingClient, FishSniperEmbeddingTask


class FakeFishSniperEmbeddingClient(FishSniperEmbeddingClient):
    """Configurable fake used by every backend test to avoid real Gemini calls.

    Default behaviour: return a fixed 1536-d vector. Tests that exercise the
    transient-failure path inject a different fake (see
    ``test_logs_api`` POST-Gemini-fail case) by overriding the FastAPI
    dependency directly.
    """

    def __init__(
        self,
        *,
        vector: list[float] | None = None,
        error_factory: Callable[[], Exception] | None = None,
    ) -> None:
        self._vector: list[float] = vector if vector is not None else [0.001] * 1536
        self._error_factory = error_factory
        self.call_count = 0

    def embed(
        self,
        *,
        text: str,
        task: FishSniperEmbeddingTask = "document",
    ) -> list[float]:
        _ = text
        _ = task
        self.call_count += 1
        if self._error_factory is not None:
            raise self._error_factory()
        return list(self._vector)


