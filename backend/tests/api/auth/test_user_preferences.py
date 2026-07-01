"""Tests for user preferences API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import create_fish_sniper_app
from shared_infras.settings import get_settings
from tests.doubles.in_memory_db import InMemoryFishSniperPersistenceAdapter
from tests.support.app_factory import install_auth_dependency_overrides
from tests.support.jwt_helpers import bearer_token_for_user

pytestmark = pytest.mark.api


def test_get_user_preferences_requires_authentication(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
) -> None:
    app = create_fish_sniper_app()
    install_auth_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
    )
    client = TestClient(app)

    response = client.get("/users/preferences")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_user_preferences_onboarding_flow(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
) -> None:
    app = create_fish_sniper_app()
    install_auth_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
    )
    client = TestClient(app)

    access_token_jwt = bearer_token_for_user(
        persistence=in_memory_persistence_adapter,
        email="prefs@example.com",
    )

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
) -> None:
    created_user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="skip@example.com",
    )

    monkeypatch.setenv("SKIP_AUTH", "true")
    monkeypatch.setenv("SKIP_AUTH_DEV_USER_ID", str(created_user_row.fish_sniper_user_id))
    get_settings.cache_clear()

    app = create_fish_sniper_app()
    install_auth_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
    )
    client = TestClient(app)

    save_response = client.post("/users/preferences", json={"region": "Tokyo"})
    assert save_response.status_code == 200

    loaded = client.get("/users/preferences")
    assert loaded.status_code == 200
    assert loaded.json()["region"] == "Tokyo"
