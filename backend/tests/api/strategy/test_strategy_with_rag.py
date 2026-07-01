"""HTTP tests for POST /agent/strategy with RAG (P4 Part 2)."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

from fastapi.testclient import TestClient

from auth.jwt_tokens import issue_access_token_jwt_for_fish_sniper_user_id
from embedding.deps import get_fish_sniper_embedding_client
from llm.models import LlmGenerationResult
from main import create_fish_sniper_app
from persistence.deps import get_persistence
from shared_infras.settings import AppSettings, get_settings
from shared_infras.time import get_reference_time_utc_callable
from tests.doubles import FakeFishSniperEmbeddingClient, InMemoryFishSniperPersistenceAdapter

_STRATEGY_LLM_JSON = json.dumps(
    {
        "todays_pattern": {
            "headline": "Post-Spawn Largemouth",
            "subline": "Shallow cover + wind lanes",
        },
        "confidence_pct": 82,
        "confidence_note": "Based on your prior trip and today's weather.",
        "holding_zones": [
            {"label": "Windblown rocky point", "weight_pct": 70},
            {"label": "First drop outside flat", "weight_pct": 20},
            {"label": "Isolated wood in 2m depth", "weight_pct": 10},
        ],
        "fish_state": (
            "Bass are holding tight to cover with this wind. "
            "Expect short feeding windows near structure."
        ),
        "recommendations": [
            {
                "tactical_role": "locator_bait",
                "lure_type": "Jig",
                "lure_color": "Black",
                "reason": "Matches cover-oriented mood and prior trip success.",
                "retrieve_technique": "Slow drag with pauses.",
            },
            {
                "tactical_role": "follow_up_bait",
                "lure_type": "Crankbait",
                "lure_color": "Chartreuse",
                "reason": "Covers slightly deeper edges if fish slide off the bank.",
                "retrieve_technique": "Steady retrieve.",
            },
            {
                "tactical_role": "finesse_cleanup",
                "lure_type": "Ned rig",
                "lure_color": "Brown",
                "reason": "Finesse change-up for lock-jaw fish on the bottom.",
                "retrieve_technique": "Drag and deadstick.",
            },
        ],
    },
)

_MOCK_STRATEGY_GENERATION_RESULT = LlmGenerationResult(
    raw_text=_STRATEGY_LLM_JSON,
    provider="gemini",
    model_id="gemini-flash",
    provider_model="test-model",
    temperature=0.8,
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


def _strategy_test_settings(
    *,
    gemini_api_key: str | None = "test-gemini-key",
    openai_api_key: str | None = None,
) -> AppSettings:
    return get_settings().model_copy(
        update={
            "gemini_api_key": gemini_api_key,
            "openai_api_key": openai_api_key,
        },
    )


def _install_strategy_dependency_overrides(
    app,
    *,
    fish_sniper_persistence: InMemoryFishSniperPersistenceAdapter,
    reference_time_utc_callable: Callable[[], datetime],
    embedding_client: FakeFishSniperEmbeddingClient,
    backend_settings: AppSettings | None = None,
) -> None:
    settings = backend_settings or _strategy_test_settings()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_persistence] = lambda: fish_sniper_persistence
    app.dependency_overrides[get_reference_time_utc_callable] = lambda: reference_time_utc_callable
    app.dependency_overrides[get_fish_sniper_embedding_client] = lambda: embedding_client


def _bearer_headers_for_user(
    *,
    fish_sniper_user_id: UUID,
    normalized_email_address: str,
) -> dict[str, str]:
    settings = get_settings()
    token = issue_access_token_jwt_for_fish_sniper_user_id(
        fish_sniper_user_id=fish_sniper_user_id,
        normalized_email_address=normalized_email_address,
        fish_sniper_backend_settings=settings,
    )
    return {"Authorization": f"Bearer {token}"}


@patch(
    "strategy.graph._generate_structured_json",
    new=AsyncMock(return_value=_MOCK_STRATEGY_GENERATION_RESULT),
)
def test_post_strategy_with_matching_log_returns_referenced_log(
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
    assert payload["todays_pattern"]["headline"] == "Post-Spawn Largemouth"
    assert payload["confidence_pct"] == 82
    assert len(payload["holding_zones"]) == 3
    assert sum(zone["weight_pct"] for zone in payload["holding_zones"]) == 100
    assert payload["recommendations"][0]["tactical_role"] == "locator_bait"
    assert payload["recommendations"][0]["reason"]


@patch(
    "strategy.graph._generate_structured_json",
    new=AsyncMock(return_value=_MOCK_STRATEGY_GENERATION_RESULT),
)
def test_post_strategy_without_done_logs_returns_zero_rag(
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


@patch(
    "strategy.graph._generate_structured_json",
    new=AsyncMock(return_value=_MOCK_STRATEGY_GENERATION_RESULT),
)
def test_post_strategy_unknown_llm_model_id_returns_400(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _ = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="bad-model@example.com",
    )
    app = create_fish_sniper_app()
    _install_strategy_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
        embedding_client=FakeFishSniperEmbeddingClient(vector=_dim1536(1.0, 0.0)),
    )
    client = TestClient(app)
    body = _strategy_request_body()
    body["llm_model_id"] = "not-in-catalog"

    response = client.post(
        "/agent/strategy",
        headers=_bearer_headers_for_user(
            fish_sniper_user_id=user_row.fish_sniper_user_id,
            normalized_email_address=user_row.normalized_email_address,
        ),
        json=body,
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "INVALID_PAYLOAD"
    assert "Unknown llm_model_id" in payload["message"]


@patch(
    "strategy.graph._generate_structured_json",
    new=AsyncMock(return_value=_MOCK_STRATEGY_GENERATION_RESULT),
)
def test_post_strategy_openai_model_without_key_returns_503(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _ = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="no-openai@example.com",
    )
    app = create_fish_sniper_app()
    _install_strategy_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
        embedding_client=FakeFishSniperEmbeddingClient(vector=_dim1536(1.0, 0.0)),
        backend_settings=_strategy_test_settings(openai_api_key=None),
    )
    client = TestClient(app)
    body = _strategy_request_body()
    body["llm_model_id"] = "gpt-4o-mini"

    response = client.post(
        "/agent/strategy",
        headers=_bearer_headers_for_user(
            fish_sniper_user_id=user_row.fish_sniper_user_id,
            normalized_email_address=user_row.normalized_email_address,
        ),
        json=body,
    )

    assert response.status_code == 503
    assert response.json() == {
        "error": "Selected model is not configured for this environment",
    }


@patch(
    "strategy.graph._generate_structured_json",
    new=AsyncMock(return_value=_MOCK_STRATEGY_GENERATION_RESULT),
)
def test_post_strategy_explicit_llm_model_id_succeeds(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _ = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="explicit-model@example.com",
    )
    app = create_fish_sniper_app()
    _install_strategy_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
        embedding_client=FakeFishSniperEmbeddingClient(vector=_dim1536(1.0, 0.0)),
    )
    client = TestClient(app)
    body = _strategy_request_body()
    body["llm_model_id"] = "gemini-flash"

    response = client.post(
        "/agent/strategy",
        headers=_bearer_headers_for_user(
            fish_sniper_user_id=user_row.fish_sniper_user_id,
            normalized_email_address=user_row.normalized_email_address,
        ),
        json=body,
    )

    assert response.status_code == 200
