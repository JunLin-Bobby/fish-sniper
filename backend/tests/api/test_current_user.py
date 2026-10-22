from uuid import UUID

from fastapi.testclient import TestClient

from app.auth.jwt import create_access_token
from app.core.config import Settings, get_settings
from app.main import create_app
from app.users.dependencies import get_users_repository
from app.users.schemas import UserRecord
from tests.fakes import InMemoryUsersRepository

TEST_USER = UserRecord(
    id=UUID("8aef95ae-16df-4d32-99d9-730b945b34ac"),
    google_sub="google-account-123",
    email="angler@example.com",
    display_name="Test Angler",
    avatar_url="https://example.com/avatar.png",
)


def build_test_client(*, include_user: bool = True) -> tuple[TestClient, Settings]:
    """建立使用固定 JWT secret 與記憶體 repository 的 /me 測試 client。"""

    settings = Settings(
        _env_file=None,
        jwt_secret_key="phase-zero-test-secret-that-is-at-least-32-bytes",
    )
    repository = InMemoryUsersRepository([TEST_USER] if include_user else [])
    app = create_app()

    def override_settings() -> Settings:
        """讓 protected route 使用測試專用 JWT secret。"""

        return settings

    def override_users_repository() -> InMemoryUsersRepository:
        """讓 protected route 從記憶體查詢 user。"""

        return repository

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_users_repository] = override_users_repository
    return TestClient(app), settings


def test_me_returns_current_user_for_valid_fishsniper_token() -> None:
    """確認有效 Bearer token 可取得其 sub 所代表的 FishSniper user。"""

    client, settings = build_test_client()
    access_token = create_access_token(
        settings,
        user_id=TEST_USER.id,
        email=TEST_USER.email,
    )

    response = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(TEST_USER.id),
        "email": TEST_USER.email,
        "display_name": TEST_USER.display_name,
        "avatar_url": TEST_USER.avatar_url,
    }


def test_me_returns_401_without_bearer_token() -> None:
    """確認缺少 Bearer token 的 request 無法進入 protected route。"""

    client, _settings = build_test_client()

    response = client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_returns_401_for_invalid_token() -> None:
    """確認簽章無效或格式錯誤的 token 會被拒絕。"""

    client, _settings = build_test_client()

    response = client.get(
        "/api/v1/me",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )

    assert response.status_code == 401


def test_me_returns_401_when_token_user_no_longer_exists() -> None:
    """確認 token 的 user UUID 不存在於 database 時不視為有效 session。"""

    client, settings = build_test_client(include_user=False)
    access_token = create_access_token(
        settings,
        user_id=TEST_USER.id,
        email=TEST_USER.email,
    )

    response = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 401
