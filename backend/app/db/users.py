"""User persistence port slice (Google OAuth find-or-create)."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UserRow:
    """Row from `users` used by auth flows."""

    user_id: UUID
    normalized_email_address: str


class UsersPersistencePort(Protocol):
    """Abstract persistence for users."""

    def fetch_user_row_by_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> UserRow | None:
        """Return the user row for an email, if present."""

    def insert_user_row_for_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> UserRow:
        """Insert a new user row and return it."""

    def fetch_user_row_for_user_id(
        self,
        *,
        user_id: UUID,
    ) -> UserRow | None:
        """Return the user row for an id, if present."""
