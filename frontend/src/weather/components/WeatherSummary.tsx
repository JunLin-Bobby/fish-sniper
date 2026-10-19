import { useTranslation } from 'react-i18next'
import type { DailyWeather } from '../api/weatherTypes.ts'
import { formatWeatherNumber, weatherPresentation } from '../lib/weatherPresentation.ts'

// 用共用預報回應呈現當日摘要，明確標示天氣與降雨機率的摘要涵義。
export function WeatherSummary(props: { weather: DailyWeather }) {
  const { t, i18n } = useTranslation()
  const summary = props.weather.summary
  const condition = weatherPresentation(summary.weather_code)
  const temperatureRange = summary.temperature_min_c === null && summary.temperature_max_c === null
    ? '—'
    : `${formatWeatherNumber(summary.temperature_min_c, i18n.language)}–${formatWeatherNumber(summary.temperature_max_c, i18n.language)} °C`
  const rain = summary.precipitation_probability_max_pct === null
    ? '—' : `${formatWeatherNumber(summary.precipitation_probability_max_pct, i18n.language, 0)}%`
  const wind = summary.wind_speed_max_mps === null
    ? '—' : `${formatWeatherNumber(summary.wind_speed_max_mps, i18n.language)} m/s`
  const cards = [
    { label: t('liveWeather.weatherLabel'), value: `${condition.icon} ${t(condition.translationKey)}`, note: t('liveWeather.dailyWeatherNote') },
    { label: t('liveWeather.temperatureRange'), value: temperatureRange, note: t('liveWeather.dailyTemperatureNote') },
    { label: t('liveWeather.maxRainProbability'), value: rain, note: t('liveWeather.maxRainNote') },
    { label: t('liveWeather.maxWindSpeed'), value: wind, note: t('liveWeather.gustValue', { value: formatWeatherNumber(summary.wind_gusts_max_mps, i18n.language) }) },
  ]

  return (
    <section aria-label={t('liveWeather.dailySummary')} className="grid gap-3">
      <h2 className="text-sm font-semibold">{t('liveWeather.dailySummary')} · {props.weather.date}</h2>
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {cards.map((card) => (
          <article key={card.label} className="min-w-0 rounded-xl border border-white/10 bg-white/4 p-3">
            <p className="text-xs text-(--fs-muted)">{card.label}</p>
            <p className="mt-2 text-lg font-bold text-slate-100 sm:text-xl">{card.value}</p>
            <p className="mt-2 text-xs leading-relaxed text-(--fs-muted)">{card.note}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
