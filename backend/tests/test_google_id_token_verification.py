"""Unit tests for backend/auth/google_id_token_verification.py (TDD RED → GREEN).

We sign test ``id_token``s with a locally-generated RSA key and inject a fake JWKS
resolver so production code paths never touch the real Google JWKS endpoint.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from auth.google_id_token_verification import (
    GoogleIdTokenInvalidError,
    GoogleVerifiedIdentity,
    verify_google_id_token_and_extract_identity,
)

_AUDIENCE_CLIENT_ID = "fishsniper-test-client.apps.googleusercontent.com"
_DEFAULT_KID = "test-key-1"


def _generate_rsa_keypair() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _make_signed_id_token(
    *,
    private_key: rsa.RSAPrivateKey,
    claims: dict[str, Any],
    kid: str = _DEFAULT_KID,
) -> str:
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )


class _FakeJwksKeyResolver:
    """Returns ``rsa.RSAPublicKey`` for a known kid; raises for anything else."""

    def __init__(self, *, kid: str, private_key: rsa.RSAPrivateKey) -> None:
        self._kid = kid
        self._public_key = private_key.public_key()

    def get_signing_key_from_jwt(self, token: str):
        unverified_header = jwt.get_unverified_header(token)
        if unverified_header.get("kid") != self._kid:
            raise jwt.exceptions.PyJWKClientError(
                f"Unknown kid {unverified_header.get('kid')!r}"
            )

        class _SigningKey:
            def __init__(self, key: object) -> None:
                self.key = key

        return _SigningKey(self._public_key)


def _valid_claims(*, now_utc: datetime, email: str = "user@example.com") -> dict[str, Any]:
    return {
        "iss": "https://accounts.google.com",
        "aud": _AUDIENCE_CLIENT_ID,
        "sub": "google-subject-12345",
        "email": email,
        "email_verified": True,
        "iat": int(now_utc.timestamp()),
        "exp": int((now_utc + timedelta(minutes=5)).timestamp()),
    }


def test_verify_returns_identity_for_valid_signed_id_token() -> None:
    now_utc = datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC)
    private_key = _generate_rsa_keypair()
    id_token = _make_signed_id_token(
        private_key=private_key,
        claims=_valid_claims(now_utc=now_utc),
    )
    resolver = _FakeJwksKeyResolver(kid=_DEFAULT_KID, private_key=private_key)

    identity = verify_google_id_token_and_extract_identity(
        id_token=id_token,
        google_oauth_client_id=_AUDIENCE_CLIENT_ID,
        reference_time_utc=now_utc,
        jwks_key_resolver=resolver,
    )

    assert isinstance(identity, GoogleVerifiedIdentity)
    assert identity.email == "user@example.com"
    assert identity.email_verified is True
    assert identity.google_subject == "google-subject-12345"


def test_verify_accepts_legacy_issuer_accounts_google_com() -> None:
    now_utc = datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC)
    private_key = _generate_rsa_keypair()
    claims = _valid_claims(now_utc=now_utc)
    claims["iss"] = "accounts.google.com"
    id_token = _make_signed_id_token(private_key=private_key, claims=claims)
    resolver = _FakeJwksKeyResolver(kid=_DEFAULT_KID, private_key=private_key)

    identity = verify_google_id_token_and_extract_identity(
        id_token=id_token,
        google_oauth_client_id=_AUDIENCE_CLIENT_ID,
        reference_time_utc=now_utc,
        jwks_key_resolver=resolver,
    )
    assert identity.email == "user@example.com"


def test_verify_rejects_wrong_audience() -> None:
    now_utc = datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC)
    private_key = _generate_rsa_keypair()
    claims = _valid_claims(now_utc=now_utc)
    claims["aud"] = "someone-else.apps.googleusercontent.com"
    id_token = _make_signed_id_token(private_key=private_key, claims=claims)
    resolver = _FakeJwksKeyResolver(kid=_DEFAULT_KID, private_key=private_key)

    with pytest.raises(GoogleIdTokenInvalidError):
        verify_google_id_token_and_extract_identity(
            id_token=id_token,
            google_oauth_client_id=_AUDIENCE_CLIENT_ID,
            reference_time_utc=now_utc,
            jwks_key_resolver=resolver,
        )


def test_verify_rejects_wrong_issuer() -> None:
    now_utc = datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC)
    private_key = _generate_rsa_keypair()
    claims = _valid_claims(now_utc=now_utc)
    claims["iss"] = "https://malicious.example.com"
    id_token = _make_signed_id_token(private_key=private_key, claims=claims)
    resolver = _FakeJwksKeyResolver(kid=_DEFAULT_KID, private_key=private_key)

    with pytest.raises(GoogleIdTokenInvalidError):
        verify_google_id_token_and_extract_identity(
            id_token=id_token,
            google_oauth_client_id=_AUDIENCE_CLIENT_ID,
            reference_time_utc=now_utc,
            jwks_key_resolver=resolver,
        )


def test_verify_rejects_expired_token() -> None:
    now_utc = datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC)
    private_key = _generate_rsa_keypair()
    claims = _valid_claims(now_utc=now_utc - timedelta(hours=1))
    claims["exp"] = int((now_utc - timedelta(minutes=1)).timestamp())
    id_token = _make_signed_id_token(private_key=private_key, claims=claims)
    resolver = _FakeJwksKeyResolver(kid=_DEFAULT_KID, private_key=private_key)

    with pytest.raises(GoogleIdTokenInvalidError):
        verify_google_id_token_and_extract_identity(
            id_token=id_token,
            google_oauth_client_id=_AUDIENCE_CLIENT_ID,
            reference_time_utc=now_utc,
            jwks_key_resolver=resolver,
        )


def test_verify_rejects_tampered_signature() -> None:
    now_utc = datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC)
    private_key = _generate_rsa_keypair()
    id_token = _make_signed_id_token(
        private_key=private_key,
        claims=_valid_claims(now_utc=now_utc),
    )

    different_keypair = _generate_rsa_keypair()
    resolver_with_wrong_key = _FakeJwksKeyResolver(
        kid=_DEFAULT_KID,
        private_key=different_keypair,
    )

    with pytest.raises(GoogleIdTokenInvalidError):
        verify_google_id_token_and_extract_identity(
            id_token=id_token,
            google_oauth_client_id=_AUDIENCE_CLIENT_ID,
            reference_time_utc=now_utc,
            jwks_key_resolver=resolver_with_wrong_key,
        )


def test_verify_ignores_iat_time_value_so_clock_skew_cannot_break_login() -> None:
    """``iat`` field must be present but its time value is not checked.

    Even an ``iat`` well beyond any reasonable ``leeway`` (here +10 minutes) must
    not cause ``ImmatureSignatureError``. We still validate ``exp`` against
    ``reference_time_utc`` separately.
    """

    now_utc = datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC)
    private_key = _generate_rsa_keypair()
    claims = _valid_claims(now_utc=now_utc)
    claims["iat"] = int((now_utc + timedelta(minutes=10)).timestamp())
    claims["exp"] = int((now_utc + timedelta(minutes=15)).timestamp())
    id_token = _make_signed_id_token(private_key=private_key, claims=claims)
    resolver = _FakeJwksKeyResolver(kid=_DEFAULT_KID, private_key=private_key)

    identity = verify_google_id_token_and_extract_identity(
        id_token=id_token,
        google_oauth_client_id=_AUDIENCE_CLIENT_ID,
        reference_time_utc=now_utc,
        jwks_key_resolver=resolver,
    )
    assert identity.email == "user@example.com"


def test_verify_preserves_email_verified_false_for_caller_to_gate() -> None:
    now_utc = datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC)
    private_key = _generate_rsa_keypair()
    claims = _valid_claims(now_utc=now_utc)
    claims["email_verified"] = False
    id_token = _make_signed_id_token(private_key=private_key, claims=claims)
    resolver = _FakeJwksKeyResolver(kid=_DEFAULT_KID, private_key=private_key)

    identity = verify_google_id_token_and_extract_identity(
        id_token=id_token,
        google_oauth_client_id=_AUDIENCE_CLIENT_ID,
        reference_time_utc=now_utc,
        jwks_key_resolver=resolver,
    )
    assert identity.email_verified is False
