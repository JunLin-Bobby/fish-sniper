import { useEffect, useMemo, useState } from 'react'
import { useOutletContext } from 'react-router-dom'

import type {
  FishSniperStrategyTargetSpecies,
  GenerateBassStrategyRequestPayload,
  GenerateBassStrategySuccessResponsePayload,
} from '../api/fishSniperApiTypes.ts'
import type { FishSniperSignedInOutletContextValue } from '../layout/fishSniperSignedInOutletContext.ts'
import { useFishSniperAgentLlmModelsRemoteState } from '../hooks/useFishSniperAgentLlmModelsRemoteState.ts'
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

const FISH_SNIPER_TARGET_SPECIES_OPTIONS = ['Largemouth Bass', 'Smallmouth Bass'] as const

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
  const [selectedLlmModelId, setSelectedLlmModelId] = useState<string | null>(null)
  const {
    agentLlmModelsRemoteStatus,
    agentLlmModelsPayload,
  } = useFishSniperAgentLlmModelsRemoteState({
    fishSniperApiBaseUrl,
    fishSniperAccessTokenJwt,
  })
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

  const [weatherRegionInput, setWeatherRegionInput] = useState('')
  const [fishingLocationInput, setFishingLocationInput] = useState('')
  const [waterDepthMetersInput, setWaterDepthMetersInput] = useState('1.5')
  const [fishingSceneTag, setFishingSceneTag] =
    useState<(typeof FISH_SNIPER_FISHING_SCENE_TAG_OPTIONS)[number]>('lake')
  const [targetSpeciesSelection, setTargetSpeciesSelection] =
    useState<FishSniperStrategyTargetSpecies>('Largemouth Bass')

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

  const isLlmModelSelectionReady =
    agentLlmModelsRemoteStatus === 'success' &&
    selectedLlmModelId !== null &&
    (agentLlmModelsPayload?.models.some((model) => model.id === selectedLlmModelId) ?? false)

  const isFormReadyToSubmit =
    weatherRegionInput.trim().length > 0 &&
    fishingLocationInput.trim().length > 0 &&
    isWaterDepthValid &&
    (weatherMode === 'auto' || isManualWeatherInputValid) &&
    isLlmModelSelectionReady

  useEffect(() => {
    if (agentLlmModelsRemoteStatus !== 'success' || !agentLlmModelsPayload) {
      return
    }
    const { models, default_model_id: defaultModelId } = agentLlmModelsPayload
    if (models.length === 0) {
      setSelectedLlmModelId(null)
      return
    }
    setSelectedLlmModelId((current) => {
      if (current !== null && models.some((model) => model.id === current)) {
        return current
      }
      if (models.some((model) => model.id === defaultModelId)) {
        return defaultModelId
      }
      return models[0]?.id ?? null
    })
  }, [agentLlmModelsRemoteStatus, agentLlmModelsPayload])

  const glassPanelClassName =
    'rounded-3xl border border-white/15 bg-white/[0.06] p-5 backdrop-blur-2xl shadow-[0_24px_70px_-34px_rgba(2,6,23,0.95)]'
  const sectionTitleClassName = 'text-xs font-semibold uppercase tracking-[0.18em] text-slate-300'
  const fieldLabelClassName = 'flex flex-col gap-1.5 text-xs font-medium text-slate-300'
  const inputClassName =
    'rounded-xl border border-slate-600/50 bg-slate-950/70 px-3 py-2.5 text-sm text-slate-100 outline-none transition-colors duration-200 placeholder:text-slate-500 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/25'
  const chipClassName =
    'inline-flex items-center rounded-full border border-white/15 bg-slate-900/70 px-2.5 py-1 text-[11px] font-medium text-slate-300'
  const headerMetaLabelClassName = 'text-sm font-semibold text-slate-100 sm:text-base'
  const headerSelectClassName =
    'min-w-[10.5rem] cursor-pointer rounded-xl border border-white/20 bg-slate-950/80 px-3 py-2 text-sm font-medium text-slate-100 outline-none transition-colors duration-200 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/25 sm:min-w-[12rem] sm:text-base'

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
      region: weatherRegionInput.trim(),
      fishing_location: fishingLocationInput.trim(),
      water_depth_m: parsedWaterDepthMeters,
      fishing_scene: fishingSceneTag,
      target_species: targetSpeciesSelection,
    }

    if (weatherMode === 'manual') {
      requestPayload.manual_weather = {
        temperature_c: parsedManualTemperatureCelsius,
        condition_code: manualConditionCode,
        wind_speed_ms: parsedManualWindMetersPerSecond,
        pressure_hpa: parsedManualPressureHectopascals,
      }
    }

    if (selectedLlmModelId) {
      requestPayload.llm_model_id = selectedLlmModelId
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
    <div className="relative isolate mx-auto w-full max-w-6xl overflow-hidden rounded-[2rem] border border-white/10 bg-[#020617] px-4 py-5 sm:px-6">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_8%_10%,rgba(16,185,129,0.2),transparent_36%),radial-gradient(circle_at_90%_8%,rgba(56,189,248,0.18),transparent_38%),radial-gradient(circle_at_80%_90%,rgba(99,102,241,0.14),transparent_42%)]" />
      <header className={`${glassPanelClassName} mb-5`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-2">
            <p className={chipClassName}>FishSniper Control Room</p>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-50 sm:text-3xl">Bass Strategy Console</h1>
            <p className="max-w-2xl text-sm text-slate-300/90">
              Keep your existing inputs, run a fresh weather-aware strategy, and get a clean tactical output.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-4 sm:gap-6">
            <span className={headerMetaLabelClassName}>
              {weatherMode === 'auto' ? 'Weather: Auto' : 'Weather: Manual'}
            </span>
            <label className={`flex items-center gap-2.5 ${headerMetaLabelClassName}`}>
              <span className="shrink-0">Model:</span>
              <select
                className={headerSelectClassName}
                value={selectedLlmModelId ?? ''}
                disabled={
                  agentLlmModelsRemoteStatus === 'loading' ||
                  agentLlmModelsRemoteStatus === 'error' ||
                  (agentLlmModelsPayload?.models.length ?? 0) === 0
                }
                onChange={(event) => setSelectedLlmModelId(event.target.value)}
                aria-label="Strategy LLM model"
              >
                {agentLlmModelsRemoteStatus === 'loading' ? (
                  <option value="">Loading models…</option>
                ) : null}
                {agentLlmModelsRemoteStatus === 'error' ? (
                  <option value="">Models unavailable</option>
                ) : null}
                {agentLlmModelsRemoteStatus === 'success' &&
                agentLlmModelsPayload &&
                agentLlmModelsPayload.models.length === 0 ? (
                  <option value="">No models configured</option>
                ) : null}
                {agentLlmModelsPayload?.models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.display_name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
        <div className="space-y-5">
          <section className={`${glassPanelClassName} space-y-4`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className={sectionTitleClassName}>Weather Source</h2>
              {weatherMode === 'auto' ? (
                <button
                  type="button"
                  className="cursor-pointer rounded-lg border border-emerald-400/45 bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-200 transition-colors duration-200 hover:bg-emerald-500/25"
                  onClick={() => void reloadAutoWeatherSnapshot()}
                >
                  Refresh
                </button>
              ) : null}
            </div>

            <div className="flex flex-wrap gap-2.5 text-xs text-slate-200">
              <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-white/15 bg-slate-900/70 px-3 py-2 transition-colors duration-200 hover:border-emerald-400/45">
                <input
                  type="radio"
                  name="fish-sniper-weather-mode"
                  checked={weatherMode === 'auto'}
                  onChange={() => setWeatherMode('auto')}
                />
                Auto (profile region)
              </label>
              <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-white/15 bg-slate-900/70 px-3 py-2 transition-colors duration-200 hover:border-emerald-400/45">
                <input
                  type="radio"
                  name="fish-sniper-weather-mode"
                  checked={weatherMode === 'manual'}
                  onChange={() => {
                    setWeatherMode('manual')
                    applyAutoSnapshotToManualWeatherFields()
                  }}
                />
                Manual (overrides Auto)
              </label>
            </div>

            {weatherMode === 'auto' ? (
              <div className="rounded-2xl border border-white/10 bg-slate-950/55 p-4 text-sm">
                {autoWeatherRemoteStatus === 'loading' ? (
                  <p className="animate-pulse text-slate-400">Loading weather…</p>
                ) : null}
                {autoWeatherRemoteStatus === 'success' && autoWeatherSnapshotPayload ? (
                  <ul className="space-y-1.5 text-slate-200">
                    <li>
                      {autoWeatherSnapshotPayload.temperature_c.toFixed(1)}°C —{' '}
                      {autoWeatherSnapshotPayload.condition}
                    </li>
                    <li>
                      Wind {autoWeatherSnapshotPayload.wind_speed_ms.toFixed(1)} m/s · Pressure{' '}
                      {autoWeatherSnapshotPayload.pressure_hpa} hPa · Humidity{' '}
                      {autoWeatherSnapshotPayload.humidity_pct}%
                    </li>
                    <li className="text-xs text-slate-400">
                      Updated {formatIsoTimestampForDisplay(autoWeatherSnapshotPayload.fetched_at)}
                    </li>
                  </ul>
                ) : null}
                {autoWeatherRemoteStatus === 'error' ? (
                  <div className="space-y-2 text-amber-100">
                    <p>Weather could not be loaded.</p>
                    {autoWeatherLastHttpStatusCode === 503 ? (
                      <p className="text-xs text-slate-400">
                        Switch to Manual and enter conditions, or fix the region in profile.
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2.5 text-sm">
                <label className={`${fieldLabelClassName} col-span-2`}>
                  Temp (°C)
                  <input
                    className={inputClassName}
                    inputMode="decimal"
                    value={manualTemperatureCelsius}
                    onChange={(event) => setManualTemperatureCelsius(event.target.value)}
                  />
                </label>
                <label className={`${fieldLabelClassName} col-span-2`}>
                  Condition code
                  <select
                    className={inputClassName}
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
                <label className={fieldLabelClassName}>
                  Wind (m/s)
                  <input
                    className={inputClassName}
                    inputMode="decimal"
                    value={manualWindSpeedMetersPerSecond}
                    onChange={(event) => setManualWindSpeedMetersPerSecond(event.target.value)}
                  />
                </label>
                <label className={fieldLabelClassName}>
                  Pressure (hPa)
                  <input
                    className={inputClassName}
                    inputMode="numeric"
                    value={manualPressureHectopascals}
                    onChange={(event) => setManualPressureHectopascals(event.target.value)}
                  />
                </label>
              </div>
            )}
          </section>

          <section className={`${glassPanelClassName} space-y-3.5`}>
            <h2 className={sectionTitleClassName}>Location Input</h2>
            <label className={fieldLabelClassName}>
              Weather region (for OpenWeatherMap)
              <input
                className={inputClassName}
                placeholder="e.g. Austin, TX"
                value={weatherRegionInput}
                onChange={(event) => setWeatherRegionInput(event.target.value)}
              />
            </label>
            <label className={fieldLabelClassName}>
              Fishing location
              <input
                className={inputClassName}
                placeholder="e.g. North shore dock"
                value={fishingLocationInput}
                onChange={(event) => setFishingLocationInput(event.target.value)}
              />
            </label>
            <label className={fieldLabelClassName}>
              Water depth (m)
              <input
                className={inputClassName}
                inputMode="decimal"
                value={waterDepthMetersInput}
                onChange={(event) => setWaterDepthMetersInput(event.target.value)}
              />
            </label>
            <div className="grid gap-2.5 sm:grid-cols-2">
              <label className={fieldLabelClassName}>
                Scene
                <select
                  className={inputClassName}
                  value={fishingSceneTag}
                  onChange={(event) =>
                    setFishingSceneTag(
                      event.target.value as (typeof FISH_SNIPER_FISHING_SCENE_TAG_OPTIONS)[number],
                    )
                  }
                >
                  {FISH_SNIPER_FISHING_SCENE_TAG_OPTIONS.map((scene) => (
                    <option key={scene} value={scene}>
                      {scene}
                    </option>
                  ))}
                </select>
              </label>
              <label className={fieldLabelClassName}>
                Target species
                <select
                  className={inputClassName}
                  value={targetSpeciesSelection}
                  onChange={(event) =>
                    setTargetSpeciesSelection(event.target.value as FishSniperStrategyTargetSpecies)
                  }
                >
                  {FISH_SNIPER_TARGET_SPECIES_OPTIONS.map((species) => (
                    <option key={species} value={species}>
                      {species}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </section>

          <button
            type="button"
            className="w-full cursor-pointer rounded-2xl bg-emerald-500 py-3 text-sm font-semibold text-slate-950 shadow-[0_14px_40px_-18px_rgba(16,185,129,0.95)] transition-colors duration-200 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!isFormReadyToSubmit || isSubmittingBassStrategy}
            onClick={() => void handleSubmitBassStrategyRequest()}
          >
            {isSubmittingBassStrategy ? 'Sniping…' : 'Snipe it'}
          </button>
        </div>

        <aside className="space-y-4">
          {strategyHardErrorMessage ? (
            <p className="rounded-2xl border border-rose-500/45 bg-rose-950/30 px-4 py-3 text-sm text-rose-100 backdrop-blur-md">
              {strategyHardErrorMessage}
            </p>
          ) : null}

          {strategyFallbackMessage ? (
            <div className="rounded-2xl border border-amber-500/45 bg-amber-950/30 p-4 text-sm text-amber-100 backdrop-blur-md">
              <p className="font-semibold">Could not generate a strategy. Try adjusting your input.</p>
              <p className="mt-1 text-xs text-amber-200/90">{strategyFallbackMessage}</p>
            </div>
          ) : null}

          {isSubmittingBassStrategy ? (
            <div className="min-h-[260px] animate-pulse space-y-3 rounded-3xl border border-white/15 bg-white/[0.06] p-5 backdrop-blur-2xl">
              <div className="h-4 w-2/3 rounded bg-slate-700/80" />
              <div className="h-4 w-full rounded bg-slate-700/80" />
              <div className="h-4 w-5/6 rounded bg-slate-700/80" />
              <div className="h-4 w-4/6 rounded bg-slate-700/80" />
            </div>
          ) : null}

          {strategySuccessPayload && !isSubmittingBassStrategy ? (
            <div className="min-h-[260px] space-y-4 rounded-3xl border border-white/15 bg-white/[0.06] p-5 backdrop-blur-2xl shadow-[0_24px_70px_-34px_rgba(2,6,23,0.95)]">
              <h2 className="text-sm font-semibold text-emerald-300">Your plan</h2>
              <p className="text-xs text-slate-400">
                Seven tiles: fish mood, three lure picks, three retrieve notes (primary → tertiary).
              </p>
              {strategySuccessPayload.referenced_log ? (
                <div
                  className={`${glassPanelClassName} !p-4 border-sky-500/25 bg-sky-950/25 sm:col-span-3`}
                >
                  <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-sky-200/90">
                    Reference log
                  </h3>
                  <p className="text-sm leading-relaxed text-slate-100">
                    This run used your{' '}
                    <span className="font-medium text-slate-50">
                      {strategySuccessPayload.referenced_log.log_date}
                    </span>{' '}
                    trip at{' '}
                    <span className="font-medium text-slate-50">
                      {strategySuccessPayload.referenced_log.fishing_location}
                    </span>
                    : {strategySuccessPayload.referenced_log.lure_type} /{' '}
                    {strategySuccessPayload.referenced_log.lure_color},{' '}
                    {strategySuccessPayload.referenced_log.retrieve_speed},{' '}
                    {strategySuccessPayload.referenced_log.caught_count} fish caught.
                  </p>
                </div>
              ) : null}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div
                  className={`${glassPanelClassName} !p-4 sm:col-span-3 border-emerald-500/20 bg-emerald-950/20`}
                >
                  <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-emerald-200/90">
                    Fish state today
                  </h3>
                  <p className="text-sm leading-relaxed text-slate-100">{strategySuccessPayload.fish_state}</p>
                </div>
                {strategySuccessPayload.recommendations.map((rec, index) => (
                  <div key={`lure-${index}`} className={`${glassPanelClassName} !p-4`}>
                    <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                      Lure {index + 1}
                    </h3>
                    <p className="text-sm font-medium text-slate-50">{rec.lure_type}</p>
                    <p className="mt-1 text-xs text-slate-400">{rec.lure_color}</p>
                  </div>
                ))}
                {strategySuccessPayload.recommendations.map((rec, index) => (
                  <div key={`tech-${index}`} className={`${glassPanelClassName} !p-4`}>
                    <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                      Technique {index + 1}
                    </h3>
                    <p className="text-sm leading-relaxed text-slate-200">{rec.retrieve_technique}</p>
                  </div>
                ))}
              </div>
              <p className="text-sm text-slate-300">{strategySuccessPayload.confidence_note}</p>
              <p className="text-xs text-slate-500">
                Generated {formatIsoTimestampForDisplay(strategySuccessPayload.generated_at)} · RAG logs{' '}
                {strategySuccessPayload.rag_logs_used}
              </p>
            </div>
          ) : (
            !isSubmittingBassStrategy &&
            !strategyFallbackMessage &&
            !strategyHardErrorMessage && (
              <div className="min-h-[260px] rounded-3xl border border-dashed border-white/20 bg-slate-900/40 p-5 text-sm text-slate-400 backdrop-blur-xl">
                Enter your spot and tap Snipe it for today&apos;s strategy.
              </div>
            )
          )}
        </aside>
      </div>
    </div>
  )
}
