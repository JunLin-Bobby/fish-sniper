// 定義 FishSniper 後端已整理好的逐時天氣與地點搜尋資料契約。
export interface WeatherHour {
  time: string
  temperature_c: number | null
  pressure_hpa: number | null
  weather_code: number | null
  precipitation_probability_pct: number | null
  wind_speed_mps: number | null
  wind_direction_deg: number | null
  wind_gusts_mps: number | null
  is_day: boolean | null
}

export interface WeatherSummary {
  weather_code: number | null
  temperature_min_c: number | null
  temperature_max_c: number | null
  precipitation_probability_max_pct: number | null
  wind_speed_max_mps: number | null
  wind_gusts_max_mps: number | null
}

export interface DailyWeather {
  date: string
  timezone: string
  source: 'open_meteo'
  summary: WeatherSummary
  hours: WeatherHour[]
}

export interface SelectedLocation {
  name: string
  latitude: number
  longitude: number
}

export interface LocationSuggestion extends SelectedLocation {
  region: string | null
  country: string | null
}
