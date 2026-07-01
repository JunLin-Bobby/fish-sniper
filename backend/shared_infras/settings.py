"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Runtime configuration for the FishSniper FastAPI backend."""

    # 不在此讀取 .env，改由 main.py 的 load_dotenv() 先注入 os.environ。
    # BaseSettings 預設即從 os.environ 映射欄位（如 GEMINI_API_KEY → gemini_api_key）；
    # extra 未設定時 pydantic-settings 也會忽略未定義的環境變數。
    # 若改回 env_file=".env"，會與 load_dotenv() 重複載入，且 import settings 時機不同會更難追。
    #
    # model_config = SettingsConfigDict(
    #     env_file=".env",
    #     env_file_encoding="utf-8",
    #     extra="ignore",
    # )

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

    openweathermap_api_key: str | None = Field(
        default=None,
        description="OpenWeatherMap API key for /weather/current.",
    )

    gemini_api_key: str | None = Field(
        default=None,
        description="Google Gemini API key for strategy generation.",
    )

    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key for catalog models with api_key_env OPENAI_API_KEY.",
    )

    llm_models_config_path: str | None = Field(
        default=None,
        description="Optional override path to llm_models.yaml (tests or alternate catalog).",
        validation_alias=AliasChoices("LLM_MODELS_CONFIG_PATH", "llm_models_config_path"),
    )

    gemini_model: str = Field(
        default="gemini-3.0-flash",
        description="Gemini model id for structured JSON and battle plan summary.",
    )

    gemini_embedding_model: str = Field(
        default="gemini-embedding-001",
        description=(
            "Gemini embedding model id; must produce vectors of "
            "gemini_embedding_dimensions length when output_dimensionality is "
            "supplied (Matryoshka). Reuses GEMINI_API_KEY for auth."
        ),
    )

    gemini_embedding_dimensions: int = Field(
        default=1536,
        description=(
            "Vector dimension requested via Gemini's output_dimensionality. "
            "Must match the fishing_logs.embedding column type vector(N)."
        ),
    )

    gemini_embedding_timeout_seconds: float = Field(
        default=5.0,
        description="Per-request timeout (seconds) for Gemini embed_content calls.",
    )

    gemini_embedding_max_attempts: int = Field(
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

    google_oauth_client_id: str | None = Field(
        default=None,
        description="Google Cloud OAuth 2.0 Client ID for the FishSniper sign-in flow.",
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

    strategy_prompt_version: str = Field(
        default="v1_production",
        description=(
            "Bass strategy prompt template bundle under backend/strategy/prompts/<version>/. "
            "Change locally to compare CoT experiments without altering API I/O."
        ),
    )


@lru_cache
def get_settings() -> AppSettings:
    """Return cached settings instance (one per process)."""

    return AppSettings()


# FastAPI 路由注入：環境變數 / .env（CORS、API keys、JWT 等）
SettingsDep = Annotated[
    AppSettings,
    Depends(get_settings),
]
