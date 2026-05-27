"""Domain types for the text-generation LLM subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

LlmProviderName = Literal["gemini", "openai"]

_DEFAULT_GENERATION_TIMEOUT_SECONDS = 120.0


class UnknownModelError(ValueError):
    """Raised when ``llm_model_id`` is not present in the model catalog."""


class RegistryConfigurationError(RuntimeError):
    """Raised when ``llm_models.yaml`` is missing, invalid, or internally inconsistent."""


class ModelConfig(BaseModel):
    """Resolved configuration for one logical model id from ``llm_models.yaml``."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    model_id: str = Field(min_length=1, description="Logical catalog id (yaml mapping key).")
    provider: LlmProviderName = Field(description="LLM vendor adapter to use.")
    provider_model: str = Field(
        min_length=1,
        validation_alias=AliasChoices("model", "provider_model"),
        description="Provider SDK model id.",
    )
    display_name: str = Field(min_length=1, description="User-facing label for model pickers.")
    temperature: float = Field(ge=0.0, le=2.0)
    api_key_env: str = Field(min_length=1, description="Environment variable name for the API key.")
    timeout_seconds: float = Field(
        default=_DEFAULT_GENERATION_TIMEOUT_SECONDS,
        gt=0.0,
        description="Single completion timeout in seconds.",
    )

    @classmethod
    def from_yaml_entry(cls, *, model_id: str, entry: Any) -> ModelConfig:
        """Validate one ``models.<id>`` block and attach ``model_id`` from the yaml key."""

        if not isinstance(entry, dict):
            raise TypeError(f"Model {model_id!r} must be a mapping")
        return cls.model_validate({**entry, "model_id": model_id})


@dataclass(frozen=True, slots=True)
class ListedLlmModel:
    """Public model entry for ``GET /agent/models`` (no secrets)."""

    id: str
    display_name: str
    provider: LlmProviderName


@dataclass(frozen=True, slots=True)
class LlmGenerationResult:
    """Normalized outcome of a single text-generation call (L1 transport layer)."""

    raw_text: str
    provider: LlmProviderName
    model_id: str
    provider_model: str
    temperature: float
