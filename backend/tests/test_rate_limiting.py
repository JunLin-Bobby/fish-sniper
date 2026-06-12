"""HTTP tests that rate limits return 429 when exceeded."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from auth.jwt_tokens import issue_access_token_jwt_for_fish_sniper_user_id
from deps import get_fish_sniper_persistence_port
from main import create_fish_sniper_app
from settings import FishSniperBackendSettings, get_fish_sniper_backend_settings
from tests.conftest import (
    InMemoryFishSniperPersistenceAdapter,
    RecordingTransactionalEmailSenderAdapter,
)
from tests.test_auth_and_user_preferences import _install_p1_dependency_overrides


def _enable_rate_limits(monkeypatch: pytest.MonkeyPatch) -> FishSniperBackendSettings:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    get_fish_sniper_backend_settings.cache_clear()
    settings = get_fish_sniper_backend_settings()
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
    app.dependency_overrides[get_fish_sniper_persistence_port] = (
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


def test_verify_otp_returns_429_when_per_minute_limit_exceeded(
    monkeypatch: pytest.MonkeyPatch,
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    recording_email_sender_adapter: RecordingTransactionalEmailSenderAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    """POST /auth/verify-otp is limited to 60/minute per email (enforce_* path)."""

    _enable_rate_limits(monkeypatch)
    now_utc, _ = frozen_clock
    app = create_fish_sniper_app()
    _install_p1_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        transactional_email_sender=recording_email_sender_adapter,
        reference_time_utc_callable=now_utc,
        otp_code_generator=lambda: "123456",
    )
    client = TestClient(app)
    normalized_email_address = f"verify-rate-{uuid4()}@example.com"

    assert (
        client.post("/auth/send-otp", json={"email": normalized_email_address}).status_code
        == 200
    )

    verify_payload = {"email": normalized_email_address, "otp": "000000"}
    for _ in range(60):
        response = client.post("/auth/verify-otp", json=verify_payload)
        assert response.status_code != 429

    rate_limited_response = client.post("/auth/verify-otp", json=verify_payload)
    assert rate_limited_response.status_code == 429
    assert rate_limited_response.json() == {"error": "Too many requests"}
