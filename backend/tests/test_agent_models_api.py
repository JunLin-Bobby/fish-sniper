"""HTTP tests for GET /agent/models."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from auth.jwt_tokens import issue_access_token_jwt_for_fish_sniper_user_id
from deps import get_fish_sniper_backend_settings, get_fish_sniper_persistence_port
from main import create_fish_sniper_app
from settings import FishSniperBackendSettings
from tests.conftest import InMemoryFishSniperPersistenceAdapter


def _test_settings(
    *,
    gemini_api_key: str | None = "test-gemini-key",
    openai_api_key: str | None = None,
) -> FishSniperBackendSettings:
    return get_fish_sniper_backend_settings().model_copy(
        update={
            "gemini_api_key": gemini_api_key,
            "openai_api_key": openai_api_key,
        },
    )


def _bearer_headers(
    *,
    fish_sniper_user_id: UUID,
    normalized_email_address: str,
    settings: FishSniperBackendSettings,
) -> dict[str, str]:
    token = issue_access_token_jwt_for_fish_sniper_user_id(
        fish_sniper_user_id=fish_sniper_user_id,
        normalized_email_address=normalized_email_address,
        fish_sniper_backend_settings=settings,
    )
    return {"Authorization": f"Bearer {token}"}


def test_get_models_lists_gemini_when_only_gemini_key_configured() -> None:
    persistence = InMemoryFishSniperPersistenceAdapter()
    user_row = persistence.insert_user_row_for_normalized_email(
        normalized_email_address="models-gemini@example.com",
    )
    settings = _test_settings(openai_api_key=None)
    app = create_fish_sniper_app()
    app.dependency_overrides[get_fish_sniper_backend_settings] = lambda: settings
    app.dependency_overrides[get_fish_sniper_persistence_port] = lambda: persistence

    response = TestClient(app).get(
        "/agent/models",
        headers=_bearer_headers(
            fish_sniper_user_id=user_row.fish_sniper_user_id,
            normalized_email_address=user_row.normalized_email_address,
            settings=settings,
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["default_model_id"] == "gemini-flash"
    assert len(payload["models"]) == 1
    assert payload["models"][0]["id"] == "gemini-flash"
    assert payload["models"][0]["display_name"] == "Gemini Flash"
    assert payload["models"][0]["provider"] == "gemini"
    assert "api_key" not in response.text
    assert "temperature" not in response.text


def test_get_models_lists_both_providers_when_both_keys_configured() -> None:
    persistence = InMemoryFishSniperPersistenceAdapter()
    user_row = persistence.insert_user_row_for_normalized_email(
        normalized_email_address="models-both@example.com",
    )
    settings = _test_settings(openai_api_key="test-openai-key")
    app = create_fish_sniper_app()
    app.dependency_overrides[get_fish_sniper_backend_settings] = lambda: settings
    app.dependency_overrides[get_fish_sniper_persistence_port] = lambda: persistence

    response = TestClient(app).get(
        "/agent/models",
        headers=_bearer_headers(
            fish_sniper_user_id=user_row.fish_sniper_user_id,
            normalized_email_address=user_row.normalized_email_address,
            settings=settings,
        ),
    )

    assert response.status_code == 200
    model_ids = {entry["id"] for entry in response.json()["models"]}
    assert model_ids == {"gemini-flash", "gpt-4o-mini"}


def test_get_models_returns_empty_list_when_no_keys_configured() -> None:
    persistence = InMemoryFishSniperPersistenceAdapter()
    user_row = persistence.insert_user_row_for_normalized_email(
        normalized_email_address="models-none@example.com",
    )
    settings = _test_settings(gemini_api_key=None, openai_api_key=None)
    app = create_fish_sniper_app()
    app.dependency_overrides[get_fish_sniper_backend_settings] = lambda: settings
    app.dependency_overrides[get_fish_sniper_persistence_port] = lambda: persistence

    response = TestClient(app).get(
        "/agent/models",
        headers=_bearer_headers(
            fish_sniper_user_id=user_row.fish_sniper_user_id,
            normalized_email_address=user_row.normalized_email_address,
            settings=settings,
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["models"] == []
    assert payload["default_model_id"] == "gemini-flash"


def test_get_models_without_auth_returns_401() -> None:
    app = create_fish_sniper_app()
    response = TestClient(app).get("/agent/models")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
