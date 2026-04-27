import { useCallback, useEffect, useMemo, useState } from 'react'

import type { UserPreferencesResponsePayload } from '../api/fishSniperApiTypes.ts'
import {
  FishSniperHttpStatusError,
  FishSniperHttpTimeoutError,
  getJsonWithFishSniperApi,
} from '../api/fishSniperJsonHttpClient.ts'

export type FishSniperUserPreferencesRemoteStatus = 'idle' | 'loading' | 'ready' | 'error'

export function useFishSniperUserPreferencesRemoteState(options: {
  apiBaseUrl: string
  accessTokenJwt: string | null
  onUnauthorizedAccessToken?: () => void
}) {
  const [remoteStatus, setRemoteStatus] = useState<FishSniperUserPreferencesRemoteStatus>('idle')
  const [userPreferences, setUserPreferences] = useState<UserPreferencesResponsePayload | null>(
    null,
  )
  const [hardFailureMessage, setHardFailureMessage] = useState<string | null>(null)

  const reloadUserPreferences = useCallback(async () => {
    if (!options.accessTokenJwt) {
      setRemoteStatus('idle')
      setUserPreferences(null)
      setHardFailureMessage(null)
      return
    }

    setRemoteStatus('loading')
    setHardFailureMessage(null)
    try {
      const loadedPreferences = await getJsonWithFishSniperApi<UserPreferencesResponsePayload>({
        apiBaseUrl: options.apiBaseUrl,
        path: '/users/preferences',
        accessTokenJwt: options.accessTokenJwt,
      })
      setUserPreferences(loadedPreferences)
      setRemoteStatus('ready')
    } catch (unknownError) {
      if (unknownError instanceof FishSniperHttpStatusError) {
        if (unknownError.httpStatusCode === 401) {
          options.onUnauthorizedAccessToken?.()
          setHardFailureMessage('Your session expired. Please sign in again.')
        } else {
          setHardFailureMessage(unknownError.responseBodyText)
        }
      } else if (unknownError instanceof FishSniperHttpTimeoutError) {
        setHardFailureMessage(unknownError.message)
      } else {
        setHardFailureMessage('Could not load your profile. Please try again.')
      }
      setRemoteStatus('error')
    }
  }, [options.accessTokenJwt, options.apiBaseUrl, options.onUnauthorizedAccessToken])

  useEffect(() => {
    void reloadUserPreferences()
  }, [reloadUserPreferences])

  return useMemo(() => {
    return {
      remoteStatus,
      userPreferences,
      hardFailureMessage,
      reloadUserPreferences,
    }
  }, [hardFailureMessage, reloadUserPreferences, remoteStatus, userPreferences])
}
