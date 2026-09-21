import { useCallback, useMemo, useState } from 'react'

import {
  clearAccessTokenFromStorage,
  readAccessTokenFromStorage,
  writeAccessTokenToStorage,
} from '../lib/tokenStorage.ts'

export interface AuthSession {
  accessToken: string | null
  persistAccessToken: (accessToken: string) => void
  signOut: () => void
}

// 管理目前的 FishSniper access token，並同步瀏覽器儲存空間與 React 狀態。
export function useAuthSession(): AuthSession {
  const [accessToken, setAccessToken] = useState<string | null>(() => readAccessTokenFromStorage())

  // 登入成功後保存後端簽發的 token，並立即更新畫面上的登入狀態。
  const persistAccessToken = useCallback((token: string) => {
    writeAccessTokenToStorage(token)
    setAccessToken(token)
  }, [])

  // 登出時移除本機 token，並將 React 狀態切回未登入。
  const signOut = useCallback(() => {
    clearAccessTokenFromStorage()
    setAccessToken(null)
  }, [])

  return useMemo(
    () => ({
      accessToken,
      persistAccessToken,
      signOut,
    }),
    [accessToken, persistAccessToken, signOut],
  )
}
