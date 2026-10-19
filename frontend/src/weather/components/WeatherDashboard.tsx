import { useTranslation } from 'react-i18next'
import type { DailyWeatherLoadState } from '../hooks/useDailyConditions.ts'
import { WeatherHourlyTable } from './WeatherHourlyTable.tsx'
import { WeatherTrendsDisclosure } from './WeatherTrendsDisclosure.tsx'

// 呈現首頁已載入的預報、錯誤與重試操作；地點、日期及 API 請求由首頁管理。
export function WeatherDashboard(props: {
  weather: DailyWeatherLoadState
  hasLocation: boolean
  onRetry: () => void
}) {
  const { t } = useTranslation()
  const isReady = props.weather.status === 'ready' && props.weather.data !== null
  return (
    <section aria-label={t('liveWeather.title')} className="grid min-w-0 gap-4 rounded-[18px] border border-(--fs-line) bg-(--fs-panel) p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold">{t('liveWeather.title')}</h2>
        <a href="https://open-meteo.com/" target="_blank" rel="noreferrer" className="text-xs text-(--fs-muted) underline decoration-white/20 underline-offset-4">
          {t('liveWeather.openMeteoCredit')}
        </a>
      </div>
      {isReady && props.weather.data ? (
        <>
          <WeatherHourlyTable weather={props.weather.data} />
          <WeatherTrendsDisclosure weather={props.weather.data} />
        </>
      ) : (
        <p role="status" className="rounded-xl bg-black/20 p-4 text-sm text-(--fs-muted)">
          {t(!props.hasLocation ? 'liveWeather.choosePrompt'
            : props.weather.status === 'error' ? 'liveWeather.tryAgain' : 'liveWeather.loadingWeather')}
        </p>
      )}
      {props.hasLocation && props.weather.status === 'error' ? (
        <button type="button" onClick={props.onRetry} className="min-h-11 w-fit rounded-lg border border-white/20 px-4 text-sm font-semibold hover:border-white/40">
          {t('liveWeather.retry')}
        </button>
      ) : null}
    </section>
  )
}
