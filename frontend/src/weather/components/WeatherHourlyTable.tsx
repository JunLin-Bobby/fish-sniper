import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { DailyWeather, WeatherHour } from '../api/weatherTypes.ts'
import { formatWeatherHour, formatWeatherNumber, weatherPresentation, windDirectionKey } from '../lib/weatherPresentation.ts'

// 將同一份逐時預報排列為橫向表格，固定指標欄，讓窄螢幕也能逐時閱讀。
export function WeatherHourlyTable(props: { weather: DailyWeather }) {
  const { t, i18n } = useTranslation()

  // 顯示可翻譯的逐時天氣與日夜圖示，避免未知代碼造成空白欄位。
  function weatherCell(hour: WeatherHour): ReactNode {
    const condition = weatherPresentation(hour.weather_code, hour.is_day)
    return <span role="img" aria-label={t(condition.translationKey)} title={t(condition.translationKey)} className="text-xl">{condition.icon}</span>
  }

  // 標示風從哪個方向吹來；箭頭指向風吹去的方向，文字保留風的來向。
  function windCell(hour: WeatherHour): ReactNode {
    const direction = windDirectionKey(hour.wind_direction_deg)
    if (direction === null) return '—'
    return (
      <span title={t('liveWeather.windFrom', { direction: t(direction) })} className="inline-flex items-center gap-1.5">
        <span aria-hidden="true" className="inline-block text-(--fs-cyan)" style={{ transform: `rotate(${hour.wind_direction_deg! + 180}deg)` }}>↑</span>
        {t(direction)}
      </span>
    )
  }

  const rows: { key: string; label: string; render: (hour: WeatherHour) => ReactNode }[] = [
    { key: 'weather', label: t('liveWeather.weatherLabel'), render: weatherCell },
    { key: 'temperature', label: t('liveWeather.temperatureC'), render: (hour) => formatWeatherNumber(hour.temperature_c, i18n.language) },
    { key: 'rain', label: t('liveWeather.rainProbabilityPct'), render: (hour) => formatWeatherNumber(hour.precipitation_probability_pct, i18n.language, 0) },
    { key: 'direction', label: t('liveWeather.windDirection'), render: windCell },
    { key: 'speed', label: t('liveWeather.windSpeedMps'), render: (hour) => formatWeatherNumber(hour.wind_speed_mps, i18n.language) },
    { key: 'gusts', label: t('liveWeather.windGustsMps'), render: (hour) => formatWeatherNumber(hour.wind_gusts_mps, i18n.language) },
    { key: 'pressure', label: t('liveWeather.pressureHpa'), render: (hour) => formatWeatherNumber(hour.pressure_hpa, i18n.language) },
  ]

  return (
    <section className="grid min-w-0 gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">{t('liveWeather.hourlyTable')}</h3>
        <p className="text-xs text-(--fs-faint)">{t('liveWeather.tableScrollHint')}</p>
      </div>
      <div role="region" aria-label={t('liveWeather.hourlyTable')} tabIndex={0} className="min-w-0 overflow-x-auto rounded-xl border border-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-(--fs-green)">
        <table className="w-max min-w-full border-separate border-spacing-0 text-center text-sm">
          <caption className="sr-only">{t('liveWeather.hourlyTable')} · {props.weather.date} · {props.weather.timezone}</caption>
          <thead>
            <tr>
              <th scope="col" className="sticky left-0 z-20 min-w-36 border-b border-r border-white/10 bg-[#0b1727] px-3 py-3 text-left font-semibold">{t('liveWeather.metric')}</th>
              {props.weather.hours.map((hour) => (
                <th key={hour.time} scope="col" className="min-w-24 border-b border-white/10 bg-[#0b1727] px-3 py-3 font-medium text-(--fs-muted)">{formatWeatherHour(hour.time, props.weather.timezone)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="odd:bg-white/3 even:bg-black/15">
                <th scope="row" className="sticky left-0 z-10 w-36 border-b border-r border-white/10 bg-[#0b1727] px-3 py-3 text-left text-xs font-semibold">{row.label}</th>
                {props.weather.hours.map((hour) => (
                  <td key={hour.time} className="border-b border-white/5 px-3 py-3 tabular-nums">{row.render(hour)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs leading-relaxed text-(--fs-faint)">{t('liveWeather.hourlyWindowNote')}</p>
    </section>
  )
}
