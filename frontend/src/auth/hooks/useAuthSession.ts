import { useCallback, useMemo, useState } from 'react'

import {
  clearAccessTokenFromStorage,
  readAccessTokenFromStorage,
  writeAccessTokenToStorage,
} from '../lib/accessTokenStorage.ts'

export interface AuthSessionState {
  accessTokenJwt: string | null
  persistAccessTokenJwt: (nextAccessTokenJwt: string) => void
  clearAccessTokenJwt: () => void
}

export function useAuthSession(): AuthSessionState {
  const [accessTokenJwt, setAccessTokenJwtState] = useState<string | null>(() => {
    return readAccessTokenFromStorage()
  })

  const persistAccessTokenJwt = useCallback((nextAccessTokenJwt: string) => {
    writeAccessTokenToStorage(nextAccessTokenJwt)
    setAccessTokenJwtState(nextAccessTokenJwt)
  }, [])

  const clearAccessTokenJwt = useCallback(() => {
    clearAccessTokenFromStorage()
    setAccessTokenJwtState(null)
  }, [])

  return useMemo(() => {
    return {
      accessTokenJwt,
      persistAccessTokenJwt,
      clearAccessTokenJwt,
    }
  }, [accessTokenJwt, clearAccessTokenJwt, persistAccessTokenJwt])
}