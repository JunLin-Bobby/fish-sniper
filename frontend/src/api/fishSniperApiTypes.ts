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

export interface ManualWeatherRequestPayload {
  temperature_c: number
  condition_code: string
  wind_speed_ms: number
  pressure_hpa: number
}

export interface GenerateBassStrategyRequestPayload {
  fishing_location: string
  water_depth_m: number
  fishing_scene: string
  target_species: string
  manual_weather?: ManualWeatherRequestPayload | null
}

export interface WeatherSnapshotPayload {
  temperature_c: number
  pressure_hpa: number
  wind_speed_ms: number
  condition_code: string
}

export interface GenerateBassStrategySuccessResponsePayload {
  lure_type: string
  lure_color: string
  retrieve_speed: string
  target_zone: string
  time_window: string
  confidence_note: string
  battle_plan_summary: string
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
