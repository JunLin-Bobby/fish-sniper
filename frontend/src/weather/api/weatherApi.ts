import { getJson } from '../../api/http.ts'
import type { DailyWeather, LocationSuggestion, SelectedLocation } from './weatherTypes.ts'

// 將座標與日期編碼成可安全附加於 API URL 的查詢參數。
function forecastPath(location: SelectedLocation, date: string): string {
  const params = new URLSearchParams({
    lat: String(location.latitude),
    lon: String(location.longitude),
    date,
  })
  return `/api/v1/weather/hourly?${params.toString()}`
}

// 取得指定釣點當地日期的逐時氣溫與海平面氣壓。
export function fetchDailyWeather(
  apiBaseUrl: string,
  location: SelectedLocation,
  date: string,
  signal?: AbortSignal,
): Promise<DailyWeather> {
  return getJson<DailyWeather>({ apiBaseUrl, path: forecastPath(location, date), signal })
}

// 將使用者輸入的地名交給後端搜尋，不讓前端直接依賴地理供應商格式。
export function searchWeatherLocations(
  apiBaseUrl: string,
  query: string,
  language: 'zh' | 'en',
  signal?: AbortSignal,
): Promise<LocationSuggestion[]> {
  const params = new URLSearchParams({ q: query, language })
  return getJson<LocationSuggestion[]>({
    apiBaseUrl,
    path: `/api/v1/weather/locations/search?${params.toString()}`,
    signal,
  })
}
