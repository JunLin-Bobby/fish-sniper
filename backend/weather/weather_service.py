"""Compose TTL cache + OpenWeatherMap for current conditions."""

from __future__ import annotations

from datetime import datetime

from settings import FishSniperBackendSettings
from weather.in_memory_weather_cache import InMemoryFishSniperWeatherSnapshotCache
from weather.openweather_client import (
    afetch_current_weather_snapshot_from_open_weather_map_or_raise_for_unavailable,
    fetch_current_weather_snapshot_from_open_weather_map_or_raise_for_unavailable,
)
from weather.port import FishSniperOpenWeatherSnapshot, WeatherSnapshotCachePort
from weather.region_normalization import normalize_region_display_name_for_weather_cache_key
from weather.weather_errors import FishSniperWeatherUnavailableError


def fetch_or_refresh_cached_current_weather_snapshot_for_region(
    *,
    profile_region_display_name: str,
    fish_sniper_backend_settings: FishSniperBackendSettings,
    weather_snapshot_cache_port: WeatherSnapshotCachePort,
    reference_time_utc: datetime,
) -> FishSniperOpenWeatherSnapshot:
    """
    Return weather for the user's saved region, using a 30-minute in-process cache when valid.

    When `fish_sniper_backend_settings.weather_fail` is true, behaves like an upstream failure.
    """

    if fish_sniper_backend_settings.weather_fail:
        raise FishSniperWeatherUnavailableError("Weather fetch disabled by WEATHER_FAIL")

    normalized_cache_key = normalize_region_display_name_for_weather_cache_key(
        region_display_name=profile_region_display_name,
    )
    cached_snapshot = weather_snapshot_cache_port.get_valid_cached_snapshot_for_normalized_region(
        normalized_region_display_name=normalized_cache_key,
        reference_time_utc=reference_time_utc,
    )
    if cached_snapshot is not None:
        return cached_snapshot

    fresh_snapshot = fetch_current_weather_snapshot_from_open_weather_map_or_raise_for_unavailable(
        region_display_name=profile_region_display_name,
        fish_sniper_backend_settings=fish_sniper_backend_settings,
        reference_time_utc=reference_time_utc,
    )
    weather_snapshot_cache_port.put_snapshot_for_normalized_region(
        normalized_region_display_name=normalized_cache_key,
        snapshot=fresh_snapshot,
    )
    return fresh_snapshot


async def afetch_or_refresh_cached_current_weather_snapshot_for_region(
    *,
    profile_region_display_name: str,
    fish_sniper_backend_settings: FishSniperBackendSettings,
    weather_snapshot_cache_port: WeatherSnapshotCachePort,
    reference_time_utc: datetime,
) -> FishSniperOpenWeatherSnapshot:
    """Async weather path: same TTL cache semantics as the sync helper."""

    if fish_sniper_backend_settings.weather_fail:
        raise FishSniperWeatherUnavailableError("Weather fetch disabled by WEATHER_FAIL")

    normalized_cache_key = normalize_region_display_name_for_weather_cache_key(
        region_display_name=profile_region_display_name,
    )
    cached_snapshot = weather_snapshot_cache_port.get_valid_cached_snapshot_for_normalized_region(
        normalized_region_display_name=normalized_cache_key,
        reference_time_utc=reference_time_utc,
    )
    if cached_snapshot is not None:
        return cached_snapshot

    fresh_snapshot = (
        await afetch_current_weather_snapshot_from_open_weather_map_or_raise_for_unavailable(
            region_display_name=profile_region_display_name,
            fish_sniper_backend_settings=fish_sniper_backend_settings,
            reference_time_utc=reference_time_utc,
        )
    )
    weather_snapshot_cache_port.put_snapshot_for_normalized_region(
        normalized_region_display_name=normalized_cache_key,
        snapshot=fresh_snapshot,
    )
    return fresh_snapshot


def create_default_in_memory_weather_cache() -> InMemoryFishSniperWeatherSnapshotCache:
    """Factory for deps wiring."""

    return InMemoryFishSniperWeatherSnapshotCache()
