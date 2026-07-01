"""User and preferences persistence port slice."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FishSniperUserRow:
    """Row from `users` used by auth and preferences flows."""

    fish_sniper_user_id: UUID
    normalized_email_address: str


@dataclass(frozen=True, slots=True)
class FishSniperUserPreferencesRow:
    """Row from `user_preferences`."""

    profile_region_display_name: str
    profile_onboarding_completed_flag: bool


class UsersPersistencePort(Protocol):
    """Abstract persistence for users and preferences."""

    def fetch_user_row_by_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> FishSniperUserRow | None:
        """Return the user row for an email, if present."""

    def insert_user_row_for_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> FishSniperUserRow:
        """Insert a new user row and return it."""

    def fetch_user_row_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> FishSniperUserRow | None:
        """Return the user row for an id, if present."""

    def delete_fish_sniper_user_account_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> bool:
        """Permanently delete the user row; returns True if a row was removed."""

    def fetch_user_preferences_row_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> FishSniperUserPreferencesRow | None:
        """Return preferences for a user, if any."""

    def upsert_user_preferences_region_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
        profile_region_display_name: str,
        profile_onboarding_completed_flag: bool,
        preferences_updated_at_utc: datetime,
    ) -> None:
        """Create or update the user's preferences row."""
