/**
 * Deduplicates Google OAuth authorization-code exchange across React StrictMode
 * double-mount in development: only one HTTP exchange runs per `code`, and every
 * caller awaits the same in-flight Promise (so the active mount can apply the result).
 *
 * A plain `Set<string>` alone is not enough once the exchange is async: the first
 * effect's promise can resolve after unmount, and the second effect would early-return
 * without ever updating UI. Sharing the Promise fixes that.
 */

import type {
  GoogleOAuthExchangeRequestPayload,
  GoogleOAuthExchangeResponsePayload,
} from '../api/fishSniperApiTypes.ts'
import {
  FishSniperHttpStatusError,
  FishSniperHttpTimeoutError,
  postJsonWithFishSniperApi,
} from '../api/fishSniperJsonHttpClient.ts'
import { readAndClearPendingPkceFlowStateFromSessionStorage } from './fishSniperGoogleOAuthPkce.ts'

export type FishSniperGoogleOAuthExchangeDedupeResult =
  | { kind: 'oauth_query_error'; message: string }
  | { kind: 'preflight_error'; message: string }
  | { kind: 'success'; accessToken: string }
  | { kind: 'server_error'; message: string }

const pendingExchangesByAuthorizationCode = new Map<
  string,
  Promise<FishSniperGoogleOAuthExchangeDedupeResult>
>()

function buildGoogleOAuthExchangePromiseForAuthorizationCode(options: {
  authorizationCode: string
  apiBaseUrl: string
}): Promise<FishSniperGoogleOAuthExchangeDedupeResult> {
  return (async (): Promise<FishSniperGoogleOAuthExchangeDedupeResult> => {
    const queryParameters = new URLSearchParams(window.location.search)
    const returnedState = queryParameters.get('state')
    const oauthErrorCode = queryParameters.get('error')

    if (oauthErrorCode) {
      return {
        kind: 'oauth_query_error',
        message: `Google sign-in was cancelled or rejected (${oauthErrorCode}).`,
      }
    }
    if (!returnedState) {
      return {
        kind: 'preflight_error',
        message: 'Missing authorization code or state in the callback URL.',
      }
    }

    const pendingPkceFlowState = readAndClearPendingPkceFlowStateFromSessionStorage()
    if (!pendingPkceFlowState) {
      return {
        kind: 'preflight_error',
        message:
          'Could not find the original sign-in attempt. Please start again from the sign-in page.',
      }
    }
    if (pendingPkceFlowState.state !== returnedState) {
      return {
        kind: 'preflight_error',
        message: 'Sign-in state mismatch. Please start again from the sign-in page.',
      }
    }

    const requestBody: GoogleOAuthExchangeRequestPayload = {
      code: options.authorizationCode,
      code_verifier: pendingPkceFlowState.codeVerifier,
      redirect_uri: pendingPkceFlowState.redirectUri,
    }

    try {
      const exchangeResponse = await postJsonWithFishSniperApi<GoogleOAuthExchangeResponsePayload>(
        {
          apiBaseUrl: options.apiBaseUrl,
          path: '/auth/google/exchange',
          requestBody,
        },
      )
      return { kind: 'success', accessToken: exchangeResponse.access_token }
    } catch (unknownError) {
      if (unknownError instanceof FishSniperHttpStatusError) {
        return {
          kind: 'server_error',
          message:
            unknownError.httpStatusCode === 403
              ? 'Your Google account email is not verified. Please verify it and try again.'
              : 'Google sign-in could not be completed. Please try again.',
        }
      }
      if (unknownError instanceof FishSniperHttpTimeoutError) {
        return { kind: 'server_error', message: unknownError.message }
      }
      return {
        kind: 'server_error',
        message: 'Unexpected error while completing Google sign-in.',
      }
    }
  })()
}

/**
 * Returns an existing in-flight/completed promise for this `authorizationCode`, or
 * starts a new exchange and caches it until the promise settles (then deletes).
 */
export function getOrStartGoogleOAuthAuthorizationCodeExchange(options: {
  authorizationCode: string
  apiBaseUrl: string
}): Promise<FishSniperGoogleOAuthExchangeDedupeResult> {
  const existingPromise = pendingExchangesByAuthorizationCode.get(options.authorizationCode)
  if (existingPromise) {
    return existingPromise
  }

  const createdPromise = buildGoogleOAuthExchangePromiseForAuthorizationCode(options)
  pendingExchangesByAuthorizationCode.set(options.authorizationCode, createdPromise)

  void createdPromise.finally(() => {
    pendingExchangesByAuthorizationCode.delete(options.authorizationCode)
  })

  return createdPromise
}
