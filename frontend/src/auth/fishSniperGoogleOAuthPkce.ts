/**
 * PKCE + state helpers for the FishSniper Google OAuth flow.
 *
 * - Generates a high-entropy `code_verifier` and the S256 `code_challenge`.
 * - Stores the verifier + a CSRF `state` in `sessionStorage` until the callback
 *   page exchanges the resulting code with the backend.
 * - Redirects the browser to Google's authorize endpoint.
 */

const FISH_SNIPER_GOOGLE_OAUTH_PKCE_VERIFIER_SESSION_KEY =
  'fish_sniper_google_oauth_pkce_verifier_v1'
const FISH_SNIPER_GOOGLE_OAUTH_PKCE_STATE_SESSION_KEY =
  'fish_sniper_google_oauth_pkce_state_v1'
const FISH_SNIPER_GOOGLE_OAUTH_PKCE_REDIRECT_URI_SESSION_KEY =
  'fish_sniper_google_oauth_pkce_redirect_uri_v1'

const GOOGLE_OAUTH_AUTHORIZE_ENDPOINT_URL =
  'https://accounts.google.com/o/oauth2/v2/auth'
const GOOGLE_OAUTH_REQUESTED_SCOPE_LIST = ['openid', 'email', 'profile']

function encodeArrayBufferAsBase64Url(arrayBuffer: ArrayBuffer): string {
  const byteArray = new Uint8Array(arrayBuffer)
  let binaryString = ''
  for (let i = 0; i < byteArray.length; i += 1) {
    binaryString += String.fromCharCode(byteArray[i])
  }
  const base64 = window.btoa(binaryString)
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function generateRandomUrlSafeString(numBytes: number): string {
  const randomBytes = new Uint8Array(numBytes)
  window.crypto.getRandomValues(randomBytes)
  return encodeArrayBufferAsBase64Url(randomBytes.buffer)
}

export async function generateCodeChallengeS256FromVerifier(
  codeVerifier: string,
): Promise<string> {
  const encoded = new TextEncoder().encode(codeVerifier)
  const digest = await window.crypto.subtle.digest('SHA-256', encoded)
  return encodeArrayBufferAsBase64Url(digest)
}

export function persistPendingPkceVerifierAndStateToSessionStorage(options: {
  codeVerifier: string
  state: string
  redirectUri: string
}): void {
  window.sessionStorage.setItem(
    FISH_SNIPER_GOOGLE_OAUTH_PKCE_VERIFIER_SESSION_KEY,
    options.codeVerifier,
  )
  window.sessionStorage.setItem(
    FISH_SNIPER_GOOGLE_OAUTH_PKCE_STATE_SESSION_KEY,
    options.state,
  )
  window.sessionStorage.setItem(
    FISH_SNIPER_GOOGLE_OAUTH_PKCE_REDIRECT_URI_SESSION_KEY,
    options.redirectUri,
  )
}

export interface PendingPkceFlowState {
  codeVerifier: string
  state: string
  redirectUri: string
}

export function readAndClearPendingPkceFlowStateFromSessionStorage(): PendingPkceFlowState | null {
  const codeVerifier = window.sessionStorage.getItem(
    FISH_SNIPER_GOOGLE_OAUTH_PKCE_VERIFIER_SESSION_KEY,
  )
  const state = window.sessionStorage.getItem(
    FISH_SNIPER_GOOGLE_OAUTH_PKCE_STATE_SESSION_KEY,
  )
  const redirectUri = window.sessionStorage.getItem(
    FISH_SNIPER_GOOGLE_OAUTH_PKCE_REDIRECT_URI_SESSION_KEY,
  )
  window.sessionStorage.removeItem(FISH_SNIPER_GOOGLE_OAUTH_PKCE_VERIFIER_SESSION_KEY)
  window.sessionStorage.removeItem(FISH_SNIPER_GOOGLE_OAUTH_PKCE_STATE_SESSION_KEY)
  window.sessionStorage.removeItem(FISH_SNIPER_GOOGLE_OAUTH_PKCE_REDIRECT_URI_SESSION_KEY)
  if (!codeVerifier || !state || !redirectUri) {
    return null
  }
  return { codeVerifier, state, redirectUri }
}

export function buildGoogleAuthorizeUrl(options: {
  clientId: string
  redirectUri: string
  codeChallenge: string
  state: string
}): string {
  const queryParameters = new URLSearchParams({
    response_type: 'code',
    client_id: options.clientId,
    redirect_uri: options.redirectUri,
    scope: GOOGLE_OAUTH_REQUESTED_SCOPE_LIST.join(' '),
    code_challenge: options.codeChallenge,
    code_challenge_method: 'S256',
    state: options.state,
    access_type: 'online',
    prompt: 'select_account',
  })
  return `${GOOGLE_OAUTH_AUTHORIZE_ENDPOINT_URL}?${queryParameters.toString()}`
}

export async function beginGoogleOAuthAuthorizationFlowFromBrowser(options: {
  clientId: string
  redirectUri: string
}): Promise<void> {
  const codeVerifier = generateRandomUrlSafeString(64)
  const state = generateRandomUrlSafeString(32)
  const codeChallenge = await generateCodeChallengeS256FromVerifier(codeVerifier)

  persistPendingPkceVerifierAndStateToSessionStorage({
    codeVerifier,
    state,
    redirectUri: options.redirectUri,
  })

  const authorizeUrl = buildGoogleAuthorizeUrl({
    clientId: options.clientId,
    redirectUri: options.redirectUri,
    codeChallenge,
    state,
  })
  window.location.assign(authorizeUrl)
}
