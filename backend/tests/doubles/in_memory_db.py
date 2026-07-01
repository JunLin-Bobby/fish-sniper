"""In-memory persistence test double."""

from __future__ import annotations

import math
from datetime import date, datetime
from uuid import UUID, uuid4

from persistence.port import (
    FishSniperFishingLogRow,
    FishSniperFishingLogSimilarityHit,
    FishSniperUserPreferencesRow,
    FishSniperUserRow,
)


def _fish_sniper_cosine_distance_between_vectors(a: list[float], b: list[float]) -> float:
    """Cosine distance ``1 - cos_sim``; matches pgvector ``<=>`` for L2-normalized inputs."""

    if not a or not b or len(a) != len(b):
        return 1.0
    dot = math.fsum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(math.fsum(x * x for x in a))
    norm_b = math.sqrt(math.fsum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    similarity = dot / (norm_a * norm_b)
    if similarity > 1.0:
        similarity = 1.0
    if similarity < -1.0:
        similarity = -1.0
    return 1.0 - similarity


class InMemoryFishSniperPersistenceAdapter:
    """In-memory persistence for fast, deterministic API tests."""

    def __init__(self) -> None:
        self._user_row_by_normalized_email: dict[str, FishSniperUserRow] = {}
        self._preferences_row_by_user_id: dict[UUID, FishSniperUserPreferencesRow] = {}
        self._fishing_log_row_list: list[FishSniperFishingLogRow] = []
        self._embedding_by_log_id: dict[UUID, list[float]] = {}

    def fetch_user_row_by_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> FishSniperUserRow | None:
        return self._user_row_by_normalized_email.get(normalized_email_address)

    def insert_user_row_for_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> FishSniperUserRow:
        new_user_id = uuid4()
        row = FishSniperUserRow(
            fish_sniper_user_id=new_user_id,
            normalized_email_address=normalized_email_address,
        )
        self._user_row_by_normalized_email[normalized_email_address] = row
        return row

    def fetch_user_row_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> FishSniperUserRow | None:
        for row in self._user_row_by_normalized_email.values():
            if row.fish_sniper_user_id == fish_sniper_user_id:
                return row
        return None

    def delete_fish_sniper_user_account_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> bool:
        user_row = self.fetch_user_row_for_user_id(fish_sniper_user_id=fish_sniper_user_id)
        if user_row is None:
            return False
        del self._user_row_by_normalized_email[user_row.normalized_email_address]
        self._preferences_row_by_user_id.pop(fish_sniper_user_id, None)
        log_ids_to_remove = {
            log_row.log_id
            for log_row in self._fishing_log_row_list
            if log_row.fish_sniper_user_id == fish_sniper_user_id
        }
        self._fishing_log_row_list = [
            log_row
            for log_row in self._fishing_log_row_list
            if log_row.fish_sniper_user_id != fish_sniper_user_id
        ]
        for log_id in log_ids_to_remove:
            self._embedding_by_log_id.pop(log_id, None)
        return True

    def fetch_user_preferences_row_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> FishSniperUserPreferencesRow | None:
        return self._preferences_row_by_user_id.get(fish_sniper_user_id)

    def upsert_user_preferences_region_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
        profile_region_display_name: str,
        profile_onboarding_completed_flag: bool,
        preferences_updated_at_utc: datetime,
    ) -> None:
        _ = preferences_updated_at_utc
        self._preferences_row_by_user_id[fish_sniper_user_id] = FishSniperUserPreferencesRow(
            profile_region_display_name=profile_region_display_name,
            profile_onboarding_completed_flag=profile_onboarding_completed_flag,
        )

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
        log_id = uuid4()
        row = FishSniperFishingLogRow(
            log_id=log_id,
            fish_sniper_user_id=fish_sniper_user_id,
            log_date=log_date,
            fishing_location=fishing_location,
            fishing_scene=fishing_scene,
            target_species=target_species,
            water_depth_m=water_depth_m,
            lure_type=lure_type,
            lure_color=lure_color,
            retrieve_speed=retrieve_speed,
            caught_count=caught_count,
            weight_lb=weight_lb,
            length_cm=length_cm,
            temperature_c=temperature_c,
            wind_speed_ms=wind_speed_ms,
            pressure_hpa=pressure_hpa,
            condition_code=condition_code,
            notes=notes,
            embedding_status="done" if embedding is not None else "pending",
            embedding_text_version=embedding_text_version,
            embedding_attempt_count=0,
            created_at_utc=reference_time_utc,
            updated_at_utc=reference_time_utc,
        )
        self._fishing_log_row_list.append(row)
        if embedding is not None:
            self._embedding_by_log_id[log_id] = list(embedding)
        return log_id

    def list_fishing_logs_for_user_id_ordered_by_date_desc(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> list[FishSniperFishingLogRow]:
        owned = [
            r for r in self._fishing_log_row_list if r.fish_sniper_user_id == fish_sniper_user_id
        ]
        return sorted(owned, key=lambda r: (r.log_date, r.updated_at_utc), reverse=True)

    def fetch_fishing_log_by_id_for_user_id(
        self,
        *,
        log_id: UUID,
        fish_sniper_user_id: UUID,
    ) -> FishSniperFishingLogRow | None:
        for row in self._fishing_log_row_list:
            if row.log_id == log_id and row.fish_sniper_user_id == fish_sniper_user_id:
                return row
        return None

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
        for index, row in enumerate(self._fishing_log_row_list):
            if row.log_id == log_id and row.fish_sniper_user_id == fish_sniper_user_id:
                updated = FishSniperFishingLogRow(
                    log_id=row.log_id,
                    fish_sniper_user_id=row.fish_sniper_user_id,
                    log_date=log_date,
                    fishing_location=fishing_location,
                    fishing_scene=fishing_scene,
                    target_species=target_species,
                    water_depth_m=water_depth_m,
                    lure_type=lure_type,
                    lure_color=lure_color,
                    retrieve_speed=retrieve_speed,
                    caught_count=caught_count,
                    weight_lb=weight_lb,
                    length_cm=length_cm,
                    temperature_c=temperature_c,
                    wind_speed_ms=wind_speed_ms,
                    pressure_hpa=pressure_hpa,
                    condition_code=condition_code,
                    notes=notes,
                    embedding_status="done" if embedding is not None else "pending",
                    embedding_text_version=embedding_text_version,
                    embedding_attempt_count=row.embedding_attempt_count,
                    created_at_utc=row.created_at_utc,
                    updated_at_utc=reference_time_utc,
                )
                self._fishing_log_row_list[index] = updated
                if embedding is not None:
                    self._embedding_by_log_id[log_id] = list(embedding)
                else:
                    self._embedding_by_log_id.pop(log_id, None)
                return updated
        return None

    def delete_fishing_log_for_user_id(
        self,
        *,
        log_id: UUID,
        fish_sniper_user_id: UUID,
    ) -> bool:
        for index, row in enumerate(self._fishing_log_row_list):
            if row.log_id == log_id and row.fish_sniper_user_id == fish_sniper_user_id:
                del self._fishing_log_row_list[index]
                self._embedding_by_log_id.pop(log_id, None)
                return True
        return False

    def fetch_fishing_logs_list_etag_fingerprint_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
    ) -> str:
        owned = [
            r for r in self._fishing_log_row_list if r.fish_sniper_user_id == fish_sniper_user_id
        ]
        if not owned:
            return "0:"
        max_updated = max(r.updated_at_utc for r in owned)
        return f"{len(owned)}:{max_updated.isoformat()}"

    def fetch_fishing_log_etag_fingerprint_for_user_id(
        self,
        *,
        log_id: UUID,
        fish_sniper_user_id: UUID,
    ) -> str | None:
        row = self.fetch_fishing_log_by_id_for_user_id(
            log_id=log_id,
            fish_sniper_user_id=fish_sniper_user_id,
        )
        if row is None:
            return None
        return f"{row.log_id}:{row.updated_at_utc.isoformat()}"

    def find_similar_fishing_log_for_user_id(
        self,
        *,
        fish_sniper_user_id: UUID,
        target_species: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[FishSniperFishingLogSimilarityHit]:
        candidates: list[FishSniperFishingLogRow] = []
        for row in self._fishing_log_row_list:
            if row.fish_sniper_user_id != fish_sniper_user_id:
                continue
            if row.target_species != target_species:
                continue
            if row.embedding_status != "done":
                continue
            if row.log_id not in self._embedding_by_log_id:
                continue
            candidates.append(row)

        hits: list[FishSniperFishingLogSimilarityHit] = []
        for row in candidates:
            stored = self._embedding_by_log_id[row.log_id]
            distance = _fish_sniper_cosine_distance_between_vectors(stored, query_embedding)
            hits.append(
                FishSniperFishingLogSimilarityHit(row=row, cosine_distance=distance),
            )
        hits.sort(key=lambda h: (h.cosine_distance, str(h.row.log_id)))
        return hits[:top_k]


