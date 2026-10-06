import { useCallback, useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DailyWeather } from '../api/weatherTypes.ts'
import { formatWeatherHour } from '../lib/weatherPresentation.ts'

type ChartPoint = DailyWeather['hours'][number] & { label: string }
type WeatherMetric = 'temperature_c' | 'pressure_hpa'

// 呈現單一環境指標，以同色漸層填滿曲線下方，氣溫以 0°C 作為軸的起點。
function MetricChart(props: {
  data: ChartPoint[]
  valueKey: WeatherMetric
  title: string
  ariaLabel: string
  color: string
  emptyMessage: string
}) {
  const fillId = useId()
  const [tickInterval, setTickInterval] = useState(1)
  const hasData = props.data.some((point) => point[props.valueKey] !== null)

  // 寬圖每兩小時顯示刻度，窄圖每四小時顯示，資料點與 tooltip 仍保留逐時值。
  const handleResize = useCallback((width: number) => {
    setTickInterval(width >= 640 ? 1 : 3)
  }, [])

  return (
    <article className="min-w-0 rounded-xl border border-white/10 bg-black/20 p-3">
      <h3 className="mb-2 min-h-10 text-sm font-semibold">{props.title}</h3>
      <div className="h-[240px] w-full sm:h-[260px]" role="img" aria-label={props.ariaLabel}>
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%" onResize={handleResize}>
            <AreaChart data={props.data} margin={{ top: 12, right: 12, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={props.color} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={props.color} stopOpacity={0.04} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,.08)" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: '#94a3b8', fontSize: 10 }} interval={tickInterval} />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                domain={props.valueKey === 'temperature_c' ? [0, 'auto'] : ['auto', 'auto']}
              />
              <Tooltip contentStyle={{ background: '#0b1727', border: '1px solid #334155' }} />
              <Area
                type="monotone"
                dataKey={props.valueKey}
                name={props.title}
                stroke={props.color}
                strokeWidth={2.5}
                fill={`url(#${fillId})`}
                baseValue="dataMin"
                dot={false}
                connectNulls={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="grid h-full place-items-center px-3 text-center text-sm text-(--fs-muted)">
            {props.emptyMessage}
          </div>
        )}
      </div>
    </article>
  )
}

// 將暖色氣溫與藍色海平面氣壓圖垂直排列，保留完整橫向時間軸。
export function WeatherChart(props: { weather: DailyWeather }) {
  const { t } = useTranslation()
  const data = props.weather.hours.map((hour) => ({
    ...hour,
    label: formatWeatherHour(hour.time, props.weather.timezone),
  }))

  return (
    <section aria-label={t('liveWeather.hourlyChart')} className="grid min-w-0 gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <h3 className="text-sm font-semibold">{t('liveWeather.hourlyChart')}</h3>
        <span className="text-xs text-(--fs-faint)">{t('liveWeather.openMeteoCredit')}</span>
      </div>
      <div className="grid min-w-0 gap-3">
        <MetricChart
          data={data}
          valueKey="temperature_c"
          title={t('liveWeather.temperatureC')}
          ariaLabel={t('liveWeather.temperatureChart')}
          color="#ffb454"
          emptyMessage={t('liveWeather.noHourlyData')}
        />
        <MetricChart
          data={data}
          valueKey="pressure_hpa"
          title={t('liveWeather.pressureHpa')}
          ariaLabel={t('liveWeather.pressureChart')}
          color="#38d6ff"
          emptyMessage={t('liveWeather.noHourlyData')}
        />
      </div>
    </section>
  )
}
