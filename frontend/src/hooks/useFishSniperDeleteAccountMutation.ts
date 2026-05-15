import { useCallback, useMemo, useState } from 'react'

import {
  deleteJsonWithFishSniperApi,
  FishSniperHttpStatusError,
  FishSniperHttpTimeoutError,
} from '../api/fishSniperJsonHttpClient.ts'

export function useFishSniperDeleteAccountMutation(options: {
  apiBaseUrl: string
  accessTokenJwt: string | null
  onUnauthorizedAccessToken?: () => void
}) {
  const [isDeletingAccount, setIsDeletingAccount] = useState(false)
  const [deleteAccountHardFailureMessage, setDeleteAccountHardFailureMessage] = useState<
    string | null
  >(null)

  const deleteFishSniperAccount = useCallback(async (): Promise<boolean> => {
    if (!options.accessTokenJwt) {
      setDeleteAccountHardFailureMessage('You must be signed in to delete your account.')
      return false
    }
    setIsDeletingAccount(true)
    setDeleteAccountHardFailureMessage(null)
    try {
      await deleteJsonWithFishSniperApi({
        apiBaseUrl: options.apiBaseUrl,
        path: '/users/me',
        requestBody: { confirmation: 'Delete' },
        accessTokenJwt: options.accessTokenJwt,
      })
    } catch (unknownError) {
      if (unknownError instanceof FishSniperHttpStatusError) {
        if (unknownError.httpStatusCode === 401) {
          options.onUnauthorizedAccessToken?.()
        }
        setDeleteAccountHardFailureMessage(unknownError.responseBodyText)
      } else if (unknownError instanceof FishSniperHttpTimeoutError) {
        setDeleteAccountHardFailureMessage(unknownError.message)
      } else {
        setDeleteAccountHardFailureMessage('Could not delete your account. Please try again.')
      }
      setIsDeletingAccount(false)
      return false
    }
    setIsDeletingAccount(false)
    return true
  }, [options.accessTokenJwt, options.apiBaseUrl, options.onUnauthorizedAccessToken])

  return useMemo(() => {
    return {
      isDeletingAccount,
      deleteAccountHardFailureMessage,
      deleteFishSniperAccount,
    }
  }, [deleteAccountHardFailureMessage, deleteFishSniperAccount, isDeletingAccount])
}
