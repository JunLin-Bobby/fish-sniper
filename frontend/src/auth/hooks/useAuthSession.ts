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

export function useAuthSession(): AuthSession {
  const [accessToken, setAccessToken] = useState<string | null>(() => readAccessTokenFromStorage())

  const persistAccessToken = useCallback((token: string) => {
    writeAccessTokenToStorage(token)
    setAccessToken(token)
  }, [])

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
