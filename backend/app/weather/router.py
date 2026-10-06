"""已登入使用者的逐時天氣與地名搜尋 API。"""

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, status

from app.auth.dependencies import CurrentUserDependency
from app.weather.dependencies import ForecastServiceDependency, WeatherServiceDependency
from app.weather.errors import ProviderError
from app.weather.schemas import DailyWeather, LocationSuggestion

router = APIRouter(prefix="/api/v1/weather", tags=["weather"])
logger = logging.getLogger(__name__)


def validate_forecast_date(day: date) -> None:
    """限制第一版查詢當天至未來六天的預報日期。"""

    today = datetime.now(ZoneInfo("Asia/Taipei")).date()
    if not today <= day <= today + timedelta(days=6):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Forecast date must be within today and the next six days.",
        )


def provider_unavailable(error: ProviderError) -> HTTPException:
    """記錄不含敏感資訊的供應商錯誤，對使用者回傳統一訊息。"""

    logger.warning(
        "Forecast provider failed: provider=%s category=%s", error.provider, error.category
    )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Forecast data is temporarily unavailable. Please try again later.",
    )


@router.get("/hourly", response_model=DailyWeather)
async def get_daily_weather(
    _current_user: CurrentUserDependency,
    service: ForecastServiceDependency,
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    day: date = Query(alias="date"),
) -> DailyWeather:
    """驗證已登入使用者、座標與日期，回傳指定釣點的逐時預報。"""

    validate_forecast_date(day)
    try:
        return await service.get_daily_weather(lat, lon, day)
    except ProviderError as error:
        raise provider_unavailable(error) from error


@router.get("/locations/search", response_model=list[LocationSuggestion])
async def search_locations(
    _current_user: CurrentUserDependency,
    service: WeatherServiceDependency,
    q: str = Query(min_length=2, max_length=80),
    language: str = Query(default="zh", pattern="^(zh|en)$"),
) -> list[LocationSuggestion]:
    """為拒絕定位或手動換釣點的使用者提供地名搜尋。"""

    if len(q.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Search term must contain at least two characters.",
        )
    try:
        return await service.search_locations(q.strip(), language)
    except ProviderError as error:
        raise provider_unavailable(error) from error
