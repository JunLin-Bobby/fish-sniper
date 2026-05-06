"""JWT access tokens for FishSniper users."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import HTTPException, status

from settings import FishSniperBackendSettings
from text_normalization import normalize_email_address_for_otp_login


def issue_access_token_jwt_for_fish_sniper_user_id(
    *,
    fish_sniper_user_id: UUID,
    normalized_email_address: str,
    fish_sniper_backend_settings: FishSniperBackendSettings,
) -> str:
    """Sign a JWT for the user id and normalized email (rate-limit key and auditing)."""

    now_utc = datetime.now(tz=UTC)
    expire_utc = now_utc + timedelta(days=fish_sniper_backend_settings.jwt_expire_days)
    payload = {
        "sub": str(fish_sniper_user_id),
        "email": normalized_email_address,
        "iat": int(now_utc.timestamp()),
        "exp": int(expire_utc.timestamp()),
    }
    return jwt.encode(
        payload,
        fish_sniper_backend_settings.jwt_secret,
        algorithm=fish_sniper_backend_settings.jwt_algorithm,
    )


def decode_fish_sniper_user_id_from_access_token_jwt(
    *,
    access_token_jwt: str,
    fish_sniper_backend_settings: FishSniperBackendSettings,
) -> UUID:
    """Validate JWT and return the embedded user id."""

    try:
        decoded_payload = jwt.decode(
            access_token_jwt,
            fish_sniper_backend_settings.jwt_secret,
            algorithms=[fish_sniper_backend_settings.jwt_algorithm],
        )
        subject = decoded_payload.get("sub")
        if not subject or not isinstance(subject, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token subject",
            )
        return UUID(subject)

    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token expired",
        ) from exc

    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from exc


def decode_fish_sniper_rate_limit_key_from_access_token_jwt(
    *,
    access_token_jwt: str,
    fish_sniper_backend_settings: FishSniperBackendSettings,
) -> str:
    """
    Decode JWT without raising HTTPException — used only for rate-limit keying.

    Returns a stable per-account string: normalized email when present, else legacy_sub:{uuid}.
    """

    try:
        decoded_payload = jwt.decode(
            access_token_jwt,
            fish_sniper_backend_settings.jwt_secret,
            algorithms=[fish_sniper_backend_settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        return "__fish_sniper_expired_jwt__"
    except jwt.InvalidTokenError:
        return "__fish_sniper_invalid_jwt__"

    email_claim = decoded_payload.get("email")
    if isinstance(email_claim, str) and email_claim.strip():
        return normalize_email_address_for_otp_login(email_claim)

    subject = decoded_payload.get("sub")
    if isinstance(subject, str) and subject.strip():
        return f"legacy_sub:{subject.strip()}"

    return "__fish_sniper_missing_jwt_claims__"
