"""Prompt strings for the general (no personal log) branch and battle plan pass."""


def build_general_best_practice_system_prompt_for_bass_strategy() -> str:
    return (
        "You are an expert Bass lure fishing coach specializing in lure selection and "
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
) -> str:
    return (
        "Environmental conditions:\n"
        f"- Weather region (from profile): {region}\n"
        f"- Fishing spot (today): {fishing_location}\n"
        f"- Fishing scene: {fishing_scene}\n"
        f"- Water depth: {water_depth_m}m\n"
        f"- Temperature: {temperature_c}°C\n"
        f"- Pressure: {pressure_hpa} hPa\n"
        f"- Wind speed: {wind_speed_ms} m/s\n"
        f"- Weather: {condition_code}\n"
        "- Target species: Bass\n\n"
        "Respond ONLY with a valid JSON object containing exactly these fields:\n"
        "{\n"
        '  "lure_type": "...",\n'
        '  "lure_color": "...",\n'
        '  "retrieve_speed": "...",\n'
        '  "target_zone": "...",\n'
        '  "time_window": "...",\n'
        '  "confidence_note": "..."\n'
        "}\n"
        "Do not include any explanation outside the JSON.\n"
        "For confidence_note when no personal logs exist, write one concise English sentence "
        "explaining that the plan is based on general best practices for the listed conditions "
        "(no past trips on file)."
    )


def build_battle_plan_system_prompt_for_markdown_summary(
    *,
    fishing_location: str,
    temperature_c: float,
    condition_code: str,
    wind_speed_ms: float,
    fishing_scene: str,
    water_depth_m: float,
    lure_type: str,
    lure_color: str,
    retrieve_speed: str,
    target_zone: str,
    time_window: str,
) -> str:
    return (
        "You are an expert Bass fishing coach writing a shore fishing battle plan.\n"
        "Write in the style of an experienced angler briefing a student before a session —\n"
        "confident, specific, and educational. "
        "Use markdown formatting with clear section headers.\n\n"
        "The angler's conditions today:\n"
        f"- Fishing spot: {fishing_location}\n"
        f"- Temperature: {temperature_c}°C\n"
        f"- Weather: {condition_code}\n"
        f"- Wind: {wind_speed_ms} m/s\n"
        f"- Fishing scene: {fishing_scene}\n"
        f"- Water depth: {water_depth_m}m\n\n"
        "The AI has already determined the optimal strategy:\n"
        f"- Lure: {lure_type} in {lure_color}\n"
        f"- Retrieve: {retrieve_speed}\n"
        f"- Target zone: {target_zone}\n"
        f"- Best time window: {time_window}\n\n"
        "Write a structured battle plan with EXACTLY these four sections:\n"
        "1. Fish condition & behavior (1 paragraph, explain WHY bass behave this way today)\n"
        "2. Target terrain features (3 numbered points, each with terrain name and reason)\n"
        "3. Recommended depth (split by morning vs afternoon)\n"
        "4. Lure selection & technique (focus on the recommended lure, explain how to work it\n"
        "   in these conditions. Add one alternative if appropriate)\n\n"
        "Language: English\n"
        "Tone: Like a knowledgeable fishing buddy — direct, practical, enthusiastic\n"
        "Do NOT use emoji anywhere in the response."
    )
