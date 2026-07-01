"""Versioned external prompt templates for the bass strategy agent."""

from strategy.prompts.registry import (
    DEFAULT_STRATEGY_PROMPT_VERSION,
    list_registered_strategy_prompt_versions,
    load_strategy_prompt_template_text,
)

__all__ = [
    "DEFAULT_STRATEGY_PROMPT_VERSION",
    "list_registered_strategy_prompt_versions",
    "load_strategy_prompt_template_text",
]
