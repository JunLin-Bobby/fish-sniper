export function readApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
}

export interface GoogleOAuthPublicConfig {
  clientId: string
  redirectUri: string
}

export function readGoogleOAuthPublicConfig(): GoogleOAuthPublicConfig | null {
  const clientId = import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID
  const redirectUri = import.meta.env.VITE_GOOGLE_OAUTH_REDIRECT_URI

  if (!clientId || !redirectUri) {
    return null
  }

  return { clientId, redirectUri }
}
