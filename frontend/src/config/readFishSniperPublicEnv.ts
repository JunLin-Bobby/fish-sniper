/** Reads public (non-secret) build-time environment variables for the FishSniper web app. */

export function readFishSniperApiBaseUrlFromPublicEnv(): string {
  const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL
  if (typeof rawApiBaseUrl !== 'string' || rawApiBaseUrl.trim().length === 0) {
    throw new Error('Missing VITE_API_BASE_URL. Copy frontend/.env.example to frontend/.env.')
  }
  return rawApiBaseUrl.replace(/\/$/, '')
}
