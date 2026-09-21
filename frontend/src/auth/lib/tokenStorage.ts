const ACCESS_TOKEN_STORAGE_KEY = 'fishsniper.accessToken'

// 從 localStorage 讀取先前登入後保存的 FishSniper access token。
export function readAccessTokenFromStorage(): string | null {
  return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)
}

// 將後端簽發的 FishSniper access token 保存到 localStorage。
export function writeAccessTokenToStorage(accessToken: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, accessToken)
}

// 登出或 token 失效時，從 localStorage 移除 FishSniper access token。
export function clearAccessTokenFromStorage(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
}
