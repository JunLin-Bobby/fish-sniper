"""逐時天氣、地點搜尋與快取的離線測試。"""

import asyncio
from datetime import date

import httpx
import pytest

from app.weather.cached_service import CachedForecastService
from app.weather.errors import ProviderError
from app.weather.memory_cache import MemoryForecastCache
from app.weather.open_meteo import OpenMeteoClient, parse_hourly_forecast
from app.weather.schemas import DailyWeather
from app.weather.weather_service import WeatherService

DAY = date(2026, 9, 30)


def forecast_payload() -> dict:
    """提供獨立於正式欄位 mapping 的供應商原始回應，涵蓋零值與缺值。"""

    return {
        "timezone": "Asia/Taipei",
        "hourly_units": {
            "temperature_2m": "°C",
            "pressure_msl": "hPa",
            "precipitation_probability": "%",
            "wind_speed_10m": "m/s",
            "wind_direction_10m": "°",
            "wind_gusts_10m": "m/s",
        },
        "hourly": {
            "time": ["2026-09-30T00:00", "2026-09-30T01:00"],
            "temperature_2m": [26.0, None],
            "pressure_msl": [1011.2, 1011.4],
            "weather_code": [0, None],
            "precipitation_probability": [0, None],
            "wind_speed_10m": [0, 2.5],
            "wind_direction_10m": [360, None],
            "wind_gusts_10m": [1.5, 4.0],
            "is_day": [0, 1],
        },
        "daily_units": {
            "temperature_2m_min": "°C",
            "temperature_2m_max": "°C",
            "precipitation_probability_max": "%",
            "wind_speed_10m_max": "m/s",
            "wind_gusts_10m_max": "m/s",
        },
        "daily": {
            "time": ["2026-09-30"],
            "weather_code": [3],
            "temperature_2m_min": [23.0],
            "temperature_2m_max": [29.0],
            "precipitation_probability_max": [20],
            "wind_speed_10m_max": [5.0],
            "wind_gusts_10m_max": [8.5],
        },
    }


def test_open_meteo_converts_hourly_arrays_and_search_results() -> None:
    """確認一次預報請求取得摘要與逐時資料，另外的地名搜尋回傳座標。"""

    forecast_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        """依 URL 回傳固定的供應商資料，避免外部網路依賴。"""

        if "geocoding" in str(request.url):
            return httpx.Response(
                200,
                json={"results": [{"name": "基隆", "latitude": 25.13, "longitude": 121.74}]},
            )
        assert request.url.host == "api.open-meteo.com"
        forecast_requests.append(request)
        assert "wind_gusts_10m" in request.url.params["hourly"].split(",")
        assert "weather_code" in request.url.params["hourly"].split(",")
        assert "temperature_2m_max" in request.url.params["daily"].split(",")
        assert request.url.params["wind_speed_unit"] == "ms"
        assert request.url.params["temperature_unit"] == "celsius"
        return httpx.Response(200, json=forecast_payload())

    async def run() -> None:
        """驗證兩種介接方法的實際回傳值。"""

        client = OpenMeteoClient(transport=httpx.MockTransport(handler))
        weather = await WeatherService(client).get_daily_weather(25.13, 121.74, DAY)
        locations = await client.search_locations("基隆", "zh")
        assert weather.hours[0].temperature_c == 26.0
        assert weather.hours[0].time.isoformat() == "2026-09-30T00:00:00+08:00"
        assert weather.hours[1].temperature_c is None
        assert weather.hours[0].precipitation_probability_pct == 0
        assert weather.hours[0].wind_speed_mps == 0
        assert weather.hours[0].is_day is False
        assert weather.hours[1].is_day is True
        assert weather.hours[1].weather_code is None
        assert weather.summary.temperature_max_c == 29
        assert weather.summary.wind_gusts_max_mps == 8.5
        assert len(forecast_requests) == 1
        assert locations[0].name == "基隆"

    asyncio.run(run())


def test_open_meteo_rejects_mismatched_hourly_arrays() -> None:
    """確認供應商資料長度不一致時不繪製錯誤圖表。"""

    def handler(_request: httpx.Request) -> httpx.Response:
        """回傳故意損壞的逐時陣列。"""

        payload = forecast_payload()
        payload["hourly"]["wind_gusts_10m"] = []
        return httpx.Response(200, json=payload)

    async def run() -> None:
        """確認驗證器把資料錯誤分類成 invalid_payload。"""

        client = OpenMeteoClient(transport=httpx.MockTransport(handler))
        with pytest.raises(ProviderError, match="invalid_payload"):
            await client.fetch_hourly_forecast(25.13, 121.74, DAY)

    asyncio.run(run())


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("hourly", "precipitation_probability", [101, 0]),
        ("hourly", "wind_speed_10m", [-1, 0]),
        ("hourly", "temperature_2m", [float("nan"), 25]),
        ("hourly", "wind_direction_10m", [361, 0]),
        ("hourly", "time", ["2026-09-30T01:00", "2026-09-30T00:00"]),
        ("hourly_units", "wind_speed_10m", "km/h"),
        ("daily", "time", ["2026-10-01"]),
        ("daily", "temperature_2m_min", [30]),
        ("daily", "precipitation_probability_max", [101]),
        ("daily", "wind_gusts_10m_max", []),
    ],
)
def test_open_meteo_rejects_invalid_extended_fields(section, field, value) -> None:
    """拒絕越界、非有限數值、錯誤單位、日期及摘要，避免誤導使用者。"""

    payload = forecast_payload()
    payload[section][field] = value
    with pytest.raises(ProviderError, match="invalid_payload"):
        parse_hourly_forecast(payload, DAY)


def test_memory_cache_expiry_and_service_decoupling() -> None:
    """確認命中不重呼叫服務，過期後會重新取得資料。"""

    class FakeWeatherService:
        """記錄未命中時的天氣服務呼叫次數。"""

        calls = 0

        async def get_daily_weather(
            self, latitude: float, longitude: float, day: date
        ) -> DailyWeather:
            """回傳不依賴供應商的測試預報。"""

            self.calls += 1
            return parse_hourly_forecast(forecast_payload(), day)

    async def run() -> None:
        """比較相同座標、不同日期與立即過期的快取結果。"""

        cache = MemoryForecastCache()
        weather = FakeWeatherService()
        service = CachedForecastService(
            weather,  # type: ignore[arg-type]
            cache,
            weather_ttl_seconds=60,
        )
        # 舊契約的快取不能遮蔽新欄位；命中 v2 後摘要與逐時資料必須完整保留。
        await cache.set("weather:v1:25.1300:121.7400:2026-09-30", {"old": True}, 60)
        first = await service.get_daily_weather(25.13, 121.74, DAY)
        second = await service.get_daily_weather(25.13, 121.74, DAY)
        assert first == second
        assert second.summary.wind_gusts_max_mps == 8.5
        assert second.hours[0].precipitation_probability_pct == 0
        await service.get_daily_weather(25.14, 121.74, DAY)
        assert weather.calls == 2
        await cache.set("short", {"ok": True}, 0)
        assert await cache.get("short") is None

    asyncio.run(run())
