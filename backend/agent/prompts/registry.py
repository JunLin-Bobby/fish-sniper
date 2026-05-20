"""Load and format versioned strategy prompt templates from ``agent/prompts/<version>/``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPTS_ROOT = Path(__file__).resolve().parent

DEFAULT_STRATEGY_PROMPT_VERSION = "v1_production"

_REGISTERED_STRATEGY_PROMPT_VERSIONS: dict[str, Path] = {
    DEFAULT_STRATEGY_PROMPT_VERSION: _PROMPTS_ROOT / DEFAULT_STRATEGY_PROMPT_VERSION,
    "v2_production": _PROMPTS_ROOT / "v2_production",
}


def list_registered_strategy_prompt_versions() -> tuple[str, ...]:
    """Return known prompt bundle ids (newest experiments add folders + registry entries)."""

    return tuple(_REGISTERED_STRATEGY_PROMPT_VERSIONS.keys())


def _resolve_strategy_prompt_version_directory(*, prompt_version: str) -> Path:
    version_directory = _REGISTERED_STRATEGY_PROMPT_VERSIONS.get(prompt_version)
    if version_directory is None:
        known = ", ".join(sorted(_REGISTERED_STRATEGY_PROMPT_VERSIONS))
        raise ValueError(
            f"Unknown strategy prompt version {prompt_version!r}; known versions: {known}"
        )
    return version_directory


@lru_cache(maxsize=32)
def load_strategy_prompt_template_text(*, prompt_version: str, template_name: str) -> str:
    """Read a ``.txt`` template from ``agent/prompts/<prompt_version>/<template_name>.txt``."""

    version_directory = _resolve_strategy_prompt_version_directory(prompt_version=prompt_version)
    template_path = version_directory / f"{template_name}.txt"
    if not template_path.is_file():
        raise FileNotFoundError(
            f"Strategy prompt template not found: {template_path} "
            f"(version={prompt_version!r}, template_name={template_name!r})"
        )
    return template_path.read_text(encoding="utf-8")


def format_strategy_prompt_template(
    *,
    prompt_version: str,
    template_name: str,
    template_variables: dict[str, object],
) -> str:
    """Load and ``str.format`` a template with the given variables."""

    template_text = load_strategy_prompt_template_text(
        prompt_version=prompt_version,
        template_name=template_name,
    )
    return template_text.format(**template_variables)
