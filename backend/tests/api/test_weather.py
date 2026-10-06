"""天氣 API 的登入保護、座標驗證與淡水氣象資料契約測試。"""

from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.auth.jwt import create_access_token
from app.core.config import Settings, get_settings
from app.db.dependencies import get_users_repository
from app.db.users import UserRecord
from app.main import create_app
from app.weather.dependencies import get_forecast_service
from app.weather.schemas import DailyWeather, WeatherHour, WeatherSummary
from tests.fakes import InMemoryUsersRepository

TEST_USER = UserRecord(
    id=UUID("8aef95ae-16df-4d32-99d9-730b945b34ac"),
    google_sub="test-google-sub",
    email="angler@example.com",
)


class FakeForecastService:
    """取代真實供應商與快取，專注驗證 API 契約。"""

    async def get_daily_weather(self, latitude, longitude, day) -> DailyWeather:
        """回傳單筆測試用逐時天氣。"""

        return DailyWeather(
            date=day,
            timezone="Asia/Taipei",
            summary=WeatherSummary(
                weather_code=3,
                temperature_min_c=23,
                temperature_max_c=29,
                precipitation_probability_max_pct=20,
                wind_speed_max_mps=5,
                wind_gusts_max_mps=8,
            ),
            hours=[
                WeatherHour(
                    time=datetime.combine(day, datetime.min.time(), tzinfo=ZoneInfo("Asia/Taipei")),
                    temperature_c=25,
                    pressure_hpa=1012,
                    weather_code=0,
                    precipitation_probability_pct=0,
                    wind_speed_mps=0,
                    wind_direction_deg=360,
                    wind_gusts_mps=1,
                    is_day=False,
                )
            ],
        )


def build_client() -> tuple[TestClient, Settings]:
    """建立使用測試 JWT、記憶體 user 與假預報服務的 API client。"""

    settings = Settings(_env_file=None, jwt_secret_key="weather-test-secret-at-least-32-bytes")
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_users_repository] = lambda: InMemoryUsersRepository([TEST_USER])
    app.dependency_overrides[get_forecast_service] = lambda: FakeForecastService()
    return TestClient(app), settings


def test_weather_route_requires_bearer_token() -> None:
    """沒有 FishSniper token 時不得取得天氣資料。"""

    client, _settings = build_client()
    today = datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat()
    response = client.get(f"/api/v1/weather/hourly?lat=25.13&lon=121.74&date={today}")
    assert response.status_code == 401


def test_weather_route_returns_shared_summary_and_hourly_data() -> None:
    """有效 token 能以一份回應取得摘要與逐時氣象，但沒有海洋及潮汐資料。"""

    client, settings = build_client()
    token = create_access_token(settings, user_id=TEST_USER.id, email=TEST_USER.email)
    today = datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat()
    headers = {"Authorization": f"Bearer {token}"}
    weather = client.get(
        f"/api/v1/weather/hourly?lat=25.13&lon=121.74&date={today}", headers=headers
    )
    assert weather.status_code == 200
    assert weather.json()["hours"][0]["temperature_c"] == 25
    assert weather.json()["hours"][0]["pressure_hpa"] == 1012
    hour = weather.json()["hours"][0]
    assert set(hour) == {
        "time",
        "temperature_c",
        "pressure_hpa",
        "weather_code",
        "precipitation_probability_pct",
        "wind_speed_mps",
        "wind_direction_deg",
        "wind_gusts_mps",
        "is_day",
    }
    assert hour["precipitation_probability_pct"] == 0
    assert hour["wind_speed_mps"] == 0
    assert hour["is_day"] is False
    assert weather.json()["summary"]["temperature_max_c"] == 29
    assert weather.json()["summary"]["wind_gusts_max_mps"] == 8
    removed_route = client.get(
        f"/api/v1/weather/tides?lat=25.13&lon=121.74&date={today}", headers=headers
    )
    assert removed_route.status_code == 404


def test_weather_route_rejects_bad_coordinates() -> None:
    """FastAPI 在呼叫供應商前擋下無效緯度。"""

    client, settings = build_client()
    token = create_access_token(settings, user_id=TEST_USER.id, email=TEST_USER.email)
    today = datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat()
    response = client.get(
        f"/api/v1/weather/hourly?lat=200&lon=121.74&date={today}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
