"""JWT access tokens for FishSniper users."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import HTTPException, status

from settings import FishSniperBackendSettings


def issue_access_token_jwt_for_fish_sniper_user_id(
    *,
    fish_sniper_user_id: UUID,
    fish_sniper_backend_settings: FishSniperBackendSettings,
) -> str:
    """Sign a short-lived JWT for the given user id."""

    now_utc = datetime.now(tz=UTC)
    expire_utc = now_utc + timedelta(days=fish_sniper_backend_settings.jwt_expire_days)
    payload = {
        "sub": str(fish_sniper_user_id),
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
