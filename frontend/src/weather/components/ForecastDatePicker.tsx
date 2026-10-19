import { useTranslation } from 'react-i18next'

// 產生台灣時區的預報日期，維持既有的今天與未來六天查詢範圍。
export function forecastDate(daysAhead: number): string {
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date(Date.now() + daysAhead * 86400000))
}

// 共用首頁的預報日期選擇；窄螢幕橫向滑動，不額外固定在畫面上。
export function ForecastDatePicker(props: { daysAhead: number; onChange: (days: number) => void }) {
  const { t } = useTranslation()
  return (
    <div role="group" aria-label={t('liveWeather.forecastDates')} className="flex min-w-0 gap-2 overflow-x-auto py-1">
      {Array.from({ length: 7 }, (_, index) => (
        <button key={index} type="button" onClick={() => props.onChange(index)} aria-pressed={props.daysAhead === index}
          className={`min-h-11 shrink-0 rounded-lg border px-3 text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-(--fs-green) ${props.daysAhead === index
            ? 'border-(--fs-green) bg-[rgba(61,255,138,.14)] text-(--fs-green-soft)'
            : 'border-white/10 text-(--fs-muted) hover:border-white/30'}`}>
          {index === 0 ? t('liveWeather.today') : index === 1 ? t('liveWeather.tomorrow') : forecastDate(index).slice(5)}
        </button>
      ))}
    </div>
  )
}
