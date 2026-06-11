import type { CurrentWeatherResponsePayload } from '../../api/fishSniperApiTypes.ts'

function HudReadout(options: { label: string; value: string; accent?: 'sonar' | 'amber' }) {
  const { label, value, accent = 'sonar' } = options
  const valueClassName =
    accent === 'amber' ? 'text-amber-300' : 'text-[#5dff9a] [text-shadow:0_0_12px_rgba(93,255,154,0.35)]'

  return (
    <div className="rounded-lg border border-white/10 bg-black/40 px-4 py-3 backdrop-blur-sm">
      <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className={`mt-1 text-sm font-semibold tabular-nums ${valueClassName}`}>{value}</p>
    </div>
  )
}

export function StrategySonarHudPanel(options: {
  fishingSceneLabel: string
  waterDepthMeters: string
  weatherMode: 'auto' | 'manual'
  autoWeatherRemoteStatus: 'idle' | 'loading' | 'success' | 'error'
  autoWeatherSnapshotPayload: CurrentWeatherResponsePayload | null
  manualTemperatureCelsius: string
  manualConditionCode: string
  onRefreshWeather: () => void
}) {
  const {
    fishingSceneLabel,
    waterDepthMeters,
    weatherMode,
    autoWeatherRemoteStatus,
    autoWeatherSnapshotPayload,
    manualTemperatureCelsius,
    manualConditionCode,
    onRefreshWeather,
  } = options

  const depthDisplay = Number.isFinite(Number.parseFloat(waterDepthMeters))
    ? `${waterDepthMeters} m`
    : '—'

  return (
    <div className="relative flex h-full min-h-[22rem] flex-col overflow-hidden rounded-2xl border border-[#3dff8a]/20 bg-[#020617]/80 p-6 shadow-[inset_0_0_60px_rgba(61,255,138,0.06)] backdrop-blur-md lg:min-h-[28rem]">
      <div className="pointer-events-none absolute inset-0 opacity-30" aria-hidden>
        <svg className="h-full w-full" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
          <circle cx="200" cy="200" r="40" fill="none" stroke="rgba(61,255,138,0.35)" strokeWidth="1" />
          <circle cx="200" cy="200" r="80" fill="none" stroke="rgba(61,255,138,0.25)" strokeWidth="1" />
          <circle cx="200" cy="200" r="120" fill="none" stroke="rgba(61,255,138,0.18)" strokeWidth="1" />
          <circle cx="200" cy="200" r="160" fill="none" stroke="rgba(61,255,138,0.12)" strokeWidth="1" />
          <line x1="200" y1="40" x2="200" y2="360" stroke="rgba(61,255,138,0.15)" strokeWidth="0.5" />
          <line x1="40" y1="200" x2="360" y2="200" stroke="rgba(61,255,138,0.15)" strokeWidth="0.5" />
          <path
            d="M200 200 L360 120 A160 160 0 0 1 200 360 Z"
            fill="rgba(61,255,138,0.08)"
            className="origin-center motion-safe:animate-[spin_8s_linear_infinite] motion-reduce:animate-none"
            style={{ transformOrigin: '200px 200px' }}
          />
        </svg>
      </div>

      <div className="relative z-10 flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[#3dff8a]/80">
            Sonar · Live feed
          </p>
          <p className="mt-1 text-lg font-semibold text-slate-100">{fishingSceneLabel}</p>
        </div>
        {weatherMode === 'auto' ? (
          <button
            type="button"
            className="cursor-pointer rounded-lg border border-[#3dff8a]/35 bg-[#3dff8a]/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-[#5dff9a] transition-colors duration-200 hover:bg-[#3dff8a]/20"
            onClick={onRefreshWeather}
          >
            Ping
          </button>
        ) : null}
      </div>

      <div className="relative z-10 mt-6 grid flex-1 grid-cols-2 gap-3 content-start">
        <HudReadout label="Depth" value={depthDisplay} accent="amber" />
        <HudReadout
          label="Conditions"
          value={weatherMode === 'auto' ? 'Auto detect' : 'Manual'}
        />
        {weatherMode === 'auto' && autoWeatherRemoteStatus === 'loading' ? (
          <p className="col-span-2 animate-pulse text-sm text-slate-400 motion-reduce:animate-none">
            Scanning atmosphere…
          </p>
        ) : null}
        {weatherMode === 'auto' && autoWeatherRemoteStatus === 'success' && autoWeatherSnapshotPayload ? (
          <>
            <HudReadout
              label="Temp"
              value={`${autoWeatherSnapshotPayload.temperature_c.toFixed(1)}°C`}
            />
            <HudReadout label="Sky" value={autoWeatherSnapshotPayload.condition} />
            <HudReadout
              label="Wind"
              value={`${autoWeatherSnapshotPayload.wind_speed_ms.toFixed(1)} m/s`}
            />
            <HudReadout label="Pressure" value={`${autoWeatherSnapshotPayload.pressure_hpa} hPa`} />
          </>
        ) : null}
        {weatherMode === 'manual' ? (
          <>
            <HudReadout label="Temp" value={`${manualTemperatureCelsius}°C`} />
            <HudReadout label="Sky" value={manualConditionCode} />
          </>
        ) : null}
        {weatherMode === 'auto' && autoWeatherRemoteStatus === 'error' ? (
          <p className="col-span-2 text-sm text-amber-200/90">
            Signal lost — switch to manual or check region in mission parameters.
          </p>
        ) : null}
      </div>
    </div>
  )
}
