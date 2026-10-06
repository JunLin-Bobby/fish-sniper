"""與快取無關的逐時天氣應用服務。"""

from datetime import date

from app.weather.open_meteo import OpenMeteoClient
from app.weather.schemas import DailyWeather, LocationSuggestion


class WeatherService:
    """提供可獨立測試的逐時預報與地名搜尋流程。"""

    def __init__(self, provider: OpenMeteoClient) -> None:
        """注入唯一的 Open-Meteo 資料來源。"""

        self._provider = provider

    async def get_daily_weather(self, latitude: float, longitude: float, day: date) -> DailyWeather:
        """取得指定釣點的逐時氣象與當日摘要，不處理快取或畫面呈現。"""

        return await self._provider.fetch_hourly_forecast(latitude, longitude, day)

    async def search_locations(self, query: str, language: str) -> list[LocationSuggestion]:
        """查詢可供手動選擇的地名，不處理快取。"""

        return await self._provider.search_locations(query, language)
