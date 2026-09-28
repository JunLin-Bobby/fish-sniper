from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import Settings


class JwtConfigurationError(RuntimeError):
    pass


class JwtAuthenticationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """通過簽章與必要欄位驗證的 FishSniper access token claims。"""

    user_id: UUID
    email: str


def create_access_token(settings: Settings, *, user_id: UUID, email: str) -> str:
    """以 FishSniper user UUID 作為 sub，簽發應用程式自己的 access token。"""

    if not settings.jwt_secret_key:
        raise JwtConfigurationError("JWT_SECRET_KEY is not configured.")

    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(days=settings.jwt_expire_days)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": "fishsniper-api",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(settings: Settings, *, access_token: str) -> AccessTokenClaims:
    """驗證 FishSniper JWT 的簽章、期限、issuer 與 user UUID subject。"""

    if not settings.jwt_secret_key:
        raise JwtConfigurationError("JWT_SECRET_KEY is not configured.")

    try:
        payload = jwt.decode(
            access_token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer="fishsniper-api",
            options={"require": ["sub", "email", "iat", "exp", "iss"]},
        )
        user_id = UUID(str(payload["sub"]))
        email = str(payload["email"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise JwtAuthenticationError("FishSniper access token is invalid or expired.") from error

    if not email:
        raise JwtAuthenticationError("FishSniper access token is missing an email.")

    return AccessTokenClaims(user_id=user_id, email=email)
