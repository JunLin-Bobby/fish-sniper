import type {
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
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
    typeof payload.fish_state !== 'string' ||
    typeof payload.confidence_note !== 'string' ||
    typeof payload.generated_at !== 'string' ||
    payload.fallback !== false ||
    !Array.isArray(payload.recommendations) ||
    payload.recommendations.length !== 3
  ) {
    return false
  }
  return payload.recommendations.every(
    (item) =>
      isRecord(item) &&
      typeof item.lure_type === 'string' &&
      typeof item.lure_color === 'string' &&
      typeof item.retrieve_technique === 'string',
  )
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
