/** Reads public (non-secret) build-time environment variables for the web app. */

export function readApiBaseUrlFromPublicEnv(): string {
  const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL
  if (typeof rawApiBaseUrl !== 'string' || rawApiBaseUrl.trim().length === 0) {
    throw new Error('Missing VITE_API_BASE_URL. Copy frontend/.env.example to frontend/.env.')
  }
  return rawApiBaseUrl.replace(/\/$/, '')
}

export interface GoogleOAuthPublicConfig {
  clientId: string
  redirectUri: string
}

export function readGoogleOAuthPublicConfigFromEnvOrNull(): GoogleOAuthPublicConfig | null {
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
