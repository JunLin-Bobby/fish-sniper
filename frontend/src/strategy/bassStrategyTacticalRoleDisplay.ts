import type { BassStrategyRecommendationTacticalRole } from '../api/fishSniperApiTypes.ts'

/** UI copy for each combo phase. API / LLM values stay as `tactical_role` snake_case. */
export interface BassStrategyTacticalRoleDisplay {
  title: string
  subtitle: string
}

export const BASS_STRATEGY_TACTICAL_ROLE_DISPLAY: Record<
  BassStrategyRecommendationTacticalRole,
  BassStrategyTacticalRoleDisplay
> = {
  locator_bait: {
    title: 'Step 1: Quick locate',
    subtitle:
      'Fish are not spread evenly across the water — cover ground and find active fish fast.',
  },
  follow_up_bait: {
    title: 'Step 2: Precision strike',
    subtitle:
      'Once you have a bite, a follow, or you are certain fish are on this spot, tighten the approach.',
  },
  finesse_cleanup: {
    title: 'Step 3: Maximum finesse',
    subtitle:
      'For fish under extreme pressure that still will not commit — slow down and extract the last bites.',
  },
}

export function getBassStrategyTacticalRoleDisplay(
  tacticalRole: BassStrategyRecommendationTacticalRole,
): BassStrategyTacticalRoleDisplay {
  return BASS_STRATEGY_TACTICAL_ROLE_DISPLAY[tacticalRole]
}
