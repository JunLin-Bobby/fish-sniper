import { useCallback, useMemo, useState } from 'react'

import type { SaveUserPreferencesResponsePayload } from '../api/fishSniperApiTypes.ts'
import {
  FishSniperHttpStatusError,
  FishSniperHttpTimeoutError,
  postJsonWithFishSniperApi,
} from '../api/fishSniperJsonHttpClient.ts'

export function useFishSniperSaveRegionOnboardingMutation(options: {
  apiBaseUrl: string
  accessTokenJwt: string | null
}) {
  const [isSavingRegion, setIsSavingRegion] = useState(false)
  const [saveRegionHardFailureMessage, setSaveRegionHardFailureMessage] = useState<string | null>(
    null,
  )

  const saveUserProfileRegionForOnboarding = useCallback(
    async (profileRegionDisplayName: string): Promise<boolean> => {
      if (!options.accessTokenJwt) {
        setSaveRegionHardFailureMessage('You must be signed in to save your region.')
        return false
      }
      setIsSavingRegion(true)
      setSaveRegionHardFailureMessage(null)
      try {
        await postJsonWithFishSniperApi<SaveUserPreferencesResponsePayload>({
          apiBaseUrl: options.apiBaseUrl,
          path: '/users/preferences',
          requestBody: { region: profileRegionDisplayName },
          accessTokenJwt: options.accessTokenJwt,
        })
      } catch (unknownError) {
        if (unknownError instanceof FishSniperHttpStatusError) {
          setSaveRegionHardFailureMessage(unknownError.responseBodyText)
        } else if (unknownError instanceof FishSniperHttpTimeoutError) {
          setSaveRegionHardFailureMessage(unknownError.message)
        } else {
          setSaveRegionHardFailureMessage('Could not save your region. Please try again.')
        }
        setIsSavingRegion(false)
        return false
      }
      setIsSavingRegion(false)
      return true
    },
    [options.accessTokenJwt, options.apiBaseUrl],
  )

  return useMemo(() => {
    return {
      isSavingRegion,
      saveRegionHardFailureMessage,
      saveUserProfileRegionForOnboarding,
    }
  }, [isSavingRegion, saveRegionHardFailureMessage, saveUserProfileRegionForOnboarding])
}
