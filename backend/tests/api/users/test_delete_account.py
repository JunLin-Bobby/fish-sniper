"""Tests for DELETE /users/me (account deletion)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from main import create_fish_sniper_app
from tests.doubles.in_memory_db import InMemoryFishSniperPersistenceAdapter
from tests.support.app_factory import install_auth_dependency_overrides
from tests.support.jwt_helpers import bearer_token_for_user

pytestmark = pytest.mark.api


def test_delete_account_requires_authentication(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
) -> None:
    app = create_fish_sniper_app()
    install_auth_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
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
) -> None:
    app = create_fish_sniper_app()
    install_auth_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
    )
    client = TestClient(app)
    token = bearer_token_for_user(
        persistence=in_memory_persistence_adapter,
        email="badconf@example.com",
    )

    response = client.request(
        "DELETE",
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation": "delete"},
    )

    assert response.status_code in (400, 422)


def test_delete_account_removes_user_preferences_and_logs(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
) -> None:
    app = create_fish_sniper_app()
    install_auth_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
    )
    client = TestClient(app)
    token = bearer_token_for_user(
        persistence=in_memory_persistence_adapter,
        email="delete@example.com",
    )

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
    reference_time_utc = datetime.now(tz=UTC)
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
