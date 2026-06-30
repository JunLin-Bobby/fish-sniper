"""OpenWeatherMap 2.5 current weather client."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from settings import AppSettings
from weather.port import FishSniperOpenWeatherSnapshot
from weather.region_normalization import normalize_region_display_name_for_open_weather_map_query
from weather.weather_errors import FishSniperWeatherUnavailableError

logger = logging.getLogger(__name__)


def map_open_weather_map_condition_id_to_fish_sniper_condition_code(*, weather_id: int) -> str:
    """Map OWM `weather[].id` to FishSniper `condition_code` (fishwise_prompt_guide §3)."""

    if weather_id == 800:
        return "sunny"
    if 801 <= weather_id <= 804:
        return "cloudy"
    if 500 <= weather_id <= 531:
        return "rainy"
    if 200 <= weather_id <= 232:
        return "stormy"
    if 600 <= weather_id <= 622:
        return "snowy"
    return "cloudy"


def _parse_open_weather_map_current_payload_or_raise(
    *,
    payload: dict[str, Any],
    reference_time_utc: datetime,
) -> FishSniperOpenWeatherSnapshot:
    weather_array = payload.get("weather")
    if not isinstance(weather_array, list) or not weather_array:
        raise FishSniperWeatherUnavailableError("OpenWeatherMap response missing weather[]")
    first_weather = weather_array[0]
    if not isinstance(first_weather, dict):
        raise FishSniperWeatherUnavailableError("OpenWeatherMap weather[0] has invalid shape")
    weather_id_raw = first_weather.get("id")
    if not isinstance(weather_id_raw, int):
        raise FishSniperWeatherUnavailableError("OpenWeatherMap weather id is not an int")
    condition_label = str(
        first_weather.get("description") or first_weather.get("main") or "unknown"
    )

    main_section = payload.get("main")
    if not isinstance(main_section, dict):
        raise FishSniperWeatherUnavailableError("OpenWeatherMap response missing main")
    temperature_raw = main_section.get("temp")
    pressure_raw = main_section.get("pressure")
    humidity_raw = main_section.get("humidity")
    if not isinstance(temperature_raw, (int, float)):
        raise FishSniperWeatherUnavailableError("OpenWeatherMap main.temp missing")
    if not isinstance(pressure_raw, (int, float)):
        raise FishSniperWeatherUnavailableError("OpenWeatherMap main.pressure missing")
    if not isinstance(humidity_raw, (int, float)):
        raise FishSniperWeatherUnavailableError("OpenWeatherMap main.humidity missing")

    wind_section = payload.get("wind") or {}
    wind_speed_raw = wind_section.get("speed") if isinstance(wind_section, dict) else None
    if not isinstance(wind_speed_raw, (int, float)):
        wind_speed_raw = 0.0

    condition_code = map_open_weather_map_condition_id_to_fish_sniper_condition_code(
        weather_id=weather_id_raw,
    )
    return FishSniperOpenWeatherSnapshot(
        temperature_celsius=float(temperature_raw),
        condition_label=condition_label,
        condition_code=condition_code,
        wind_speed_meters_per_second=float(wind_speed_raw),
        pressure_hectopascals=int(pressure_raw),
        humidity_percent=int(humidity_raw),
        fetched_at_utc=reference_time_utc.astimezone(UTC),
    )


def fetch_current_weather_snapshot_from_open_weather_map_or_raise_for_unavailable(
    *,
    region_display_name: str,
    fish_sniper_backend_settings: AppSettings,
    reference_time_utc: datetime,
) -> FishSniperOpenWeatherSnapshot:
    """Fetch OWM current weather; raise FishSniperWeatherUnavailableError on failure."""

    api_key = fish_sniper_backend_settings.openweathermap_api_key
    if not api_key:
        raise FishSniperWeatherUnavailableError("OpenWeatherMap API key is not configured")

    query_city = normalize_region_display_name_for_open_weather_map_query(
        region_display_name=region_display_name,
    )
    request_url = "https://api.openweathermap.org/data/2.5/weather"
    request_params = {"q": query_city, "units": "metric", "appid": api_key}

    try:
        response = httpx.get(request_url, params=request_params, timeout=15.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("OpenWeatherMap request failed")
        raise FishSniperWeatherUnavailableError("OpenWeatherMap request failed") from exc

    try:
        payload: dict[str, Any] = response.json()
        return _parse_open_weather_map_current_payload_or_raise(
            payload=payload,
            reference_time_utc=reference_time_utc,
        )
    except FishSniperWeatherUnavailableError:
        raise
    except Exception as exc:
        logger.exception("Failed to parse OpenWeatherMap JSON payload")
        raise FishSniperWeatherUnavailableError(
            "OpenWeatherMap response could not be parsed"
        ) from exc


async def afetch_current_weather_snapshot_from_open_weather_map_or_raise_for_unavailable(
    *,
    region_display_name: str,
    fish_sniper_backend_settings: AppSettings,
    reference_time_utc: datetime,
) -> FishSniperOpenWeatherSnapshot:
    """Async OWM current weather fetch via ``httpx.AsyncClient``."""

    api_key = fish_sniper_backend_settings.openweathermap_api_key
    if not api_key:
        raise FishSniperWeatherUnavailableError("OpenWeatherMap API key is not configured")

    query_city = normalize_region_display_name_for_open_weather_map_query(
        region_display_name=region_display_name,
    )
    request_url = "https://api.openweathermap.org/data/2.5/weather"
    request_params = {"q": query_city, "units": "metric", "appid": api_key}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(request_url, params=request_params)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("OpenWeatherMap async request failed")
        raise FishSniperWeatherUnavailableError("OpenWeatherMap request failed") from exc

    try:
        payload: dict[str, Any] = response.json()
        return _parse_open_weather_map_current_payload_or_raise(
            payload=payload,
            reference_time_utc=reference_time_utc,
        )
    except FishSniperWeatherUnavailableError:
        raise
    except Exception as exc:
        logger.exception("Failed to parse OpenWeatherMap JSON payload")
        raise FishSniperWeatherUnavailableError(
            "OpenWeatherMap response could not be parsed"
        ) from exc
