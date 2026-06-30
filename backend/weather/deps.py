"""Weather domain FastAPI dependency providers."""

from __future__ import annotations

from weather.port import WeatherSnapshotCachePort
from weather.weather_service import create_default_in_memory_weather_cache

_weather_snapshot_cache_singleton: WeatherSnapshotCachePort | None = None


def get_fish_sniper_weather_snapshot_cache_port() -> WeatherSnapshotCachePort:
    """Return the process-wide in-memory weather cache (swap for Redis-backed cache later)."""

    global _weather_snapshot_cache_singleton
    if _weather_snapshot_cache_singleton is None:
        _weather_snapshot_cache_singleton = create_default_in_memory_weather_cache()
    return _weather_snapshot_cache_singleton
