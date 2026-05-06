"""Process-local dict cache with 30-minute TTL for weather snapshots."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta

from weather.port import FishSniperOpenWeatherSnapshot, WeatherSnapshotCachePort

_WEATHER_CACHE_TTL = timedelta(minutes=30)


class InMemoryFishSniperWeatherSnapshotCache(WeatherSnapshotCachePort):
    """In-memory TTL cache; thread-safe for sync FastAPI handlers under threadpool workers."""

    def __init__(self) -> None:
        self._snapshot_and_cached_at_tuple_by_region: dict[
            str,
            tuple[FishSniperOpenWeatherSnapshot, datetime],
        ] = {}
        self._threading_lock = threading.Lock()

    def get_valid_cached_snapshot_for_normalized_region(
        self,
        *,
        normalized_region_display_name: str,
        reference_time_utc: datetime,
    ) -> FishSniperOpenWeatherSnapshot | None:
        with self._threading_lock:
            entry = self._snapshot_and_cached_at_tuple_by_region.get(normalized_region_display_name)
            if entry is None:
                return None
            snapshot, cached_at_utc = entry
            if reference_time_utc - cached_at_utc > _WEATHER_CACHE_TTL:
                del self._snapshot_and_cached_at_tuple_by_region[normalized_region_display_name]
                return None
            return snapshot

    def put_snapshot_for_normalized_region(
        self,
        *,
        normalized_region_display_name: str,
        snapshot: FishSniperOpenWeatherSnapshot,
    ) -> None:
        with self._threading_lock:
            self._snapshot_and_cached_at_tuple_by_region[normalized_region_display_name] = (
                snapshot,
                snapshot.fetched_at_utc,
            )
