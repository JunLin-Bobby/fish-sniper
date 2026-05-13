"""Pydantic models for POST /agent/strategy."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

FishSniperStrategyTargetSpeciesLiteral = Literal["Largemouth Bass", "Smallmouth Bass"]


class ManualWeatherPayload(BaseModel):
    """Optional manual weather used when OpenWeatherMap returns 503."""

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
        description="Optional manual weather snapshot when automatic weather is unavailable.",
    )

    @model_validator(mode="after")
    def validate_non_empty_location_region_and_scene(self) -> GenerateBassStrategyRequestBody:
        if not self.region.strip():
            raise ValueError("region must not be empty")
        if not self.fishing_location.strip():
            raise ValueError("fishing_location must not be empty")
        if not self.fishing_scene.strip():
            raise ValueError("fishing_scene must not be empty")
        return self


class WeatherSnapshotPayload(BaseModel):
    """Weather fields echoed back with a successful strategy response."""

    temperature_c: float = Field(description="Temperature in degrees Celsius.")
    pressure_hpa: int = Field(description="Pressure in hectopascals.")
    wind_speed_ms: float = Field(description="Wind speed in meters per second.")
    condition_code: str = Field(description="Normalized FishSniper condition_code value.")


class BassStrategyRecommendationItem(BaseModel):
    """One ranked lure option from the structured LLM output."""

    lure_type: str = Field(description="Recommended lure category for this slot.")
    lure_color: str = Field(description="Recommended color or pattern.")
    retrieve_technique: str = Field(
        description="How to work the lure (cadence, speed, pauses) for this option.",
    )

    @field_validator("lure_type", "lure_color", "retrieve_technique", mode="before")
    @classmethod
    def strip_outer_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("lure_type", "lure_color", "retrieve_technique")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Recommendation fields must be non-empty strings.")
        return value


class BassStrategyStructuredLlmOutputBody(BaseModel):
    """Shape of the single Gemini JSON object (Steps 5–6 validation)."""

    fish_state: str = Field(
        description="Short paragraph on how the target bass are likely behaving today.",
    )
    confidence_note: str = Field(
        description="Rationale; no-log branch cites general best practices.",
    )
    recommendations: Annotated[
        list[BassStrategyRecommendationItem],
        Field(
            min_length=3,
            max_length=3,
            description="Exactly three ranked lure options (primary through tertiary).",
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


class ReferencedLogPayload(BaseModel):
    """Summary of the fishing log that informed the strategy (P4 Part 2 RAG)."""

    log_id: UUID = Field(description="Referenced fishing log id.")
    log_date: date = Field(description="Date of the referenced trip (ISO calendar date).")
    fishing_location: str = Field(description="Location label from the referenced log.")
    lure_type: str = Field(description="Lure category from the referenced log.")
    lure_color: str = Field(description="Lure color from the referenced log.")
    retrieve_speed: str = Field(description="Retrieve style from the referenced log.")
    caught_count: int = Field(description="Fish caught on the referenced trip.")


class GenerateBassStrategySuccessResponseBody(BaseModel):
    """Successful structured strategy: fish state, three lure rows, and weather echo."""

    fish_state: str = Field(description="Likely bass behavior / mood for today's conditions.")
    recommendations: Annotated[
        list[BassStrategyRecommendationItem],
        Field(
            min_length=3,
            max_length=3,
            description="Three ranked lure recommendations with retrieve guidance.",
        ),
    ]
    confidence_note: str = Field(description="Short rationale; P2 uses a no-log general note.")
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


class GenerateBassStrategyFallbackResponseBody(BaseModel):
    """LLM JSON could not be validated after retries."""

    fallback: Literal[True] = Field(default=True, description="Signals degraded output.")
    message: str = Field(description="User-facing guidance to adjust inputs and retry.")
    generated_at: datetime = Field(description="UTC timestamp when the fallback was returned.")
