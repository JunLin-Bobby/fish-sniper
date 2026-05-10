"""Persistence port for FishSniper P1 (users, OTP, preferences) and P3 (fishing logs)."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FishSniperFishingLogRow:
    """Row from `fishing_logs` exposed to the API layer.

    Vector-related columns added in P4 Part 1:
    * ``embedding_status``: ``'pending' | 'done' | 'failed'`` — single source of truth.
    * ``embedding_text_version``: schema version of the natural-language template
      used to generate the row's vector. Bumped when the composer changes.
    * ``embedding_attempt_count``: reserved for the Part 2 background worker
      (incremented when retrying transient OpenAI failures). Part 1 never
      writes this field; it is exposed here so the row mapper round-trips
      cleanly with Supabase.
    """

    log_id: UUID
    fish_sniper_user_id: UUID
    log_date: date
    fishing_location: str
    fishing_scene: str
    target_species: str
    water_depth_m: float
    lure_type: str
    lure_color: str
    retrieve_speed: str
    caught_count: int
    weight_lb: float | None
    length_cm: float | None
    temperature_c: float
    wind_speed_ms: float
    pressure_hpa: int
    condition_code: str
    notes: str
    embedding_status: str
    embedding_text_version: int
    embedding_attempt_count: int
    created_at_utc: datetime
    updated_at_utc: datetime


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

    def insert_fishing_log_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
        log_date: date,
        fishing_location: str,
        fishing_scene: str,
        target_species: str,
        water_depth_m: float,
        lure_type: str,
        lure_color: str,
        retrieve_speed: str,
        caught_count: int,
        weight_lb: float | None,
        length_cm: float | None,
        temperature_c: float,
        wind_speed_ms: float,
        pressure_hpa: int,
        condition_code: str,
        notes: str,
        embedding: list[float] | None,
        embedding_text_version: int,
        reference_time_utc: datetime,
    ) -> UUID:
        """Insert a fishing log for the user; returns the new log id.

        ``embedding=None`` means the OpenAI call failed (or was skipped) and the
        row should be persisted with ``embedding_status='pending'``. A non-None
        vector results in ``embedding_status='done'``.
        """

    def list_fishing_logs_for_user_id_ordered_by_date_desc(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> list[FishSniperFishingLogRow]:
        """Return logs for the user ordered by `date` desc, then `updated_at` desc."""

    def fetch_fishing_log_by_id_for_user_id(
        self,
        *,
        log_id: UUID,
        fish_sniper_user_id: UUID,
    ) -> FishSniperFishingLogRow | None:
        """Return a log owned by the user, if it exists."""

    def update_fishing_log_for_user_id(
        self,
        *,
        log_id: UUID,
        fish_sniper_user_id: UUID,
        log_date: date,
        fishing_location: str,
        fishing_scene: str,
        target_species: str,
        water_depth_m: float,
        lure_type: str,
        lure_color: str,
        retrieve_speed: str,
        caught_count: int,
        weight_lb: float | None,
        length_cm: float | None,
        temperature_c: float,
        wind_speed_ms: float,
        pressure_hpa: int,
        condition_code: str,
        notes: str,
        embedding: list[float] | None,
        embedding_text_version: int,
        reference_time_utc: datetime,
    ) -> FishSniperFishingLogRow | None:
        """Replace fields for an owned log; returns None if missing or not owned.

        Same ``embedding`` semantics as ``insert_fishing_log_for_user_id``: ``None``
        keeps the row in ``embedding_status='pending'``; a vector flips it to ``'done'``.
        """

    def delete_fishing_log_for_user_id(
        self,
        *,
        log_id: UUID,
        fish_sniper_user_id: UUID,
    ) -> bool:
        """Delete an owned log; returns True if a row was removed."""

    def fetch_fishing_logs_list_etag_fingerprint_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> str:
        """Stable fingerprint string for list ETag (count + max updated_at)."""

    def fetch_fishing_log_etag_fingerprint_for_user_id(
        self,
        *,
        log_id: UUID,
        fish_sniper_user_id: UUID,
    ) -> str | None:
        """Fingerprint for a single log ETag; None if not found or not owned."""
