import { useCallback, useEffect, useMemo, useState } from 'react'
import { useOutletContext } from 'react-router-dom'

import type {
  CreateOrUpdateFishingLogRequestPayload,
  CurrentWeatherResponsePayload,
  FishingLogResponsePayload,
  FishSniperStrategyTargetSpecies,
} from '../api/fishSniperApiTypes.ts'
import {
  deleteFishSniperFishingLog,
  getFishSniperFishingLogsListWithEtag,
  patchFishSniperFishingLog,
  postFishSniperFishingLog,
} from '../api/fishSniperFishingLogsHttpClient.ts'
import { getJsonWithFishSniperApi } from '../api/fishSniperJsonHttpClient.ts'
import fishSniperLureColorsCatalogJson from '../data/fishSniperLureColors.json'
import fishSniperLureTypesCatalogJson from '../data/fishSniperLureTypes.json'
import {
  findLureSelectionForStoredSubCategoryName,
  getLureSubCategoryNameFromSelection,
  isLureColorNameInCatalog,
  type FishSniperLureColorsFileShape,
  type FishSniperLureTypesFileShape,
} from '../fishSniperLogs/fishSniperLureAndColorCatalog.ts'
import {
  invalidateFishSniperLogsListCacheInSessionStorage,
  readFishSniperLogsListCacheFromSessionStorage,
  writeFishSniperLogsListCacheToSessionStorage,
} from '../fishSniperLogs/fishSniperLogsListSessionCache.ts'
import {
  validateFishSniperMyLogForm,
  type FishSniperMyLogFormFieldErrorKey,
} from '../fishSniperLogs/fishSniperMyLogFormValidation.ts'
import type { FishSniperSignedInOutletContextValue } from '../layout/fishSniperSignedInOutletContext.ts'

const fishSniperLureTypesCatalogForMyLogForm: FishSniperLureTypesFileShape = fishSniperLureTypesCatalogJson
const fishSniperLureColorsCatalogForMyLogForm: FishSniperLureColorsFileShape = fishSniperLureColorsCatalogJson

const FISH_SNIPER_FISHING_SCENE_TAG_OPTIONS = ['river', 'lake', 'reservoir', 'pond'] as const

const FISH_SNIPER_CONDITION_CODE_OPTIONS = [
  'sunny',
  'cloudy',
  'rainy',
  'stormy',
  'snowy',
] as const

const FISH_SNIPER_LOG_TARGET_SPECIES_OPTIONS: readonly FishSniperStrategyTargetSpecies[] = [
  'Largemouth Bass',
  'Smallmouth Bass',
]

const FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME =
  'text-sm font-extrabold tracking-tight text-fuchsia-200 [text-shadow:0_0_22px_rgba(240,171,252,0.95),0_0_10px_rgba(244,63,94,0.65)]'

const FISH_SNIPER_MY_LOG_BANNER_ERROR_CLASS_NAME =
  'rounded-2xl border border-fuchsia-400/70 bg-fuchsia-950/45 px-4 py-3 text-sm font-semibold text-fuchsia-100 [text-shadow:0_0_18px_rgba(232,121,249,0.55)]'

function isFishSniperStrategyTargetSpeciesValue(
  value: string,
): value is FishSniperStrategyTargetSpecies {
  return (FISH_SNIPER_LOG_TARGET_SPECIES_OPTIONS as readonly string[]).includes(value)
}

function isFishSniperConditionCodeValue(
  value: string,
): value is (typeof FISH_SNIPER_CONDITION_CODE_OPTIONS)[number] {
  return (FISH_SNIPER_CONDITION_CODE_OPTIONS as readonly string[]).includes(value)
}

