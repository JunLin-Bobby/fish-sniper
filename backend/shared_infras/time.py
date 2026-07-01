"""Reference UTC clock for routes and tests (overridable via dependency_overrides)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends


def _default_reference_time_utc_callable() -> datetime:
    return datetime.now(tz=UTC)


def get_reference_time_utc_callable() -> Callable[[], datetime]:
    """Return a callable that yields the current UTC time (overridable in tests)."""

    return _default_reference_time_utc_callable


ReferenceTimeUtcCallableDep = Annotated[
    Callable[[], datetime],
    Depends(get_reference_time_utc_callable),
]
