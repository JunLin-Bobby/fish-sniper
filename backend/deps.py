"""FastAPI dependency providers.

Routes 透過下方 Annotated[..., Depends(...)] 注入依賴；測試以 app.dependency_overrides 替換實作。
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from email_delivery.port import TransactionalEmailSenderPort
from email_delivery.resend_transactional_email_adapter import ResendTransactionalEmailSenderAdapter
from embedding.port import FishSniperEmbeddingClient
from llm.registry import ModelRegistry, load_registry
from llm.router import TextGenerationRouter
from persistence.port import FishSniperPersistencePort
from settings import get_fish_sniper_backend_settings
from weather.port import WeatherSnapshotCachePort
from weather.weather_service import create_default_in_memory_weather_cache

# ---------------------------------------------------------------------------
# 模組級 singleton（程序內共用實例；lazy 建立）
# ---------------------------------------------------------------------------

_supabase_fish_sniper_persistence_singleton: FishSniperPersistencePort | None = None
_fish_sniper_weather_snapshot_cache_singleton: WeatherSnapshotCachePort | None = None
_fish_sniper_embedding_client_singleton: FishSniperEmbeddingClient | None = None
_model_registry_singleton: ModelRegistry | None = None
_text_generation_router_singleton: TextGenerationRouter | None = None


# ---------------------------------------------------------------------------
# 通用：時間來源（OTP 過期、log 時間戳；測試可 override 成固定時鐘）
# ---------------------------------------------------------------------------


def _default_reference_time_utc_callable() -> datetime:
    return datetime.now(tz=UTC)

def get_reference_time_utc_callable() -> Callable[[], datetime]:
    """Return a callable that yields the current UTC time (overridable in tests)."""

    return _default_reference_time_utc_callable


# ---------------------------------------------------------------------------
# 持久化：Supabase（users、logs、OTP 表、preferences）
# ---------------------------------------------------------------------------


def get_fish_sniper_persistence_port() -> FishSniperPersistencePort:
    """Return the process-wide Supabase persistence adapter."""

    global _supabase_fish_sniper_persistence_singleton
    from persistence.supabase_fish_sniper_persistence_adapter import (
        SupabaseFishSniperPersistenceAdapter,
    )

    settings = get_fish_sniper_backend_settings()
    if settings.supabase_url is None or not settings.supabase_service_role_key:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Database is not configured for this environment"},
        )
    if _supabase_fish_sniper_persistence_singleton is None:
        _supabase_fish_sniper_persistence_singleton = SupabaseFishSniperPersistenceAdapter(settings)
    return _supabase_fish_sniper_persistence_singleton


# ---------------------------------------------------------------------------
# 認證：Google OAuth（使用中 — POST /auth/google/exchange）
# ---------------------------------------------------------------------------


def get_google_oauth_token_exchange_callable() -> Callable[..., dict]:
    """Return the production token-exchange callable (overridable in tests)."""

    from auth.google_oauth_client import exchange_authorization_code_for_token_response

    return exchange_authorization_code_for_token_response


def get_google_jwks_key_resolver():
    """Return the production Google JWKS key resolver (overridable in tests)."""

    from auth.google_id_token_verification import build_default_google_jwks_key_resolver

    return build_default_google_jwks_key_resolver()


# ---------------------------------------------------------------------------
# [暫時棄用] 認證：Email OTP / Resend（需付費 email 服務與寄件網域，目前未開通）
# ---------------------------------------------------------------------------


def get_transactional_email_sender_port() -> TransactionalEmailSenderPort:
    """Return a Resend-backed sender (requires RESEND_API_KEY).

    [暫時棄用 — Email OTP / Resend] 需 Resend 與寄件網域；目前未開通，待有 email 服務後可恢復。
    """

    settings = get_fish_sniper_backend_settings()
    if not settings.resend_api_key:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Email delivery is not configured for this environment"},
        )
    return ResendTransactionalEmailSenderAdapter(settings)


def get_otp_code_generator_callable() -> Callable[[], str]:
    """Return the production OTP generator (overridable in tests).

    [暫時棄用 — Email OTP / Resend] 僅 send-otp 使用；需 email 服務與網域，目前未開通。
    """

    from auth.otp_code import generate_six_digit_otp_code_from_secrets

    return generate_six_digit_otp_code_from_secrets


# ---------------------------------------------------------------------------
# 天氣：OpenWeatherMap 結果的快取（策略 graph、/weather/current）
# ---------------------------------------------------------------------------


def get_fish_sniper_weather_snapshot_cache_port() -> WeatherSnapshotCachePort:
    """Return the process-wide in-memory weather cache (swap for Redis-backed cache later)."""

    global _fish_sniper_weather_snapshot_cache_singleton
    if _fish_sniper_weather_snapshot_cache_singleton is None:
        _fish_sniper_weather_snapshot_cache_singleton = create_default_in_memory_weather_cache()
    return _fish_sniper_weather_snapshot_cache_singleton


# ---------------------------------------------------------------------------
# Embedding：釣魚紀錄向量（POST/PATCH /logs、策略 RAG）
# ---------------------------------------------------------------------------


def get_fish_sniper_embedding_client() -> FishSniperEmbeddingClient:
    """Return the process-wide Gemini embedding client.

    Tests should override this dependency with a fake before issuing requests
    that hit ``/logs`` POST or PATCH (see ``test_logs_api`` helpers).
    """

    global _fish_sniper_embedding_client_singleton
    from embedding.gemini_embedding_client import GeminiFishSniperEmbeddingClient

    if _fish_sniper_embedding_client_singleton is None:
        settings = get_fish_sniper_backend_settings()
        _fish_sniper_embedding_client_singleton = GeminiFishSniperEmbeddingClient(
            fish_sniper_backend_settings=settings,
        )
    return _fish_sniper_embedding_client_singleton


# ---------------------------------------------------------------------------
# LLM：策略生成模型 catalog + 多 provider 路由（/agent/*）
# ---------------------------------------------------------------------------


def get_model_registry() -> ModelRegistry:
    """Return the process-wide LLM model catalog (loaded from ``llm_models.yaml``)."""

    global _model_registry_singleton

    if _model_registry_singleton is None:
        _model_registry_singleton = load_registry(
            backend_settings=get_fish_sniper_backend_settings(),
        )
    return _model_registry_singleton


def get_text_generation_router() -> TextGenerationRouter:
    """Return the process-wide text-generation router (registry + provider adapters)."""

    global _text_generation_router_singleton

    if _text_generation_router_singleton is None:
        _text_generation_router_singleton = TextGenerationRouter(
            model_registry=get_model_registry(),
        )
    return _text_generation_router_singleton


# ---------------------------------------------------------------------------
# 路由用型別別名（Annotated Depends — 與上方 provider 一一對應）
# 設定注入見 settings.FishSniperSettingsDep
# ---------------------------------------------------------------------------

# 持久化
FishSniperPersistenceDep = Annotated[
    FishSniperPersistencePort,
    Depends(get_fish_sniper_persistence_port),
]

# 通用：可 mock 的 UTC 時鐘
ReferenceTimeUtcCallableDep = Annotated[
    Callable[[], datetime],
    Depends(get_reference_time_utc_callable),
]

# 認證 — Google OAuth
GoogleOAuthTokenExchangeCallableDep = Annotated[
    Callable[..., dict],
    Depends(get_google_oauth_token_exchange_callable),
]
GoogleJwksKeyResolverDep = Annotated[
    object,
    Depends(get_google_jwks_key_resolver),
]

# [暫時棄用] 認證 — Email OTP / Resend
TransactionalEmailSenderDep = Annotated[
    TransactionalEmailSenderPort,
    Depends(get_transactional_email_sender_port),
]
OtpCodeGeneratorDep = Annotated[
    Callable[[], str],
    Depends(get_otp_code_generator_callable),
]

# Embedding
FishSniperEmbeddingClientDep = Annotated[
    FishSniperEmbeddingClient,
    Depends(get_fish_sniper_embedding_client),
]

# LLM
ModelRegistryDep = Annotated[
    ModelRegistry,
    Depends(get_model_registry),
]
TextGenerationRouterDep = Annotated[
    TextGenerationRouter,
    Depends(get_text_generation_router),
]
