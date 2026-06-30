"""Top-level FastAPI dependency assembly — re-exports domain providers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from auth.deps import (
    GoogleJwksKeyResolverDep,
    GoogleOAuthTokenExchangeCallableDep,
    get_google_jwks_key_resolver,
    get_google_oauth_token_exchange_callable,
)
from embedding.deps import (
    FishSniperEmbeddingClientDep,
    get_fish_sniper_embedding_client,
)
from persistence.port import PersistencePort
from settings import get_settings
from strategy.deps import (
    ModelRegistryDep,
    TextGenerationRouterDep,
    get_model_registry,
    get_text_generation_router,
)
from weather.deps import get_fish_sniper_weather_snapshot_cache_port

_supabase_persistence_singleton: PersistencePort | None = None


def _default_reference_time_utc_callable() -> datetime:
    return datetime.now(tz=UTC)


def get_reference_time_utc_callable() -> Callable[[], datetime]:
    """Return a callable that yields the current UTC time (overridable in tests)."""

    return _default_reference_time_utc_callable


def get_persistence() -> PersistencePort:
    """Return the process-wide Supabase persistence adapter."""

    global _supabase_persistence_singleton
    from persistence.supabase_fish_sniper_persistence_adapter import (
        SupabaseFishSniperPersistenceAdapter,
    )

    settings = get_settings()
    if settings.supabase_url is None or not settings.supabase_service_role_key:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Database is not configured for this environment"},
        )
    if _supabase_persistence_singleton is None:
        _supabase_persistence_singleton = SupabaseFishSniperPersistenceAdapter(settings)
    return _supabase_persistence_singleton


PersistenceDep = Annotated[
    PersistencePort,
    Depends(get_persistence),
]
ReferenceTimeUtcCallableDep = Annotated[
    Callable[[], datetime],
    Depends(get_reference_time_utc_callable),
]

__all__ = [
    "FishSniperEmbeddingClientDep",
    "PersistenceDep",
    "GoogleJwksKeyResolverDep",
    "GoogleOAuthTokenExchangeCallableDep",
    "ModelRegistryDep",
    "ReferenceTimeUtcCallableDep",
    "TextGenerationRouterDep",
    "get_fish_sniper_embedding_client",
    "get_persistence",
    "get_fish_sniper_weather_snapshot_cache_port",
    "get_google_jwks_key_resolver",
    "get_google_oauth_token_exchange_callable",
    "get_model_registry",
    "get_reference_time_utc_callable",
    "get_text_generation_router",
]
