"""HTTP tests that Google OAuth exchange rate limits return 429 when exceeded."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.auth.deps import (
    get_google_jwks_key_resolver,
    get_google_oauth_token_exchange_callable,
)
from app.auth.google_id_token import GoogleVerifiedIdentity
from app.core.settings import get_settings
from app.core.time import get_reference_time_utc_callable
from app.db.deps import get_persistence
from app.main import create_app
from tests.doubles.in_memory_db import InMemoryPersistenceAdapter


def test_google_oauth_exchange_returns_429_when_per_ip_minute_limit_exceeded(
    monkeypatch: pytest.MonkeyPatch,
    in_memory_persistence_adapter: InMemoryPersistenceAdapter,
    frozen_clock,
) -> None:
    """POST /auth/google/exchange is limited to 30/minute per client IP."""

    now_utc, _advance = frozen_clock
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-google-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-google-client-secret")
    monkeypatch.setenv(
        "GOOGLE_OAUTH_ALLOWED_REDIRECT_URIS",
        "http://localhost:5173/auth/google/callback",
    )
    get_settings.cache_clear()

    def fake_token_exchange(**_kwargs: object) -> dict[str, str]:
        return {"id_token": "fake-id-token"}

    def fake_verify_identity(**_kwargs: object) -> GoogleVerifiedIdentity:
        return GoogleVerifiedIdentity(
            email="rate-limit@example.com",
            email_verified=True,
            google_subject="rate-limit-sub",
        )

    monkeypatch.setattr(
        "app.auth.service.verify_google_id_token_and_extract_identity",
        fake_verify_identity,
    )

    app = create_app()
    app.dependency_overrides[get_persistence] = lambda: in_memory_persistence_adapter
    app.dependency_overrides[get_reference_time_utc_callable] = lambda: now_utc
    app.dependency_overrides[get_google_oauth_token_exchange_callable] = (
        lambda: fake_token_exchange
    )
    app.dependency_overrides[get_google_jwks_key_resolver] = lambda: MagicMock()

    client = TestClient(app)
    request_body = {
        "code": "fake-code",
        "code_verifier": "fake-verifier",
        "redirect_uri": "http://localhost:5173/auth/google/callback",
    }

    for _ in range(30):
        response = client.post("/auth/google/exchange", json=request_body)
        assert response.status_code == 200

    rate_limited_response = client.post("/auth/google/exchange", json=request_body)
    assert rate_limited_response.status_code == 429
    assert rate_limited_response.json() == {"error": "Too many requests"}
