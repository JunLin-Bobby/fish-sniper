"""FastAPI dependency providers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from email_delivery.port import TransactionalEmailSenderPort
from email_delivery.resend_transactional_email_adapter import ResendTransactionalEmailSenderAdapter
from embedding.port import FishSniperEmbeddingClient
from persistence.port import FishSniperPersistencePort
from settings import FishSniperBackendSettings, get_fish_sniper_backend_settings
from weather.port import WeatherSnapshotCachePort
from weather.weather_service import create_default_in_memory_weather_cache

_supabase_fish_sniper_persistence_singleton: FishSniperPersistencePort | None = None
_fish_sniper_weather_snapshot_cache_singleton: WeatherSnapshotCachePort | None = None
_fish_sniper_embedding_client_singleton: FishSniperEmbeddingClient | None = None


def _default_reference_time_utc_callable() -> datetime:
    return datetime.now(tz=UTC)


def get_reference_time_utc_callable() -> Callable[[], datetime]:
    """Return a callable that yields the current UTC time (overridable in tests)."""

    return _default_reference_time_utc_callable


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


def get_transactional_email_sender_port() -> TransactionalEmailSenderPort:
    """Return a Resend-backed sender (requires RESEND_API_KEY)."""

    settings = get_fish_sniper_backend_settings()
    if not settings.resend_api_key:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Email delivery is not configured for this environment"},
        )
    return ResendTransactionalEmailSenderAdapter(settings)


def get_fish_sniper_weather_snapshot_cache_port() -> WeatherSnapshotCachePort:
    """Return the process-wide in-memory weather cache (swap for Redis-backed cache later)."""

    global _fish_sniper_weather_snapshot_cache_singleton
    if _fish_sniper_weather_snapshot_cache_singleton is None:
        _fish_sniper_weather_snapshot_cache_singleton = create_default_in_memory_weather_cache()
    return _fish_sniper_weather_snapshot_cache_singleton


def get_otp_code_generator_callable() -> Callable[[], str]:
    """Return the production OTP generator (overridable in tests)."""

    from auth.otp_code import generate_six_digit_otp_code_from_secrets

    return generate_six_digit_otp_code_from_secrets


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


FishSniperSettingsDep = Annotated[
    FishSniperBackendSettings,
    Depends(get_fish_sniper_backend_settings),
]
FishSniperPersistenceDep = Annotated[
    FishSniperPersistencePort,
    Depends(get_fish_sniper_persistence_port),
]
TransactionalEmailSenderDep = Annotated[
    TransactionalEmailSenderPort,
    Depends(get_transactional_email_sender_port),
]
ReferenceTimeUtcCallableDep = Annotated[
    Callable[[], datetime],
    Depends(get_reference_time_utc_callable),
]
OtpCodeGeneratorDep = Annotated[
    Callable[[], str],
    Depends(get_otp_code_generator_callable),
]
FishSniperEmbeddingClientDep = Annotated[
    FishSniperEmbeddingClient,
    Depends(get_fish_sniper_embedding_client),
]
