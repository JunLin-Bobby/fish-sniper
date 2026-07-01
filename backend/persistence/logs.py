"""Fishing logs persistence port slice."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FishSniperFishingLogRow:
    """Row from `fishing_logs` exposed to the API layer."""

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
class FishSniperFishingLogSimilarityHit:
    """Row plus cosine distance from pgvector ``<=>`` (P4 Part 2 RAG)."""

    row: FishSniperFishingLogRow
    cosine_distance: float


class LogsPersistencePort(Protocol):
    """Abstract persistence for fishing logs and RAG similarity search."""

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
        """Insert a fishing log for the user; returns the new log id."""

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
        """Replace fields for an owned log; returns None if missing or not owned."""

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

    def find_similar_fishing_log_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
        target_species: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[FishSniperFishingLogSimilarityHit]:
        """Return up to ``top_k`` similar logs ordered by cosine distance ascending."""
