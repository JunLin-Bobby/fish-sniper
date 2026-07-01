"""Persistence FastAPI dependency providers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from persistence.port import PersistencePort
from shared_infras.settings import get_settings

_supabase_persistence_singleton: PersistencePort | None = None


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
