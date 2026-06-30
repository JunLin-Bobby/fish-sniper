"""Unit tests for strategy LangGraph Step 2 RAG node (P4 Part 2)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from embedding.port import (
    FishSniperEmbeddingMisconfiguredError,
    FishSniperEmbeddingUnavailableError,
)
from persistence.errors import FishSniperPersistenceUnavailableError
from settings import AppSettings
from strategy.graph import node_search_personal_reference_log
from strategy.schemas import GenerateBassStrategyRequestBody, ManualWeatherPayload
from tests.doubles import FakeFishSniperEmbeddingClient, InMemoryFishSniperPersistenceAdapter


def _dim1536(a: float, b: float = 0.0) -> list[float]:
    v = [0.0] * 1536
    v[0] = a
    v[1] = b
    return v


def _base_state(
    *,
    persistence: InMemoryFishSniperPersistenceAdapter,
    embedding: FakeFishSniperEmbeddingClient,
    request: GenerateBassStrategyRequestBody,
    user_id,
) -> dict:
    return {
        "fish_sniper_user_id": user_id,
        "parsed_request_body": request,
        "fish_sniper_backend_settings": AppSettings(),
        "persistence_port": persistence,
        "weather_snapshot_cache_port": object(),
        "reference_time_utc": datetime(2026, 5, 10, 12, 0, 0, tzinfo=UTC),
        "langfuse_client": None,
        "profile_region_display_name": "Boston",
        "temperature_celsius": 18.0,
        "pressure_hectopascals": 1010,
        "wind_speed_meters_per_second": 2.0,
        "condition_code": "cloudy",
        "embedding_client": embedding,
    }


@pytest.mark.asyncio
async def test_rag_node_returns_empty_when_embedding_transient_fails() -> None:
    adapter = InMemoryFishSniperPersistenceAdapter()
    user = adapter.insert_user_row_for_normalized_email(normalized_email_address="g1@example.com")
    request = GenerateBassStrategyRequestBody(
        region="Boston",
        fishing_location="Pond",
        water_depth_m=1.0,
        fishing_scene="lake",
        target_species="Largemouth Bass",
        manual_weather=ManualWeatherPayload(
            temperature_c=18.0,
            condition_code="cloudy",
            wind_speed_ms=2.0,
            pressure_hpa=1010,
        ),
    )
    embed = FakeFishSniperEmbeddingClient(
        error_factory=lambda: FishSniperEmbeddingUnavailableError("down"),
    )
    state = _base_state(
        persistence=adapter,
        embedding=embed,
        request=request,
        user_id=user.fish_sniper_user_id,
    )
    out = await node_search_personal_reference_log(state)
    assert out["has_personal_log"] is False
    assert out["retrieved_log_count"] == 0


@pytest.mark.asyncio
async def test_rag_node_returns_empty_when_persistence_fails() -> None:
    class FlakyPersistence(InMemoryFishSniperPersistenceAdapter):
        def find_similar_fishing_log_for_user_id(self, **_kwargs):
            raise FishSniperPersistenceUnavailableError("db")

    adapter = FlakyPersistence()
    user = adapter.insert_user_row_for_normalized_email(normalized_email_address="g2@example.com")
    request = GenerateBassStrategyRequestBody(
        region="Boston",
        fishing_location="Pond",
        water_depth_m=1.0,
        fishing_scene="lake",
        target_species="Largemouth Bass",
        manual_weather=ManualWeatherPayload(
            temperature_c=18.0,
            condition_code="cloudy",
            wind_speed_ms=2.0,
            pressure_hpa=1010,
        ),
    )
    state = _base_state(
        persistence=adapter,
        embedding=FakeFishSniperEmbeddingClient(vector=_dim1536(1.0)),
        request=request,
        user_id=user.fish_sniper_user_id,
    )
    out = await node_search_personal_reference_log(state)
    assert out["has_personal_log"] is False


@pytest.mark.asyncio
async def test_rag_node_propagates_misconfigured_embedding_error() -> None:
    adapter = InMemoryFishSniperPersistenceAdapter()
    user = adapter.insert_user_row_for_normalized_email(normalized_email_address="g3@example.com")
    request = GenerateBassStrategyRequestBody(
        region="Boston",
        fishing_location="Pond",
        water_depth_m=1.0,
        fishing_scene="lake",
        target_species="Largemouth Bass",
        manual_weather=ManualWeatherPayload(
            temperature_c=18.0,
            condition_code="cloudy",
            wind_speed_ms=2.0,
            pressure_hpa=1010,
        ),
    )
    embed = FakeFishSniperEmbeddingClient(
        error_factory=lambda: FishSniperEmbeddingMisconfiguredError("bad"),
    )
    state = _base_state(
        persistence=adapter,
        embedding=embed,
        request=request,
        user_id=user.fish_sniper_user_id,
    )
    with pytest.raises(FishSniperEmbeddingMisconfiguredError):
        await node_search_personal_reference_log(state)


@pytest.mark.asyncio
async def test_rag_node_selects_top_hit_when_logs_exist() -> None:
    adapter = InMemoryFishSniperPersistenceAdapter()
    user = adapter.insert_user_row_for_normalized_email(normalized_email_address="g4@example.com")
    now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)

    adapter.insert_fishing_log_for_user_id(
        fish_sniper_user_id=user.fish_sniper_user_id,
        log_date=date(2026, 5, 1),
        fishing_location="Far pond",
        fishing_scene="lake",
        target_species="Largemouth Bass",
        water_depth_m=2.0,
        lure_type="Crank",
        lure_color="Red",
        retrieve_speed="Fast",
        caught_count=0,
        weight_lb=None,
        length_cm=None,
        temperature_c=20.0,
        wind_speed_ms=1.0,
        pressure_hpa=1010,
        condition_code="sunny",
        notes="",
        embedding=_dim1536(0.0, 1.0),
        embedding_text_version=1,
        reference_time_utc=now,
    )
    log_close = adapter.insert_fishing_log_for_user_id(
        fish_sniper_user_id=user.fish_sniper_user_id,
        log_date=date(2026, 5, 2),
        fishing_location="Close pond",
        fishing_scene="lake",
        target_species="Largemouth Bass",
        water_depth_m=1.5,
        lure_type="Jig",
        lure_color="Black",
        retrieve_speed="Slow",
        caught_count=2,
        weight_lb=None,
        length_cm=None,
        temperature_c=20.0,
        wind_speed_ms=1.0,
        pressure_hpa=1010,
        condition_code="sunny",
        notes="",
        embedding=_dim1536(1.0, 0.0),
        embedding_text_version=1,
        reference_time_utc=now,
    )
    request = GenerateBassStrategyRequestBody(
        region="Boston",
        fishing_location="Close pond",
        water_depth_m=1.5,
        fishing_scene="lake",
        target_species="Largemouth Bass",
        manual_weather=ManualWeatherPayload(
            temperature_c=20.0,
            condition_code="sunny",
            wind_speed_ms=1.0,
            pressure_hpa=1010,
        ),
    )
    state = _base_state(
        persistence=adapter,
        embedding=FakeFishSniperEmbeddingClient(vector=_dim1536(1.0, 0.0)),
        request=request,
        user_id=user.fish_sniper_user_id,
    )
    out = await node_search_personal_reference_log(state)
    assert out["has_personal_log"] is True
    assert out["selected_reference_log"].log_id == log_close
    assert out["retrieved_log_count"] == 2
