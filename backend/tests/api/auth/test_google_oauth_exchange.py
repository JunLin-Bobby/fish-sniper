"""Integration tests for POST /auth/google/exchange (TDD RED → GREEN).

Strategy:
* Override the FastAPI deps that wrap the two outbound collaborators (Google token
  endpoint and JWKS resolver) with locally-signed test fixtures, so the suite never
  performs real HTTPS.
* The persistence layer is the in-memory adapter from ``tests/conftest.py``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from auth.deps import (
    get_google_jwks_key_resolver,
    get_google_oauth_token_exchange_callable,
)
from auth.google_id_token_verification import GoogleJwksKeyResolver
from main import create_fish_sniper_app
from persistence.deps import get_persistence
from shared_infras.settings import get_settings
from shared_infras.time import get_reference_time_utc_callable
from tests.doubles.in_memory_db import InMemoryFishSniperPersistenceAdapter

_TEST_CLIENT_ID = "fishsniper-test-client.apps.googleusercontent.com"
_TEST_CLIENT_SECRET = "test-client-secret"
_TEST_REDIRECT_URI = "http://localhost:5173/auth/google/callback"
_TEST_KID = "test-key-1"


@pytest.fixture(autouse=True)
def configure_google_oauth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide GOOGLE_OAUTH_* settings to the cached settings instance."""

    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", _TEST_CLIENT_ID)
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", _TEST_CLIENT_SECRET)
    monkeypatch.setenv("GOOGLE_OAUTH_ALLOWED_REDIRECT_URIS", _TEST_REDIRECT_URI)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _generate_rsa_keypair() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _sign_id_token(
    *,
    private_key: rsa.RSAPrivateKey,
    claims: dict[str, Any],
) -> str:
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": _TEST_KID})


def _valid_google_claims(*, email: str = "user@example.com") -> dict[str, Any]:
    now_utc = datetime.now(tz=UTC)
    return {
        "iss": "https://accounts.google.com",
        "aud": _TEST_CLIENT_ID,
        "sub": "google-sub-12345",
        "email": email,
        "email_verified": True,
        "iat": int(now_utc.timestamp()),
        "exp": int((now_utc + timedelta(minutes=5)).timestamp()),
    }


class _FakeJwksKeyResolver(GoogleJwksKeyResolver):
    def __init__(self, *, kid: str, private_key: rsa.RSAPrivateKey) -> None:
        self._kid = kid
        self._public_key = private_key.public_key()

    def get_signing_key_from_jwt(self, token: str) -> Any:
        unverified_header = jwt.get_unverified_header(token)
        if unverified_header.get("kid") != self._kid:
            raise jwt.exceptions.PyJWKClientError(
                f"Unknown kid {unverified_header.get('kid')!r}"
            )

        class _SigningKey:
            def __init__(self, key: object) -> None:
                self.key = key

        return _SigningKey(self._public_key)


def _install_google_oauth_dependency_overrides(
    app: Any,
    *,
    fish_sniper_persistence: InMemoryFishSniperPersistenceAdapter,
    reference_time_utc_callable: Callable[[], datetime],
    fake_token_response: dict[str, Any],
    jwks_key_resolver: GoogleJwksKeyResolver,
) -> None:
    app.dependency_overrides[get_persistence] = lambda: fish_sniper_persistence
    app.dependency_overrides[get_reference_time_utc_callable] = lambda: reference_time_utc_callable
    app.dependency_overrides[get_google_oauth_token_exchange_callable] = (
        lambda: lambda **_kwargs: fake_token_response
    )
    app.dependency_overrides[get_google_jwks_key_resolver] = lambda: jwks_key_resolver


