/** Browser persistence for the access JWT. */

const ACCESS_TOKEN_STORAGE_KEY = 'access_token_jwt_v1'

export function readAccessTokenFromStorage(): string | null {
  return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)
}

export function writeAccessTokenToStorage(accessTokenJwt: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, accessTokenJwt)
}

export function clearAccessTokenFromStorage(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
}
