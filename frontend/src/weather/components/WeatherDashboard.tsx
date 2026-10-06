import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useDailyConditions } from '../hooks/useDailyConditions.ts'
import { useSelectedLocation } from '../hooks/useSelectedLocation.ts'
import { LocationPicker } from './LocationPicker.tsx'
import { WeatherChart } from './WeatherChart.tsx'
import { WeatherHourlyTable } from './WeatherHourlyTable.tsx'
import { WeatherSummary } from './WeatherSummary.tsx'

// 產生台灣時區的預報日期字串，供當天與未來六天使用。
function taiwanDate(daysAhead: number): string {
  const date = new Date(Date.now() + daysAhead * 86400000)
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(date)
}

// 一次載入釣點預報，共用回應並依序呈現摘要、逐時表格、氣溫與氣壓圖。
export function WeatherDashboard(props: { apiBaseUrl: string; onUnauthorized: () => void }) {
  const { t } = useTranslation()
  const [daysAhead, setDaysAhead] = useState(0)
  const { location, status, requestBrowserLocation, selectLocation } = useSelectedLocation()
  const { weather, retry } = useDailyConditions(
    props.apiBaseUrl, location, taiwanDate(daysAhead), props.onUnauthorized,
  )

  return (
    <section className="grid min-w-0 gap-4 rounded-[18px] border border-(--fs-line) bg-(--fs-panel) p-[18px] shadow-[inset_0_1px_rgba(255,255,255,0.04)] backdrop-blur-[18px]">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-(--fs-faint)">{t('liveWeather.section')}</p>
        <h2 className="mt-1 text-[17px] font-semibold">{t('liveWeather.title')}</h2>
      </div>
      <LocationPicker
        apiBaseUrl={props.apiBaseUrl}
        location={location}
        status={status}
        onUseCurrentLocation={requestBrowserLocation}
        onSelectLocation={selectLocation}
        onUnauthorized={props.onUnauthorized}
      />
      <div className="flex flex-wrap gap-1.5" aria-label={t('liveWeather.forecastDates')}>
        {Array.from({ length: 7 }, (_, index) => (
          <button
            key={index}
            type="button"
            onClick={() => setDaysAhead(index)}
            aria-pressed={daysAhead === index}
            className={`rounded-lg border px-2.5 py-1.5 text-xs ${daysAhead === index
              ? 'border-(--fs-green) bg-[rgba(61,255,138,.14)] text-(--fs-green-soft)'
              : 'border-white/10 text-(--fs-muted)'}`}
          >
            {index === 0 ? t('liveWeather.today') : index === 1 ? t('liveWeather.tomorrow') : taiwanDate(index).slice(5)}
          </button>
        ))}
      </div>
      {!location ? (
        <p className="rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-(--fs-muted)">{t('liveWeather.choosePrompt')}</p>
      ) : (
        weather.status === 'ready' && weather.data
          ? <>
              <WeatherSummary weather={weather.data} />
              <WeatherHourlyTable weather={weather.data} />
              <WeatherChart weather={weather.data} />
            </>
          : <p className="rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-(--fs-muted)">{t(weather.status === 'error' ? 'liveWeather.tryAgain' : 'liveWeather.loadingWeather')}</p>
      )}
      {weather.status === 'error' ? (
        <button type="button" onClick={retry} className="w-fit rounded-lg border border-white/20 px-3 py-2 text-xs font-semibold hover:border-white/40">
          {t('liveWeather.retry')}
        </button>
      ) : null}
    </section>
  )
}
