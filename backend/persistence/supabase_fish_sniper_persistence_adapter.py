"""Supabase-backed persistence for P1 auth and preferences."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from supabase import Client, create_client

from persistence.errors import FishSniperPersistenceUnavailableError
from persistence.port import FishSniperUserPreferencesRow, FishSniperUserRow
from settings import FishSniperBackendSettings

logger = logging.getLogger(__name__)


def _parse_supabase_timestamptz_to_utc(value: object) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)

    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)

        return parsed.astimezone(UTC)

    raise FishSniperPersistenceUnavailableError(f"Unexpected timestamp shape: {type(value)}")


def _format_timestamptz_for_supabase(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class SupabaseFishSniperPersistenceAdapter:
    """Implements `FishSniperPersistencePort` using Supabase PostgREST."""

    def __init__(self, fish_sniper_backend_settings: FishSniperBackendSettings) -> None:
        supabase_url = fish_sniper_backend_settings.supabase_url or ""
        service_role_key = fish_sniper_backend_settings.supabase_service_role_key or ""
        self._client: Client = create_client(supabase_url, service_role_key)

    def fetch_seconds_since_last_otp_send_for_email(
        self,
        *,
        normalized_email_address: str,
        reference_time_utc: datetime,
    ) -> float | None:
        try:
            response = (
                self._client.table("otp_codes")
                .select("created_at")
                .eq("email", normalized_email_address)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            created_at_utc = _parse_supabase_timestamptz_to_utc(response.data[0]["created_at"])
            return (reference_time_utc - created_at_utc).total_seconds()
            
        except Exception as exc:  # noqa: BLE001 — map provider errors to a single app error type
            logger.exception("Supabase OTP cooldown lookup failed")
            raise FishSniperPersistenceUnavailableError("otp cooldown lookup failed") from exc

    def insert_pending_otp_challenge_for_email(
        self,
        *,
        normalized_email_address: str,
        otp_code_six_digits: str,
        otp_expires_at_utc: datetime,
        otp_created_at_utc: datetime,
    ) -> None:
        try:
            self._client.table("otp_codes").insert(
                {
                    "email": normalized_email_address,
                    "code": otp_code_six_digits,
                    "expires_at": _format_timestamptz_for_supabase(otp_expires_at_utc),
                    "created_at": _format_timestamptz_for_supabase(otp_created_at_utc),
                }
            ).execute()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase OTP insert failed")
            raise FishSniperPersistenceUnavailableError("otp insert failed") from exc

    def delete_matching_unexpired_otp_or_noop(
        self,
        *,
        normalized_email_address: str,
        otp_code_six_digits: str,
        reference_time_utc: datetime,
    ) -> bool:
        try:
            select_response = (
                self._client.table("otp_codes")
                .select("id")
                .eq("email", normalized_email_address)
                .eq("code", otp_code_six_digits)
                .gt("expires_at", _format_timestamptz_for_supabase(reference_time_utc))
                .limit(1)
                .execute()
            )
            if not select_response.data:
                return False
            otp_row_id = select_response.data[0]["id"]
            self._client.table("otp_codes").delete().eq("id", otp_row_id).execute()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase OTP consume/delete failed")
            raise FishSniperPersistenceUnavailableError("otp consume failed") from exc

    def fetch_user_row_by_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> FishSniperUserRow | None:
        try:
            response = (
                self._client.table("users")
                .select("id,email")
                .eq("email", normalized_email_address)
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            row = response.data[0]
            return FishSniperUserRow(
                fish_sniper_user_id=UUID(str(row["id"])),
                normalized_email_address=str(row["email"]),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase user lookup failed")
            raise FishSniperPersistenceUnavailableError("user lookup failed") from exc

    def insert_user_row_for_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> FishSniperUserRow:
        try:
            insert_response = (
                self._client.table("users")
                .insert({"email": normalized_email_address})
                .execute()
            )
            if not insert_response.data:
                raise FishSniperPersistenceUnavailableError("user insert returned no row")
            row = insert_response.data[0]
            return FishSniperUserRow(
                fish_sniper_user_id=UUID(str(row["id"])),
                normalized_email_address=str(row["email"]),
            )
        except FishSniperPersistenceUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase user insert failed")
            raise FishSniperPersistenceUnavailableError("user insert failed") from exc

    def fetch_user_preferences_row_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> FishSniperUserPreferencesRow | None:
        try:
            response = (
                self._client.table("user_preferences")
                .select("region,onboarding_completed")
                .eq("user_id", str(fish_sniper_user_id))
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            row = response.data[0]
            return FishSniperUserPreferencesRow(
                profile_region_display_name=str(row["region"]),
                profile_onboarding_completed_flag=bool(row["onboarding_completed"]),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase preferences lookup failed")
            raise FishSniperPersistenceUnavailableError("preferences lookup failed") from exc

    def upsert_user_preferences_region_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
        profile_region_display_name: str,
        profile_onboarding_completed_flag: bool,
        preferences_updated_at_utc: datetime,
    ) -> None:
        try:
            self._client.table("user_preferences").upsert(
                {
                    "user_id": str(fish_sniper_user_id),
                    "region": profile_region_display_name,
                    "onboarding_completed": profile_onboarding_completed_flag,
                    "updated_at": _format_timestamptz_for_supabase(preferences_updated_at_utc),
                },
                on_conflict="user_id",
            ).execute()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase preferences upsert failed")
            raise FishSniperPersistenceUnavailableError("preferences upsert failed") from exc
