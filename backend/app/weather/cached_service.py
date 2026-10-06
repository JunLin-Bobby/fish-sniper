"""可替換快取與實際預報服務之間的唯一組裝層。"""

from datetime import date

from app.weather.cache import ForecastCache
from app.weather.schemas import DailyWeather
from app.weather.weather_service import WeatherService


class CachedForecastService:
    """以相同介面包住天氣服務，不讓供應商程式依賴快取。"""

    def __init__(
        self,
        weather_service: WeatherService,
        cache: ForecastCache,
        *,
        weather_ttl_seconds: int,
    ) -> None:
        """注入預報服務與快取實作，可獨立更換記憶體、Redis 或資料庫。"""

        self._weather_service = weather_service
        self._cache = cache
        self._weather_ttl_seconds = weather_ttl_seconds

    @staticmethod
    def _cache_key(kind: str, latitude: float, longitude: float, day: date) -> str:
        """使用資料種類、契約版本、經緯度與日期製作 key，避免沿用缺欄位的舊快取。"""

        return f"{kind}:v2:{latitude:.4f}:{longitude:.4f}:{day.isoformat()}"

    async def get_daily_weather(self, latitude: float, longitude: float, day: date) -> DailyWeather:
        """命中時回傳逐時資料，否則取得新預報並保存。"""

        key = self._cache_key("weather", latitude, longitude, day)
        cached = await self._cache.get(key)
        if cached is not None:
            return DailyWeather.model_validate(cached)
        result = await self._weather_service.get_daily_weather(latitude, longitude, day)
        await self._cache.set(key, result.model_dump(mode="json"), self._weather_ttl_seconds)
        return result