def test_google_exchange_creates_new_user_and_returns_jwt(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _ = frozen_clock
    private_key = _generate_rsa_keypair()
    signed_id_token = _sign_id_token(
        private_key=private_key,
        claims=_valid_google_claims(email="new@example.com"),
    )

    app = create_fish_sniper_app()
    _install_google_oauth_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
        fake_token_response={"id_token": signed_id_token},
        jwks_key_resolver=_FakeJwksKeyResolver(kid=_TEST_KID, private_key=private_key),
    )
    client = TestClient(app)

    response = client.post(
        "/auth/google/exchange",
        json={
            "code": "abc",
            "code_verifier": "verifier",
            "redirect_uri": _TEST_REDIRECT_URI,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_new_user"] is True
    assert isinstance(body["access_token"], str) and body["access_token"].count(".") == 2


def test_google_exchange_merges_existing_user_by_email(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="merge@example.com",
    )
    now_utc, _ = frozen_clock

    private_key = _generate_rsa_keypair()
    signed_id_token = _sign_id_token(
        private_key=private_key,
        claims=_valid_google_claims(email="Merge@Example.COM"),
    )

    app = create_fish_sniper_app()
    _install_google_oauth_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
        fake_token_response={"id_token": signed_id_token},
        jwks_key_resolver=_FakeJwksKeyResolver(kid=_TEST_KID, private_key=private_key),
    )
    client = TestClient(app)

    response = client.post(
        "/auth/google/exchange",
        json={
            "code": "abc",
            "code_verifier": "verifier",
            "redirect_uri": _TEST_REDIRECT_URI,
        },
    )

    assert response.status_code == 200
    assert response.json()["is_new_user"] is False


def test_google_exchange_rejects_redirect_uri_not_in_whitelist(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _ = frozen_clock
    private_key = _generate_rsa_keypair()
    app = create_fish_sniper_app()
    _install_google_oauth_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
        fake_token_response={"id_token": "unused"},
        jwks_key_resolver=_FakeJwksKeyResolver(kid=_TEST_KID, private_key=private_key),
    )
    client = TestClient(app)

    response = client.post(
        "/auth/google/exchange",
        json={
            "code": "abc",
            "code_verifier": "verifier",
            "redirect_uri": "https://malicious.example.com/auth/google/callback",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"error": "Invalid Google OAuth exchange request"}


def test_google_exchange_returns_403_when_email_not_verified(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _ = frozen_clock
    private_key = _generate_rsa_keypair()
    claims = _valid_google_claims(email="unverified@example.com")
    claims["email_verified"] = False
    signed_id_token = _sign_id_token(private_key=private_key, claims=claims)

    app = create_fish_sniper_app()
    _install_google_oauth_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
        fake_token_response={"id_token": signed_id_token},
        jwks_key_resolver=_FakeJwksKeyResolver(kid=_TEST_KID, private_key=private_key),
    )
    client = TestClient(app)

    response = client.post(
        "/auth/google/exchange",
        json={
            "code": "abc",
            "code_verifier": "verifier",
            "redirect_uri": _TEST_REDIRECT_URI,
        },
    )

    assert response.status_code == 403
    assert response.json() == {"error": "Google account email is not verified"}


def test_google_exchange_returns_500_when_client_id_unset(
    monkeypatch: pytest.MonkeyPatch,
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    # ``delenv`` alone does not win over ``SettingsConfigDict(env_file=".env")``:
    # pydantic-settings still reads ``GOOGLE_OAUTH_CLIENT_ID`` from ``backend/.env``.
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "")
    get_settings.cache_clear()
    now_utc, _ = frozen_clock
    private_key = _generate_rsa_keypair()

    app = create_fish_sniper_app()
    _install_google_oauth_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
        fake_token_response={"id_token": "unused"},
        jwks_key_resolver=_FakeJwksKeyResolver(kid=_TEST_KID, private_key=private_key),
    )
    client = TestClient(app)

    response = client.post(
        "/auth/google/exchange",
        json={
            "code": "abc",
            "code_verifier": "verifier",
            "redirect_uri": _TEST_REDIRECT_URI,
        },
    )

    assert response.status_code == 500
