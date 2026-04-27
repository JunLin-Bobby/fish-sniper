"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FishSniperBackendSettings(BaseSettings):
    """Runtime configuration for the FishSniper FastAPI backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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

    resend_api_key: str | None = Field(
        default=None,
        description="Resend API key for transactional email.",
    )

    resend_from_email: str = Field(
        default="FishSniper <no-reply@example.com>",
        description="From header for OTP emails (must be a verified sender in Resend).",
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


@lru_cache
def get_fish_sniper_backend_settings() -> FishSniperBackendSettings:
    """Return cached settings instance (one per process)."""

    return FishSniperBackendSettings()
