"""Schema validation for POST /agent/strategy structured LLM JSON (single-call shape)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas.agent_schemas import BassStrategyStructuredLlmOutputBody


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
