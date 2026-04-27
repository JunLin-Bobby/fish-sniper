"""Persistence port for FishSniper P1 (users, OTP, preferences)."""

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


class FishSniperPersistencePort(Protocol):
    """Abstract persistence for OTP auth and user preferences."""

    def fetch_seconds_since_last_otp_send_for_email(
        self,
        *,
        normalized_email_address: str,
        reference_time_utc: datetime,
    ) -> float | None:
        """
        Return seconds since the most recent OTP send for this email, or None if none.

        Used to enforce a 60-second cooldown between sends.
        """

    def insert_pending_otp_challenge_for_email(
        self,
        *,
        normalized_email_address: str,
        otp_code_six_digits: str,
        otp_expires_at_utc: datetime,
        otp_created_at_utc: datetime,
    ) -> None:
        """Persist a new OTP challenge row."""

    def delete_matching_unexpired_otp_or_noop(
        self,
        *,
        normalized_email_address: str,
        otp_code_six_digits: str,
        reference_time_utc: datetime,
    ) -> bool:
        """
        Delete exactly one matching OTP row if it exists and is not expired.

        Returns True if a row was deleted.
        """

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
