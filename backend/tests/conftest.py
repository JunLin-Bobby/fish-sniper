"""Shared pytest fixtures for FishSniper backend tests."""

from __future__ import annotations

import os

os.environ["FRONTEND_ORIGIN"] = "http://localhost:5173"
os.environ["RATE_LIMIT_ENABLED"] = "false"

from collections.abc import Callable
from datetime import datetime, timedelta

import pytest

from shared_infras.settings import get_settings
from tests.doubles.fake_embedding import FakeFishSniperEmbeddingClient
from tests.doubles.in_memory_db import InMemoryFishSniperPersistenceAdapter


@pytest.fixture
def frozen_clock() -> tuple[Callable[[], datetime], Callable[[float], None]]:
    """Controllable UTC clock for tests that need deterministic timestamps."""

    from datetime import UTC

    current = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)

    def now_utc() -> datetime:
        return current

    def advance_seconds(seconds: float) -> None:
        nonlocal current
        current = current + timedelta(seconds=seconds)

    return now_utc, advance_seconds


@pytest.fixture
def in_memory_persistence_adapter() -> InMemoryFishSniperPersistenceAdapter:
    return InMemoryFishSniperPersistenceAdapter()


@pytest.fixture(autouse=True)
def reset_fish_sniper_backend_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stabilize JWT settings and avoid leaking lru_cache between tests."""

    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret")
    monkeypatch.setenv("SKIP_AUTH", "false")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:5173")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_fish_sniper_embedding_client() -> FakeFishSniperEmbeddingClient:
    return FakeFishSniperEmbeddingClient()
