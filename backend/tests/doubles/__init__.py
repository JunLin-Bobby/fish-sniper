"""Test doubles."""

from tests.doubles.fake_embedding import FakeFishSniperEmbeddingClient
from tests.doubles.in_memory_db import InMemoryFishSniperPersistenceAdapter

__all__ = ["FakeFishSniperEmbeddingClient", "InMemoryFishSniperPersistenceAdapter"]
