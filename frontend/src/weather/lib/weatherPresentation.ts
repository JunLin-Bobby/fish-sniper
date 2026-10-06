type WeatherPresentation = { translationKey: string; icon: string }

// 保留 WMO 原始代碼，僅在呈現邊界對應語系 key 與天氣圖示。
const weatherCodes: Record<number, WeatherPresentation> = {
  0: { translationKey: 'weatherConditions.clear', icon: '☀️' },
  1: { translationKey: 'weatherConditions.mainlyClear', icon: '🌤️' },
  2: { translationKey: 'weatherConditions.partlyCloudy', icon: '⛅' },
  3: { translationKey: 'weatherConditions.overcast', icon: '☁️' },
  45: { translationKey: 'weatherConditions.fog', icon: '🌫️' },
  48: { translationKey: 'weatherConditions.freezingFog', icon: '🌫️' },
  51: { translationKey: 'weatherConditions.lightDrizzle', icon: '🌦️' },
  53: { translationKey: 'weatherConditions.drizzle', icon: '🌦️' },
  55: { translationKey: 'weatherConditions.heavyDrizzle', icon: '🌧️' },
  56: { translationKey: 'weatherConditions.freezingDrizzle', icon: '🌧️' },
  57: { translationKey: 'weatherConditions.freezingDrizzle', icon: '🌧️' },
  61: { translationKey: 'weatherConditions.lightRain', icon: '🌧️' },
  63: { translationKey: 'weatherConditions.rain', icon: '🌧️' },
  65: { translationKey: 'weatherConditions.heavyRain', icon: '🌧️' },
  66: { translationKey: 'weatherConditions.freezingRain', icon: '🌧️' },
  67: { translationKey: 'weatherConditions.freezingRain', icon: '🌧️' },
  71: { translationKey: 'weatherConditions.lightSnow', icon: '🌨️' },
  73: { translationKey: 'weatherConditions.snow', icon: '🌨️' },
  75: { translationKey: 'weatherConditions.heavySnow', icon: '🌨️' },
  77: { translationKey: 'weatherConditions.snowGrains', icon: '🌨️' },
  80: { translationKey: 'weatherConditions.lightShowers', icon: '🌦️' },
  81: { translationKey: 'weatherConditions.showers', icon: '🌧️' },
  82: { translationKey: 'weatherConditions.heavyShowers', icon: '🌧️' },
  85: { translationKey: 'weatherConditions.snowShowers', icon: '🌨️' },
  86: { translationKey: 'weatherConditions.snowShowers', icon: '🌨️' },
  95: { translationKey: 'weatherConditions.thunderstorm', icon: '⛈️' },
  96: { translationKey: 'weatherConditions.thunderstormHail', icon: '⛈️' },
  97: { translationKey: 'weatherConditions.heavyThunderstorm', icon: '⛈️' },
  99: { translationKey: 'weatherConditions.thunderstormHail', icon: '⛈️' },
}

// 依天氣代碼與日夜資訊選擇圖示；未知代碼保留友善的 fallback。
export function weatherPresentation(code: number | null, isDay: boolean | null = true): WeatherPresentation {
  const presentation = code === null ? undefined : weatherCodes[code]
  if (!presentation) return { translationKey: 'weatherConditions.unknown', icon: '—' }
  if (isDay === false && code !== null && code <= 2) {
    return { ...presentation, icon: code === 0 ? '🌙' : '☁️🌙' }
  }
  return presentation
}

// 將有效數值依語系格式化，保留 0；null 或非有限值以破折號呈現。
export function formatWeatherNumber(value: number | null, locale: string, digits = 1): string {
  if (value === null || !Number.isFinite(value)) return '—'
  return new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(value)
}

// 以預報地點時區顯示 24 小時時間，供圖表和表格共用。
export function formatWeatherHour(time: string, timezone: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: timezone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).format(new Date(time))
}

// 將風的來向角度轉成八方位語系 key，360° 與 0° 同樣代表北風。
export function windDirectionKey(degrees: number | null): string | null {
  if (degrees === null || !Number.isFinite(degrees)) return null
  const directions = ['north', 'northEast', 'east', 'southEast', 'south', 'southWest', 'west', 'northWest']
  const index = Math.round((((degrees % 360) + 360) % 360) / 45) % 8
  return `weatherDirections.${directions[index]}`
}
