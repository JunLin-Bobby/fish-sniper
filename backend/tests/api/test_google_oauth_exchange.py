from fastapi.testclient import TestClient

from app.auth.google_oauth import GoogleOAuthConfigurationError
from app.auth.schemas import AuthTokenResponse, GoogleOAuthExchangeRequest
from app.core.config import Settings
from app.main import create_app


def test_google_oauth_exchange_returns_access_token(monkeypatch) -> None:
    async def fake_exchange_google_oauth_code(
        settings: Settings,
        payload: GoogleOAuthExchangeRequest,
    ) -> AuthTokenResponse:
        assert settings.app_name == "FishSniper API"
        assert payload.code == "authorization-code"
        assert payload.code_verifier == "pkce-verifier"
        return AuthTokenResponse(access_token="fishsniper-access-token")

    monkeypatch.setattr(
        "app.auth.router.exchange_google_oauth_code",
        fake_exchange_google_oauth_code,
    )
    client = TestClient(create_app())

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
    async def fake_exchange_google_oauth_code(
        settings: Settings,
        payload: GoogleOAuthExchangeRequest,
    ) -> AuthTokenResponse:
        raise GoogleOAuthConfigurationError("Google OAuth client credentials are not configured.")

    monkeypatch.setattr(
        "app.auth.router.exchange_google_oauth_code",
        fake_exchange_google_oauth_code,
    )
    client = TestClient(create_app())

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
