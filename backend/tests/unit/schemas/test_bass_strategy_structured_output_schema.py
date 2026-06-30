"""Schema validation for POST /agent/strategy structured LLM JSON (v2 shape)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from strategy.schemas import (
    FISH_STATE_MAX_LENGTH,
    BassStrategyStructuredLlmOutputBody,
    GenerateBassStrategySuccessResponseBody,
    ReferencedLogPayload,
    WeatherSnapshotPayload,
)


def _valid_recommendation(
    tactical_role: str,
    *,
    lure_type: str = "Jerkbait",
    lure_color: str = "Ghost shad",
    reason: str = "Matches cloudy mid-column activity.",
    retrieve_technique: str = "Jerk-pause 2s, repeat.",
) -> dict[str, str]:
    return {
        "tactical_role": tactical_role,
        "lure_type": lure_type,
        "lure_color": lure_color,
        "reason": reason,
        "retrieve_technique": retrieve_technique,
    }


def _valid_v2_llm_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "todays_pattern": {
            "headline": "Post-Spawn Largemouth",
            "subline": "Shallow Flats + Windblown Banks",
        },
        "confidence_pct": 82,
        "confidence_note": "General best practices only; no past trips on file.",
        "holding_zones": [
            {"label": "Windblown rocky point", "weight_pct": 70},
            {"label": "First drop outside spawning flat", "weight_pct": 20},
            {"label": "Isolated wood in 2m depth", "weight_pct": 10},
        ],
        "fish_state": (
            "Bass should be active in mid-column with this wind and cloud cover. "
            "Expect short feeding windows along wind-blown banks."
        ),
        "recommendations": [
            _valid_recommendation("locator_bait"),
            _valid_recommendation(
                "follow_up_bait",
                lure_type="Swimbait",
                lure_color="Green pumpkin",
                retrieve_technique="Slow steady retrieve.",
            ),
            _valid_recommendation(
                "finesse_cleanup",
                lure_type="Ned rig",
                lure_color="Brown",
                retrieve_technique="Drag with long pauses on bottom.",
            ),
        ],
    }
    payload.update(overrides)
    return payload


def test_bass_strategy_structured_llm_output_accepts_v2_payload() -> None:
    model = BassStrategyStructuredLlmOutputBody.model_validate(_valid_v2_llm_payload())
    assert model.todays_pattern.headline == "Post-Spawn Largemouth"
    assert model.confidence_pct == 82
    assert len(model.holding_zones) == 3
    assert sum(zone.weight_pct for zone in model.holding_zones) == 100
    assert len(model.recommendations) == 3
    assert model.recommendations[0].tactical_role == "locator_bait"
    assert model.recommendations[1].tactical_role == "follow_up_bait"
    assert model.recommendations[2].tactical_role == "finesse_cleanup"


def test_bass_strategy_structured_llm_output_strips_string_fields() -> None:
    payload = _valid_v2_llm_payload(
        todays_pattern={
            "headline": "  Post-Spawn Largemouth  ",
            "subline": "  Shallow Flats  ",
        },
        fish_state="  First sentence. Second sentence.  ",
        confidence_note="  Note with padding.  ",
        holding_zones=[
            {"label": "  Windblown rocky point  ", "weight_pct": 70},
            {"label": "  First drop  ", "weight_pct": 20},
            {"label": "  Wood cover  ", "weight_pct": 10},
        ],
        recommendations=[
            _valid_recommendation(
                "locator_bait",
                lure_type="  Jerkbait  ",
                lure_color="  Ghost shad  ",
                reason="  Cloud cover push.  ",
                retrieve_technique="  Jerk-pause.  ",
            ),
            _valid_recommendation("follow_up_bait"),
            _valid_recommendation("finesse_cleanup"),
        ],
    )
    model = BassStrategyStructuredLlmOutputBody.model_validate(payload)
    assert model.todays_pattern.headline == "Post-Spawn Largemouth"
    assert model.holding_zones[0].label == "Windblown rocky point"
    assert model.recommendations[0].lure_type == "Jerkbait"


@pytest.mark.parametrize(
    "confidence_pct",
    [0, 100],
)
def test_bass_strategy_structured_llm_output_accepts_confidence_pct_bounds(
    confidence_pct: int,
) -> None:
    model = BassStrategyStructuredLlmOutputBody.model_validate(
        _valid_v2_llm_payload(confidence_pct=confidence_pct),
    )
    assert model.confidence_pct == confidence_pct


@pytest.mark.parametrize(
    "bad_payload",
    [
        pytest.param(
            {k: v for k, v in _valid_v2_llm_payload().items() if k != "todays_pattern"},
            id="missing_todays_pattern",
        ),
        pytest.param(
            _valid_v2_llm_payload(
                holding_zones=[
                    {"label": "A", "weight_pct": 50},
                    {"label": "B", "weight_pct": 30},
                    {"label": "C", "weight_pct": 30},
                ],
            ),
            id="holding_zones_weights_not_100",
        ),
        pytest.param(
            _valid_v2_llm_payload(
                holding_zones=[
                    {"label": "A", "weight_pct": 0},
                    {"label": "B", "weight_pct": 50},
                    {"label": "C", "weight_pct": 50},
                ],
            ),
            id="holding_zone_weight_below_1",
        ),
        pytest.param(
            _valid_v2_llm_payload(
                recommendations=[
                    _valid_recommendation("follow_up_bait"),
                    _valid_recommendation("locator_bait"),
                    _valid_recommendation("finesse_cleanup"),
                ],
            ),
            id="recommendation_tactical_roles_out_of_order",
        ),
        pytest.param(
            _valid_v2_llm_payload(confidence_pct=101),
            id="confidence_pct_above_100",
        ),
        pytest.param(
            _valid_v2_llm_payload(confidence_pct=-1),
            id="confidence_pct_below_0",
        ),
        pytest.param(
            _valid_v2_llm_payload(fish_state="x" * (FISH_STATE_MAX_LENGTH + 1)),
            id="fish_state_exceeds_max_length",
        ),
        pytest.param(
            {
                "fish_state": "x",
                "confidence_note": "y",
                "recommendations": [
                    _valid_recommendation("locator_bait"),
                    _valid_recommendation("follow_up_bait"),
                ],
            },
            id="legacy_shape_missing_v2_fields",
        ),
        pytest.param(
            _valid_v2_llm_payload(fish_state=""),
            id="blank_fish_state",
        ),
        pytest.param(
            _valid_v2_llm_payload(
                recommendations=[
                    _valid_recommendation("locator_bait", reason=""),
                    _valid_recommendation("follow_up_bait"),
                    _valid_recommendation("finesse_cleanup"),
                ],
            ),
            id="blank_recommendation_reason",
        ),
    ],
)
def test_bass_strategy_structured_llm_output_rejects_invalid_shapes(bad_payload: dict) -> None:
    with pytest.raises(ValidationError):
        BassStrategyStructuredLlmOutputBody.model_validate(bad_payload)


def _three_recommendations_for_success_response() -> list[dict[str, str]]:
    return [
        _valid_recommendation("locator_bait"),
        _valid_recommendation("follow_up_bait"),
        _valid_recommendation("finesse_cleanup"),
    ]


def _valid_v2_success_strategy_fields() -> dict[str, object]:
    llm_fields = _valid_v2_llm_payload()
    return {
        "todays_pattern": llm_fields["todays_pattern"],
        "confidence_pct": llm_fields["confidence_pct"],
        "confidence_note": llm_fields["confidence_note"],
        "holding_zones": llm_fields["holding_zones"],
        "fish_state": llm_fields["fish_state"],
        "recommendations": llm_fields["recommendations"],
    }


def _weather_snapshot() -> WeatherSnapshotPayload:
    return WeatherSnapshotPayload(
        temperature_c=1.0,
        pressure_hpa=1000,
        wind_speed_ms=1.0,
        condition_code="sunny",
    )


def test_generate_bass_strategy_success_accepts_v2_payload() -> None:
    body = GenerateBassStrategySuccessResponseBody(
        **_valid_v2_success_strategy_fields(),
        weather_snapshot=_weather_snapshot(),
        rag_logs_used=0,
        referenced_log=None,
        generated_at=datetime.now(tz=UTC),
    )
    assert body.todays_pattern.headline == "Post-Spawn Largemouth"
    assert body.confidence_pct == 82
    assert body.recommendations[0].tactical_role == "locator_bait"
    assert body.fallback is False


@pytest.mark.parametrize(
    "bad_overrides",
    [
        pytest.param({"confidence_pct": 101}, id="confidence_pct_above_100"),
        pytest.param(
            {
                "holding_zones": [
                    {"label": "A", "weight_pct": 50},
                    {"label": "B", "weight_pct": 30},
                    {"label": "C", "weight_pct": 30},
                ],
            },
            id="holding_zones_weights_not_100",
        ),
        pytest.param(
            {
                "recommendations": [
                    _valid_recommendation("follow_up_bait"),
                    _valid_recommendation("locator_bait"),
                    _valid_recommendation("finesse_cleanup"),
                ],
            },
            id="recommendation_tactical_roles_out_of_order",
        ),
    ],
)
def test_generate_bass_strategy_success_rejects_invalid_v2_fields(
    bad_overrides: dict[str, object],
) -> None:
    fields = _valid_v2_success_strategy_fields()
    fields.update(bad_overrides)
    with pytest.raises(ValidationError):
        GenerateBassStrategySuccessResponseBody(
            **fields,
            weather_snapshot=_weather_snapshot(),
            rag_logs_used=0,
            referenced_log=None,
            generated_at=datetime.now(tz=UTC),
        )


def test_generate_bass_strategy_success_accepts_referenced_log_none() -> None:
    body = GenerateBassStrategySuccessResponseBody(
        **_valid_v2_success_strategy_fields(),
        weather_snapshot=_weather_snapshot(),
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
        **_valid_v2_success_strategy_fields(),
        weather_snapshot=_weather_snapshot(),
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
