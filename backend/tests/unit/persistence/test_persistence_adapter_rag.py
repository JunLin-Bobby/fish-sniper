"""Persistence RAG similarity search (P4 Part 2)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest

from persistence.errors import FishSniperPersistenceUnavailableError
from persistence.port import FishSniperFishingLogSimilarityHit
from persistence.supabase_fish_sniper_persistence_adapter import (
    SupabaseFishSniperPersistenceAdapter,
)
from settings import AppSettings
from tests.doubles.in_memory_db import InMemoryFishSniperPersistenceAdapter


def _dim1536(a: float, b: float = 0.0) -> list[float]:
    v = [0.0] * 1536
    v[0] = a
    v[1] = b
    return v


def _minimal_insert_kwargs(
    *,
    fish_sniper_user_id: UUID,
    embedding: list[float] | None,
    target_species: str = "Largemouth Bass",
    fishing_location: str = "Spot A",
) -> dict:
    now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    return dict(
        fish_sniper_user_id=fish_sniper_user_id,
        log_date=date(2026, 5, 1),
        fishing_location=fishing_location,
        fishing_scene="lake",
        target_species=target_species,
        water_depth_m=1.5,
        lure_type="Jig",
        lure_color="Black",
        retrieve_speed="Slow",
        caught_count=1,
        weight_lb=None,
        length_cm=None,
        temperature_c=20.0,
        wind_speed_ms=1.0,
        pressure_hpa=1010,
        condition_code="sunny",
        notes="",
        embedding=embedding,
        embedding_text_version=1,
        reference_time_utc=now,
    )


def test_in_memory_find_similar_returns_empty_when_no_done_embeddings() -> None:
    adapter = InMemoryFishSniperPersistenceAdapter()
    user = adapter.insert_user_row_for_normalized_email(normalized_email_address="rag@example.com")
    adapter.insert_fishing_log_for_user_id(
        **_minimal_insert_kwargs(
            fish_sniper_user_id=user.fish_sniper_user_id,
            embedding=None,
        ),
    )
    hits = adapter.find_similar_fishing_log_for_user_id(
        fish_sniper_user_id=user.fish_sniper_user_id,
        target_species="Largemouth Bass",
        query_embedding=_dim1536(1.0),
        top_k=3,
    )
    assert hits == []


def test_in_memory_find_similar_orders_by_cosine_distance_with_tie_breaker() -> None:
    adapter = InMemoryFishSniperPersistenceAdapter()
    user = adapter.insert_user_row_for_normalized_email(normalized_email_address="rag2@example.com")
    v_match = _dim1536(1.0, 0.0)
    v_other = _dim1536(0.0, 1.0)
    adapter.insert_fishing_log_for_user_id(
        **_minimal_insert_kwargs(
            fish_sniper_user_id=user.fish_sniper_user_id,
            embedding=v_other,
            fishing_location="Far",
        ),
    )
    adapter.insert_fishing_log_for_user_id(
        **_minimal_insert_kwargs(
            fish_sniper_user_id=user.fish_sniper_user_id,
            embedding=v_match,
            fishing_location="Close",
        ),
    )
    hits = adapter.find_similar_fishing_log_for_user_id(
        fish_sniper_user_id=user.fish_sniper_user_id,
        target_species="Largemouth Bass",
        query_embedding=_dim1536(1.0, 0.0),
        top_k=3,
    )
    assert len(hits) == 2
    assert hits[0].cosine_distance <= hits[1].cosine_distance
    assert hits[0].row.fishing_location == "Close"


def test_in_memory_find_similar_filters_target_species() -> None:
    adapter = InMemoryFishSniperPersistenceAdapter()
    user = adapter.insert_user_row_for_normalized_email(normalized_email_address="rag3@example.com")
    adapter.insert_fishing_log_for_user_id(
        **_minimal_insert_kwargs(
            fish_sniper_user_id=user.fish_sniper_user_id,
            embedding=_dim1536(1.0),
            target_species="Smallmouth Bass",
        ),
    )
    hits = adapter.find_similar_fishing_log_for_user_id(
        fish_sniper_user_id=user.fish_sniper_user_id,
        target_species="Largemouth Bass",
        query_embedding=_dim1536(1.0),
        top_k=3,
    )
    assert hits == []


def test_in_memory_delete_removes_embedding_sidecar() -> None:
    adapter = InMemoryFishSniperPersistenceAdapter()
    user = adapter.insert_user_row_for_normalized_email(normalized_email_address="rag4@example.com")
    log_id = adapter.insert_fishing_log_for_user_id(
        **_minimal_insert_kwargs(
            fish_sniper_user_id=user.fish_sniper_user_id,
            embedding=_dim1536(1.0),
        ),
    )
    assert adapter.delete_fishing_log_for_user_id(
        log_id=log_id,
        fish_sniper_user_id=user.fish_sniper_user_id,
    )
    hits = adapter.find_similar_fishing_log_for_user_id(
        fish_sniper_user_id=user.fish_sniper_user_id,
        target_species="Largemouth Bass",
        query_embedding=_dim1536(1.0),
        top_k=3,
    )
    assert hits == []


@patch("persistence.supabase_fish_sniper_persistence_adapter.create_client")
def test_supabase_find_similar_maps_rpc_payload_to_hits(mock_create_client: MagicMock) -> None:
    uid = uuid4()
    log_id = uuid4()
    log_jsonb = {
        "id": str(log_id),
        "user_id": str(uid),
        "date": "2026-05-01",
        "fishing_location": "River",
        "fishing_scene": "river",
        "target_species": "Largemouth Bass",
        "water_depth_m": 2.0,
        "lure_type": "Crank",
        "lure_color": "Red",
        "retrieve_speed": "Medium",
        "caught_count": 2,
        "weight_lb": None,
        "length_cm": None,
        "temperature_c": 19.0,
        "wind_speed_ms": 2.0,
        "pressure_hpa": 1009,
        "condition_code": "cloudy",
        "notes": "n",
        "embedding_status": "done",
        "embedding_text_version": 1,
        "embedding_attempt_count": 0,
        "created_at": "2026-05-01T12:00:00Z",
        "updated_at": "2026-05-01T12:00:00Z",
    }
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    mock_client.rpc.return_value.execute.return_value = MagicMock(
        data=[{"log_jsonb": log_jsonb, "cosine_distance": 0.42}],
    )

    settings = AppSettings(
        supabase_url="http://localhost:54321",
        supabase_service_role_key="test-service-role",
    )
    adapter = SupabaseFishSniperPersistenceAdapter(settings)
    q = [0.01] * 1536
    hits = adapter.find_similar_fishing_log_for_user_id(
        fish_sniper_user_id=uid,
        target_species="Largemouth Bass",
        query_embedding=q,
        top_k=3,
    )

    assert len(hits) == 1
    assert isinstance(hits[0], FishSniperFishingLogSimilarityHit)
    assert hits[0].row.log_id == log_id
    assert hits[0].cosine_distance == pytest.approx(0.42)
    mock_client.rpc.assert_called_once()
    call_kw = mock_client.rpc.call_args[0][1]
    assert call_kw["p_user_id"] == str(uid)
    assert call_kw["p_target_species"] == "Largemouth Bass"
    assert call_kw["p_limit"] == 3
    assert call_kw["p_query_embedding"].startswith("[")
    assert call_kw["p_query_embedding"].endswith("]")


@patch("persistence.supabase_fish_sniper_persistence_adapter.create_client")
def test_supabase_find_similar_timeout_maps_to_unavailable(mock_create_client: MagicMock) -> None:
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client
    mock_client.rpc.return_value.execute.side_effect = httpx.TimeoutException("timeout")

    settings = AppSettings(
        supabase_url="http://localhost:54321",
        supabase_service_role_key="test-service-role",
    )
    adapter = SupabaseFishSniperPersistenceAdapter(settings)

    with pytest.raises(FishSniperPersistenceUnavailableError):
        adapter.find_similar_fishing_log_for_user_id(
            fish_sniper_user_id=uuid4(),
            target_species="Largemouth Bass",
            query_embedding=[0.1] * 1536,
            top_k=1,
        )
