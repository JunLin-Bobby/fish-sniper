"""前端使用的穩定逐時天氣與地點搜尋資料契約。"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WeatherHour(BaseModel):
    """單一整點的氣象預報；風速統一為 m/s，缺資料時保留 null。"""

    model_config = ConfigDict(allow_inf_nan=False)

    time: datetime
    temperature_c: float | None
    pressure_hpa: float | None
    weather_code: int | None = Field(default=None, ge=0)
    precipitation_probability_pct: float | None = Field(default=None, ge=0, le=100)
    wind_speed_mps: float | None = Field(default=None, ge=0)
    wind_direction_deg: float | None = Field(default=None, ge=0, le=360)
    wind_gusts_mps: float | None = Field(default=None, ge=0)
    is_day: bool | None = None


class WeatherSummary(BaseModel):
    """當日摘要；天氣代碼代表當日最嚴重的預報狀況。"""

    model_config = ConfigDict(allow_inf_nan=False)

    weather_code: int | None = Field(default=None, ge=0)
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    precipitation_probability_max_pct: float | None = Field(default=None, ge=0, le=100)
    wind_speed_max_mps: float | None = Field(default=None, ge=0)
    wind_gusts_max_mps: float | None = Field(default=None, ge=0)


class DailyWeather(BaseModel):
    """指定釣點與當地日期的逐時預報。"""

    date: date
    timezone: str
    source: Literal["open_meteo"] = "open_meteo"
    summary: WeatherSummary = Field(default_factory=WeatherSummary)
    hours: list[WeatherHour]


class LocationSuggestion(BaseModel):
    """手動地名搜尋結果，供使用者選定釣點。"""

    name: str
    region: str | None = None
    country: str | None = None
    latitude: float
    longitude: float
