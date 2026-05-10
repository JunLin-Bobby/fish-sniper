/** Typed FishSniper API envelopes (P1). */

export interface SendEmailOtpResponsePayload {
  message: string
}

export interface VerifyEmailOtpResponsePayload {
  access_token: string
  is_new_user: boolean
}

export interface UserPreferencesResponsePayload {
  region: string | null
  onboarding_completed: boolean
}

export interface SaveUserPreferencesResponsePayload {
  message: string
}

export interface FishSniperTopLevelErrorPayload {
  error: string
}

export interface FishSniperHttpDetailEnvelopePayload {
  detail: string | Record<string, unknown>
}

/** GET /weather/current */

export interface CurrentWeatherResponsePayload {
  temperature_c: number
  condition: string
  condition_code: string
  wind_speed_ms: number
  pressure_hpa: number
  humidity_pct: number
  fetched_at: string
}

/** POST /agent/strategy */

export type FishSniperStrategyTargetSpecies = 'Largemouth Bass' | 'Smallmouth Bass'

export interface ManualWeatherRequestPayload {
  temperature_c: number
  condition_code: string
  wind_speed_ms: number
  pressure_hpa: number
}

export interface GenerateBassStrategyRequestPayload {
  region: string
  fishing_location: string
  water_depth_m: number
  fishing_scene: string
  target_species: FishSniperStrategyTargetSpecies
  manual_weather?: ManualWeatherRequestPayload | null
}

export interface WeatherSnapshotPayload {
  temperature_c: number
  pressure_hpa: number
  wind_speed_ms: number
  condition_code: string
}

export interface BassStrategyRecommendationPayload {
  lure_type: string
  lure_color: string
  retrieve_technique: string
}

export interface GenerateBassStrategySuccessResponsePayload {
  fish_state: string
  recommendations: [BassStrategyRecommendationPayload, BassStrategyRecommendationPayload, BassStrategyRecommendationPayload]
  confidence_note: string
  weather_snapshot: WeatherSnapshotPayload
  rag_logs_used: number
  generated_at: string
  fallback: false
}

export interface GenerateBassStrategyFallbackResponsePayload {
  fallback: true
  message: string
  generated_at: string
}

/** GET/POST/PATCH /logs (P3 + P4 Part 1 vector readiness fields) */

/**
 * Vector readiness for a fishing log.
 *  - 'pending': OpenAI embedding has not been written yet (initial state, or transient
 *    failure that the Part 2 background worker will retry).
 *  - 'done':    Vector is current and queryable.
 *  - 'failed':  Background worker gave up after exceeding `embedding_attempt_count`.
 *
 * UI may surface a small "synced" indicator when `'done'`; `'pending'` and `'failed'`
 * are intentionally not exposed verbatim because users don't action them.
 */
export type FishSniperEmbeddingStatus = 'pending' | 'done' | 'failed'

export interface FishingLogResponsePayload {
  log_id: string
  date: string
  fishing_location: string
  fishing_scene: string
  target_species: FishSniperStrategyTargetSpecies
  water_depth_m: number
  lure_type: string
  lure_color: string
  retrieve_speed: string
  caught_count: number
  weight_lb: number | null
  length_cm: number | null
  temperature_c: number
  wind_speed_ms: number
  pressure_hpa: number
  condition_code: string
  notes: string
  embedding_status: FishSniperEmbeddingStatus
  embedding_text_version: number
  created_at: string
  updated_at: string
}

export interface CreateFishingLogResponsePayload {
  log_id: string
}

export interface CreateOrUpdateFishingLogRequestPayload {
  date: string
  fishing_location: string
  fishing_scene: string
  target_species: FishSniperStrategyTargetSpecies
  water_depth_m: number
  lure_type: string
  lure_color: string
  retrieve_speed: string
  caught_count: number
  weight_lb: number | null
  length_cm: number | null
  temperature_c: number
  wind_speed_ms: number
  pressure_hpa: number
  condition_code: string
  notes: string
}
