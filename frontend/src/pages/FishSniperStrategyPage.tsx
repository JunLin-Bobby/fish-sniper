import { useMemo, useState } from 'react'
import { useOutletContext } from 'react-router-dom'

import { FishSniperBattlePlanMarkdownSection } from '../components/FishSniperBattlePlanMarkdownSection.tsx'
import type {
  GenerateBassStrategyRequestPayload,
  GenerateBassStrategySuccessResponsePayload,
} from '../api/fishSniperApiTypes.ts'
import type { FishSniperSignedInOutletContextValue } from '../layout/fishSniperSignedInOutletContext.ts'
import { useFishSniperAutoWeatherSnapshotRemoteState } from '../hooks/useFishSniperAutoWeatherSnapshotRemoteState.ts'
import { useFishSniperSubmitBassStrategyMutation } from '../hooks/useFishSniperSubmitBassStrategyMutation.ts'

const FISH_SNIPER_FISHING_SCENE_TAG_OPTIONS = ['river', 'lake', 'reservoir', 'pond'] as const

const FISH_SNIPER_MANUAL_CONDITION_CODE_OPTIONS = [
  'sunny',
  'cloudy',
  'rainy',
  'stormy',
  'snowy',
] as const

function isFishSniperManualConditionCodeValue(
  value: string,
): value is (typeof FISH_SNIPER_MANUAL_CONDITION_CODE_OPTIONS)[number] {
  return (FISH_SNIPER_MANUAL_CONDITION_CODE_OPTIONS as readonly string[]).includes(value)
}

