import { useState, type SyntheticEvent } from 'react'
import { useTranslation } from 'react-i18next'
import type { DailyWeather } from '../api/weatherTypes.ts'
import { WeatherChart } from './WeatherChart.tsx'

// 預設收合兩張趨勢圖，只有展開時才掛載圖表，不觸發任何資料請求。
export function WeatherTrendsDisclosure(props: { weather: DailyWeather }) {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)

  // 同步原生 details 狀態，確保 Recharts 在可見且有尺寸的容器內初始化。
  function handleToggle(event: SyntheticEvent<HTMLDetailsElement>): void {
    setIsOpen(event.currentTarget.open)
  }

  return (
    <details onToggle={handleToggle} className="group rounded-xl border border-white/10 bg-black/15">
      <summary className="flex min-h-12 cursor-pointer list-none items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-(--fs-green)">
        <span aria-hidden="true" className="text-(--fs-cyan)">{isOpen ? '−' : '+'}</span>
        {t('liveWeather.viewTrends')}
      </summary>
      {isOpen ? <div className="px-3 pb-3"><WeatherChart weather={props.weather} /></div> : null}
    </details>
  )
}
