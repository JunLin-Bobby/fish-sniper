"""Embedding FastAPI dependency providers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from embedding.port import FishSniperEmbeddingClient
from shared_infras.settings import get_settings

_embedding_client_singleton: FishSniperEmbeddingClient | None = None


def get_fish_sniper_embedding_client() -> FishSniperEmbeddingClient:
    """Return the process-wide Gemini embedding client."""

    global _embedding_client_singleton
    from embedding.gemini_embedding_client import GeminiFishSniperEmbeddingClient

    if _embedding_client_singleton is None:
        settings = get_settings()
        _embedding_client_singleton = GeminiFishSniperEmbeddingClient(
            fish_sniper_backend_settings=settings,
        )
    return _embedding_client_singleton


FishSniperEmbeddingClientDep = Annotated[
    FishSniperEmbeddingClient,
    Depends(get_fish_sniper_embedding_client),
]
