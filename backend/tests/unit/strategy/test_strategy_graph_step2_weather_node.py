"""Unit tests for strategy LangGraph Step 1 weather-loading node.

Pins the *override* semantics of `manual_weather`: when present, the node MUST skip
OpenWeatherMap entirely and use the manual values; OWM is only consulted when
`manual_weather` is absent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from settings import AppSettings
from strategy.graph import (
    node_load_region_and_weather,
)
from strategy.schemas import GenerateBassStrategyRequestBody, ManualWeatherPayload
from weather.port import FishSniperOpenWeatherSnapshot
from weather.weather_errors import FishSniperWeatherUnavailableError


def _make_request_body(
    *,
    manual_weather: ManualWeatherPayload | None,
) -> GenerateBassStrategyRequestBody:
    return GenerateBassStrategyRequestBody(
        region="Boston",
        fishing_location="Close pond",
        water_depth_m=1.5,
        fishing_scene="lake",
        target_species="Largemouth Bass",
        manual_weather=manual_weather,
    )


def _base_state(*, request: GenerateBassStrategyRequestBody) -> dict[str, Any]:
    return {
        "fish_sniper_user_id": uuid4(),
        "parsed_request_body": request,
        "fish_sniper_backend_settings": AppSettings(),
        "persistence_port": object(),
        "weather_snapshot_cache_port": object(),
        "reference_time_utc": datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC),
        "langfuse_client": None,
    }


def _owm_snapshot(*, temperature_celsius: float) -> FishSniperOpenWeatherSnapshot:
    return FishSniperOpenWeatherSnapshot(
        temperature_celsius=temperature_celsius,
        condition_label="Clouds",
        condition_code="cloudy",
        wind_speed_meters_per_second=3.0,
        pressure_hectopascals=1013,
        humidity_percent=60,
        fetched_at_utc=datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC),
    )


_TARGET = (
    "strategy.graph."
    "afetch_or_refresh_cached_current_weather_snapshot_for_region"
)


@pytest.mark.asyncio
async def test_step2_uses_manual_weather_and_skips_open_weather_map_when_manual_provided() -> None:
    request = _make_request_body(
        manual_weather=ManualWeatherPayload(
            temperature_c=30.0,
            condition_code="sunny",
            wind_speed_ms=1.5,
            pressure_hpa=1008,
        ),
    )
    state = _base_state(request=request)

    with patch(
        _TARGET,
        new=AsyncMock(return_value=_owm_snapshot(temperature_celsius=11.0)),
    ) as owm_mock:
        result = await node_load_region_and_weather(state)

    assert owm_mock.await_count == 0, "OWM must not be called when manual_weather is provided"
    assert result["temperature_celsius"] == 30.0
    assert result["condition_code"] == "sunny"
    assert result["wind_speed_meters_per_second"] == 1.5
    assert result["pressure_hectopascals"] == 1008
    assert result["profile_region_display_name"] == "Boston"
    assert "terminal_http_status" not in result


@pytest.mark.asyncio
async def test_step2_uses_open_weather_map_when_manual_weather_absent() -> None:
    request = _make_request_body(manual_weather=None)
    state = _base_state(request=request)

    with patch(
        _TARGET,
        new=AsyncMock(return_value=_owm_snapshot(temperature_celsius=11.0)),
    ) as owm_mock:
        result = await node_load_region_and_weather(state)

    assert owm_mock.await_count == 1
    assert result["temperature_celsius"] == 11.0
    assert result["condition_code"] == "cloudy"
    assert result["wind_speed_meters_per_second"] == 3.0
    assert result["pressure_hectopascals"] == 1013
    assert result["profile_region_display_name"] == "Boston"


@pytest.mark.asyncio
async def test_step2_returns_503_when_no_manual_and_open_weather_map_unavailable() -> None:
    request = _make_request_body(manual_weather=None)
    state = _base_state(request=request)

    with patch(_TARGET, new=AsyncMock(side_effect=FishSniperWeatherUnavailableError("down"))):
        result = await node_load_region_and_weather(state)

    assert result["terminal_http_status"] == 503
    assert result["terminal_error_envelope"] == {"error": "Weather service unavailable"}
