"""Tests for P1 email OTP auth and user preferences (TDD)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from deps import (
    get_fish_sniper_persistence_port,
    get_otp_code_generator_callable,
    get_reference_time_utc_callable,
    get_transactional_email_sender_port,
)
from main import create_fish_sniper_app
from tests.conftest import (
    ExplodingTransactionalEmailSenderAdapter,
    InMemoryFishSniperPersistenceAdapter,
    RecordingTransactionalEmailSenderAdapter,
)


def _install_p1_dependency_overrides(
    app,
    *,
    fish_sniper_persistence: InMemoryFishSniperPersistenceAdapter,
    transactional_email_sender: RecordingTransactionalEmailSenderAdapter
    | ExplodingTransactionalEmailSenderAdapter,
    reference_time_utc_callable: Callable[[], datetime],
    otp_code_generator: Callable[[], str] | None = None,
) -> None:
    app.dependency_overrides[get_fish_sniper_persistence_port] = (
        lambda: fish_sniper_persistence
    )
    app.dependency_overrides[get_transactional_email_sender_port] = (
        lambda: transactional_email_sender
    )
    app.dependency_overrides[get_reference_time_utc_callable] = (
        lambda: reference_time_utc_callable
    )
    if otp_code_generator is not None:
        app.dependency_overrides[get_otp_code_generator_callable] = lambda: otp_code_generator


def test_send_email_otp_returns_success_envelope(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    recording_email_sender_adapter: RecordingTransactionalEmailSenderAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _advance_seconds = frozen_clock
    app = create_fish_sniper_app()
    _install_p1_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        transactional_email_sender=recording_email_sender_adapter,
        reference_time_utc_callable=now_utc,
        otp_code_generator=lambda: "123456",
    )
    client = TestClient(app)

    response = client.post("/auth/send-otp", json={"email": "Angler@Example.com"})

    assert response.status_code == 200
    assert response.json() == {"message": "OTP sent"}
    assert recording_email_sender_adapter.recipient_and_otp_tuple_list == [
        ("angler@example.com", "123456"),
    ]


def test_send_email_otp_rate_limited_within_sixty_seconds(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    recording_email_sender_adapter: RecordingTransactionalEmailSenderAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, advance_seconds = frozen_clock
    app = create_fish_sniper_app()
    _install_p1_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        transactional_email_sender=recording_email_sender_adapter,
        reference_time_utc_callable=now_utc,
        otp_code_generator=lambda: "123456",
    )
    client = TestClient(app)

    first_response = client.post("/auth/send-otp", json={"email": "rate@example.com"})
    assert first_response.status_code == 200

    advance_seconds(30)
    second_response = client.post("/auth/send-otp", json={"email": "rate@example.com"})
    assert second_response.status_code == 429
    assert second_response.json() == {
        "error": "Too many requests, please wait 60 seconds",
    }


def test_send_email_otp_email_delivery_failure_returns_502(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    exploding_email_sender_adapter: ExplodingTransactionalEmailSenderAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _advance_seconds = frozen_clock
    app = create_fish_sniper_app()
    _install_p1_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        transactional_email_sender=exploding_email_sender_adapter,
        reference_time_utc_callable=now_utc,
        otp_code_generator=lambda: "123456",
    )
    client = TestClient(app)

    response = client.post("/auth/send-otp", json={"email": "fail@example.com"})
    assert response.status_code == 502
    assert response.json() == {"error": "Email delivery failed"}


def test_verify_email_otp_rejects_invalid_code(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    recording_email_sender_adapter: RecordingTransactionalEmailSenderAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _advance_seconds = frozen_clock
    app = create_fish_sniper_app()
    _install_p1_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        transactional_email_sender=recording_email_sender_adapter,
        reference_time_utc_callable=now_utc,
        otp_code_generator=lambda: "123456",
    )
    client = TestClient(app)

    send_response = client.post("/auth/send-otp", json={"email": "verify@example.com"})
    assert send_response.status_code == 200

    verify_response = client.post(
        "/auth/verify-otp",
        json={"email": "verify@example.com", "otp": "000000"},
    )
    assert verify_response.status_code == 400
    assert verify_response.json() == {"error": "Invalid or expired OTP"}


def test_verify_email_otp_issues_jwt_for_new_user(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    recording_email_sender_adapter: RecordingTransactionalEmailSenderAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _advance_seconds = frozen_clock
    app = create_fish_sniper_app()
    _install_p1_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        transactional_email_sender=recording_email_sender_adapter,
        reference_time_utc_callable=now_utc,
        otp_code_generator=lambda: "654321",
    )
    client = TestClient(app)

    assert client.post("/auth/send-otp", json={"email": "new@example.com"}).status_code == 200

    verify_response = client.post(
        "/auth/verify-otp",
        json={"email": "new@example.com", "otp": "654321"},
    )
    assert verify_response.status_code == 200
    payload = verify_response.json()
    assert payload["is_new_user"] is True
    assert isinstance(payload["access_token"], str)
    assert len(payload["access_token"]) > 20


def test_verify_email_otp_marks_existing_user_as_not_new(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    recording_email_sender_adapter: RecordingTransactionalEmailSenderAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _advance_seconds = frozen_clock
    in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="old@example.com",
    )
    app = create_fish_sniper_app()
    _install_p1_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        transactional_email_sender=recording_email_sender_adapter,
        reference_time_utc_callable=now_utc,
        otp_code_generator=lambda: "111222",
    )
    client = TestClient(app)

    assert client.post("/auth/send-otp", json={"email": "old@example.com"}).status_code == 200
    verify_response = client.post(
        "/auth/verify-otp",
        json={"email": "old@example.com", "otp": "111222"},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["is_new_user"] is False


def test_get_user_preferences_requires_authentication(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    recording_email_sender_adapter: RecordingTransactionalEmailSenderAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _advance_seconds = frozen_clock
    app = create_fish_sniper_app()
    _install_p1_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        transactional_email_sender=recording_email_sender_adapter,
        reference_time_utc_callable=now_utc,
        otp_code_generator=lambda: "123456",
    )
    client = TestClient(app)

    response = client.get("/users/preferences")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_user_preferences_onboarding_flow(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    recording_email_sender_adapter: RecordingTransactionalEmailSenderAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _advance_seconds = frozen_clock
    app = create_fish_sniper_app()
    _install_p1_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        transactional_email_sender=recording_email_sender_adapter,
        reference_time_utc_callable=now_utc,
        otp_code_generator=lambda: "888999",
    )
    client = TestClient(app)

    assert client.post("/auth/send-otp", json={"email": "prefs@example.com"}).status_code == 200
    verify_response = client.post(
        "/auth/verify-otp",
        json={"email": "prefs@example.com", "otp": "888999"},
    )
    assert verify_response.status_code == 200
    access_token_jwt = verify_response.json()["access_token"]

    empty_prefs = client.get(
        "/users/preferences",
        headers={"Authorization": f"Bearer {access_token_jwt}"},
    )
    assert empty_prefs.status_code == 200
    assert empty_prefs.json() == {"region": None, "onboarding_completed": False}

    save_response = client.post(
        "/users/preferences",
        headers={"Authorization": f"Bearer {access_token_jwt}"},
        json={"region": "Boston"},
    )
    assert save_response.status_code == 200
    assert save_response.json() == {"message": "Preferences saved"}

    loaded_prefs = client.get(
        "/users/preferences",
        headers={"Authorization": f"Bearer {access_token_jwt}"},
    )
    assert loaded_prefs.status_code == 200
    assert loaded_prefs.json() == {"region": "Boston", "onboarding_completed": True}


def test_skip_auth_uses_configured_dev_user_for_preferences(
    monkeypatch: pytest.MonkeyPatch,
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    recording_email_sender_adapter: RecordingTransactionalEmailSenderAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _advance_seconds = frozen_clock
    created_user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="skip@example.com",
    )

    monkeypatch.setenv("SKIP_AUTH", "true")
    monkeypatch.setenv("SKIP_AUTH_DEV_USER_ID", str(created_user_row.fish_sniper_user_id))
    from settings import get_fish_sniper_backend_settings

    get_fish_sniper_backend_settings.cache_clear()

    app = create_fish_sniper_app()
    _install_p1_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        transactional_email_sender=recording_email_sender_adapter,
        reference_time_utc_callable=now_utc,
    )
    client = TestClient(app)

    save_response = client.post("/users/preferences", json={"region": "Tokyo"})
    assert save_response.status_code == 200

    loaded = client.get("/users/preferences")
    assert loaded.status_code == 200
    assert loaded.json()["region"] == "Tokyo"
