"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import AliasChoices, Field
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

    openweathermap_api_key: str | None = Field(
        default=None,
        description="OpenWeatherMap API key for /weather/current.",
    )

    gemini_api_key: str | None = Field(
        default=None,
        description="Google Gemini API key for strategy generation.",
    )

    gemini_model: str = Field(
        default="gemini-3.0-flash",
        description="Gemini model id for structured JSON and battle plan summary.",
    )

    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key for embedding writes and similarity-search queries.",
    )

    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description=(
            "OpenAI embedding model id; must produce vectors of "
            "openai_embedding_dimensions length."
        ),
    )

    openai_embedding_dimensions: int = Field(
        default=1536,
        description=(
            "Vector dimension produced by openai_embedding_model. Must match the "
            "fishing_logs.embedding column type vector(N)."
        ),
    )

    openai_embedding_timeout_seconds: float = Field(
        default=5.0,
        description="Per-request timeout for OpenAI embedding calls.",
    )

    openai_embedding_max_attempts: int = Field(
        default=2,
        description=(
            "Maximum number of attempts (initial + retries) per embedding call. "
            "2 means: try once, retry once on transient failure, then give up."
        ),
    )

    langfuse_public_key: str | None = Field(
        default=None,
        description="Langfuse public key (optional; tracing disabled if unset).",
    )

    langfuse_secret_key: str | None = Field(
        default=None,
        description="Langfuse secret key (optional).",
    )

    langfuse_base_url: str | None = Field(
        default=None,
        description=(
            "Langfuse base URL (official env: LANGFUSE_BASE_URL), "
            "e.g. https://us.cloud.langfuse.com or https://cloud.langfuse.com. "
            "Passed to the SDK as ``host``."
        ),
    )

    weather_fail: bool = Field(
        default=False,
        description="If true, weather fetch always fails (local dev/tests). Env: WEATHER_FAIL.",
        validation_alias=AliasChoices("WEATHER_FAIL", "weather_fail"),
    )

    rate_limit_enabled: bool = Field(
        default=True,
        description="If false, slowapi and email bucket limits are skipped (tests).",
    )

    skip_auth_rate_limit_email: str = Field(
        default="skip-auth-dev@fishsniper.local",
        description="Synthetic email key for rate limits when SKIP_AUTH is enabled.",
    )


@lru_cache
def get_fish_sniper_backend_settings() -> FishSniperBackendSettings:
    """Return cached settings instance (one per process)."""

    return FishSniperBackendSettings()
