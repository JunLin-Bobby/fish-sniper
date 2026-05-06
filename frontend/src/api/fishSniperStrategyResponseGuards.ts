import type { GenerateBassStrategyFallbackResponsePayload } from './fishSniperApiTypes.ts'

export function isFishSniperGenerateBassStrategyFallbackResponsePayload(
  value: unknown,
): value is GenerateBassStrategyFallbackResponsePayload {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const record = value as Record<string, unknown>
  return (
    record.fallback === true &&
    typeof record.message === 'string' &&
    typeof record.generated_at === 'string'
  )
}
