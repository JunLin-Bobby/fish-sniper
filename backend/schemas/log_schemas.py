"""Pydantic models for fishing logs (P3)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from schemas.agent_schemas import FishSniperStrategyTargetSpeciesLiteral

FishSniperConditionCode = Literal["sunny", "cloudy", "rainy", "stormy", "snowy"]

FishSniperEmbeddingStatusLiteral = Literal["pending", "done", "failed"]


class CreateOrUpdateFishingLogRequestBody(BaseModel):
    """Request body for `POST /logs` and `PATCH /logs/{log_id}` (full replace)."""

    date: date
    fishing_location: str = Field(min_length=1)
    fishing_scene: str = Field(min_length=1)
    target_species: FishSniperStrategyTargetSpeciesLiteral = Field(
        description="Target bass species recorded for this log (Largemouth or Smallmouth).",
    )
    water_depth_m: float = Field(ge=0)
    lure_type: str = Field(min_length=1)
    lure_color: str = Field(min_length=1)
    retrieve_speed: str = Field(min_length=1)
    caught_count: int = Field(ge=0)
    weight_lb: float | None = Field(
        default=None,
        description="Catch weight in pounds (lb), optional.",
    )
    length_cm: float | None = None
    temperature_c: float
    wind_speed_ms: float
    pressure_hpa: int
    condition_code: FishSniperConditionCode
    notes: str


class CreateFishingLogResponseBody(BaseModel):
    """Response for `POST /logs`."""

    log_id: UUID


class FishingLogResponseBody(BaseModel):
    """Single log returned by list/detail/patch."""

    log_id: UUID
    date: date
    fishing_location: str
    fishing_scene: str
    target_species: FishSniperStrategyTargetSpeciesLiteral = Field(
        description="Target bass species for this log (Largemouth or Smallmouth).",
    )
    water_depth_m: float
    lure_type: str
    lure_color: str
    retrieve_speed: str
    caught_count: int
    weight_lb: float | None = Field(description="Catch weight in pounds (lb), optional.")
    length_cm: float | None
    temperature_c: float
    wind_speed_ms: float
    pressure_hpa: int
    condition_code: str
    notes: str
    embedding_status: FishSniperEmbeddingStatusLiteral = Field(
        description=(
            "Vector readiness flag: `pending` when the OpenAI embedding call has not "
            "yet succeeded for this row, `done` when the row's vector is current and "
            "queryable, `failed` when the background worker has given up."
        ),
    )
    embedding_text_version: int = Field(
        description=(
            "Schema version of the natural-language template used to produce this "
            "row's vector. Future template changes will bump this number and require "
            "backfill before similarity search filters by version."
        ),
    )
    created_at: datetime
    updated_at: datetime
