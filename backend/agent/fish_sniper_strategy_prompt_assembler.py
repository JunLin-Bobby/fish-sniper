"""Assemble bass strategy prompts from versioned external templates (P4 Part 2)."""

from __future__ import annotations

from agent.prompts.registry import (
    DEFAULT_STRATEGY_PROMPT_VERSION,
    format_strategy_prompt_template,
)
from persistence.port import FishSniperFishingLogRow

# =============================================================================
# Internal helpers — prompt 版本解析、user prompt 共用 template 變數
# =============================================================================


def _resolve_strategy_prompt_version(*, prompt_version: str | None) -> str:
    """回傳明確指定的 prompt 版本，否則使用 production 預設版本。"""

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
    """組裝 user prompt 模板所需的環境與釣況欄位字典。"""

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


# =============================================================================
# Public builders — 依 RAG 分支組裝 system / user prompt 文字
# =============================================================================


def build_general_system_prompt(
    *,
    target_species: str,
    prompt_version: str | None = None,
) -> str:
    """無個人日誌時：載入 general_system 模板，產生通用最佳實踐 system prompt。"""

    version = _resolve_strategy_prompt_version(prompt_version=prompt_version)
    return format_strategy_prompt_template(
        prompt_version=version,
        template_name="general_system",
        template_variables={"target_species": target_species},
    )


def build_personalized_system_prompt(
    *,
    target_species: str,
    reference_log: FishSniperFishingLogRow,
    prompt_version: str | None = None,
) -> str:
    """有 RAG 參考日誌時：載入 personalized_system 模板，注入參考釣行紀錄欄位。"""

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


def build_user_prompt(
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
    """組裝 user prompt：帶入即時環境 JSON 指令，依 personalized 切換模板分支。"""

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