function formatIsoTimestampForDisplay(isoTimestamp: string): string {
  const parsed = Date.parse(isoTimestamp)
  if (Number.isNaN(parsed)) {
    return isoTimestamp
  }
  return new Date(parsed).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function FishSniperStrategyPage() {
  const { fishSniperApiBaseUrl, fishSniperAccessTokenJwt } =
    useOutletContext<FishSniperSignedInOutletContextValue>()

  const [weatherMode, setWeatherMode] = useState<'auto' | 'manual'>('auto')
  const {
    autoWeatherRemoteStatus,
    autoWeatherSnapshotPayload,
    autoWeatherLastHttpStatusCode,
    reloadAutoWeatherSnapshot,
  } = useFishSniperAutoWeatherSnapshotRemoteState({
    fishSniperApiBaseUrl,
    fishSniperAccessTokenJwt,
    isAutoWeatherEnabled: weatherMode === 'auto',
  })

  const [fishingLocationInput, setFishingLocationInput] = useState('')
  const [waterDepthMetersInput, setWaterDepthMetersInput] = useState('1.5')
  const [fishingSceneTag, setFishingSceneTag] =
    useState<(typeof FISH_SNIPER_FISHING_SCENE_TAG_OPTIONS)[number]>('lake')
  const [targetSpeciesInput, setTargetSpeciesInput] = useState('bass')

  const [manualTemperatureCelsius, setManualTemperatureCelsius] = useState('18')
  const [manualConditionCode, setManualConditionCode] =
    useState<(typeof FISH_SNIPER_MANUAL_CONDITION_CODE_OPTIONS)[number]>('cloudy')
  const [manualWindSpeedMetersPerSecond, setManualWindSpeedMetersPerSecond] = useState('3')
  const [manualPressureHectopascals, setManualPressureHectopascals] = useState('1013')

  const { submitBassStrategyRequest, isSubmittingBassStrategy } =
    useFishSniperSubmitBassStrategyMutation({
      fishSniperApiBaseUrl,
      fishSniperAccessTokenJwt,
    })

  const [strategySuccessPayload, setStrategySuccessPayload] =
    useState<GenerateBassStrategySuccessResponsePayload | null>(null)
  const [strategyFallbackMessage, setStrategyFallbackMessage] = useState<string | null>(null)
  const [strategyHardErrorMessage, setStrategyHardErrorMessage] = useState<string | null>(null)

  const parsedWaterDepthMeters = useMemo(() => Number.parseFloat(waterDepthMetersInput), [waterDepthMetersInput])
  const isWaterDepthValid = Number.isFinite(parsedWaterDepthMeters) && parsedWaterDepthMeters >= 0

  const parsedManualTemperatureCelsius = Number.parseFloat(manualTemperatureCelsius)
  const parsedManualWindMetersPerSecond = Number.parseFloat(manualWindSpeedMetersPerSecond)
  const parsedManualPressureHectopascals = Number.parseInt(manualPressureHectopascals, 10)
  const isManualWeatherInputValid =
    Number.isFinite(parsedManualTemperatureCelsius) &&
    Number.isFinite(parsedManualWindMetersPerSecond) &&
    Number.isFinite(parsedManualPressureHectopascals) &&
    parsedManualPressureHectopascals > 0

  const isFormReadyToSubmit =
    fishingLocationInput.trim().length > 0 &&
    isWaterDepthValid &&
    targetSpeciesInput.trim().length > 0 &&
    (weatherMode === 'auto' || isManualWeatherInputValid)

  function applyAutoSnapshotToManualWeatherFields(): void {
    if (!autoWeatherSnapshotPayload) {
      return
    }
    setManualTemperatureCelsius(String(autoWeatherSnapshotPayload.temperature_c))
    const snapshotConditionCode = autoWeatherSnapshotPayload.condition_code
    setManualConditionCode(
      isFishSniperManualConditionCodeValue(snapshotConditionCode) ? snapshotConditionCode : 'cloudy',
    )
    setManualWindSpeedMetersPerSecond(String(autoWeatherSnapshotPayload.wind_speed_ms))
    setManualPressureHectopascals(String(autoWeatherSnapshotPayload.pressure_hpa))
  }

  async function handleSubmitBassStrategyRequest(): Promise<void> {
    setStrategySuccessPayload(null)
    setStrategyFallbackMessage(null)
    setStrategyHardErrorMessage(null)

    const requestPayload: GenerateBassStrategyRequestPayload = {
      fishing_location: fishingLocationInput.trim(),
      water_depth_m: parsedWaterDepthMeters,
      fishing_scene: fishingSceneTag,
      target_species: targetSpeciesInput.trim(),
    }

    if (weatherMode === 'manual') {
      requestPayload.manual_weather = {
        temperature_c: parsedManualTemperatureCelsius,
        condition_code: manualConditionCode,
        wind_speed_ms: parsedManualWindMetersPerSecond,
        pressure_hpa: parsedManualPressureHectopascals,
      }
    }

    const submitResult = await submitBassStrategyRequest(requestPayload)

    if (submitResult.outcome === 'success') {
      setStrategySuccessPayload(submitResult.successPayload)
      return
    }
    if (submitResult.outcome === 'fallback') {
      setStrategyFallbackMessage(submitResult.fallbackPayload.message)
      return
    }
    if (submitResult.outcome === 'http_error') {
      setStrategyHardErrorMessage(submitResult.userVisibleMessage)
      return
    }
    setStrategyHardErrorMessage('Could not read the strategy response. Please try again.')
  }

  return (
    <div className="mx-auto flex w-full max-w-lg flex-col gap-6 pb-8">
      <div>
        <h1 className="text-xl font-semibold text-gray-100">Strategy</h1>
        <p className="mt-1 text-sm text-gray-500">
          Enter your spot and tap Snipe it for today&apos;s strategy.
        </p>
      </div>

      <section className="space-y-2 rounded-md border border-gray-800 bg-gray-900/30 p-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-gray-200">Weather</h2>
          {weatherMode === 'auto' ? (
            <button
              type="button"
              className="text-xs text-emerald-400 hover:text-emerald-300"
              onClick={() => void reloadAutoWeatherSnapshot()}
            >
              Refresh
            </button>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-3 text-xs text-gray-400">
          <label className="flex cursor-pointer items-center gap-1.5">
            <input
              type="radio"
              name="fish-sniper-weather-mode"
              checked={weatherMode === 'auto'}
              onChange={() => setWeatherMode('auto')}
            />
            Auto (profile region)
          </label>
          <label className="flex cursor-pointer items-center gap-1.5">
            <input
              type="radio"
              name="fish-sniper-weather-mode"
              checked={weatherMode === 'manual'}
              onChange={() => {
                setWeatherMode('manual')
                applyAutoSnapshotToManualWeatherFields()
              }}
            />
            Manual
          </label>
        </div>

        {weatherMode === 'auto' ? (
          <div className="text-sm">
            {autoWeatherRemoteStatus === 'loading' ? (
              <p className="animate-pulse text-gray-500">Loading weather…</p>
            ) : null}
            {autoWeatherRemoteStatus === 'success' && autoWeatherSnapshotPayload ? (
              <ul className="space-y-1 text-gray-300">
                <li>
                  {autoWeatherSnapshotPayload.temperature_c.toFixed(1)}°C —{' '}
                  {autoWeatherSnapshotPayload.condition}
                </li>
                <li>
                  Wind {autoWeatherSnapshotPayload.wind_speed_ms.toFixed(1)} m/s · Pressure{' '}
                  {autoWeatherSnapshotPayload.pressure_hpa} hPa · Humidity{' '}
                  {autoWeatherSnapshotPayload.humidity_pct}%
                </li>
                <li className="text-xs text-gray-500">
                  Updated {formatIsoTimestampForDisplay(autoWeatherSnapshotPayload.fetched_at)}
                </li>
              </ul>
            ) : null}
            {autoWeatherRemoteStatus === 'error' ? (
              <div className="space-y-2 text-amber-200/90">
                <p>Weather could not be loaded.</p>
                {autoWeatherLastHttpStatusCode === 503 ? (
                  <p className="text-xs text-gray-400">
                    Try switching to Manual and enter conditions, or check your region in profile.
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2 text-sm">
            <label className="col-span-2 flex flex-col gap-1 text-xs text-gray-500">
              Temp (°C)
              <input
                className="rounded-md border border-gray-800 bg-gray-950 px-2 py-1.5 text-gray-100 outline-none focus:border-emerald-500"
                inputMode="decimal"
                value={manualTemperatureCelsius}
                onChange={(event) => setManualTemperatureCelsius(event.target.value)}
              />
            </label>
            <label className="col-span-2 flex flex-col gap-1 text-xs text-gray-500">
              Condition code
              <select
                className="rounded-md border border-gray-800 bg-gray-950 px-2 py-1.5 text-gray-100 outline-none focus:border-emerald-500"
                value={manualConditionCode}
                onChange={(event) =>
                  setManualConditionCode(
                    event.target.value as (typeof FISH_SNIPER_MANUAL_CONDITION_CODE_OPTIONS)[number],
                  )
                }
              >
                {FISH_SNIPER_MANUAL_CONDITION_CODE_OPTIONS.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-gray-500">
              Wind (m/s)
              <input
                className="rounded-md border border-gray-800 bg-gray-950 px-2 py-1.5 text-gray-100 outline-none focus:border-emerald-500"
                inputMode="decimal"
                value={manualWindSpeedMetersPerSecond}
                onChange={(event) => setManualWindSpeedMetersPerSecond(event.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-gray-500">
              Pressure (hPa)
              <input
                className="rounded-md border border-gray-800 bg-gray-950 px-2 py-1.5 text-gray-100 outline-none focus:border-emerald-500"
                inputMode="numeric"
                value={manualPressureHectopascals}
                onChange={(event) => setManualPressureHectopascals(event.target.value)}
              />
            </label>
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-200">Today&apos;s spot</h2>
        <label className="flex flex-col gap-1 text-xs text-gray-500">
          Fishing location
          <input
            className="rounded-md border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-100 outline-none focus:border-emerald-500"
            placeholder="e.g. North shore dock"
            value={fishingLocationInput}
            onChange={(event) => setFishingLocationInput(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-gray-500">
          Water depth (m)
          <input
            className="rounded-md border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-100 outline-none focus:border-emerald-500"
            inputMode="decimal"
            value={waterDepthMetersInput}
            onChange={(event) => setWaterDepthMetersInput(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-gray-500">
          Scene
          <select
            className="rounded-md border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-100 outline-none focus:border-emerald-500"
            value={fishingSceneTag}
            onChange={(event) =>
              setFishingSceneTag(event.target.value as (typeof FISH_SNIPER_FISHING_SCENE_TAG_OPTIONS)[number])
            }
          >
            {FISH_SNIPER_FISHING_SCENE_TAG_OPTIONS.map((scene) => (
              <option key={scene} value={scene}>
                {scene}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-gray-500">
          Target species
          <input
            className="rounded-md border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-100 outline-none focus:border-emerald-500"
            value={targetSpeciesInput}
            onChange={(event) => setTargetSpeciesInput(event.target.value)}
          />
        </label>
      </section>

      <button
        type="button"
        className="w-full rounded-md bg-emerald-500 py-2.5 text-sm font-semibold text-gray-950 hover:bg-emerald-400 disabled:opacity-50"
        disabled={!isFormReadyToSubmit || isSubmittingBassStrategy}
        onClick={() => void handleSubmitBassStrategyRequest()}
      >
        {isSubmittingBassStrategy ? 'Sniping…' : 'Snipe it'}
      </button>

      {strategyHardErrorMessage ? (
        <p className="text-sm text-red-400">{strategyHardErrorMessage}</p>
      ) : null}

      {strategyFallbackMessage ? (
        <div className="rounded-md border border-amber-900/50 bg-amber-950/20 p-3 text-sm text-amber-100">
          <p className="font-semibold">Could not generate a strategy. Try adjusting your input.</p>
          <p className="mt-1 text-xs text-amber-200/80">{strategyFallbackMessage}</p>
        </div>
      ) : null}

      {isSubmittingBassStrategy ? (
        <div className="animate-pulse space-y-2 rounded-md border border-gray-800 bg-gray-900/20 p-3">
          <div className="h-4 w-2/3 rounded bg-gray-800" />
          <div className="h-4 w-full rounded bg-gray-800" />
          <div className="h-4 w-5/6 rounded bg-gray-800" />
        </div>
      ) : null}

      {strategySuccessPayload && !isSubmittingBassStrategy ? (
        <div className="space-y-4 rounded-md border border-gray-800 bg-gray-900/20 p-4">
          <h2 className="text-sm font-semibold text-emerald-300">Your plan</h2>
          <dl className="grid grid-cols-1 gap-2 text-sm text-gray-300 sm:grid-cols-2">
            <div>
              <dt className="text-xs text-gray-500">Lure</dt>
              <dd>
                {strategySuccessPayload.lure_type} · {strategySuccessPayload.lure_color}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500">Retrieve</dt>
              <dd>{strategySuccessPayload.retrieve_speed}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500">Target zone</dt>
              <dd>{strategySuccessPayload.target_zone}</dd>
            </div>
            <div>
              <dt className="text-xs text-gray-500">Time window</dt>
              <dd>{strategySuccessPayload.time_window}</dd>
            </div>
          </dl>
          <p className="text-sm text-gray-400">{strategySuccessPayload.confidence_note}</p>
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
              Battle plan
            </h3>
            <FishSniperBattlePlanMarkdownSection
              battlePlanMarkdown={strategySuccessPayload.battle_plan_summary}
            />
          </div>
          <p className="text-xs text-gray-600">
            Generated {formatIsoTimestampForDisplay(strategySuccessPayload.generated_at)} · RAG logs{' '}
            {strategySuccessPayload.rag_logs_used}
          </p>
        </div>
      ) : null}
    </div>
  )
}
