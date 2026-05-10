"""Prompt strings for the general (no personal log) single-call structured JSON branch."""


def build_general_best_practice_system_prompt_for_bass_strategy(*, target_species: str) -> str:
    return (
        f"You are an expert {target_species} lure fishing coach specializing in lure selection and "
        "retrieval techniques.\n"
        "The angler has no past records for similar conditions.\n"
        "Provide a general best-practice strategy based on the environmental conditions provided."
    )


def build_shared_user_prompt_for_environmental_json_strategy(
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
) -> str:
    return (
        "Environmental conditions:\n"
        f"- Weather region: {region}\n"
        f"- Fishing spot (today): {fishing_location}\n"
        f"- Fishing scene: {fishing_scene}\n"
        f"- Water depth: {water_depth_m}m\n"
        f"- Temperature: {temperature_c}°C\n"
        f"- Pressure: {pressure_hpa} hPa\n"
        f"- Wind speed: {wind_speed_ms} m/s\n"
        f"- Weather: {condition_code}\n"
        f"- Target species: {target_species}\n\n"
        "Respond ONLY with a valid JSON object containing exactly these fields:\n"
        "{\n"
        '  "fish_state": "2–4 short English sentences on how the bass are likely behaving today '
        "and why, tied to the listed conditions (no markdown, no emoji).\",\n"
        '  "confidence_note": "One concise English sentence; when no personal logs exist, say the '
        "plan is from general best practices for these conditions (no past trips on file).\",\n"
        '  "recommendations": [\n'
        "    {\n"
        '      "lure_type": "Primary lure category",\n'
        '      "lure_color": "Color or pattern",\n'
        '      "retrieve_technique": "Brief retrieve: cadence, speed, pauses (one or two sentences '
        "max).\"\n"
        "    },\n"
        "    { ... second option ... },\n"
        "    { ... third option ... }\n"
        "  ]\n"
        "}\n"
        "The recommendations array MUST contain exactly three objects, ordered best-first "
        "(primary, secondary, tertiary). Each string field must be non-empty.\n"
        "Do not include any explanation outside the JSON."
    )
