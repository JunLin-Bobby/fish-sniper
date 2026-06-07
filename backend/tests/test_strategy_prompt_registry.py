"""Tests for versioned external strategy prompt templates."""

from __future__ import annotations

import pytest

from agent.fish_sniper_strategy_prompt_assembler import build_general_system_prompt
from agent.prompts.registry import (
    DEFAULT_STRATEGY_PROMPT_VERSION,
    format_strategy_prompt_template,
    list_registered_strategy_prompt_versions,
    load_strategy_prompt_template_text,
)


def test_default_strategy_prompt_version_is_registered() -> None:
    assert DEFAULT_STRATEGY_PROMPT_VERSION in list_registered_strategy_prompt_versions()


def test_load_v1_general_system_template_contains_target_species_placeholder() -> None:
    raw = load_strategy_prompt_template_text(
        prompt_version="v1_production",
        template_name="general_system",
    )
    assert "{target_species}" in raw


def test_unknown_prompt_version_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown strategy prompt version"):
        format_strategy_prompt_template(
            prompt_version="does_not_exist",
            template_name="general_system",
            template_variables={"target_species": "Largemouth Bass"},
        )


def test_assembler_uses_v1_production_by_default() -> None:
    text = build_general_system_prompt(
        target_species="Largemouth Bass",
    )
    assert "no past records" in text
    assert "Largemouth Bass" in text
