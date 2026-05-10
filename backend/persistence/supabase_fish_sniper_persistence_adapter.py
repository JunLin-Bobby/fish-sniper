"""Supabase-backed persistence for P1 auth, preferences, and P3/P4 fishing logs."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from supabase import Client, create_client

from persistence.errors import FishSniperPersistenceUnavailableError
from persistence.port import (
    FishSniperFishingLogRow,
    FishSniperUserPreferencesRow,
    FishSniperUserRow,
)
from settings import FishSniperBackendSettings

logger = logging.getLogger(__name__)

# Explicit column list for SELECTs — avoids pulling the heavy `embedding` vector back
# over the wire for routes that only need the row's metadata. Part 2 RAG queries
# will use a dedicated similarity-search RPC and won't go through this list.
_FISHING_LOGS_SELECT_COLUMNS = (
    "id,user_id,date,fishing_location,fishing_scene,target_species,"
    "water_depth_m,lure_type,lure_color,retrieve_speed,caught_count,"
    "weight_lb,length_cm,temperature_c,wind_speed_ms,pressure_hpa,"
    "condition_code,notes,"
    "embedding_status,embedding_text_version,embedding_attempt_count,"
    "created_at,updated_at"
)


def _serialize_embedding_for_pgvector(embedding: list[float] | None) -> str | None:
    """Return ``'[v1,v2,...]'`` form expected by the RPC's ``::vector`` cast, or None."""

    if embedding is None:
        return None
    return "[" + ",".join(repr(float(component)) for component in embedding) + "]"


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


def _parse_supabase_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise FishSniperPersistenceUnavailableError(f"Unexpected date shape: {type(value)}")


def _fish_sniper_fishing_log_row_from_supabase(row: dict) -> FishSniperFishingLogRow:
    weight = row.get("weight_lb")
    length = row.get("length_cm")
    target_species_raw = row.get("target_species")
    target_species = (
        str(target_species_raw) if target_species_raw is not None else "Largemouth Bass"
    )
    return FishSniperFishingLogRow(
        log_id=UUID(str(row["id"])),
        fish_sniper_user_id=UUID(str(row["user_id"])),
        log_date=_parse_supabase_date(row["date"]),
        fishing_location=str(row["fishing_location"]),
        fishing_scene=str(row["fishing_scene"]),
        target_species=target_species,
        water_depth_m=float(row["water_depth_m"]),
        lure_type=str(row["lure_type"]),
        lure_color=str(row["lure_color"]),
        retrieve_speed=str(row["retrieve_speed"]),
        caught_count=int(row["caught_count"]),
        weight_lb=None if weight is None else float(weight),
        length_cm=None if length is None else float(length),
        temperature_c=float(row["temperature_c"]),
        wind_speed_ms=float(row["wind_speed_ms"]),
        pressure_hpa=int(row["pressure_hpa"]),
        condition_code=str(row["condition_code"]),
        notes=str(row["notes"]),
        embedding_status=str(row.get("embedding_status", "pending")),
        embedding_text_version=int(row.get("embedding_text_version", 1)),
        embedding_attempt_count=int(row.get("embedding_attempt_count", 0)),
        created_at_utc=_parse_supabase_timestamptz_to_utc(row["created_at"]),
        updated_at_utc=_parse_supabase_timestamptz_to_utc(row["updated_at"]),
    )


