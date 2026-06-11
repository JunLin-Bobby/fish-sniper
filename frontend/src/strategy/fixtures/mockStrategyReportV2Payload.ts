import type { GenerateBassStrategySuccessResponsePayload } from '../../api/fishSniperApiTypes.ts'

/** Shared v2 success payload for tests and static mock previews. */
export const mockStrategyReportV2SuccessPayload: GenerateBassStrategySuccessResponsePayload = {
  todays_pattern: {
    headline: 'Post-Spawn Largemouth',
    subline: 'Shallow flats + windblown banks',
  },
  confidence_pct: 82,
  confidence_note: 'Plan based on general best practices for cloudy, warming conditions.',
  holding_zones: [
    { label: 'Windblown rocky point', weight_pct: 70 },
    { label: 'First drop outside spawning flat', weight_pct: 20 },
    { label: 'Isolated wood in 2m depth', weight_pct: 10 },
  ],
  fish_state:
    'Fish are holding on brush piles in 6–10 ft after the cold front. Active window is late morning once surface temps climb.',
  recommendations: [
    {
      tactical_role: 'locator_bait',
      lure_type: 'Football Jig',
      lure_color: 'Green pumpkin',
      reason: 'Covers bottom transitions to locate active fish on brush piles.',
      retrieve_technique: 'Slow drag with 2-second pauses on bottom transitions.',
    },
    {
      tactical_role: 'follow_up_bait',
      lure_type: 'Mid-depth crankbait',
      lure_color: 'Shad pattern',
      reason: 'Follow-up for fish that track but refuse the jig.',
      retrieve_technique: 'Moderate retrieve, deflect off stumps, pause on contact.',
    },
    {
      tactical_role: 'finesse_cleanup',
      lure_type: 'Ned rig',
      lure_color: 'Mushroom head / green pumpkin TRD',
      reason: 'Finesse cleanup along dock shade for pressured fish.',
      retrieve_technique: 'Dead-stick hops along dock shade lines.',
    },
  ],
  weather_snapshot: {
    temperature_c: 18.5,
    pressure_hpa: 1015,
    wind_speed_ms: 3.2,
    condition_code: 'cloudy',
  },
  rag_logs_used: 0,
  referenced_log: null,
  generated_at: '2026-06-07T08:30:00.000Z',
  fallback: false,
}
