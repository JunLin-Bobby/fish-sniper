"""Tests for DELETE /users/me (account deletion)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

from fastapi.testclient import TestClient

from main import create_fish_sniper_app
from tests.conftest import (
    InMemoryFishSniperPersistenceAdapter,
    RecordingTransactionalEmailSenderAdapter,
)
from tests.test_auth_and_user_preferences import _install_p1_dependency_overrides


def _bearer_token_for_email(
    client: TestClient,
    *,
    email: str,
    otp: str,
) -> str:
    assert client.post("/auth/send-otp", json={"email": email}).status_code == 200
    verify_response = client.post("/auth/verify-otp", json={"email": email, "otp": otp})
    assert verify_response.status_code == 200
    return verify_response.json()["access_token"]


def test_delete_account_requires_authentication(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    recording_email_sender_adapter: RecordingTransactionalEmailSenderAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _ = frozen_clock
    app = create_fish_sniper_app()
    _install_p1_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        transactional_email_sender=recording_email_sender_adapter,
        reference_time_utc_callable=now_utc,
    )
    client = TestClient(app)

    response = client.request(
        "DELETE",
        "/users/me",
        json={"confirmation": "Delete"},
    )

    assert response.status_code == 401


def test_delete_account_rejects_wrong_confirmation(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    recording_email_sender_adapter: RecordingTransactionalEmailSenderAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
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
    token = _bearer_token_for_email(client, email="badconf@example.com", otp="123456")

    response = client.request(
        "DELETE",
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation": "delete"},
    )

    assert response.status_code in (400, 422)


def test_delete_account_removes_user_preferences_and_logs(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    recording_email_sender_adapter: RecordingTransactionalEmailSenderAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _ = frozen_clock
    app = create_fish_sniper_app()
    _install_p1_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        transactional_email_sender=recording_email_sender_adapter,
        reference_time_utc_callable=now_utc,
        otp_code_generator=lambda: "654321",
    )
    client = TestClient(app)
    token = _bearer_token_for_email(client, email="delete@example.com", otp="654321")

    save_response = client.post(
        "/users/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"region": "Boston"},
    )
    assert save_response.status_code == 200

    user_row = in_memory_persistence_adapter.fetch_user_row_by_normalized_email(
        normalized_email_address="delete@example.com",
    )
    assert user_row is not None
    reference_time_utc = now_utc()
    in_memory_persistence_adapter.insert_fishing_log_for_user_id(
        fish_sniper_user_id=user_row.fish_sniper_user_id,
        log_date=date(2026, 5, 1),
        fishing_location="Pond",
        fishing_scene="lake",
        target_species="Largemouth Bass",
        water_depth_m=1.0,
        lure_type="Jig",
        lure_color="Black",
        retrieve_speed="Slow",
        caught_count=1,
        weight_lb=None,
        length_cm=None,
        temperature_c=20.0,
        wind_speed_ms=1.0,
        pressure_hpa=1010,
        condition_code="sunny",
        notes="",
        embedding=[0.1] * 1536,
        embedding_text_version=1,
        reference_time_utc=reference_time_utc,
    )

    delete_response = client.request(
        "DELETE",
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation": "Delete"},
    )
    assert delete_response.status_code == 204

    assert (
        in_memory_persistence_adapter.fetch_user_row_by_normalized_email(
            normalized_email_address="delete@example.com",
        )
        is None
    )
    assert (
        in_memory_persistence_adapter.fetch_user_preferences_row_for_user_id(
            fish_sniper_user_id=user_row.fish_sniper_user_id,
        )
        is None
    )
    assert (
        in_memory_persistence_adapter.list_fishing_logs_for_user_id_ordered_by_date_desc(
            fish_sniper_user_id=user_row.fish_sniper_user_id,
        )
        == []
    )

    prefs_after = client.get(
        "/users/preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert prefs_after.status_code == 401
