"""Composite persistence port re-exporting users and logs slices."""

from typing import Protocol

from persistence.logs import (
    FishSniperFishingLogRow,
    FishSniperFishingLogSimilarityHit,
    LogsPersistencePort,
)
from persistence.users import (
    FishSniperUserPreferencesRow,
    FishSniperUserRow,
    UsersPersistencePort,
)


class PersistencePort(UsersPersistencePort, LogsPersistencePort, Protocol):
    """Full persistence port: users, preferences, and fishing logs."""


# Re-export row types and sub-ports for consumers that need a narrower dependency.
__all__ = [
    "FishSniperFishingLogRow",
    "FishSniperFishingLogSimilarityHit",
    "PersistencePort",
    "FishSniperUserPreferencesRow",
    "FishSniperUserRow",
    "LogsPersistencePort",
    "UsersPersistencePort",
]
