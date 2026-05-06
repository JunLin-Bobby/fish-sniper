"""Normalize user preference region labels for weather cache keys and OWM queries."""


def normalize_region_display_name_for_open_weather_map_query(*, region_display_name: str) -> str:
    """Collapse whitespace; preserve case for OWM city search (`q=` can be case-sensitive)."""

    collapsed_whitespace = " ".join(region_display_name.strip().split())
    return collapsed_whitespace


def normalize_region_display_name_for_weather_cache_key(*, region_display_name: str) -> str:
    """Case-insensitive cache key so 'Boston' and 'boston' share one entry."""

    return normalize_region_display_name_for_open_weather_map_query(
        region_display_name=region_display_name,
    ).casefold()
