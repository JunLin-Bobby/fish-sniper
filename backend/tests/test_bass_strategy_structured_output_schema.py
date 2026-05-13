"""Schema validation for POST /agent/strategy structured LLM JSON (single-call shape)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from schemas.agent_schemas import (
    BassStrategyStructuredLlmOutputBody,
    GenerateBassStrategySuccessResponseBody,
    ReferencedLogPayload,
    WeatherSnapshotPayload,
)


def test_bass_strategy_structured_llm_output_accepts_three_recommendations() -> None:
    payload = {
        "fish_state": "Bass should be active in mid-column with this wind and cloud cover.",
        "confidence_note": "General best practices only; no past trips on file.",
        "recommendations": [
            {
                "lure_type": "Jerkbait",
                "lure_color": "Ghost shad",
                "retrieve_technique": "Jerk-pause 2s, repeat.",
            },
            {
                "lure_type": "Swimbait",
                "lure_color": "Green pumpkin",
                "retrieve_technique": "Slow steady retrieve.",
            },
            {
                "lure_type": "Ned rig",
                "lure_color": "Brown",
                "retrieve_technique": "Drag with long pauses on bottom.",
            },
        ],
    }
    model = BassStrategyStructuredLlmOutputBody.model_validate(payload)
    assert len(model.recommendations) == 3
    assert model.recommendations[0].lure_type == "Jerkbait"


@pytest.mark.parametrize(
    "bad_payload",
    [
        {
            "fish_state": "x",
            "confidence_note": "y",
            "recommendations": [
                {"lure_type": "a", "lure_color": "b", "retrieve_technique": "c"},
                {"lure_type": "a", "lure_color": "b", "retrieve_technique": "c"},
            ],
        },
        {
            "fish_state": "x",
            "confidence_note": "y",
            "recommendations": [],
        },
        {
            "fish_state": "",
            "confidence_note": "y",
            "recommendations": [
                {"lure_type": "a", "lure_color": "b", "retrieve_technique": "c"},
                {"lure_type": "a", "lure_color": "b", "retrieve_technique": "c"},
                {"lure_type": "a", "lure_color": "b", "retrieve_technique": "c"},
            ],
        },
    ],
)
def test_bass_strategy_structured_llm_output_rejects_invalid_shapes(bad_payload: dict) -> None:
    with pytest.raises(ValidationError):
        BassStrategyStructuredLlmOutputBody.model_validate(bad_payload)


def test_generate_bass_strategy_success_accepts_referenced_log_none() -> None:
    body = GenerateBassStrategySuccessResponseBody(
        fish_state="x",
        confidence_note="y",
        recommendations=[
            {"lure_type": "a", "lure_color": "b", "retrieve_technique": "c"},
            {"lure_type": "a", "lure_color": "b", "retrieve_technique": "c"},
            {"lure_type": "a", "lure_color": "b", "retrieve_technique": "c"},
        ],
        weather_snapshot=WeatherSnapshotPayload(
            temperature_c=1.0,
            pressure_hpa=1000,
            wind_speed_ms=1.0,
            condition_code="sunny",
        ),
        rag_logs_used=0,
        referenced_log=None,
        generated_at=datetime.now(tz=UTC),
    )
    assert body.referenced_log is None
    assert body.rag_logs_used == 0


def test_generate_bass_strategy_success_accepts_referenced_log_payload() -> None:
    lid = uuid4()
    ref = ReferencedLogPayload(
        log_id=lid,
        log_date=date(2026, 4, 15),
        fishing_location="River",
        lure_type="Jig",
        lure_color="Black",
        retrieve_speed="Slow",
        caught_count=2,
    )
    body = GenerateBassStrategySuccessResponseBody(
        fish_state="x",
        confidence_note="y",
        recommendations=[
            {"lure_type": "a", "lure_color": "b", "retrieve_technique": "c"},
            {"lure_type": "a", "lure_color": "b", "retrieve_technique": "c"},
            {"lure_type": "a", "lure_color": "b", "retrieve_technique": "c"},
        ],
        weather_snapshot=WeatherSnapshotPayload(
            temperature_c=1.0,
            pressure_hpa=1000,
            wind_speed_ms=1.0,
            condition_code="sunny",
        ),
        rag_logs_used=1,
        referenced_log=ref,
        generated_at=datetime.now(tz=UTC),
    )
    assert body.rag_logs_used == 1
    assert body.referenced_log is not None
    assert body.referenced_log.log_id == lid


def test_referenced_log_payload_rejects_missing_field() -> None:
    with pytest.raises(ValidationError):
        ReferencedLogPayload.model_validate(
            {
                "log_id": str(uuid4()),
                "log_date": "2026-04-15",
                "fishing_location": "X",
                "lure_type": "Jig",
                "lure_color": "Black",
                "retrieve_speed": "Slow",
            },
        )
