from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FishSniper API"
    app_env: str = "development"
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:5174",
        validation_alias=AliasChoices("CORS_ORIGINS", "FRONTEND_ORIGIN"),
    )

    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_allowed_redirect_uris: str = Field(
        default="http://localhost:5173/auth/google/callback",
        validation_alias=AliasChoices(
            "GOOGLE_OAUTH_ALLOWED_REDIRECT_URIS",
            "GOOGLE_OAUTH_REDIRECT_URI",
        ),
    )

    jwt_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "JWT_SECRET"),
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 1

    supabase_url: str = ""
    supabase_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY"),
    )

    weather_request_timeout_seconds: float = 10.0
    weather_cache_ttl_seconds: int = 1800

    catch_photo_bucket: str = "catch-photos"
    catch_photo_max_bytes: int = Field(default=20 * 1024 * 1024, ge=1)
    catch_photo_max_pixels: int = Field(default=60_000_000, ge=1)
    catch_photo_max_edge: int = Field(default=2048, ge=64, le=4096)
    catch_photo_signed_url_seconds: int = Field(default=300, ge=30, le=3600)
    catch_upload_receive_seconds: float = Field(default=45, gt=0, le=120)
    catch_upload_processing_seconds: float = Field(default=30, gt=0, le=120)
    catch_cleanup_interval_seconds: int = Field(default=60, ge=0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def cors_origin_list(self) -> list[str]:
        """將逗號分隔的 CORS 設定轉成 FastAPI middleware 可使用的清單。"""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def google_oauth_allowed_redirect_uri_list(self) -> list[str]:
        """將 Google OAuth redirect URI 白名單解析成去除空白的清單。"""

        return [
            redirect_uri.strip()
            for redirect_uri in self.google_oauth_allowed_redirect_uris.split(",")
            if redirect_uri.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """建立並快取整個 FastAPI process 共用的環境設定。"""

    return Settings()
