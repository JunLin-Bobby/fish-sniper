import asyncio
from uuid import UUID

from app.auth.jwt import decode_access_token
from app.auth.schemas import GoogleOAuthExchangeRequest
from app.auth.service import exchange_google_oauth_code
from app.core.config import Settings
from app.db.users import UserRecord
from tests.fakes import InMemoryUsersRepository


def test_google_exchange_uses_internal_user_id_as_fishsniper_subject(monkeypatch) -> None:
    """確認 Google sub 只用於找 user，而 FishSniper JWT sub 使用內部 UUID。"""

    user = UserRecord(
        id=UUID("8aef95ae-16df-4d32-99d9-730b945b34ac"),
        google_sub="google-account-123",
        email="angler@example.com",
        display_name="Test Angler",
        avatar_url="https://example.com/avatar.png",
    )
    repository = InMemoryUsersRepository([user])
    settings = Settings(
        _env_file=None,
        jwt_secret_key="phase-zero-test-secret-that-is-at-least-32-bytes",
    )

    async def fake_exchange_google_tokens(*_args, **_kwargs) -> dict[str, str]:
        """避免測試實際呼叫 Google token endpoint。"""

        return {"id_token": "verified-by-test-double"}

    def fake_verify_google_id_token(*_args, **_kwargs) -> dict[str, object]:
        """回傳代表已通過 Google signature validation 的固定 claims。"""

        return {
            "sub": user.google_sub,
            "email": user.email,
            "name": user.display_name,
            "picture": user.avatar_url,
        }

    monkeypatch.setattr(
        "app.auth.service.exchange_authorization_code_for_google_tokens",
        fake_exchange_google_tokens,
    )
    monkeypatch.setattr(
        "app.auth.service.verify_google_id_token",
        fake_verify_google_id_token,
    )

    response = asyncio.run(
        exchange_google_oauth_code(
            settings,
            GoogleOAuthExchangeRequest(
                code="authorization-code",
                code_verifier="pkce-verifier",
                redirect_uri="http://localhost:5173/auth/google/callback",
            ),
            repository,
        )
    )
    claims = decode_access_token(settings, access_token=response.access_token)

    assert claims.user_id == user.id
    assert repository.last_google_identity == {
        "google_sub": user.google_sub,
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
    }
