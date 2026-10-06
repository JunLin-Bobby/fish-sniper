"""Open-Meteo 逐時預報與地名搜尋介接。"""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from pydantic import ValidationError

from app.weather.errors import ProviderError
from app.weather.schemas import DailyWeather, LocationSuggestion, WeatherHour, WeatherSummary

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# 在供應商邊界對應原始欄位，讓其他服務只使用 FishSniper 的資料契約。
HOURLY_FIELDS = {
    "temperature_2m": "temperature_c",
    "pressure_msl": "pressure_hpa",
    "weather_code": "weather_code",
    "precipitation_probability": "precipitation_probability_pct",
    "wind_speed_10m": "wind_speed_mps",
    "wind_direction_10m": "wind_direction_deg",
    "wind_gusts_10m": "wind_gusts_mps",
    "is_day": "is_day",
}
DAILY_FIELDS = {
    "weather_code": "weather_code",
    "temperature_2m_min": "temperature_min_c",
    "temperature_2m_max": "temperature_max_c",
    "precipitation_probability_max": "precipitation_probability_max_pct",
    "wind_speed_10m_max": "wind_speed_max_mps",
    "wind_gusts_10m_max": "wind_gusts_max_mps",
}
HOURLY_UNITS = {
    "temperature_2m": "°C",
    "pressure_msl": "hPa",
    "precipitation_probability": "%",
    "wind_speed_10m": "m/s",
    "wind_direction_10m": "°",
    "wind_gusts_10m": "m/s",
}
DAILY_UNITS = {
    "temperature_2m_min": "°C",
    "temperature_2m_max": "°C",
    "precipitation_probability_max": "%",
    "wind_speed_10m_max": "m/s",
    "wind_gusts_10m_max": "m/s",
}


class OpenMeteoClient:
    """將 Open-Meteo HTTP 與原始 JSON 限制在單一邊界。"""

    def __init__(
        self, *, timeout_seconds: float = 10.0, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        """保存逾時設定與可供測試替換的 HTTP transport。"""

        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def _get_json(self, url: str, params: dict[str, str | float]) -> dict[str, Any]:
        """發送 GET，並把連線、額度與格式問題轉成安全錯誤類別。"""

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, transport=self._transport
            ) as client:
                response = await client.get(url, params=params)
        except httpx.TimeoutException as error:
            raise ProviderError("open_meteo", "timeout") from error
        except httpx.HTTPError as error:
            raise ProviderError("open_meteo", "network") from error
        if response.status_code == 429:
            raise ProviderError("open_meteo", "rate_limited")
        if response.status_code >= 400:
            raise ProviderError("open_meteo", f"http_{response.status_code}")
        try:
            payload = response.json()
        except ValueError as error:
            raise ProviderError("open_meteo", "invalid_json") from error
        if not isinstance(payload, dict) or payload.get("error"):
            raise ProviderError("open_meteo", "invalid_payload")
        return payload

    async def fetch_hourly_forecast(
        self, latitude: float, longitude: float, day: date
    ) -> DailyWeather:
        """以一次 HTTP 請求取得逐時氣象與當日摘要，指定一致的溫度及風速單位。"""

        payload = await self._get_json(
            FORECAST_URL,
            {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": ",".join(HOURLY_FIELDS),
                "daily": ",".join(DAILY_FIELDS),
                "temperature_unit": "celsius",
                "wind_speed_unit": "ms",
                "timezone": "auto",
                "start_date": day.isoformat(),
                "end_date": day.isoformat(),
            },
        )
        return parse_hourly_forecast(payload, day)

    async def search_locations(self, query: str, language: str) -> list[LocationSuggestion]:
        """將地名搜尋結果整理成前端可選擇的座標清單。"""

        payload = await self._get_json(
            GEOCODING_URL,
            {"name": query, "count": "8", "language": language},
        )
        results = payload.get("results", [])
        if not isinstance(results, list):
            raise ProviderError("open_meteo", "invalid_payload")
        try:
            return [
                LocationSuggestion(
                    name=item["name"],
                    region=item.get("admin1"),
                    country=item.get("country"),
                    latitude=item["latitude"],
                    longitude=item["longitude"],
                )
                for item in results
            ]
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            raise ProviderError("open_meteo", "invalid_payload") from error


def parse_hourly_forecast(payload: dict[str, Any], day: date) -> DailyWeather:
    """驗證各欄位的單位、陣列與日期，將逐時資料和摘要整理成共用回應。"""

    try:
        timezone_name = str(payload["timezone"])
        timezone = ZoneInfo(timezone_name)
        hourly = payload["hourly"]
        times = hourly["time"]
        if not isinstance(times, list) or not times:
            raise ValueError("missing hourly timestamps")
        validate_arrays(hourly, HOURLY_FIELDS, len(times))
        validate_units(payload["hourly_units"], HOURLY_UNITS)
        hours = [
            WeatherHour(
                time=datetime.fromisoformat(timestamp).replace(tzinfo=timezone),
                **{target: hourly[source][index] for source, target in HOURLY_FIELDS.items()},
            )
            for index, timestamp in enumerate(times)
        ]
        if any(hour.time.date() != day for hour in hours):
            raise ValueError("response contains the wrong local date")
        if any(first.time >= second.time for first, second in zip(hours, hours[1:])):
            raise ValueError("hourly timestamps are duplicated or out of order")
        daily = payload["daily"]
        if daily["time"] != [day.isoformat()]:
            raise ValueError("daily response contains the wrong local date")
        validate_arrays(daily, DAILY_FIELDS, 1)
        validate_units(payload["daily_units"], DAILY_UNITS)
        summary = WeatherSummary(
            **{target: daily[source][0] for source, target in DAILY_FIELDS.items()}
        )
        if (
            summary.temperature_min_c is not None
            and summary.temperature_max_c is not None
            and summary.temperature_min_c > summary.temperature_max_c
        ):
            raise ValueError("daily minimum temperature exceeds maximum")
        return DailyWeather(date=day, timezone=timezone_name, summary=summary, hours=hours)
    except (KeyError, TypeError, ValueError, ValidationError, ZoneInfoNotFoundError) as error:
        raise ProviderError("open_meteo", "invalid_payload") from error


def validate_arrays(data: dict[str, Any], fields: dict[str, str], expected_length: int) -> None:
    """確認每個請求欄位都有對齊的陣列，避免不同時間的值被誤配。"""

    for field in fields:
        values = data[field]
        if not isinstance(values, list) or len(values) != expected_length:
            raise ValueError(f"invalid array for {field}")


def validate_units(units: dict[str, Any], expected_units: dict[str, str]) -> None:
    """拒絕單位不符的供應商回應，避免把 km/h 數值誤標成 m/s。"""

    for field, expected_unit in expected_units.items():
        if units[field] != expected_unit:
            raise ValueError(f"unexpected unit for {field}")
