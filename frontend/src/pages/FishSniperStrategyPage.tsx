import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useNavigate, useOutletContext, useSearchParams } from 'react-router-dom'

import type {
  FishSniperStrategyTargetSpecies,
  GenerateBassStrategyRequestPayload,
} from '../api/fishSniperApiTypes.ts'
import type { FishSniperSignedInOutletContextValue } from '../layout/fishSniperSignedInOutletContext.ts'
import { useFishSniperAgentLlmModelsRemoteState } from '../hooks/useFishSniperAgentLlmModelsRemoteState.ts'
import { useFishSniperAutoWeatherSnapshotRemoteState } from '../hooks/useFishSniperAutoWeatherSnapshotRemoteState.ts'
import { useFishSniperSubmitBassStrategyMutation } from '../hooks/useFishSniperSubmitBassStrategyMutation.ts'
import { StrategySonarHudPanel } from '../strategy/console/StrategySonarHudPanel.tsx'
import { saveStrategyReportToSessionStorage } from '../strategy/strategyReportSessionStorage.ts'
import { FishSniperTacticalPageShell } from '../ui/FishSniperTacticalPageShell.tsx'
import {
  fishSniperTacticalErrorBannerClassName,
  fishSniperTacticalEyebrowClassName,
  fishSniperTacticalInputClassName,
  fishSniperTacticalMutedTextClassName,
  fishSniperTacticalOptionTileActiveClassName,
  fishSniperTacticalOptionTileBaseClassName,
  fishSniperTacticalOptionTileIdleClassName,
  fishSniperTacticalPageTitleClassName,
  fishSniperTacticalPrimaryButtonClassName,
  fishSniperTacticalSelectClassName,
  fishSniperTacticalWarningBannerClassName,
} from '../ui/fishSniperTacticalUi.ts'

const FISH_SNIPER_FISHING_SCENE_TAG_OPTIONS = ['river', 'lake', 'reservoir', 'pond'] as const

const FISH_SNIPER_MANUAL_CONDITION_CODE_OPTIONS = [
  'sunny',
  'cloudy',
  'rainy',
  'stormy',
  'snowy',
] as const

const FISH_SNIPER_TARGET_SPECIES_OPTIONS = ['Largemouth Bass', 'Smallmouth Bass'] as const

const TARGET_SPECIES_SHORT_LABEL: Record<FishSniperStrategyTargetSpecies, string> = {
  'Largemouth Bass': 'Largemouth',
  'Smallmouth Bass': 'Smallmouth',
}

function capitalizeSceneTag(scene: string): string {
  return scene.charAt(0).toUpperCase() + scene.slice(1)
}

function isFishSniperManualConditionCodeValue(
  value: string,
): value is (typeof FISH_SNIPER_MANUAL_CONDITION_CODE_OPTIONS)[number] {
  return (FISH_SNIPER_MANUAL_CONDITION_CODE_OPTIONS as readonly string[]).includes(value)
}

function MissionQuestion(options: { question: string; children: ReactNode }) {
  return (
    <div className="space-y-3">
      <h2 className="text-lg font-medium tracking-tight text-slate-100 sm:text-xl">
        {options.question}
      </h2>
      {options.children}
    </div>
  )
}

