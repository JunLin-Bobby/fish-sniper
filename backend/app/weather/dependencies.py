"""將供應商、純預報服務與共用記憶體快取組裝給 API 使用。"""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.weather.cached_service import CachedForecastService
from app.weather.memory_cache import MemoryForecastCache
from app.weather.open_meteo import OpenMeteoClient
from app.weather.weather_service import WeatherService

_shared_cache = MemoryForecastCache()


def get_weather_service(settings: Settings = Depends(get_settings)) -> WeatherService:
    """建立只負責供應商與資料轉換、不含快取的天氣服務。"""

    return WeatherService(OpenMeteoClient(timeout_seconds=settings.weather_request_timeout_seconds))


def get_forecast_service(settings: Settings = Depends(get_settings)) -> CachedForecastService:
    """替每個 request 組裝服務，但共用同一個 process 的記憶體快取。"""

    timeout = settings.weather_request_timeout_seconds
    return CachedForecastService(
        WeatherService(OpenMeteoClient(timeout_seconds=timeout)),
        _shared_cache,
        weather_ttl_seconds=settings.weather_cache_ttl_seconds,
    )


WeatherServiceDependency = Annotated[WeatherService, Depends(get_weather_service)]
ForecastServiceDependency = Annotated[CachedForecastService, Depends(get_forecast_service)]
