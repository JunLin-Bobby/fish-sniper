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
