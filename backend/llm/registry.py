"""Load and query the LLM model catalog from ``llm_models.yaml``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from llm.adapters.keys import has_api_key_for_model
from llm.models import (
    ListedLlmModel,
    ModelConfig,
    RegistryConfigurationError,
    UnknownModelError,
)
from settings import FishSniperBackendSettings

# --- Module constants ---------------------------------------------------------

_DEFAULT_LLM_MODELS_CONFIG_PATH = (
    Path(__file__).resolve().parent / "config" / "llm_models.yaml"
)

# --- Public entry points ------------------------------------------------------
# Start here to see what this module exposes for loading the catalog.


def load_registry(
    *,
    yaml_path: Path | None = None,
    config_path_override: str | None = None,
    backend_settings: FishSniperBackendSettings | None = None,
) -> ModelRegistry:
    """Load and validate the LLM model catalog from ``llm_models.yaml``.

    When ``yaml_path`` is omitted, resolves via ``config_path_override``,
    ``backend_settings.llm_models_config_path``, or the package default config file.
    """

    resolved_yaml_path = yaml_path or resolve_config_path(
        config_path_override=config_path_override,
        backend_settings=backend_settings,
    )

    if not resolved_yaml_path.is_file():
        raise RegistryConfigurationError(
            f"LLM models config not found: {resolved_yaml_path}",
        )

    try:
        raw_yaml_document = yaml.safe_load(
            resolved_yaml_path.read_text(encoding="utf-8"),
        )
    except yaml.YAMLError as exc:
        raise RegistryConfigurationError(
            f"LLM models config YAML parse failed: {resolved_yaml_path}",
        ) from exc

    return _build_registry(
        parsed_yaml_document=raw_yaml_document,
        yaml_path=resolved_yaml_path,
    )


# --- Public query type --------------------------------------------------------
# In-memory catalog returned by ``load_registry``.


class ModelRegistry:
    """In-memory catalog of allowlisted text-generation models."""

    def __init__(
        self,
        *,
        default_model_id: str,
        model_config_by_id: dict[str, ModelConfig],
    ) -> None:
        if default_model_id not in model_config_by_id:
            raise RegistryConfigurationError(
                f"default_model_id={default_model_id!r} is not defined under models",
            )
        self._default_model_id = default_model_id
        self._model_config_by_id = dict(model_config_by_id)

    def default_model_id(self) -> str:
        return self._default_model_id

    def has_model(self, model_id: str) -> bool:
        return model_id in self._model_config_by_id

    def get_config(self, model_id: str) -> ModelConfig:
        model_config = self._model_config_by_id.get(model_id)
        if model_config is None:
            raise UnknownModelError(f"Unknown llm_model_id: {model_id!r}")
        return model_config

    def list_available(
        self,
        *,
        backend_settings: FishSniperBackendSettings,
    ) -> list[ListedLlmModel]:
        """Return catalog entries whose API key is configured in settings."""

        listed: list[ListedLlmModel] = []
        for model_id, model_config in self._model_config_by_id.items():
            if not has_api_key_for_model(
                model_config=model_config,
                backend_settings=backend_settings,
            ):
                continue
            listed.append(
                ListedLlmModel(
                    id=model_id,
                    display_name=model_config.display_name,
                    provider=model_config.provider,
                ),
            )
        return listed


# --- Internal: load pipeline --------------------------------------------------
# Call order is top-to-bottom (callers appear above callees).


def _build_registry(
    *,
    parsed_yaml_document: Any,
    yaml_path: Path,
) -> ModelRegistry:
    if not isinstance(parsed_yaml_document, dict):
        raise RegistryConfigurationError(
            f"LLM models config root must be a mapping: {yaml_path}",
        )

    default_model_id = parsed_yaml_document.get("default_model_id")
    if not isinstance(default_model_id, str) or not default_model_id.strip():
        raise RegistryConfigurationError(
            f"default_model_id must be a non-empty string: {yaml_path}",
        )
    default_model_id = default_model_id.strip()

    model_config_by_id = _parse_models(
        raw_models=parsed_yaml_document.get("models"),
        yaml_path=yaml_path,
    )

    return ModelRegistry(
        default_model_id=default_model_id,
        model_config_by_id=model_config_by_id,
    )


def _parse_models(
    *,
    raw_models: Any,
    yaml_path: Path,
) -> dict[str, ModelConfig]:
    if not isinstance(raw_models, dict) or not raw_models:
        raise RegistryConfigurationError(
            f"models must be a non-empty mapping: {yaml_path}",
        )

    model_config_by_id: dict[str, ModelConfig] = {}
    for model_id, raw_entry in raw_models.items():
        if not isinstance(model_id, str) or not model_id.strip():
            raise RegistryConfigurationError(
                f"Model id keys must be non-empty strings: {yaml_path}",
            )
        catalog_model_id = model_id.strip()
        try:
            model_config_by_id[catalog_model_id] = ModelConfig.from_yaml_entry(
                model_id=catalog_model_id,
                entry=raw_entry,
            )
        except (ValidationError, TypeError) as exc:
            if isinstance(exc, ValidationError):
                detail = _format_validation_error(validation_error=exc)
            else:
                detail = str(exc)
            raise RegistryConfigurationError(
                f"LLM models config validation failed for model {catalog_model_id!r} "
                f"({yaml_path}): {detail}",
            ) from exc

    return model_config_by_id


# --- Internal: utilities ------------------------------------------------------
# Shared helpers invoked by the sections above.


def resolve_config_path(
    *,
    config_path_override: str | None = None,
    backend_settings: FishSniperBackendSettings | None = None,
) -> Path:
    """Return the yaml path from override, settings, or the package default."""

    if config_path_override:
        return Path(config_path_override)
    if backend_settings is not None:
        settings_path = (backend_settings.llm_models_config_path or "").strip()
        if settings_path:
            return Path(settings_path)
    return _DEFAULT_LLM_MODELS_CONFIG_PATH


def _format_validation_error(*, validation_error: ValidationError) -> str:
    detail_parts: list[str] = []
    for error in validation_error.errors():
        location = ".".join(str(part) for part in error.get("loc", ()))
        message = error.get("msg", "invalid value")
        if location:
            detail_parts.append(f"{location}: {message}")
        else:
            detail_parts.append(str(message))
    return "; ".join(detail_parts)
