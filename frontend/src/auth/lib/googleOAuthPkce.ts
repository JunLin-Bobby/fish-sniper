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

// 將位元組轉成 OAuth PKCE 使用的 Base64URL 字串格式。
function base64UrlEncodeBytes(bytes: Uint8Array): string {
  const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join('')
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

// 使用瀏覽器的安全亂數產生 state 或 code_verifier。
function createRandomBase64UrlString(byteLength: number): string {
  const bytes = new Uint8Array(byteLength)
  crypto.getRandomValues(bytes)
  return base64UrlEncodeBytes(bytes)
}

// 對 code_verifier 做 SHA-256，產生要先交給 Google 的 code_challenge。
async function createCodeChallenge(codeVerifier: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(codeVerifier))
  return base64UrlEncodeBytes(new Uint8Array(digest))
}

// 暫存本次登入請求，讓 Google 導回 callback 頁面後可以接續驗證與交換。
function writeStoredGoogleOAuthRequest(request: StoredGoogleOAuthRequest): void {
  sessionStorage.setItem(GOOGLE_OAUTH_CODE_VERIFIER_STORAGE_KEY, request.codeVerifier)
  sessionStorage.setItem(GOOGLE_OAUTH_STATE_STORAGE_KEY, request.state)
  sessionStorage.setItem(GOOGLE_OAUTH_REDIRECT_URI_STORAGE_KEY, request.redirectUri)
}

// 從目前分頁的 sessionStorage 讀取登入開始前保存的 PKCE 與 state 資料。
export function readStoredGoogleOAuthRequest(): StoredGoogleOAuthRequest | null {
  const codeVerifier = sessionStorage.getItem(GOOGLE_OAUTH_CODE_VERIFIER_STORAGE_KEY)
  const state = sessionStorage.getItem(GOOGLE_OAUTH_STATE_STORAGE_KEY)
  const redirectUri = sessionStorage.getItem(GOOGLE_OAUTH_REDIRECT_URI_STORAGE_KEY)

  if (!codeVerifier || !state || !redirectUri) {
    return null
  }

  return { codeVerifier, redirectUri, state }
}

// 登入完成或失敗後清除一次性的 OAuth 請求資料，避免被重複使用。
export function clearStoredGoogleOAuthRequest(): void {
  sessionStorage.removeItem(GOOGLE_OAUTH_CODE_VERIFIER_STORAGE_KEY)
  sessionStorage.removeItem(GOOGLE_OAUTH_STATE_STORAGE_KEY)
  sessionStorage.removeItem(GOOGLE_OAUTH_REDIRECT_URI_STORAGE_KEY)
}

// 建立 PKCE 與 state、組合 Google 授權網址，最後將瀏覽器導向 Google 登入頁。
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
