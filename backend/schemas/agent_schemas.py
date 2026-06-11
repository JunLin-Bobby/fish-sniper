"""Pydantic models for agent routes (strategy + model catalog).

Schema layers (top → bottom in this file):

1. **HTTP request** — ``POST /agent/strategy`` body from the client.
2. **LLM structured output** — JSON shape the model must return; validated in LangGraph Step 5.
3. **HTTP response parts** — Weather echo and RAG reference log attached to success payloads.
4. **HTTP response envelopes** — ``POST /agent/strategy`` success vs fallback discriminated union.
5. **Model catalog** — ``GET /agent/models`` list for the strategy UI.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

# =============================================================================
# Shared literals
# =============================================================================

FishSniperStrategyTargetSpeciesLiteral = Literal["Largemouth Bass", "Smallmouth Bass"]


# =============================================================================
# Layer 1 — HTTP request (POST /agent/strategy body)
# =============================================================================


class ManualWeatherPayload(BaseModel):
    """Optional weather override on the strategy request (skips OpenWeatherMap)."""

    temperature_c: float = Field(description="Air temperature in degrees Celsius.")
    condition_code: str = Field(
        description="FishSniper weather bucket: sunny|cloudy|rainy|stormy|snowy.",
    )
    wind_speed_ms: float = Field(description="Wind speed in meters per second.")
    pressure_hpa: int = Field(description="Air pressure in hectopascals.")


class GenerateBassStrategyRequestBody(BaseModel):
    """User-supplied fishing context for the LangGraph strategy pipeline."""

    region: str = Field(
        min_length=1,
        description="City or region label for weather lookup (OpenWeatherMap query).",
    )
    fishing_location: str = Field(
        description="Free-text fishing spot label used for display and future RAG filters.",
    )
    water_depth_m: float = Field(description="Water depth in meters at the spot.")
    fishing_scene: str = Field(
        description="Structured scene tag, e.g. river|lake|reservoir|pond.",
    )
    target_species: FishSniperStrategyTargetSpeciesLiteral = Field(
        description="Target black bass species for lure and retrieve guidance.",
    )

    manual_weather: ManualWeatherPayload | None = Field(
        default=None,
        description=(
            "When provided, the strategy pipeline uses these values directly and skips "
            "OpenWeatherMap. Otherwise OWM is queried using `region`."
        ),
    )

    llm_model_id: str | None = Field(
        default=None,
        description=(
            "Logical text-generation model id from the catalog (see GET /agent/models). "
            "Omitted values use the catalog default_model_id."
        ),
    )

    @field_validator("llm_model_id", mode="before")
    @classmethod
    def normalize_llm_model_id(cls, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return value  # type: ignore[return-value]

    @model_validator(mode="after")
    def validate_non_empty_location_region_and_scene(self) -> GenerateBassStrategyRequestBody:
        if not self.region.strip():
            raise ValueError("region must not be empty")
        if not self.fishing_location.strip():
            raise ValueError("fishing_location must not be empty")
        if not self.fishing_scene.strip():
            raise ValueError("fishing_scene must not be empty")
        return self


# =============================================================================
# Layer 2 — LLM structured output (LangGraph Step 5 validation)
# =============================================================================

BassStrategyRecommendationTacticalRoleLiteral = Literal[
    "locator_bait",
    "follow_up_bait",
    "finesse_cleanup",
]

_EXPECTED_RECOMMENDATION_TACTICAL_ROLES: tuple[
    BassStrategyRecommendationTacticalRoleLiteral,
    ...,
] = (
    "locator_bait",
    "follow_up_bait",
    "finesse_cleanup",
)

FISH_STATE_MAX_LENGTH = 320


def _validate_holding_zone_weights(holding_zones: list[HoldingZoneItem]) -> None:
    if sum(zone.weight_pct for zone in holding_zones) != 100:
        raise ValueError("holding_zones weight_pct must sum to 100")


def _validate_recommendation_tactical_role_sequence(
    recommendations: list[BassStrategyRecommendationItem],
) -> None:
    for index, (recommendation, expected_role) in enumerate(
        zip(recommendations, _EXPECTED_RECOMMENDATION_TACTICAL_ROLES, strict=True),
    ):
        if recommendation.tactical_role != expected_role:
            raise ValueError(
                f"recommendations[{index}].tactical_role must be {expected_role!r}, "
                f"got {recommendation.tactical_role!r}",
            )


class TodaysPatternPayload(BaseModel):
    """Hero pattern headline for the tactical report (Today's Pattern)."""

    headline: str = Field(description="Primary pattern label, e.g. Post-Spawn Largemouth.")
    subline: str = Field(
        description="Supporting pattern context, e.g. Shallow Flats + Windblown Banks.",
    )

    @field_validator("headline", "subline", mode="before")
    @classmethod
    def strip_outer_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("headline", "subline")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("todays_pattern headline and subline must be non-empty strings.")
        return value


class HoldingZoneItem(BaseModel):
    """One weighted holding-zone hypothesis for Likely Holding Zone."""

    label: str = Field(description="Short zone description for the report UI.")
    weight_pct: int = Field(
        ge=1,
        le=100,
        description="Relative weight for this zone; all three zones must sum to 100.",
    )

    @field_validator("label", mode="before")
    @classmethod
    def strip_outer_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("label")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("holding_zones label must be a non-empty string.")
        return value


class BassStrategyRecommendationItem(BaseModel):
    """One lure in the day's tactical combo chain (not ranked by quality)."""

    tactical_role: BassStrategyRecommendationTacticalRoleLiteral = Field(
        description=(
            "Combo phase: locator_bait (search/find fish), follow_up_bait (induce bite), "
            "or finesse_cleanup (pressured or lethargic fish)."
        ),
    )
    lure_type: str = Field(description="Recommended lure category for this slot.")
    lure_color: str = Field(description="Recommended color or pattern.")
    reason: str = Field(description="Why this lure fits today's pattern and conditions.")
    retrieve_technique: str = Field(
        description="How to work the lure (cadence, speed, pauses) for this option.",
    )

    @field_validator(
        "lure_type",
        "lure_color",
        "reason",
        "retrieve_technique",
        mode="before",
    )
    @classmethod
    def strip_outer_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("lure_type", "lure_color", "reason", "retrieve_technique")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Recommendation fields must be non-empty strings.")
        return value


class BassStrategyStructuredLlmOutputBody(BaseModel):
    """Shape of the single LLM JSON object parsed after Step 4 generation."""

    todays_pattern: TodaysPatternPayload = Field(
        description="Structured Today's Pattern hero for the tactical report.",
    )
    confidence_pct: int = Field(
        ge=0,
        le=100,
        description="Numeric confidence 0–100; complements confidence_note.",
    )
    confidence_note: str = Field(
        description="Rationale; no-log branch cites general best practices.",
    )
    holding_zones: Annotated[
        list[HoldingZoneItem],
        Field(
            min_length=3,
            max_length=3,
            description="Exactly three weighted holding-zone hypotheses.",
        ),
    ]
    fish_state: str = Field(
        max_length=FISH_STATE_MAX_LENGTH,
        description="Exactly two short sentences on likely bass behavior today.",
    )
    recommendations: Annotated[
        list[BassStrategyRecommendationItem],
        Field(
            min_length=3,
            max_length=3,
            description="Exactly three combo-chain lure options (locator through finesse cleanup).",
        ),
    ]

    @field_validator("fish_state", "confidence_note", mode="before")
    @classmethod
    def strip_outer_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("fish_state", "confidence_note")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("fish_state and confidence_note must be non-empty strings.")
        return value

    @model_validator(mode="after")
    def validate_holding_zone_weights_and_recommendation_tactical_roles(
        self,
    ) -> BassStrategyStructuredLlmOutputBody:
        _validate_holding_zone_weights(self.holding_zones)
        _validate_recommendation_tactical_role_sequence(self.recommendations)
        return self


# =============================================================================
# Layer 3 — HTTP response parts (pipeline enrichment, not from LLM JSON)
# =============================================================================


class WeatherSnapshotPayload(BaseModel):
    """Weather fields echoed on success (from OWM fetch or manual_weather on the request)."""

    temperature_c: float = Field(description="Temperature in degrees Celsius.")
    pressure_hpa: int = Field(description="Pressure in hectopascals.")
    wind_speed_ms: float = Field(description="Wind speed in meters per second.")
    condition_code: str = Field(description="Normalized FishSniper condition_code value.")


class ReferencedLogPayload(BaseModel):
    """Summary of the personal fishing log used for RAG personalization."""

    log_id: UUID = Field(description="Referenced fishing log id.")
    log_date: date = Field(description="Date of the referenced trip (ISO calendar date).")
    fishing_location: str = Field(description="Location label from the referenced log.")
    lure_type: str = Field(description="Lure category from the referenced log.")
    lure_color: str = Field(description="Lure color from the referenced log.")
    retrieve_speed: str = Field(description="Retrieve style from the referenced log.")
    caught_count: int = Field(description="Fish caught on the referenced trip.")


# =============================================================================
# Layer 4 — HTTP response envelopes (POST /agent/strategy)
# =============================================================================


class GenerateBassStrategySuccessResponseBody(BaseModel):
    """Successful strategy response returned to the client."""

    todays_pattern: TodaysPatternPayload = Field(
        description="Structured Today's Pattern hero for the tactical report.",
    )
    confidence_pct: int = Field(
        ge=0,
        le=100,
        description="Numeric confidence 0–100; complements confidence_note.",
    )
    confidence_note: str = Field(description="Short rationale; P2 uses a no-log general note.")
    holding_zones: Annotated[
        list[HoldingZoneItem],
        Field(
            min_length=3,
            max_length=3,
            description="Exactly three weighted holding-zone hypotheses.",
        ),
    ]
    fish_state: str = Field(
        max_length=FISH_STATE_MAX_LENGTH,
        description="Exactly two short sentences on likely bass behavior today.",
    )
    recommendations: Annotated[
        list[BassStrategyRecommendationItem],
        Field(
            min_length=3,
            max_length=3,
            description="Three combo-chain lure recommendations with tactical_role, reason, and retrieve guidance.",
        ),
    ]
    weather_snapshot: WeatherSnapshotPayload = Field(
        description="Weather used for generation (live or manual).",
    )
    rag_logs_used: int = Field(
        description="0 when no personal log was used; 1 when referenced_log is populated.",
    )
    referenced_log: ReferencedLogPayload | None = Field(
        default=None,
        description="Past fishing log used for personalization; null when RAG degraded or empty.",
    )
    generated_at: datetime = Field(description="UTC timestamp when the response was finalized.")
    fallback: Literal[False] = Field(default=False, description="Always false for this shape.")

    @field_validator("fish_state", "confidence_note", mode="before")
    @classmethod
    def strip_outer_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("fish_state", "confidence_note")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("fish_state and confidence_note must be non-empty strings.")
        return value

    @model_validator(mode="after")
    def validate_holding_zone_weights_and_recommendation_tactical_roles(
        self,
    ) -> GenerateBassStrategySuccessResponseBody:
        _validate_holding_zone_weights(self.holding_zones)
        _validate_recommendation_tactical_role_sequence(self.recommendations)
        return self


class GenerateBassStrategyFallbackResponseBody(BaseModel):
    """Degraded response when LLM JSON validation exhausts retries."""

    fallback: Literal[True] = Field(default=True, description="Signals degraded output.")
    message: str = Field(description="User-facing guidance to adjust inputs and retry.")
    generated_at: datetime = Field(description="UTC timestamp when the fallback was returned.")


# =============================================================================
# Layer 5 — HTTP response (GET /agent/models)
# =============================================================================


class ListedAgentLlmModelItem(BaseModel):
    """One allowlisted text-generation model exposed to the strategy UI."""

    id: str = Field(description="Logical catalog model id (POST /agent/strategy llm_model_id).")
    display_name: str = Field(description="User-facing label for model pickers.")
    provider: Literal["gemini", "openai"] = Field(description="LLM vendor for this catalog entry.")


class ListAgentLlmModelsResponseBody(BaseModel):
    """Model catalog for the strategy form (only entries with configured API keys)."""

    models: list[ListedAgentLlmModelItem] = Field(
        description="Models whose API keys are set; empty when no provider is configured.",
    )
    default_model_id: str = Field(
        description="Catalog default when POST /agent/strategy omits llm_model_id.",
    )
