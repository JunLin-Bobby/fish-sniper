"""Shared pytest fixtures for FishSniper backend tests."""

from __future__ import annotations

import os

# Force predictable CORS + rate limits before `main` is imported by test modules.
os.environ["FRONTEND_ORIGIN"] = "http://localhost:5173"
os.environ["RATE_LIMIT_ENABLED"] = "false"

import math
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from embedding.port import FishSniperEmbeddingClient, FishSniperEmbeddingTask
from persistence.port import (
    FishSniperFishingLogRow,
    FishSniperFishingLogSimilarityHit,
    FishSniperUserPreferencesRow,
    FishSniperUserRow,
)
from settings import get_fish_sniper_backend_settings


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
        self._otp_challenge_row_list: list[dict[str, object]] = []
        self._user_row_by_normalized_email: dict[str, FishSniperUserRow] = {}
        self._preferences_row_by_user_id: dict[UUID, FishSniperUserPreferencesRow] = {}
        self._fishing_log_row_list: list[FishSniperFishingLogRow] = []
        self._embedding_by_log_id: dict[UUID, list[float]] = {}

    def fetch_seconds_since_last_otp_send_for_email(
        self,
        *,
        normalized_email_address: str,
        reference_time_utc: datetime,
    ) -> float | None:
        matching_created_at_list: list[datetime] = []
        for otp_row in self._otp_challenge_row_list:
            if otp_row["normalized_email_address"] == normalized_email_address:
                created_at = otp_row["otp_created_at_utc"]
                assert isinstance(created_at, datetime)
                matching_created_at_list.append(created_at)
        if not matching_created_at_list:
            return None
        latest_created_at_utc = max(matching_created_at_list)
        return (reference_time_utc - latest_created_at_utc).total_seconds()

    def insert_pending_otp_challenge_for_email(
        self,
        *,
        normalized_email_address: str,
        otp_code_six_digits: str,
        otp_expires_at_utc: datetime,
        otp_created_at_utc: datetime,
    ) -> None:
        self._otp_challenge_row_list.append(
            {
                "normalized_email_address": normalized_email_address,
                "otp_code_six_digits": otp_code_six_digits,
                "otp_expires_at_utc": otp_expires_at_utc,
                "otp_created_at_utc": otp_created_at_utc,
            }
        )

    def delete_matching_unexpired_otp_or_noop(
        self,
        *,
        normalized_email_address: str,
        otp_code_six_digits: str,
        reference_time_utc: datetime,
    ) -> bool:
        for index, otp_row in enumerate(self._otp_challenge_row_list):
            expires_at = otp_row["otp_expires_at_utc"]
            if (
                otp_row["normalized_email_address"] == normalized_email_address
                and otp_row["otp_code_six_digits"] == otp_code_six_digits
                and isinstance(expires_at, datetime)
                and expires_at > reference_time_utc
            ):
                del self._otp_challenge_row_list[index]
                return True
        return False

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

    def delete_otp_codes_for_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> None:
        self._otp_challenge_row_list = [
            otp_row
            for otp_row in self._otp_challenge_row_list
            if otp_row["normalized_email_address"] != normalized_email_address
        ]

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


class FakeFishSniperEmbeddingClient(FishSniperEmbeddingClient):
    """Configurable fake used by every backend test to avoid real Gemini calls.

    Default behaviour: return a fixed 1536-d vector. Tests that exercise the
    transient-failure path inject a different fake (see
    ``test_logs_api`` POST-Gemini-fail case) by overriding the FastAPI
    dependency directly.
    """

    def __init__(
        self,
        *,
        vector: list[float] | None = None,
        error_factory: Callable[[], Exception] | None = None,
    ) -> None:
        self._vector: list[float] = vector if vector is not None else [0.001] * 1536
        self._error_factory = error_factory
        self.call_count = 0

    def embed(
        self,
        *,
        text: str,
        task: FishSniperEmbeddingTask = "document",
    ) -> list[float]:
        _ = text
        _ = task
        self.call_count += 1
        if self._error_factory is not None:
            raise self._error_factory()
        return list(self._vector)


class RecordingTransactionalEmailSenderAdapter:
    """Captures OTP email sends for assertions."""

    def __init__(self) -> None:
        self.recipient_and_otp_tuple_list: list[tuple[str, str]] = []

    def send_fish_sniper_email_otp_message(
        self,
        *,
        recipient_email_address: str,
        otp_code_six_digits: str,
    ) -> None:
        self.recipient_and_otp_tuple_list.append((recipient_email_address, otp_code_six_digits))


class ExplodingTransactionalEmailSenderAdapter:
    """Always fails email delivery."""

    def send_fish_sniper_email_otp_message(
        self,
        *,
        recipient_email_address: str,
        otp_code_six_digits: str,
    ) -> None:
        _ = (recipient_email_address, otp_code_six_digits)
        raise RuntimeError("simulated email delivery failure")


@pytest.fixture
def frozen_clock() -> tuple[Callable[[], datetime], Callable[[float], None]]:
    """Controllable UTC clock for OTP cooldown tests."""

    current = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)

    def now_utc() -> datetime:
        return current

    def advance_seconds(seconds: float) -> None:
        nonlocal current
        current = current + timedelta(seconds=seconds)

    return now_utc, advance_seconds


@pytest.fixture
def in_memory_persistence_adapter() -> InMemoryFishSniperPersistenceAdapter:
    return InMemoryFishSniperPersistenceAdapter()


@pytest.fixture
def recording_email_sender_adapter() -> RecordingTransactionalEmailSenderAdapter:
    return RecordingTransactionalEmailSenderAdapter()


@pytest.fixture
def exploding_email_sender_adapter() -> ExplodingTransactionalEmailSenderAdapter:
    return ExplodingTransactionalEmailSenderAdapter()


@pytest.fixture(autouse=True)
def reset_fish_sniper_backend_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stabilize JWT settings and avoid leaking lru_cache between tests."""

    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret")
    monkeypatch.setenv("SKIP_AUTH", "false")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:5173")
    get_fish_sniper_backend_settings.cache_clear()
    yield
    get_fish_sniper_backend_settings.cache_clear()


@pytest.fixture
def fake_fish_sniper_embedding_client() -> FakeFishSniperEmbeddingClient:
    """Default fake embedding client (returns a fixed 1536-d vector)."""

    return FakeFishSniperEmbeddingClient()
