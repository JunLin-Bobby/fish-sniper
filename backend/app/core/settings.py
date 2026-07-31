"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic import Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Runtime configuration for the FastAPI backend (auth-only)."""

    frontend_origin: str = Field(
        default="http://localhost:5173",
        description="Allowed browser origin for CORS (Cloudflare Pages URL in production).",
    )

    skip_auth: bool = Field(
        default=False,
        description="If true, JWT checks are bypassed and a fixed dev user id is used.",
    )

    skip_auth_dev_user_id: str = Field(
        default="00000000-0000-0000-0000-000000000001",
        description="UUID string injected when SKIP_AUTH is enabled.",
    )

    supabase_url: str | None = Field(
        default=None,
        description="Supabase project URL for PostgREST access.",
    )

    supabase_service_role_key: str | None = Field(
        default=None,
        description="Supabase service role key (server-side only).",
    )

    jwt_secret: str = Field(
        default="change-me-in-production",
        description="HMAC secret for signing access tokens.",
    )

    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm.",
    )

    jwt_expire_days: int = Field(
        default=7,
        description="Access token lifetime in days.",
    )

    rate_limit_enabled: bool = Field(
        default=True,
        description="If false, slowapi and auth route limits are skipped (tests).",
    )

    skip_auth_rate_limit_email: str = Field(
        default="skip-auth-dev@fishsniper.local",
        description="Synthetic email key for rate limits when SKIP_AUTH is enabled.",
    )

    google_oauth_client_id: str | None = Field(
        default=None,
        description="Google Cloud OAuth 2.0 Client ID for the sign-in flow.",
    )

    google_oauth_client_secret: str | None = Field(
        default=None,
        description="Google Cloud OAuth 2.0 Client Secret (server-side only).",
    )

    google_oauth_allowed_redirect_uris: str = Field(
        default="http://localhost:5173/auth/google/callback",
        description=(
            "Comma-separated whitelist of redirect URIs accepted by the "
            "Google OAuth exchange endpoint. Must match Google Cloud Console exactly."
        ),
    )


@lru_cache
def get_settings() -> AppSettings:
    """Return cached settings instance (one per process)."""

    return AppSettings()


SettingsDep = Annotated[
    AppSettings,
    Depends(get_settings),
]
