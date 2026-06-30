"""Extract a JSON object from Gemini outputs that may include markdown fences."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_first_json_object_dict_from_llm_text(*, raw_llm_text: str) -> dict[str, Any]:
    """
    Parse the first top-level JSON object from model text.

    Strips optional ```json fences and ignores prose outside the object.
    """

    text = raw_llm_text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()

    start_index = text.find("{")
    end_index = text.rfind("}")
    if start_index == -1 or end_index == -1 or end_index <= start_index:
        raise ValueError("No JSON object found in model output")

    candidate_json = text[start_index : end_index + 1]
    return json.loads(candidate_json)


def validate_non_empty_string_fields_exist(
    *,
    parsed_json_object: dict[str, Any],
    required_field_name_list: list[str],
) -> None:
    """Ensure each required key maps to a non-empty string."""

    for field_name in required_field_name_list:
        value = parsed_json_object.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing or empty string field: {field_name}")