function formatLogDateForDisplay(isoDate: string): string {
  const parsed = Date.parse(isoDate)
  if (Number.isNaN(parsed)) {
    return isoDate
  }
  return new Date(parsed).toLocaleDateString(undefined, { dateStyle: 'medium' })
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

export function FishSniperMyLogsPage() {
  const { fishSniperApiBaseUrl, fishSniperAccessTokenJwt } =
    useOutletContext<FishSniperSignedInOutletContextValue>()

  const glassPanelClassName =
    'rounded-3xl border border-white/15 bg-white/[0.06] p-5 backdrop-blur-2xl shadow-[0_24px_70px_-34px_rgba(2,6,23,0.95)]'
  const sectionTitleClassName = 'text-xs font-semibold uppercase tracking-[0.18em] text-slate-300'
  const fieldLabelClassName = 'flex flex-col gap-1.5 text-xs font-medium text-slate-300'
  const inputClassName =
    'rounded-xl border border-slate-600/50 bg-slate-950/70 px-3 py-2.5 text-sm text-slate-100 outline-none transition-colors duration-200 placeholder:text-slate-500 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/25'
  const chipClassName =
    'inline-flex items-center rounded-full border border-white/15 bg-slate-900/70 px-2.5 py-1 text-[11px] font-medium text-slate-300'

  const [logs, setLogs] = useState<FishingLogResponsePayload[]>([])
  const [listLoadStatus, setListLoadStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const [listErrorMessage, setListErrorMessage] = useState<string | null>(null)

  const [expandedLogId, setExpandedLogId] = useState<string | null>(null)

  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingLog, setEditingLog] = useState<FishingLogResponsePayload | null>(null)
  const [formSubmitError, setFormSubmitError] = useState<string | null>(null)
  const [isSavingLog, setIsSavingLog] = useState(false)
  const [logFormSubmitAttempted, setLogFormSubmitAttempted] = useState(false)

  const [logDateInput, setLogDateInput] = useState('')
  const [fishingLocationInput, setFishingLocationInput] = useState('')
  const [waterDepthMetersInput, setWaterDepthMetersInput] = useState('1.5')
  const [fishingSceneTag, setFishingSceneTag] =
    useState<(typeof FISH_SNIPER_FISHING_SCENE_TAG_OPTIONS)[number]>('lake')
  const [targetSpeciesSelection, setTargetSpeciesSelection] =
    useState<FishSniperStrategyTargetSpecies>('Largemouth Bass')
  const [selectedLureCategoryId, setSelectedLureCategoryId] = useState<number | null>(null)
  const [selectedLureSubCategoryId, setSelectedLureSubCategoryId] = useState<number | null>(null)
  const [selectedLureColorName, setSelectedLureColorName] = useState('')
  const [retrieveSpeedInput, setRetrieveSpeedInput] = useState('')
  const [caughtCountInput, setCaughtCountInput] = useState('0')
  const [weightLbInput, setWeightLbInput] = useState('')
  const [lengthCmInput, setLengthCmInput] = useState('')
  const [notesInput, setNotesInput] = useState('')

  const [weatherMode, setWeatherMode] = useState<'load_region' | 'manual'>('load_region')
  const [weatherRegionQueryInput, setWeatherRegionQueryInput] = useState('')
  const [isFetchingWeatherForForm, setIsFetchingWeatherForForm] = useState(false)
  const [weatherFetchError, setWeatherFetchError] = useState<string | null>(null)

  const [manualTemperatureCelsius, setManualTemperatureCelsius] = useState('18')
  const [manualConditionCode, setManualConditionCode] =
    useState<(typeof FISH_SNIPER_CONDITION_CODE_OPTIONS)[number]>('cloudy')
  const [manualWindSpeedMetersPerSecond, setManualWindSpeedMetersPerSecond] = useState('3')
  const [manualPressureHectopascals, setManualPressureHectopascals] = useState('1013')

  const parsedWaterDepthMeters = useMemo(() => Number.parseFloat(waterDepthMetersInput), [waterDepthMetersInput])

  const parsedCaughtCountForPayload = useMemo(() => {
    const trimmed = caughtCountInput.trim()
    if (!/^\d+$/.test(trimmed)) {
      return Number.NaN
    }
    return Number.parseInt(trimmed, 10)
  }, [caughtCountInput])

  const parsedWeightLb = weightLbInput.trim() === '' ? null : Number.parseFloat(weightLbInput)

  const parsedLengthCm = lengthCmInput.trim() === '' ? null : Number.parseFloat(lengthCmInput)

  const parsedManualTemperatureCelsius = Number.parseFloat(manualTemperatureCelsius)
  const parsedManualWindMetersPerSecond = Number.parseFloat(manualWindSpeedMetersPerSecond)
  const parsedManualPressureHectopascals = Number.parseInt(manualPressureHectopascals, 10)

  const logFormValidationInput = useMemo(
    () => ({
      logDateValue: logDateInput,
      fishingLocation: fishingLocationInput,
      targetSpecies: targetSpeciesSelection,
      waterDepthMetersText: waterDepthMetersInput,
      lureCategoryId: selectedLureCategoryId,
      lureSubCategoryId: selectedLureSubCategoryId,
      lureTypesCatalog: fishSniperLureTypesCatalogForMyLogForm,
      lureColorName: selectedLureColorName,
      lureColorsCatalog: fishSniperLureColorsCatalogForMyLogForm,
      retrieveSpeed: retrieveSpeedInput,
      caughtCountText: caughtCountInput,
      weightLbText: weightLbInput,
      lengthCmText: lengthCmInput,
      manualTemperatureText: manualTemperatureCelsius,
      manualWindText: manualWindSpeedMetersPerSecond,
      manualPressureText: manualPressureHectopascals,
    }),
    [
      logDateInput,
      fishingLocationInput,
      targetSpeciesSelection,
      waterDepthMetersInput,
      selectedLureCategoryId,
      selectedLureSubCategoryId,
      selectedLureColorName,
      retrieveSpeedInput,
      caughtCountInput,
      weightLbInput,
      lengthCmInput,
      manualTemperatureCelsius,
      manualWindSpeedMetersPerSecond,
      manualPressureHectopascals,
    ],
  )

  const logFormFieldErrorMap = useMemo(() => {
    if (!logFormSubmitAttempted) {
      return {}
    }
    return validateFishSniperMyLogForm(logFormValidationInput)
  }, [logFormSubmitAttempted, logFormValidationInput])

  function readFishSniperMyLogFormFieldError(field: FishSniperMyLogFormFieldErrorKey): string | undefined {
    return logFormFieldErrorMap[field]
  }

  function buildFishSniperMyLogInputClassName(field: FishSniperMyLogFormFieldErrorKey): string {
    const hasError = Boolean(logFormFieldErrorMap[field])
    return [
      inputClassName,
      hasError ? 'border-rose-500/70 focus:border-rose-400 focus:ring-rose-500/25' : '',
    ]
      .filter(Boolean)
      .join(' ')
  }

  const reloadLogsFromNetwork = useCallback(
    async (options: { allowConditional: boolean }) => {
      setListErrorMessage(null)
      setListLoadStatus('loading')
      const cacheSnapshot = readFishSniperLogsListCacheFromSessionStorage()
      const ifNoneMatch =
        options.allowConditional && cacheSnapshot?.etag ? cacheSnapshot.etag : null

      const result = await getFishSniperFishingLogsListWithEtag({
        apiBaseUrl: fishSniperApiBaseUrl,
        accessTokenJwt: fishSniperAccessTokenJwt,
        ifNoneMatch,
      })

      if (result.outcome === 'full') {
        setLogs(result.logs)
        writeFishSniperLogsListCacheToSessionStorage({
          etag: result.etag.length > 0 ? result.etag : null,
          logsJson: JSON.stringify(result.logs),
        })
        setListLoadStatus('ready')
        return
      }

      if (result.outcome === 'not_modified') {
        if (cacheSnapshot?.logsJson) {
          try {
            const cachedLogs = JSON.parse(cacheSnapshot.logsJson) as FishingLogResponsePayload[]
            setLogs(cachedLogs)
          } catch {
            setLogs([])
          }
        }
        setListLoadStatus('ready')
        return
      }

      setListErrorMessage(result.message)
      setListLoadStatus('error')
    },
    [fishSniperApiBaseUrl, fishSniperAccessTokenJwt],
  )

  useEffect(() => {
    const cacheSnapshot = readFishSniperLogsListCacheFromSessionStorage()
    if (cacheSnapshot?.logsJson) {
      try {
        setLogs(JSON.parse(cacheSnapshot.logsJson) as FishingLogResponsePayload[])
      } catch {
        setLogs([])
      }
    }
    void reloadLogsFromNetwork({ allowConditional: true })
  }, [reloadLogsFromNetwork])

  useEffect(() => {
    if (!isFormOpen) {
      return
    }
    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key !== 'Escape') {
        return
      }
      if (isSavingLog) {
        return
      }
      event.preventDefault()
      setIsFormOpen(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isFormOpen, isSavingLog])

  const selectedLureCategoryForForm = useMemo(() => {
    if (selectedLureCategoryId === null) {
      return null
    }
    return (
      fishSniperLureTypesCatalogForMyLogForm.lureTypes.find(
        (category) => category.id === selectedLureCategoryId,
      ) ?? null
    )
  }, [selectedLureCategoryId])

  function handleLureCategorySelectChange(nextCategoryIdRaw: string): void {
    if (nextCategoryIdRaw.length === 0) {
      setSelectedLureCategoryId(null)
      setSelectedLureSubCategoryId(null)
      return
    }
    const nextCategoryId = Number.parseInt(nextCategoryIdRaw, 10)
    if (!Number.isFinite(nextCategoryId)) {
      return
    }
    setSelectedLureCategoryId(nextCategoryId)
    const category = fishSniperLureTypesCatalogForMyLogForm.lureTypes.find(
      (entry) => entry.id === nextCategoryId,
    )
    const firstSubCategory = category?.subCategories[0]
    setSelectedLureSubCategoryId(firstSubCategory ? firstSubCategory.id : null)
  }

  function openNewLogForm(): void {
    setEditingLog(null)
    setFormSubmitError(null)
    setWeatherFetchError(null)
    setLogFormSubmitAttempted(false)
    setLogDateInput(new Date().toISOString().slice(0, 10))
    setFishingLocationInput('')
    setWaterDepthMetersInput('1.5')
    setFishingSceneTag('lake')
    setSelectedLureCategoryId(null)
    setSelectedLureSubCategoryId(null)
    setSelectedLureColorName('')
    setRetrieveSpeedInput('')
    setCaughtCountInput('0')
    setWeightLbInput('')
    setLengthCmInput('')
    setNotesInput('')
    setWeatherMode('load_region')
    setWeatherRegionQueryInput('')
    setManualTemperatureCelsius('18')
    setManualConditionCode('cloudy')
    setManualWindSpeedMetersPerSecond('3')
    setManualPressureHectopascals('1013')
    setIsFormOpen(true)
  }

  function openEditLogForm(log: FishingLogResponsePayload): void {
    setEditingLog(log)
    setFormSubmitError(null)
    setWeatherFetchError(null)
    setLogFormSubmitAttempted(false)
    setLogDateInput(log.date)
    setFishingLocationInput(log.fishing_location)
    setWaterDepthMetersInput(String(log.water_depth_m))
    setFishingSceneTag(
      (FISH_SNIPER_FISHING_SCENE_TAG_OPTIONS as readonly string[]).includes(log.fishing_scene)
        ? (log.fishing_scene as (typeof FISH_SNIPER_FISHING_SCENE_TAG_OPTIONS)[number])
        : 'lake',
    )
    setTargetSpeciesSelection(
      isFishSniperStrategyTargetSpeciesValue(log.target_species)
        ? log.target_species
        : 'Largemouth Bass',
    )
    const lureSelection = findLureSelectionForStoredSubCategoryName(
      fishSniperLureTypesCatalogForMyLogForm,
      log.lure_type,
    )
    if (lureSelection) {
      setSelectedLureCategoryId(lureSelection.lureCategoryId)
      setSelectedLureSubCategoryId(lureSelection.lureSubCategoryId)
    } else {
      setSelectedLureCategoryId(null)
      setSelectedLureSubCategoryId(null)
    }
    setSelectedLureColorName(
      isLureColorNameInCatalog(fishSniperLureColorsCatalogForMyLogForm, log.lure_color)
        ? log.lure_color.trim()
        : '',
    )
    setRetrieveSpeedInput(log.retrieve_speed)
    setCaughtCountInput(String(log.caught_count))
    setWeightLbInput(log.weight_lb === null ? '' : String(log.weight_lb))
    setLengthCmInput(log.length_cm === null ? '' : String(log.length_cm))
    setNotesInput(log.notes)
    setWeatherMode('manual')
    setManualTemperatureCelsius(String(log.temperature_c))
    setManualConditionCode(
      isFishSniperConditionCodeValue(log.condition_code) ? log.condition_code : 'cloudy',
    )
    setManualWindSpeedMetersPerSecond(String(log.wind_speed_ms))
    setManualPressureHectopascals(String(log.pressure_hpa))
    setIsFormOpen(true)
  }

  async function handleFetchWeatherIntoForm(): Promise<void> {
    setWeatherFetchError(null)
    const region = weatherRegionQueryInput.trim()
    if (region.length === 0) {
      setWeatherFetchError('Enter a region to load weather.')
      return
    }
    setIsFetchingWeatherForForm(true)
    try {
      const snapshot = await getJsonWithFishSniperApi<CurrentWeatherResponsePayload>({
        apiBaseUrl: fishSniperApiBaseUrl,
        path: `/weather/current?region=${encodeURIComponent(region)}`,
        accessTokenJwt: fishSniperAccessTokenJwt,
      })
      setManualTemperatureCelsius(String(snapshot.temperature_c))
      const code = snapshot.condition_code
      setManualConditionCode(isFishSniperConditionCodeValue(code) ? code : 'cloudy')
      setManualWindSpeedMetersPerSecond(String(snapshot.wind_speed_ms))
      setManualPressureHectopascals(String(snapshot.pressure_hpa))
    } catch {
      setWeatherFetchError('Could not load weather. Try manual values or another region.')
    } finally {
      setIsFetchingWeatherForForm(false)
    }
  }

  function buildCreateOrUpdatePayload(): CreateOrUpdateFishingLogRequestPayload {
    if (selectedLureCategoryId === null || selectedLureSubCategoryId === null) {
      throw new Error('FishSniperMyLogsPage: lure selection is required before building the payload.')
    }
    const lureSubCategoryName = getLureSubCategoryNameFromSelection(
      fishSniperLureTypesCatalogForMyLogForm,
      selectedLureCategoryId,
      selectedLureSubCategoryId,
    )
    if (!lureSubCategoryName) {
      throw new Error('FishSniperMyLogsPage: lure selection does not resolve to a catalog subtype.')
    }
    return {
      date: logDateInput.trim(),
      fishing_location: fishingLocationInput,
      fishing_scene: fishingSceneTag,
      target_species: targetSpeciesSelection,
      water_depth_m: parsedWaterDepthMeters,
      lure_type: lureSubCategoryName,
      lure_color: selectedLureColorName.trim(),
      retrieve_speed: retrieveSpeedInput.trim(),
      caught_count: parsedCaughtCountForPayload,
      weight_lb: weightLbInput.trim() === '' ? null : (parsedWeightLb as number),
      length_cm: lengthCmInput.trim() === '' ? null : (parsedLengthCm as number),
      temperature_c: parsedManualTemperatureCelsius,
      wind_speed_ms: parsedManualWindMetersPerSecond,
      pressure_hpa: parsedManualPressureHectopascals,
      condition_code: manualConditionCode,
      notes: notesInput,
    }
  }

  async function handleSaveLogForm(): Promise<void> {
    const logFormFieldErrors = validateFishSniperMyLogForm(logFormValidationInput)
    setLogFormSubmitAttempted(true)
    if (Object.keys(logFormFieldErrors).length > 0) {
      return
    }
    setFormSubmitError(null)
    setIsSavingLog(true)
    const payload = buildCreateOrUpdatePayload()
    try {
      if (editingLog) {
        await patchFishSniperFishingLog({
          apiBaseUrl: fishSniperApiBaseUrl,
          accessTokenJwt: fishSniperAccessTokenJwt,
          logId: editingLog.log_id,
          requestBody: payload,
        })
      } else {
        await postFishSniperFishingLog({
          apiBaseUrl: fishSniperApiBaseUrl,
          accessTokenJwt: fishSniperAccessTokenJwt,
          requestBody: payload,
        })
      }
      invalidateFishSniperLogsListCacheInSessionStorage()
      await reloadLogsFromNetwork({ allowConditional: false })
      setIsFormOpen(false)
      setEditingLog(null)
    } catch (unknownError) {
      const message =
        unknownError instanceof Error ? unknownError.message : 'Could not save log. Try again.'
      setFormSubmitError(message)
    } finally {
      setIsSavingLog(false)
    }
  }

  async function handleDeleteLog(log: FishingLogResponsePayload): Promise<void> {
    const confirmed = window.confirm(
      `Delete this log from ${formatLogDateForDisplay(log.date)} at ${log.fishing_location}?`,
    )
    if (!confirmed) {
      return
    }
    try {
      await deleteFishSniperFishingLog({
        apiBaseUrl: fishSniperApiBaseUrl,
        accessTokenJwt: fishSniperAccessTokenJwt,
        logId: log.log_id,
      })
      invalidateFishSniperLogsListCacheInSessionStorage()
      await reloadLogsFromNetwork({ allowConditional: false })
      if (expandedLogId === log.log_id) {
        setExpandedLogId(null)
      }
    } catch {
      window.alert('Could not delete log. Try again.')
    }
  }

  return (
    <div className="relative isolate mx-auto w-full max-w-6xl overflow-hidden rounded-[2rem] border border-white/10 bg-[#020617] px-4 py-5 sm:px-6">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_8%_10%,rgba(16,185,129,0.2),transparent_36%),radial-gradient(circle_at_90%_8%,rgba(56,189,248,0.18),transparent_38%),radial-gradient(circle_at_80%_90%,rgba(99,102,241,0.14),transparent_42%)]" />

      <header className={`${glassPanelClassName} mb-5`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-2">
            <p className={chipClassName}>FishSniper Logbook</p>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-50 sm:text-3xl">My Fishing Logs</h1>
            <p className="max-w-2xl text-sm text-slate-300/90">
              Record sessions with the same glass console feel as Strategy. Weather values are stored exactly as you
              save them.
            </p>
          </div>
          <span className={chipClassName}>
            {listLoadStatus === 'loading' ? 'Syncing…' : `${logs.length} logged`}
          </span>
        </div>
      </header>

      {listErrorMessage ? (
        <p className={`mb-4 ${FISH_SNIPER_MY_LOG_BANNER_ERROR_CLASS_NAME}`}>{listErrorMessage}</p>
      ) : null}

      {listLoadStatus === 'loading' && logs.length === 0 ? (
        <div className={`${glassPanelClassName} animate-pulse space-y-3 motion-reduce:animate-none`}>
          <div className="h-4 w-2/3 rounded bg-slate-700/80" />
          <div className="h-4 w-full rounded bg-slate-700/80" />
          <div className="h-4 w-5/6 rounded bg-slate-700/80" />
        </div>
      ) : null}

      <ul className="space-y-3 pb-24">
        {logs.map((log) => {
          const isExpanded = expandedLogId === log.log_id
          return (
            <li key={log.log_id}>
              <div
                className={`${glassPanelClassName} cursor-pointer transition-colors duration-200 hover:border-emerald-500/25`}
                role="button"
                tabIndex={0}
                onClick={() => setExpandedLogId(isExpanded ? null : log.log_id)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    setExpandedLogId(isExpanded ? null : log.log_id)
                  }
                }}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="text-sm font-semibold text-slate-50">{formatLogDateForDisplay(log.date)}</span>
                    <span className="text-sm text-slate-200">{log.fishing_location}</span>
                    <span className={chipClassName}>{log.target_species}</span>
                    <span className={chipClassName}>{log.lure_type}</span>
                    <span className="text-xs text-slate-400">Caught {log.caught_count}</span>
                  </div>
                  <span className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                    {isExpanded ? 'Hide' : 'Expand'}
                  </span>
                </div>

                {isExpanded ? (
                  <div className="mt-4 space-y-4 border-t border-white/10 pt-4">
                    <dl className="grid grid-cols-1 gap-3 text-sm text-slate-200 sm:grid-cols-2">
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Scene</dt>
                        <dd>{log.fishing_scene}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Species</dt>
                        <dd>{log.target_species}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Depth (m)</dt>
                        <dd>{log.water_depth_m}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Lure color</dt>
                        <dd>{log.lure_color}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Retrieve</dt>
                        <dd>{log.retrieve_speed}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Weight (lb)</dt>
                        <dd>{log.weight_lb === null ? '—' : log.weight_lb}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Length (cm)</dt>
                        <dd>{log.length_cm === null ? '—' : log.length_cm}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Temp / condition</dt>
                        <dd>
                          {log.temperature_c}°C · {log.condition_code}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Wind / pressure</dt>
                        <dd>
                          {log.wind_speed_ms} m/s · {log.pressure_hpa} hPa
                        </dd>
                      </div>
                      <div className="sm:col-span-2">
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Notes</dt>
                        <dd className="text-slate-300">{log.notes || '—'}</dd>
                      </div>
                      <div className="sm:col-span-2 text-xs text-slate-500">
                        Updated {formatIsoTimestampForDisplay(log.updated_at)}
                        {log.embedding_status === 'done' ? ' · synced' : ''}
                      </div>
                    </dl>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="cursor-pointer rounded-xl border border-emerald-400/45 bg-emerald-500/15 px-4 py-2 text-xs font-semibold text-emerald-200 transition-colors duration-200 hover:bg-emerald-500/25"
                        onClick={(event) => {
                          event.stopPropagation()
                          openEditLogForm(log)
                        }}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="cursor-pointer rounded-xl border border-rose-500/45 bg-rose-950/30 px-4 py-2 text-xs font-semibold text-rose-100 transition-colors duration-200 hover:bg-rose-900/40"
                        onClick={(event) => {
                          event.stopPropagation()
                          void handleDeleteLog(log)
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            </li>
          )
        })}
      </ul>

      {listLoadStatus === 'ready' && logs.length === 0 ? (
        <p className={`${glassPanelClassName} text-center text-sm text-slate-400`}>
          No logs yet. Tap + to record your first session.
        </p>
      ) : null}

      <button
        type="button"
        aria-label="Add fishing log"
        className="fixed bottom-24 right-4 z-30 flex h-14 w-14 cursor-pointer items-center justify-center rounded-full bg-emerald-500 text-slate-950 shadow-[0_14px_40px_-12px_rgba(16,185,129,0.9)] transition-colors duration-200 hover:bg-emerald-400 sm:bottom-28"
        onClick={() => openNewLogForm()}
      >
        <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" aria-hidden>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
      </button>

      {isFormOpen ? (
        <div
          className="fixed inset-0 z-40 flex items-end justify-center bg-black/60 p-4 sm:items-center motion-reduce:transition-none"
          role="presentation"
        >
          <div
            className={`${glassPanelClassName} max-h-[90vh] w-full max-w-lg overflow-y-auto shadow-2xl`}
            role="dialog"
            aria-modal="true"
            aria-labelledby="fish-sniper-log-form-title"
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <h2 id="fish-sniper-log-form-title" className="text-lg font-semibold text-slate-50">
                {editingLog ? 'Edit log' : 'New log'}
              </h2>
              <button
                type="button"
                className="cursor-pointer rounded-xl border border-white/20 bg-slate-950/60 px-4 py-2 text-sm font-semibold text-slate-100 shadow-sm transition-colors duration-200 hover:border-white/35 hover:bg-slate-900/70 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isSavingLog}
                onClick={() => setIsFormOpen(false)}
              >
                Close
              </button>
            </div>

            {formSubmitError ? (
              <p className={`mb-3 ${FISH_SNIPER_MY_LOG_BANNER_ERROR_CLASS_NAME}`}>{formSubmitError}</p>
            ) : null}

            <div className="space-y-4">
              <label className={fieldLabelClassName}>
                Date
                <input
                  className={buildFishSniperMyLogInputClassName('date')}
                  type="date"
                  value={logDateInput}
                  onChange={(event) => setLogDateInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.ctrlKey || event.metaKey || event.altKey) {
                      return
                    }
                    const allowedKeys = new Set([
                      'Tab',
                      'Escape',
                      'Enter',
                      ' ',
                      'ArrowUp',
                      'ArrowDown',
                      'ArrowLeft',
                      'ArrowRight',
                      'Home',
                      'End',
                      'PageUp',
                      'PageDown',
                    ])
                    if (allowedKeys.has(event.key)) {
                      return
                    }
                    event.preventDefault()
                  }}
                  onPaste={(event) => {
                    event.preventDefault()
                  }}
                  onClick={(event) => {
                    const element = event.currentTarget
                    if (typeof element.showPicker === 'function') {
                      void element.showPicker()
                    }
                  }}
                />
                {readFishSniperMyLogFormFieldError('date') ? (
                  <span className={FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME}>
                    {readFishSniperMyLogFormFieldError('date')}
                  </span>
                ) : (
                  <span className="text-[11px] font-normal leading-snug text-slate-500">
                    Use the calendar control — typing is disabled.
                  </span>
                )}
              </label>

              <label className={fieldLabelClassName}>
                Fishing location
                <input
                  className={buildFishSniperMyLogInputClassName('fishing_location')}
                  value={fishingLocationInput}
                  onChange={(event) => setFishingLocationInput(event.target.value)}
                  placeholder="e.g. North shore dock"
                />
                {readFishSniperMyLogFormFieldError('fishing_location') ? (
                  <span className={FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME}>
                    {readFishSniperMyLogFormFieldError('fishing_location')}
                  </span>
                ) : (
                  <span className="text-[11px] font-normal leading-snug text-slate-500">
                    與之後個人化建議相關，請與實際釣點用語保持一致（含大小寫）。
                  </span>
                )}
              </label>

              <label className={fieldLabelClassName}>
                Water depth (m)
                <input
                  className={buildFishSniperMyLogInputClassName('water_depth_m')}
                  inputMode="decimal"
                  value={waterDepthMetersInput}
                  onChange={(event) => setWaterDepthMetersInput(event.target.value)}
                />
                {readFishSniperMyLogFormFieldError('water_depth_m') ? (
                  <span className={FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME}>
                    {readFishSniperMyLogFormFieldError('water_depth_m')}
                  </span>
                ) : null}
              </label>

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
                  className={buildFishSniperMyLogInputClassName('target_species')}
                  value={targetSpeciesSelection}
                  onChange={(event) =>
                    setTargetSpeciesSelection(event.target.value as FishSniperStrategyTargetSpecies)
                  }
                >
                  {FISH_SNIPER_LOG_TARGET_SPECIES_OPTIONS.map((speciesOption) => (
                    <option key={speciesOption} value={speciesOption}>
                      {speciesOption}
                    </option>
                  ))}
                </select>
                {readFishSniperMyLogFormFieldError('target_species') ? (
                  <span className={FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME}>
                    {readFishSniperMyLogFormFieldError('target_species')}
                  </span>
                ) : null}
              </label>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className={fieldLabelClassName}>
                  Lure category
                  <select
                    className={buildFishSniperMyLogInputClassName('lure_type')}
                    value={selectedLureCategoryId === null ? '' : String(selectedLureCategoryId)}
                    onChange={(event) => handleLureCategorySelectChange(event.target.value)}
                  >
                    <option value="">Select category</option>
                    {fishSniperLureTypesCatalogForMyLogForm.lureTypes.map((category) => (
                      <option key={category.id} value={String(category.id)}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className={fieldLabelClassName}>
                  Lure subtype
                  <select
                    className={buildFishSniperMyLogInputClassName('lure_type')}
                    value={selectedLureSubCategoryId === null ? '' : String(selectedLureSubCategoryId)}
                    disabled={selectedLureCategoryForForm === null}
                    onChange={(event) => {
                      const nextRaw = event.target.value
                      if (nextRaw.length === 0) {
                        setSelectedLureSubCategoryId(null)
                        return
                      }
                      const parsedId = Number.parseInt(nextRaw, 10)
                      setSelectedLureSubCategoryId(Number.isFinite(parsedId) ? parsedId : null)
                    }}
                  >
                    <option value="">Select subtype</option>
                    {(selectedLureCategoryForForm?.subCategories ?? []).map((subCategory) => (
                      <option key={subCategory.id} value={String(subCategory.id)}>
                        {subCategory.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              {readFishSniperMyLogFormFieldError('lure_type') ? (
                <p className={`-mt-2 sm:col-span-2 ${FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME}`}>
                  {readFishSniperMyLogFormFieldError('lure_type')}
                </p>
              ) : null}

              <label className={fieldLabelClassName}>
                Lure color
                <select
                  className={buildFishSniperMyLogInputClassName('lure_color')}
                  value={selectedLureColorName}
                  onChange={(event) => setSelectedLureColorName(event.target.value)}
                >
                  <option value="">Select color</option>
                  {fishSniperLureColorsCatalogForMyLogForm.colors.map((colorEntry) => (
                    <option key={colorEntry.id} value={colorEntry.name}>
                      {colorEntry.name}
                    </option>
                  ))}
                </select>
                {readFishSniperMyLogFormFieldError('lure_color') ? (
                  <span className={FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME}>
                    {readFishSniperMyLogFormFieldError('lure_color')}
                  </span>
                ) : null}
              </label>

              <label className={fieldLabelClassName}>
                Retrieve speed
                <input
                  className={buildFishSniperMyLogInputClassName('retrieve_speed')}
                  value={retrieveSpeedInput}
                  onChange={(event) => setRetrieveSpeedInput(event.target.value)}
                  placeholder="e.g. Slow"
                />
                {readFishSniperMyLogFormFieldError('retrieve_speed') ? (
                  <span className={FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME}>
                    {readFishSniperMyLogFormFieldError('retrieve_speed')}
                  </span>
                ) : null}
              </label>

              <div className="grid grid-cols-2 gap-3">
                <label className={fieldLabelClassName}>
                  Caught count
                  <input
                    className={buildFishSniperMyLogInputClassName('caught_count')}
                    inputMode="numeric"
                    value={caughtCountInput}
                    onChange={(event) => setCaughtCountInput(event.target.value)}
                  />
                  {readFishSniperMyLogFormFieldError('caught_count') ? (
                    <span className={FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME}>
                      {readFishSniperMyLogFormFieldError('caught_count')}
                    </span>
                  ) : null}
                </label>
                <label className={fieldLabelClassName}>
                  Weight (lb)
                  <input
                    className={buildFishSniperMyLogInputClassName('weight_lb')}
                    inputMode="decimal"
                    value={weightLbInput}
                    onChange={(event) => setWeightLbInput(event.target.value)}
                    placeholder="optional"
                  />
                  {readFishSniperMyLogFormFieldError('weight_lb') ? (
                    <span className={FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME}>
                      {readFishSniperMyLogFormFieldError('weight_lb')}
                    </span>
                  ) : null}
                </label>
              </div>

              <label className={fieldLabelClassName}>
                Length (cm)
                <input
                  className={buildFishSniperMyLogInputClassName('length_cm')}
                  inputMode="decimal"
                  value={lengthCmInput}
                  onChange={(event) => setLengthCmInput(event.target.value)}
                  placeholder="optional"
                />
                {readFishSniperMyLogFormFieldError('length_cm') ? (
                  <span className={FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME}>
                    {readFishSniperMyLogFormFieldError('length_cm')}
                  </span>
                ) : null}
              </label>

              <section className="space-y-3 rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                <h3 className={sectionTitleClassName}>Weather for this log</h3>
                <div className="flex flex-wrap gap-2.5 text-xs text-slate-200">
                  <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-white/15 bg-slate-900/70 px-3 py-2 transition-colors duration-200 hover:border-emerald-400/45">
                    <input
                      type="radio"
                      name="fish-sniper-log-weather-mode"
                      checked={weatherMode === 'load_region'}
                      onChange={() => setWeatherMode('load_region')}
                    />
                    Load by region
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-white/15 bg-slate-900/70 px-3 py-2 transition-colors duration-200 hover:border-emerald-400/45">
                    <input
                      type="radio"
                      name="fish-sniper-log-weather-mode"
                      checked={weatherMode === 'manual'}
                      onChange={() => setWeatherMode('manual')}
                    />
                    Manual
                  </label>
                </div>

                {weatherMode === 'load_region' ? (
                  <div className="space-y-2">
                    <label className={fieldLabelClassName}>
                      Weather query region
                      <input
                        className={inputClassName}
                        value={weatherRegionQueryInput}
                        onChange={(event) => setWeatherRegionQueryInput(event.target.value)}
                        placeholder="e.g. Boston"
                      />
                    </label>
                    {weatherFetchError ? <p className="text-xs text-amber-200">{weatherFetchError}</p> : null}
                    <button
                      type="button"
                      className="cursor-pointer rounded-xl border border-emerald-400/45 bg-emerald-500/15 px-3 py-2 text-xs font-semibold text-emerald-200 transition-colors duration-200 hover:bg-emerald-500/25 disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={isFetchingWeatherForForm}
                      onClick={() => void handleFetchWeatherIntoForm()}
                    >
                      {isFetchingWeatherForForm ? 'Loading…' : 'Fetch weather into form'}
                    </button>
                    <p className="text-[11px] text-slate-500">
                      Fills temperature, condition, wind, and pressure. You can switch to Manual to tweak.
                    </p>
                  </div>
                ) : null}

                <div className="grid grid-cols-2 gap-2.5 text-sm">
                  <label className={`${fieldLabelClassName} col-span-2`}>
                    Temp (°C)
                    <input
                      className={buildFishSniperMyLogInputClassName('temperature_c')}
                      inputMode="decimal"
                      value={manualTemperatureCelsius}
                      onChange={(event) => setManualTemperatureCelsius(event.target.value)}
                    />
                    {readFishSniperMyLogFormFieldError('temperature_c') ? (
                      <span className={FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME}>
                        {readFishSniperMyLogFormFieldError('temperature_c')}
                      </span>
                    ) : null}
                  </label>
                  <label className={`${fieldLabelClassName} col-span-2`}>
                    Condition code
                    <select
                      className={inputClassName}
                      value={manualConditionCode}
                      onChange={(event) =>
                        setManualConditionCode(
                          event.target.value as (typeof FISH_SNIPER_CONDITION_CODE_OPTIONS)[number],
                        )
                      }
                    >
                      {FISH_SNIPER_CONDITION_CODE_OPTIONS.map((code) => (
                        <option key={code} value={code}>
                          {code}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className={fieldLabelClassName}>
                    Wind (m/s)
                    <input
                      className={buildFishSniperMyLogInputClassName('wind_speed_ms')}
                      inputMode="decimal"
                      value={manualWindSpeedMetersPerSecond}
                      onChange={(event) => setManualWindSpeedMetersPerSecond(event.target.value)}
                    />
                    {readFishSniperMyLogFormFieldError('wind_speed_ms') ? (
                      <span className={FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME}>
                        {readFishSniperMyLogFormFieldError('wind_speed_ms')}
                      </span>
                    ) : null}
                  </label>
                  <label className={fieldLabelClassName}>
                    Pressure (hPa)
                    <input
                      className={buildFishSniperMyLogInputClassName('pressure_hpa')}
                      inputMode="numeric"
                      value={manualPressureHectopascals}
                      onChange={(event) => setManualPressureHectopascals(event.target.value)}
                    />
                    {readFishSniperMyLogFormFieldError('pressure_hpa') ? (
                      <span className={FISH_SNIPER_MY_LOG_FIELD_ERROR_TEXT_CLASS_NAME}>
                        {readFishSniperMyLogFormFieldError('pressure_hpa')}
                      </span>
                    ) : null}
                  </label>
                </div>
              </section>

              <label className={fieldLabelClassName}>
                Notes
                <textarea
                  className={`${inputClassName} min-h-[88px] resize-y`}
                  value={notesInput}
                  onChange={(event) => setNotesInput(event.target.value)}
                />
              </label>

              <button
                type="button"
                className="w-full cursor-pointer rounded-2xl bg-emerald-500 py-3 text-sm font-semibold text-slate-950 shadow-[0_14px_40px_-18px_rgba(16,185,129,0.95)] transition-colors duration-200 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={isSavingLog}
                onClick={() => void handleSaveLogForm()}
              >
                {isSavingLog ? 'Saving…' : editingLog ? 'Save changes' : 'Save log'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
