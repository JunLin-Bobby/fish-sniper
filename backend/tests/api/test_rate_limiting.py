"""HTTP tests that rate limits return 429 when exceeded."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from auth.jwt_tokens import issue_access_token_jwt_for_fish_sniper_user_id
from main import create_fish_sniper_app
from persistence.deps import get_persistence
from shared_infras.settings import AppSettings, get_settings
from tests.doubles.in_memory_db import InMemoryFishSniperPersistenceAdapter


def _enable_rate_limits(monkeypatch: pytest.MonkeyPatch) -> AppSettings:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.rate_limit_enabled is True
    return settings


def test_slowapi_bearer_route_returns_429_when_minute_limit_exceeded(
    monkeypatch: pytest.MonkeyPatch,
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
) -> None:
    """GET /agent/models is limited to 120/minute per email via @fish_sniper_api_limiter.limit."""

    settings = _enable_rate_limits(monkeypatch).model_copy(
        update={"gemini_api_key": "test-gemini-key"},
    )
    normalized_email_address = f"rate-limit-models-{uuid4()}@example.com"
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address=normalized_email_address,
    )
    app = create_fish_sniper_app()
    app.dependency_overrides[get_persistence] = (
        lambda: in_memory_persistence_adapter
    )
    token = issue_access_token_jwt_for_fish_sniper_user_id(
        fish_sniper_user_id=user_row.fish_sniper_user_id,
        normalized_email_address=normalized_email_address,
        fish_sniper_backend_settings=settings,
    )
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}

    for _ in range(120):
        response = client.get("/agent/models", headers=headers)
        assert response.status_code == 200

    rate_limited_response = client.get("/agent/models", headers=headers)
    assert rate_limited_response.status_code == 429
    assert rate_limited_response.json() == {"error": "Too many requests"}
