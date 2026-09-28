from fastapi.testclient import TestClient

from app.auth.google_oauth import GoogleOAuthConfigurationError
from app.auth.schemas import AuthTokenResponse, GoogleOAuthExchangeRequest
from app.core.config import Settings
from app.db.dependencies import get_users_repository
from app.db.users import UsersRepository
from app.main import create_app
from tests.fakes import InMemoryUsersRepository


def test_google_oauth_exchange_returns_access_token(monkeypatch) -> None:
    """確認 auth route 會把 service 簽發的 FishSniper token 回傳給 frontend。"""

    async def fake_exchange_google_oauth_code(
        settings: Settings,
        payload: GoogleOAuthExchangeRequest,
        users_repository: UsersRepository,
    ) -> AuthTokenResponse:
        """取代外部 Google 與 Supabase 呼叫，只驗證 route 傳入的資料。"""

        assert settings.app_name == "FishSniper API"
        assert payload.code == "authorization-code"
        assert payload.code_verifier == "pkce-verifier"
        assert isinstance(users_repository, InMemoryUsersRepository)
        return AuthTokenResponse(access_token="fishsniper-access-token")

    def override_users_repository() -> InMemoryUsersRepository:
        """提供不連接 Supabase 的測試 users repository。"""

        return InMemoryUsersRepository()

    monkeypatch.setattr(
        "app.auth.router.exchange_google_oauth_code",
        fake_exchange_google_oauth_code,
    )
    app = create_app()
    app.dependency_overrides[get_users_repository] = override_users_repository
    client = TestClient(app)

    response = client.post(
        "/auth/google/exchange",
        json={
            "code": "authorization-code",
            "code_verifier": "pkce-verifier",
            "redirect_uri": "http://localhost:5173/auth/google/callback",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "fishsniper-access-token",
        "token_type": "bearer",
    }


def test_google_oauth_exchange_returns_503_when_google_credentials_missing(monkeypatch) -> None:
    """確認 auth configuration error 仍會被 route 轉成 HTTP 503。"""

    async def fake_exchange_google_oauth_code(
        settings: Settings,
        payload: GoogleOAuthExchangeRequest,
        users_repository: UsersRepository,
    ) -> AuthTokenResponse:
        """模擬 Google OAuth credentials 缺失的 service failure。"""

        raise GoogleOAuthConfigurationError("Google OAuth client credentials are not configured.")

    def override_users_repository() -> InMemoryUsersRepository:
        """提供不連接 Supabase 的測試 users repository。"""

        return InMemoryUsersRepository()

    monkeypatch.setattr(
        "app.auth.router.exchange_google_oauth_code",
        fake_exchange_google_oauth_code,
    )
    app = create_app()
    app.dependency_overrides[get_users_repository] = override_users_repository
    client = TestClient(app)

    response = client.post(
        "/auth/google/exchange",
        json={
            "code": "authorization-code",
            "code_verifier": "pkce-verifier",
            "redirect_uri": "http://localhost:5173/auth/google/callback",
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Google OAuth client credentials are not configured.",
    }
