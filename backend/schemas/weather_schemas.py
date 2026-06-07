"""Pydantic models for GET /weather/current."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CurrentWeatherResponseBody(BaseModel):
    """OpenAPI body for live weather used by the Strategy page and agent Step 1."""

    temperature_c: float = Field(description="Air temperature in degrees Celsius (metric).")
    condition: str = Field(description="Human-readable weather description from the provider.")
    condition_code: str = Field(
        description="Normalized FishSniper weather bucket: sunny|cloudy|rainy|stormy|snowy.",
    )
    wind_speed_ms: float = Field(description="Wind speed in meters per second.")
    pressure_hpa: int = Field(description="Sea-level air pressure in hectopascals.")
    humidity_pct: int = Field(description="Relative humidity percentage (0–100).")
    fetched_at: datetime = Field(description="UTC timestamp when this snapshot was produced.")
