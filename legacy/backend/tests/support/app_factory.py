"""Shared test app factory helpers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.core.time import get_reference_time_utc_callable
from app.db.deps import get_persistence
from tests.doubles.in_memory_db import InMemoryPersistenceAdapter


def install_auth_dependency_overrides(
    app,
    *,
    persistence: InMemoryPersistenceAdapter,
    reference_time_utc_callable: Callable[[], datetime] | None = None,
) -> None:
    app.dependency_overrides[get_persistence] = lambda: persistence
    if reference_time_utc_callable is not None:
        app.dependency_overrides[get_reference_time_utc_callable] = (
            lambda: reference_time_utc_callable
        )
