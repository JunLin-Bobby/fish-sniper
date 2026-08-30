import type { GoogleOAuthPublicConfig } from '../../config/env.ts'

const GOOGLE_AUTHORIZE_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
const GOOGLE_OAUTH_CODE_VERIFIER_STORAGE_KEY = 'fishsniper.googleOAuth.codeVerifier'
const GOOGLE_OAUTH_STATE_STORAGE_KEY = 'fishsniper.googleOAuth.state'
const GOOGLE_OAUTH_REDIRECT_URI_STORAGE_KEY = 'fishsniper.googleOAuth.redirectUri'

export interface StoredGoogleOAuthRequest {
  codeVerifier: string
  redirectUri: string
  state: string
}

function base64UrlEncodeBytes(bytes: Uint8Array): string {
  const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join('')
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function createRandomBase64UrlString(byteLength: number): string {
  const bytes = new Uint8Array(byteLength)
  crypto.getRandomValues(bytes)
  return base64UrlEncodeBytes(bytes)
}

async function createCodeChallenge(codeVerifier: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(codeVerifier))
  return base64UrlEncodeBytes(new Uint8Array(digest))
}

function writeStoredGoogleOAuthRequest(request: StoredGoogleOAuthRequest): void {
  sessionStorage.setItem(GOOGLE_OAUTH_CODE_VERIFIER_STORAGE_KEY, request.codeVerifier)
  sessionStorage.setItem(GOOGLE_OAUTH_STATE_STORAGE_KEY, request.state)
  sessionStorage.setItem(GOOGLE_OAUTH_REDIRECT_URI_STORAGE_KEY, request.redirectUri)
}

export function readStoredGoogleOAuthRequest(): StoredGoogleOAuthRequest | null {
  const codeVerifier = sessionStorage.getItem(GOOGLE_OAUTH_CODE_VERIFIER_STORAGE_KEY)
  const state = sessionStorage.getItem(GOOGLE_OAUTH_STATE_STORAGE_KEY)
  const redirectUri = sessionStorage.getItem(GOOGLE_OAUTH_REDIRECT_URI_STORAGE_KEY)

  if (!codeVerifier || !state || !redirectUri) {
    return null
  }

  return { codeVerifier, redirectUri, state }
}

export function clearStoredGoogleOAuthRequest(): void {
  sessionStorage.removeItem(GOOGLE_OAUTH_CODE_VERIFIER_STORAGE_KEY)
  sessionStorage.removeItem(GOOGLE_OAUTH_STATE_STORAGE_KEY)
  sessionStorage.removeItem(GOOGLE_OAUTH_REDIRECT_URI_STORAGE_KEY)
}

export async function beginGoogleOAuthAuthorizationFlowFromBrowser(
  config: GoogleOAuthPublicConfig,
): Promise<void> {
  const codeVerifier = createRandomBase64UrlString(32)
  const state = createRandomBase64UrlString(32)
  const codeChallenge = await createCodeChallenge(codeVerifier)

  writeStoredGoogleOAuthRequest({
    codeVerifier,
    redirectUri: config.redirectUri,
    state,
  })

  const authorizeUrl = new URL(GOOGLE_AUTHORIZE_ENDPOINT)
  authorizeUrl.searchParams.set('client_id', config.clientId)
  authorizeUrl.searchParams.set('redirect_uri', config.redirectUri)
  authorizeUrl.searchParams.set('response_type', 'code')
  authorizeUrl.searchParams.set('scope', 'openid email profile')
  authorizeUrl.searchParams.set('state', state)
  authorizeUrl.searchParams.set('code_challenge', codeChallenge)
  authorizeUrl.searchParams.set('code_challenge_method', 'S256')
  authorizeUrl.searchParams.set('prompt', 'select_account')

  window.location.assign(authorizeUrl.toString())
}
