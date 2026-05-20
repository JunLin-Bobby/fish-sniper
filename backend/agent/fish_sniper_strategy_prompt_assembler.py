"""Assemble bass strategy prompts from versioned external templates (P4 Part 2)."""

from __future__ import annotations

from agent.prompts.registry import (
    DEFAULT_STRATEGY_PROMPT_VERSION,
    format_strategy_prompt_template,
)
from persistence.port import FishSniperFishingLogRow


def _resolve_strategy_prompt_version(*, prompt_version: str | None) -> str:
    return prompt_version or DEFAULT_STRATEGY_PROMPT_VERSION


def _shared_user_prompt_template_variables(
    *,
    region: str,
    fishing_location: str,
    fishing_scene: str,
    water_depth_m: float,
    temperature_c: float,
    pressure_hpa: int,
    wind_speed_ms: float,
    condition_code: str,
    target_species: str,
) -> dict[str, object]:
    return {
        "region": region,
        "fishing_location": fishing_location,
        "fishing_scene": fishing_scene,
        "water_depth_m": water_depth_m,
        "temperature_c": temperature_c,
        "pressure_hpa": pressure_hpa,
        "wind_speed_ms": wind_speed_ms,
        "condition_code": condition_code,
        "target_species": target_species,
    }


def assembler_build_general_best_practice_system_prompt_for_bass_strategy(
    *,
    target_species: str,
    prompt_version: str | None = None,
) -> str:
    version = _resolve_strategy_prompt_version(prompt_version=prompt_version)
    return format_strategy_prompt_template(
        prompt_version=version,
        template_name="general_system",
        template_variables={"target_species": target_species},
    )


def assembler_build_personalized_system_prompt_with_reference_log_for_bass_strategy(
    *,
    target_species: str,
    reference_log: FishSniperFishingLogRow,
    prompt_version: str | None = None,
) -> str:
    version = _resolve_strategy_prompt_version(prompt_version=prompt_version)
    return format_strategy_prompt_template(
        prompt_version=version,
        template_name="personalized_system",
        template_variables={
            "target_species": target_species,
            "reference_log_date": reference_log.log_date.isoformat(),
            "reference_log_location": reference_log.fishing_location,
            "reference_log_scene": reference_log.fishing_scene,
            "reference_log_depth_m": reference_log.water_depth_m,
            "reference_log_temperature_c": reference_log.temperature_c,
            "reference_log_condition_code": reference_log.condition_code,
            "reference_log_wind_speed_ms": reference_log.wind_speed_ms,
            "reference_log_pressure_hpa": reference_log.pressure_hpa,
            "reference_log_lure_type": reference_log.lure_type,
            "reference_log_lure_color": reference_log.lure_color,
            "reference_log_retrieve_speed": reference_log.retrieve_speed,
            "reference_log_caught_count": reference_log.caught_count,
            "reference_log_notes": reference_log.notes,
        },
    )


def assembler_build_shared_user_prompt_for_environmental_json_strategy(
    *,
    region: str,
    fishing_location: str,
    fishing_scene: str,
    water_depth_m: float,
    temperature_c: float,
    pressure_hpa: int,
    wind_speed_ms: float,
    condition_code: str,
    target_species: str,
    personalized: bool = False,
    prompt_version: str | None = None,
) -> str:
    version = _resolve_strategy_prompt_version(prompt_version=prompt_version)
    template_name = (
        "user_environmental_json_personalized"
        if personalized
        else "user_environmental_json_general"
    )
    return format_strategy_prompt_template(
        prompt_version=version,
        template_name=template_name,
        template_variables=_shared_user_prompt_template_variables(
            region=region,
            fishing_location=fishing_location,
            fishing_scene=fishing_scene,
            water_depth_m=water_depth_m,
            temperature_c=temperature_c,
            pressure_hpa=pressure_hpa,
            wind_speed_ms=wind_speed_ms,
            condition_code=condition_code,
            target_species=target_species,
        ),
    )
