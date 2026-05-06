"""Pydantic models for POST /agent/strategy."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


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

    fishing_location: str = Field(
        description="Free-text fishing spot label used for display and future RAG filters.",
    )
    water_depth_m: float = Field(description="Water depth in meters at the spot.")
    fishing_scene: str = Field(
        description="Structured scene tag, e.g. river|lake|reservoir|pond.",
    )
    target_species: str = Field(description="Target species; FishSniper P2 expects bass.")

    manual_weather: ManualWeatherPayload | None = Field(
        default=None,
        description="Optional manual weather snapshot when automatic weather is unavailable.",
    )

    @model_validator(mode="after")
    def validate_non_empty_location_and_species(self) -> GenerateBassStrategyRequestBody:
        if not self.fishing_location.strip():
            raise ValueError("fishing_location must not be empty")
        if not self.target_species.strip():
            raise ValueError("target_species must not be empty")
        if not self.fishing_scene.strip():
            raise ValueError("fishing_scene must not be empty")
        return self


class WeatherSnapshotPayload(BaseModel):
    """Weather fields echoed back with a successful strategy response."""

    temperature_c: float = Field(description="Temperature in degrees Celsius.")
    pressure_hpa: int = Field(description="Pressure in hectopascals.")
    wind_speed_ms: float = Field(description="Wind speed in meters per second.")
    condition_code: str = Field(description="Normalized FishSniper condition_code value.")


class GenerateBassStrategySuccessResponseBody(BaseModel):
    """Successful structured strategy plus markdown battle plan."""

    lure_type: str = Field(description="Recommended lure category.")
    lure_color: str = Field(description="Recommended lure color pattern.")
    retrieve_speed: str = Field(description="Retrieve cadence guidance.")
    target_zone: str = Field(description="Where to focus casts for this session.")
    time_window: str = Field(description="Preferred time window to fish this pattern.")
    confidence_note: str = Field(description="Short rationale; P2 uses a no-log general note.")
    battle_plan_summary: str = Field(description="Markdown battle plan for the session.")
    weather_snapshot: WeatherSnapshotPayload = Field(
        description="Weather used for generation (live or manual).",
    )
    rag_logs_used: int = Field(
        description="Count of personal logs incorporated; P2 is always 0.",
    )
    generated_at: datetime = Field(description="UTC timestamp when the response was finalized.")
    fallback: Literal[False] = Field(default=False, description="Always false for this shape.")


class GenerateBassStrategyFallbackResponseBody(BaseModel):
    """LLM JSON could not be validated after retries."""

    fallback: Literal[True] = Field(default=True, description="Signals degraded output.")
    message: str = Field(description="User-facing guidance to adjust inputs and retry.")
    generated_at: datetime = Field(description="UTC timestamp when the fallback was returned.")