def _unwrap_rpc_jsonb_response(response_data: Any) -> dict | None:
    """RPC returns ``jsonb`` → supabase-py may surface it as dict, [dict], or None."""

    if response_data is None:
        return None
    if isinstance(response_data, dict):
        return response_data
    if isinstance(response_data, list):
        if not response_data:
            return None
        first = response_data[0]
        return first if isinstance(first, dict) else None
    return None


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
                self._client.table("users").insert({"email": normalized_email_address}).execute()
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
        # The atomic "row + vector + status" write happens inside the RPC
        # `fish_sniper_insert_log_with_embedding`
        # (see scripts/supabase_p4_part1_log_embeddings.sql).
        try:
            rpc_payload: dict[str, Any] = {
                "p_user_id": str(fish_sniper_user_id),
                "p_date": log_date.isoformat(),
                "p_fishing_location": fishing_location,
                "p_fishing_scene": fishing_scene,
                "p_target_species": target_species,
                "p_water_depth_m": water_depth_m,
                "p_lure_type": lure_type,
                "p_lure_color": lure_color,
                "p_retrieve_speed": retrieve_speed,
                "p_caught_count": caught_count,
                "p_weight_lb": weight_lb,
                "p_length_cm": length_cm,
                "p_temperature_c": temperature_c,
                "p_wind_speed_ms": wind_speed_ms,
                "p_pressure_hpa": pressure_hpa,
                "p_condition_code": condition_code,
                "p_notes": notes,
                "p_embedding": _serialize_embedding_for_pgvector(embedding),
                "p_embedding_text_version": embedding_text_version,
                "p_reference_time_utc": _format_timestamptz_for_supabase(reference_time_utc),
            }
            response = self._client.rpc(
                "fish_sniper_insert_log_with_embedding",
                rpc_payload,
            ).execute()
            row = _unwrap_rpc_jsonb_response(response.data)
            if row is None or "id" not in row:
                raise FishSniperPersistenceUnavailableError(
                    "fishing log insert RPC returned empty payload"
                )
            return UUID(str(row["id"]))
        except FishSniperPersistenceUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase fishing log insert RPC failed")
            raise FishSniperPersistenceUnavailableError("fishing log insert failed") from exc

    def list_fishing_logs_for_user_id_ordered_by_date_desc(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> list[FishSniperFishingLogRow]:
        try:
            response = (
                self._client.table("fishing_logs")
                .select(_FISHING_LOGS_SELECT_COLUMNS)
                .eq("user_id", str(fish_sniper_user_id))
                .order("date", desc=True)
                .order("updated_at", desc=True)
                .execute()
            )
            rows = response.data or []
            return [_fish_sniper_fishing_log_row_from_supabase(row) for row in rows]
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase fishing log list failed")
            raise FishSniperPersistenceUnavailableError("fishing log list failed") from exc

    def fetch_fishing_log_by_id_for_user_id(
        self,
        *,
        log_id: UUID,
        fish_sniper_user_id: UUID,
    ) -> FishSniperFishingLogRow | None:
        try:
            response = (
                self._client.table("fishing_logs")
                .select(_FISHING_LOGS_SELECT_COLUMNS)
                .eq("id", str(log_id))
                .eq("user_id", str(fish_sniper_user_id))
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            return _fish_sniper_fishing_log_row_from_supabase(response.data[0])
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase fishing log fetch failed")
            raise FishSniperPersistenceUnavailableError("fishing log fetch failed") from exc

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
        # Atomic "update row + vector + status" via RPC. The RPC returns NULL when
        # either the log id doesn't exist or it belongs to another user — both
        # collapse to a 404 in the route handler.
        try:
            rpc_payload: dict[str, Any] = {
                "p_log_id": str(log_id),
                "p_user_id": str(fish_sniper_user_id),
                "p_date": log_date.isoformat(),
                "p_fishing_location": fishing_location,
                "p_fishing_scene": fishing_scene,
                "p_target_species": target_species,
                "p_water_depth_m": water_depth_m,
                "p_lure_type": lure_type,
                "p_lure_color": lure_color,
                "p_retrieve_speed": retrieve_speed,
                "p_caught_count": caught_count,
                "p_weight_lb": weight_lb,
                "p_length_cm": length_cm,
                "p_temperature_c": temperature_c,
                "p_wind_speed_ms": wind_speed_ms,
                "p_pressure_hpa": pressure_hpa,
                "p_condition_code": condition_code,
                "p_notes": notes,
                "p_embedding": _serialize_embedding_for_pgvector(embedding),
                "p_embedding_text_version": embedding_text_version,
                "p_reference_time_utc": _format_timestamptz_for_supabase(reference_time_utc),
            }
            response = self._client.rpc(
                "fish_sniper_update_log_with_embedding",
                rpc_payload,
            ).execute()
            row = _unwrap_rpc_jsonb_response(response.data)
            if row is None:
                return None
            return _fish_sniper_fishing_log_row_from_supabase(row)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase fishing log update RPC failed")
            raise FishSniperPersistenceUnavailableError("fishing log update failed") from exc

    def delete_fishing_log_for_user_id(
        self,
        *,
        log_id: UUID,
        fish_sniper_user_id: UUID,
    ) -> bool:
        try:
            existing = self.fetch_fishing_log_by_id_for_user_id(
                log_id=log_id,
                fish_sniper_user_id=fish_sniper_user_id,
            )
            if existing is None:
                return False
            self._client.table("fishing_logs").delete().eq("id", str(log_id)).eq(
                "user_id",
                str(fish_sniper_user_id),
            ).execute()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase fishing log delete failed")
            raise FishSniperPersistenceUnavailableError("fishing log delete failed") from exc

    def fetch_fishing_logs_list_etag_fingerprint_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> str:
        try:
            response = (
                self._client.table("fishing_logs")
                .select("updated_at")
                .eq("user_id", str(fish_sniper_user_id))
                .execute()
            )
            rows = response.data or []
            if not rows:
                return "0:"
            max_updated_at_utc = max(
                _parse_supabase_timestamptz_to_utc(row["updated_at"]) for row in rows
            )
            return f"{len(rows)}:{max_updated_at_utc.isoformat()}"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase fishing log list etag fingerprint failed")
            raise FishSniperPersistenceUnavailableError(
                "fishing log list etag fingerprint failed",
            ) from exc

    def fetch_fishing_log_etag_fingerprint_for_user_id(
        self,
        *,
        log_id: UUID,
        fish_sniper_user_id: UUID,
    ) -> str | None:
        try:
            response = (
                self._client.table("fishing_logs")
                .select("id,updated_at")
                .eq("id", str(log_id))
                .eq("user_id", str(fish_sniper_user_id))
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            row = response.data[0]
            updated_at_utc = _parse_supabase_timestamptz_to_utc(row["updated_at"])
            return f'{row["id"]}:{updated_at_utc.isoformat()}'
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase fishing log etag fingerprint failed")
            raise FishSniperPersistenceUnavailableError(
                "fishing log etag fingerprint failed",
            ) from exc
