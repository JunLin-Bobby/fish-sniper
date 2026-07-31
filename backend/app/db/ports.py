"""Composite persistence port (auth-only)."""

from typing import Protocol

from app.db.users import UserRow, UsersPersistencePort


class PersistencePort(UsersPersistencePort, Protocol):
    """Full persistence port: users for Google OAuth."""


__all__ = [
    "PersistencePort",
    "UserRow",
    "UsersPersistencePort",
]
