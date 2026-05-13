/** Reads public (non-secret) build-time environment variables for the FishSniper web app. */

export function readFishSniperApiBaseUrlFromPublicEnv(): string {
  const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL
  if (typeof rawApiBaseUrl !== 'string' || rawApiBaseUrl.trim().length === 0) {
    throw new Error('Missing VITE_API_BASE_URL. Copy frontend/.env.example to frontend/.env.')
  }
  return rawApiBaseUrl.replace(/\/$/, '')
}

export interface FishSniperGoogleOAuthPublicConfig {
  clientId: string
  redirectUri: string
}

export function readFishSniperGoogleOAuthPublicConfigFromEnvOrNull(): FishSniperGoogleOAuthPublicConfig | null {
  const rawClientId = import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID
  const rawRedirectUri = import.meta.env.VITE_GOOGLE_OAUTH_REDIRECT_URI
  if (
    typeof rawClientId !== 'string' ||
    rawClientId.trim().length === 0 ||
    typeof rawRedirectUri !== 'string' ||
    rawRedirectUri.trim().length === 0
  ) {
    return null
  }
  return { clientId: rawClientId.trim(), redirectUri: rawRedirectUri.trim() }
}

export function readFishSniperShouldShowEmailOtpLoginFromEnv(): boolean {
  const rawValue = import.meta.env.VITE_SHOW_EMAIL_OTP_LOGIN
  if (typeof rawValue !== 'string') {
    return true
  }
  return rawValue.trim().toLowerCase() !== 'false'
}
