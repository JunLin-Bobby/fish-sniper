"""HTTP tests for POST /agent/strategy with RAG (P4 Part 2)."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient

from auth.jwt_tokens import issue_access_token_jwt_for_fish_sniper_user_id
from deps import (
    get_fish_sniper_embedding_client,
    get_fish_sniper_persistence_port,
    get_reference_time_utc_callable,
)
from main import create_fish_sniper_app
from settings import get_fish_sniper_backend_settings
from tests.conftest import FakeFishSniperEmbeddingClient, InMemoryFishSniperPersistenceAdapter

_STRATEGY_LLM_JSON = json.dumps(
    {
        "fish_state": "Bass are holding tight to cover with this wind.",
        "confidence_note": "Based on your prior trip and today's weather.",
        "recommendations": [
            {
                "lure_type": "Jig",
                "lure_color": "Black",
                "retrieve_technique": "Slow drag with pauses.",
            },
            {
                "lure_type": "Crankbait",
                "lure_color": "Chartreuse",
                "retrieve_technique": "Steady retrieve.",
            },
            {
                "lure_type": "Ned rig",
                "lure_color": "Brown",
                "retrieve_technique": "Drag and deadstick.",
            },
        ],
    },
)


def _dim1536(a: float, b: float = 0.0) -> list[float]:
    v = [0.0] * 1536
    v[0] = a
    v[1] = b
    return v


def _strategy_request_body() -> dict:
    return {
        "region": "Boston",
        "fishing_location": "Close pond",
        "water_depth_m": 1.5,
        "fishing_scene": "lake",
        "target_species": "Largemouth Bass",
        "manual_weather": {
            "temperature_c": 20.0,
            "condition_code": "sunny",
            "wind_speed_ms": 1.0,
            "pressure_hpa": 1010,
        },
    }


def _install_strategy_dependency_overrides(
    app,
    *,
    fish_sniper_persistence: InMemoryFishSniperPersistenceAdapter,
    reference_time_utc_callable: Callable[[], datetime],
    embedding_client: FakeFishSniperEmbeddingClient,
) -> None:
    app.dependency_overrides[get_fish_sniper_persistence_port] = lambda: fish_sniper_persistence
    app.dependency_overrides[get_reference_time_utc_callable] = lambda: reference_time_utc_callable
    app.dependency_overrides[get_fish_sniper_embedding_client] = lambda: embedding_client


def _bearer_headers_for_user(
    *,
    fish_sniper_user_id: UUID,
    normalized_email_address: str,
) -> dict[str, str]:
    settings = get_fish_sniper_backend_settings()
    token = issue_access_token_jwt_for_fish_sniper_user_id(
        fish_sniper_user_id=fish_sniper_user_id,
        normalized_email_address=normalized_email_address,
        fish_sniper_backend_settings=settings,
    )
    return {"Authorization": f"Bearer {token}"}


@patch(
    "agent.fish_sniper_strategy_lang_graph.generate_text_from_gemini_with_system_and_user_prompts",
    return_value=_STRATEGY_LLM_JSON,
)
def test_post_strategy_with_matching_log_returns_referenced_log(
    _mock_gemini: object,
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _ = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="strat@example.com",
    )
    uid = user_row.fish_sniper_user_id
    now = now_utc()
    log_id = in_memory_persistence_adapter.insert_fishing_log_for_user_id(
        fish_sniper_user_id=uid,
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

    app = create_fish_sniper_app()
    _install_strategy_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
        embedding_client=FakeFishSniperEmbeddingClient(vector=_dim1536(1.0, 0.0)),
    )
    client = TestClient(app)
    response = client.post(
        "/agent/strategy",
        headers=_bearer_headers_for_user(
            fish_sniper_user_id=uid,
            normalized_email_address=user_row.normalized_email_address,
        ),
        json=_strategy_request_body(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["rag_logs_used"] == 1
    assert payload["referenced_log"] is not None
    assert payload["referenced_log"]["log_id"] == str(log_id)
    assert payload["referenced_log"]["fishing_location"] == "Close pond"
    assert payload["referenced_log"]["caught_count"] == 2


@patch(
    "agent.fish_sniper_strategy_lang_graph.generate_text_from_gemini_with_system_and_user_prompts",
    return_value=_STRATEGY_LLM_JSON,
)
def test_post_strategy_without_done_logs_returns_zero_rag(
    _mock_gemini: object,
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _ = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="strat2@example.com",
    )
    uid = user_row.fish_sniper_user_id

    app = create_fish_sniper_app()
    _install_strategy_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
        embedding_client=FakeFishSniperEmbeddingClient(vector=_dim1536(1.0, 0.0)),
    )
    client = TestClient(app)
    response = client.post(
        "/agent/strategy",
        headers=_bearer_headers_for_user(
            fish_sniper_user_id=uid,
            normalized_email_address=user_row.normalized_email_address,
        ),
        json=_strategy_request_body(),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["rag_logs_used"] == 0
    assert payload.get("referenced_log") in (None, {})
