"""Persistence FastAPI dependency providers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.settings import get_settings
from app.db.ports import PersistencePort

_supabase_persistence_singleton: PersistencePort | None = None


def get_persistence() -> PersistencePort:
    """Return the process-wide Supabase persistence adapter."""

    global _supabase_persistence_singleton
    from app.db.supabase import (
        SupabasePersistenceAdapter,
    )

    settings = get_settings()
    if settings.supabase_url is None or not settings.supabase_service_role_key:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Database is not configured for this environment"},
        )
    if _supabase_persistence_singleton is None:
        _supabase_persistence_singleton = SupabasePersistenceAdapter(settings)
    return _supabase_persistence_singleton


PersistenceDep = Annotated[
    PersistencePort,
    Depends(get_persistence),
]
