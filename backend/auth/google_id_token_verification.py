"""Verify Google-issued ``id_token`` JWTs (RS256, JWKS).

We always perform full signature verification (never ``decode(... verify=False)``).
The JWKS resolver is injected so unit tests can sign with a local RSA keypair and
production wiring uses ``jwt.PyJWKClient`` against Google's certs URL.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Protocol

import jwt

logger = logging.getLogger(__name__)

GOOGLE_OIDC_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_ACCEPTED_GOOGLE_ISSUERS = frozenset(
    {"https://accounts.google.com", "accounts.google.com"}
)

# Google issues ``iat`` against its own clock. If the local clock is even a few
# seconds behind Google's, PyJWT raises ``ImmatureSignatureError`` ("not yet valid
# (iat)"). We disable timed validation of ``iat`` entirely (the field is still
# required to be present) — ``iat`` is not security-critical for our flow:
# replay window is already bounded by ``exp`` (validated below against
# ``reference_time_utc``), and signature/aud/iss are still enforced. ``leeway``
# remains as defense-in-depth for any future ``nbf`` claim Google might add.
_ACCEPTED_GOOGLE_CLOCK_SKEW_TOLERANCE_SECONDS = 60


class GoogleIdTokenInvalidError(Exception):
    """Raised when an id_token fails signature, issuer, audience, or expiry checks."""


@dataclass(frozen=True, slots=True)
class GoogleVerifiedIdentity:
    """Identity claims extracted from a fully-verified Google id_token."""

    email: str
    email_verified: bool
    google_subject: str


class GoogleJwksKeyResolver(Protocol):
    """Returns a signing key whose ``.key`` attribute is usable with ``jwt.decode``.

    Matches the relevant surface of ``jwt.PyJWKClient`` so production code can
    pass a real ``PyJWKClient`` and tests can inject a fake.
    """

    def get_signing_key_from_jwt(self, token: str) -> Any: ...


def verify_google_id_token_and_extract_identity(
    *,
    id_token: str,
    google_oauth_client_id: str,
    reference_time_utc: datetime,
    jwks_key_resolver: GoogleJwksKeyResolver,
) -> GoogleVerifiedIdentity:
    """Verify ``id_token`` signature/claims and return identity fields."""

    try:
        signing_key = jwks_key_resolver.get_signing_key_from_jwt(id_token)
    except jwt.exceptions.PyJWTError as exc:
        raise GoogleIdTokenInvalidError(
            "Failed to resolve Google JWKS signing key"
        ) from exc
    except Exception as exc:
        raise GoogleIdTokenInvalidError(
            "Failed to resolve Google JWKS signing key"
        ) from exc

    public_key = getattr(signing_key, "key", signing_key)

    try:
        decoded_claims: dict[str, Any] = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=google_oauth_client_id,
            leeway=_ACCEPTED_GOOGLE_CLOCK_SKEW_TOLERANCE_SECONDS,
            options={
                "require": ["exp", "iat", "aud", "iss"],
                # Expiration is validated below using ``reference_time_utc`` so the
                # function is deterministic in tests (PyJWT 2.10 has no current_time
                # injection point for decode).
                "verify_exp": False,
                # ``iat`` field must be present (via ``require`` above), but its
                # value is not used for time validation — see clock-skew comment.
                "verify_iat": False,
            },
        )
    except jwt.InvalidAudienceError as exc:
        logger.warning("Google id_token audience mismatch (expected %s)", google_oauth_client_id)
        raise GoogleIdTokenInvalidError("Google id_token audience mismatch") from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("Google id_token failed verification: %s", exc)
        raise GoogleIdTokenInvalidError("Google id_token failed verification") from exc

    if decoded_claims.get("iss") not in _ACCEPTED_GOOGLE_ISSUERS:
        raise GoogleIdTokenInvalidError("Google id_token has unexpected issuer")

    exp_timestamp = decoded_claims.get("exp")
    if not isinstance(exp_timestamp, (int, float)):
        raise GoogleIdTokenInvalidError("Google id_token missing exp claim")
    if exp_timestamp < int(reference_time_utc.timestamp()):
        raise GoogleIdTokenInvalidError("Google id_token expired (per reference time)")

    email_claim = decoded_claims.get("email")
    if not isinstance(email_claim, str) or not email_claim.strip():
        raise GoogleIdTokenInvalidError("Google id_token missing email claim")

    google_subject_claim = decoded_claims.get("sub")
    if not isinstance(google_subject_claim, str) or not google_subject_claim.strip():
        raise GoogleIdTokenInvalidError("Google id_token missing sub claim")

    email_verified_claim = decoded_claims.get("email_verified", False)
    email_verified_bool = bool(email_verified_claim)

    return GoogleVerifiedIdentity(
        email=email_claim,
        email_verified=email_verified_bool,
        google_subject=google_subject_claim,
    )


@lru_cache(maxsize=1)
def build_default_google_jwks_key_resolver() -> jwt.PyJWKClient:
    """Process-wide JWKS client for production wiring."""

    return jwt.PyJWKClient(GOOGLE_OIDC_JWKS_URL, cache_keys=True)