export function FishSniperStrategyPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const reportMissingNotice = searchParams.get('report') === 'missing'

  const { fishSniperApiBaseUrl, fishSniperAccessTokenJwt, userPreferences } =
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
    if (!userPreferences?.region) {
      return
    }
    setWeatherRegionInput((current) => (current.trim().length > 0 ? current : userPreferences.region ?? ''))
  }, [userPreferences?.region])

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
      saveStrategyReportToSessionStorage({
        successPayload: submitResult.successPayload,
        requestSummary: {
          region: requestPayload.region,
          fishing_location: requestPayload.fishing_location,
          fishing_scene: requestPayload.fishing_scene,
          target_species: requestPayload.target_species,
          water_depth_m: requestPayload.water_depth_m,
        },
      })
      navigate('/strategy/report')
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
    <FishSniperTacticalPageShell>
        <header className="mb-8 border-b border-[#3dff8a]/15 pb-8 lg:mb-10">
          <p className={fishSniperTacticalEyebrowClassName}>FishSniper · Tactical command</p>
          <h1 className={`mt-2 ${fishSniperTacticalPageTitleClassName}`}>Mission brief</h1>
          <p className={`mt-3 max-w-2xl ${fishSniperTacticalMutedTextClassName}`}>
            Set your water, target, and conditions — then deploy a full tactical readout.
          </p>
        </header>

        {reportMissingNotice ? (
          <p className={`mb-6 ${fishSniperTacticalMutedTextClassName} rounded-xl border border-slate-500/40 bg-black/40 px-4 py-3`}>
            No strategy report in this session. Deploy one below.
          </p>
        ) : null}

        {strategyHardErrorMessage ? (
          <p className={`mb-6 ${fishSniperTacticalErrorBannerClassName}`}>{strategyHardErrorMessage}</p>
        ) : null}

        {strategyFallbackMessage ? (
          <div className={`mb-6 ${fishSniperTacticalWarningBannerClassName}`}>
            <p className="font-semibold">Could not generate a strategy. Try adjusting your mission.</p>
            <p className="mt-1 text-xs text-amber-200/90">{strategyFallbackMessage}</p>
          </div>
        ) : null}

        {isSubmittingBassStrategy ? (
          <div className="mb-8 animate-pulse rounded-2xl border border-[#3dff8a]/20 bg-black/40 p-8 motion-reduce:animate-none">
            <p className="text-sm font-semibold uppercase tracking-widest text-[#5dff9a]">
              Deploying strategy…
            </p>
          </div>
        ) : null}

        <div
          className={
            isSubmittingBassStrategy
              ? 'pointer-events-none grid grid-cols-1 gap-8 opacity-50 lg:grid-cols-12 lg:gap-10'
              : 'grid grid-cols-1 gap-8 lg:grid-cols-12 lg:gap-10'
          }
        >
          <div className="flex flex-col gap-8 lg:col-span-5 xl:col-span-5">
            <MissionQuestion question="Where are you fishing?">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {FISH_SNIPER_FISHING_SCENE_TAG_OPTIONS.map((scene) => {
                  const isSelected = fishingSceneTag === scene
                  return (
                    <button
                      key={scene}
                      type="button"
                      className={`${fishSniperTacticalOptionTileBaseClassName} ${
                        isSelected ? fishSniperTacticalOptionTileActiveClassName : fishSniperTacticalOptionTileIdleClassName
                      }`}
                      onClick={() => setFishingSceneTag(scene)}
                    >
                      {capitalizeSceneTag(scene)}
                    </button>
                  )
                })}
              </div>
              <input
                className={fishSniperTacticalInputClassName}
                placeholder="Spot name — e.g. North shore dock"
                value={fishingLocationInput}
                aria-label="Fishing spot"
                onChange={(event) => setFishingLocationInput(event.target.value)}
              />
            </MissionQuestion>

            <MissionQuestion question="Target?">
              <div className="grid grid-cols-2 gap-3">
                {FISH_SNIPER_TARGET_SPECIES_OPTIONS.map((species) => {
                  const isSelected = targetSpeciesSelection === species
                  return (
                    <button
                      key={species}
                      type="button"
                      className={`${fishSniperTacticalOptionTileBaseClassName} py-4 text-base ${
                        isSelected ? fishSniperTacticalOptionTileActiveClassName : fishSniperTacticalOptionTileIdleClassName
                      }`}
                      onClick={() => setTargetSpeciesSelection(species)}
                    >
                      {TARGET_SPECIES_SHORT_LABEL[species]}
                    </button>
                  )
                })}
              </div>
            </MissionQuestion>

            <MissionQuestion question="Conditions?">
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  className={`${fishSniperTacticalOptionTileBaseClassName} py-4 ${
                    weatherMode === 'auto' ? fishSniperTacticalOptionTileActiveClassName : fishSniperTacticalOptionTileIdleClassName
                  }`}
                  onClick={() => setWeatherMode('auto')}
                >
                  Auto detect
                </button>
                <button
                  type="button"
                  className={`${fishSniperTacticalOptionTileBaseClassName} py-4 ${
                    weatherMode === 'manual' ? fishSniperTacticalOptionTileActiveClassName : fishSniperTacticalOptionTileIdleClassName
                  }`}
                  onClick={() => {
                    setWeatherMode('manual')
                    applyAutoSnapshotToManualWeatherFields()
                  }}
                >
                  Manual
                </button>
              </div>
            </MissionQuestion>

            <details className="group rounded-xl border border-white/10 bg-black/30 open:border-amber-500/25">
              <summary className="cursor-pointer list-none px-5 py-4 text-sm font-medium text-slate-300 transition-colors duration-200 hover:text-amber-200 [&::-webkit-details-marker]:hidden">
                <span className="uppercase tracking-[0.14em] text-amber-400/90">Mission parameters</span>
                <span className="mt-1 block text-xs text-slate-500 group-open:hidden">
                  Region, depth, model, manual weather
                </span>
              </summary>
              <div className="flex flex-col gap-4 border-t border-white/10 px-5 pb-5 pt-4">
                <label className="flex flex-col gap-1.5 text-xs font-medium text-slate-400">
                  Weather region
                  <input
                    className={fishSniperTacticalInputClassName}
                    placeholder="e.g. Austin, TX"
                    value={weatherRegionInput}
                    onChange={(event) => setWeatherRegionInput(event.target.value)}
                  />
                </label>
                <label className="flex flex-col gap-1.5 text-xs font-medium text-slate-400">
                  Water depth (m)
                  <input
                    className={fishSniperTacticalInputClassName}
                    inputMode="decimal"
                    value={waterDepthMetersInput}
                    onChange={(event) => setWaterDepthMetersInput(event.target.value)}
                  />
                </label>
                <label className="flex flex-col gap-1.5 text-xs font-medium text-slate-400">
                  Analysis model
                  <select
                    className={fishSniperTacticalSelectClassName}
                    value={selectedLlmModelId ?? ''}
                    disabled={
                      agentLlmModelsRemoteStatus === 'loading' ||
                      agentLlmModelsRemoteStatus === 'error' ||
                      (agentLlmModelsPayload?.models.length ?? 0) === 0
                    }
                    onChange={(event) => setSelectedLlmModelId(event.target.value)}
                  >
                    {agentLlmModelsPayload?.models.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.display_name}
                      </option>
                    ))}
                  </select>
                </label>
                {weatherMode === 'manual' ? (
                  <div className="grid grid-cols-2 gap-3">
                    <label className="col-span-2 flex flex-col gap-1.5 text-xs font-medium text-slate-400">
                      Temp (°C)
                      <input
                        className={fishSniperTacticalInputClassName}
                        inputMode="decimal"
                        value={manualTemperatureCelsius}
                        onChange={(event) => setManualTemperatureCelsius(event.target.value)}
                      />
                    </label>
                    <label className="col-span-2 flex flex-col gap-1.5 text-xs font-medium text-slate-400">
                      Sky
                      <select
                        className={fishSniperTacticalSelectClassName}
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
                    <label className="flex flex-col gap-1.5 text-xs font-medium text-slate-400">
                      Wind (m/s)
                      <input
                        className={fishSniperTacticalInputClassName}
                        inputMode="decimal"
                        value={manualWindSpeedMetersPerSecond}
                        onChange={(event) => setManualWindSpeedMetersPerSecond(event.target.value)}
                      />
                    </label>
                    <label className="flex flex-col gap-1.5 text-xs font-medium text-slate-400">
                      Pressure (hPa)
                      <input
                        className={fishSniperTacticalInputClassName}
                        inputMode="numeric"
                        value={manualPressureHectopascals}
                        onChange={(event) => setManualPressureHectopascals(event.target.value)}
                      />
                    </label>
                  </div>
                ) : null}
                {weatherMode === 'auto' && autoWeatherRemoteStatus === 'error' && autoWeatherLastHttpStatusCode === 503 ? (
                  <p className="text-xs leading-relaxed text-amber-200/90">
                    Auto weather unavailable — set region here or switch to manual conditions.
                  </p>
                ) : null}
              </div>
            </details>

            <button
              type="button"
              className={fishSniperTacticalPrimaryButtonClassName}
              disabled={!isFormReadyToSubmit || isSubmittingBassStrategy}
              onClick={() => void handleSubmitBassStrategyRequest()}
            >
              {isSubmittingBassStrategy ? 'Deploying…' : 'Generate strategy'}
            </button>
          </div>

          <div className="lg:col-span-7 xl:col-span-7">
            <StrategySonarHudPanel
              fishingSceneLabel={capitalizeSceneTag(fishingSceneTag)}
              waterDepthMeters={waterDepthMetersInput}
              weatherMode={weatherMode}
              autoWeatherRemoteStatus={autoWeatherRemoteStatus}
              autoWeatherSnapshotPayload={autoWeatherSnapshotPayload}
              manualTemperatureCelsius={manualTemperatureCelsius}
              manualConditionCode={manualConditionCode}
              onRefreshWeather={() => void reloadAutoWeatherSnapshot()}
            />
          </div>
        </div>
    </FishSniperTacticalPageShell>
  )
}
