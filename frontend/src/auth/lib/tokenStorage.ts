const ACCESS_TOKEN_STORAGE_KEY = 'fishsniper.accessToken'

export function readAccessTokenFromStorage(): string | null {
  return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)
}

export function writeAccessTokenToStorage(accessToken: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, accessToken)
}

export function clearAccessTokenFromStorage(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
}
