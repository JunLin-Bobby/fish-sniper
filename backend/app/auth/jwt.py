from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import Settings


class JwtConfigurationError(RuntimeError):
    pass


def create_access_token(settings: Settings, *, subject: str, email: str) -> str:
    if not settings.jwt_secret_key:
        raise JwtConfigurationError("JWT_SECRET_KEY is not configured.")

    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "email": email,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": "fishsniper-api",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
