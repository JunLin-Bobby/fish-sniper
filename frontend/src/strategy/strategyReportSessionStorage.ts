import type {
  BassStrategyRecommendationTacticalRole,
  FishSniperStrategyTargetSpecies,
  GenerateBassStrategySuccessResponsePayload,
} from '../api/fishSniperApiTypes.ts'

export const FISH_SNIPER_STRATEGY_REPORT_SESSION_STORAGE_KEY = 'fish_sniper_strategy_report_v1'

export type StrategyReportRequestSummary = {
  region: string
  fishing_location: string
  fishing_scene: string
  target_species: FishSniperStrategyTargetSpecies
  water_depth_m: number
}

export type StoredStrategyReport = {
  version: 1
  savedAt: string
  successPayload: GenerateBassStrategySuccessResponsePayload
  requestSummary: StrategyReportRequestSummary
}

const TACTICAL_ROLES: ReadonlySet<BassStrategyRecommendationTacticalRole> = new Set([
  'locator_bait',
  'follow_up_bait',
  'finesse_cleanup',
])

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isTodaysPattern(value: unknown): boolean {
  return (
    isRecord(value) &&
    typeof value.headline === 'string' &&
    typeof value.subline === 'string'
  )
}

function isHoldingZoneItem(value: unknown): boolean {
  return (
    isRecord(value) &&
    typeof value.label === 'string' &&
    typeof value.weight_pct === 'number'
  )
}

function isRecommendationItem(value: unknown): boolean {
  return (
    isRecord(value) &&
    typeof value.tactical_role === 'string' &&
    TACTICAL_ROLES.has(value.tactical_role as BassStrategyRecommendationTacticalRole) &&
    typeof value.lure_type === 'string' &&
    typeof value.lure_color === 'string' &&
    typeof value.reason === 'string' &&
    typeof value.retrieve_technique === 'string'
  )
}

function isStoredStrategyReport(value: unknown): value is StoredStrategyReport {
  if (!isRecord(value) || value.version !== 1) {
    return false
  }
  if (typeof value.savedAt !== 'string') {
    return false
  }
  if (!isRecord(value.requestSummary) || !isRecord(value.successPayload)) {
    return false
  }
  const summary = value.requestSummary
  if (
    typeof summary.region !== 'string' ||
    typeof summary.fishing_location !== 'string' ||
    typeof summary.fishing_scene !== 'string' ||
    typeof summary.target_species !== 'string' ||
    typeof summary.water_depth_m !== 'number'
  ) {
    return false
  }
  const payload = value.successPayload
  if (
    !isTodaysPattern(payload.todays_pattern) ||
    typeof payload.confidence_pct !== 'number' ||
    typeof payload.confidence_note !== 'string' ||
    typeof payload.fish_state !== 'string' ||
    typeof payload.generated_at !== 'string' ||
    payload.fallback !== false ||
    !Array.isArray(payload.holding_zones) ||
    payload.holding_zones.length !== 3 ||
    !payload.holding_zones.every(isHoldingZoneItem) ||
    !Array.isArray(payload.recommendations) ||
    payload.recommendations.length !== 3 ||
    !payload.recommendations.every(isRecommendationItem)
  ) {
    return false
  }
  return true
}

export function writeStrategyReportToSessionStorage(report: StoredStrategyReport): void {
  sessionStorage.setItem(FISH_SNIPER_STRATEGY_REPORT_SESSION_STORAGE_KEY, JSON.stringify(report))
}

export function readStrategyReportFromSessionStorage(): StoredStrategyReport | null {
  const raw = sessionStorage.getItem(FISH_SNIPER_STRATEGY_REPORT_SESSION_STORAGE_KEY)
  if (!raw) {
    return null
  }
  try {
    const parsed: unknown = JSON.parse(raw)
    if (!isStoredStrategyReport(parsed)) {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

export function clearStrategyReportSessionStorage(): void {
  sessionStorage.removeItem(FISH_SNIPER_STRATEGY_REPORT_SESSION_STORAGE_KEY)
}

export function saveStrategyReportToSessionStorage(options: {
  successPayload: GenerateBassStrategySuccessResponsePayload
  requestSummary: StrategyReportRequestSummary
}): void {
  writeStrategyReportToSessionStorage({
    version: 1,
    savedAt: new Date().toISOString(),
    successPayload: options.successPayload,
    requestSummary: options.requestSummary,
  })
}
