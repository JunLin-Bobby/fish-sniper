"""Shared test app factory helpers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from persistence.deps import get_persistence
from shared_infras.time import get_reference_time_utc_callable
from tests.doubles.in_memory_db import InMemoryFishSniperPersistenceAdapter


def install_auth_dependency_overrides(
    app,
    *,
    fish_sniper_persistence: InMemoryFishSniperPersistenceAdapter,
    reference_time_utc_callable: Callable[[], datetime] | None = None,
) -> None:
    app.dependency_overrides[get_persistence] = lambda: fish_sniper_persistence
    if reference_time_utc_callable is not None:
        app.dependency_overrides[get_reference_time_utc_callable] = (
            lambda: reference_time_utc_callable
        )
