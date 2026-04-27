import { useCallback, useMemo, useState } from 'react'

import {
  clearFishSniperAccessTokenJwtFromBrowserStorage,
  readFishSniperAccessTokenJwtFromBrowserStorage,
  writeFishSniperAccessTokenJwtToBrowserStorage,
} from '../auth/fishSniperAccessTokenStorage.ts'

export function useFishSniperAuthSessionState() {
  const [accessTokenJwt, setAccessTokenJwtState] = useState<string | null>(() => {
    return readFishSniperAccessTokenJwtFromBrowserStorage()
  })

  const persistAccessTokenJwt = useCallback((nextAccessTokenJwt: string) => {
    writeFishSniperAccessTokenJwtToBrowserStorage(nextAccessTokenJwt)
    setAccessTokenJwtState(nextAccessTokenJwt)
  }, [])

  const clearAccessTokenJwt = useCallback(() => {
    clearFishSniperAccessTokenJwtFromBrowserStorage()
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
