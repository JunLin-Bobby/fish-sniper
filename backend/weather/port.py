"""Cache port for OpenWeatherMap snapshots (memory today, Redis later)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FishSniperOpenWeatherSnapshot:
    """Normalized weather fields returned by GET /weather/current and used by the agent."""

    temperature_celsius: float
    condition_label: str
    condition_code: str
    wind_speed_meters_per_second: float
    pressure_hectopascals: int
    humidity_percent: int
    fetched_at_utc: datetime


class WeatherSnapshotCachePort(Protocol):
    """TTL cache for weather snapshots keyed by normalized region label."""

    def get_valid_cached_snapshot_for_normalized_region(
        self,
        *,
        normalized_region_display_name: str,
        reference_time_utc: datetime,
    ) -> FishSniperOpenWeatherSnapshot | None:
        """Return a snapshot if still within TTL; otherwise None."""

    def put_snapshot_for_normalized_region(
        self,
        *,
        normalized_region_display_name: str,
        snapshot: FishSniperOpenWeatherSnapshot,
    ) -> None:
        """Store snapshot and refresh TTL bookkeeping."""
