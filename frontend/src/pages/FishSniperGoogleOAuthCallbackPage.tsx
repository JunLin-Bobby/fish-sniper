import { useEffect, useRef, useState } from 'react'

import { getOrStartGoogleOAuthAuthorizationCodeExchange } from '../auth/fishSniperGoogleOAuthExchangeDedupe.ts'

/** Renders the `/auth/google/callback` page that exchanges the auth code with backend. */
export function FishSniperGoogleOAuthCallbackPage(options: {
  apiBaseUrl: string
  onAuthenticatedWithAccessToken: (accessTokenJwt: string) => void
  onReturnToSignIn: () => void
}) {
  const [callbackStatusMessage, setCallbackStatusMessage] = useState<string>(
    'Completing Google sign-in…',
  )
  const [callbackFailureMessage, setCallbackFailureMessage] = useState<string | null>(null)

  const optionsRef = useRef(options)
  optionsRef.current = options

  useEffect(() => {
    let cancelled = false

    const queryParameters = new URLSearchParams(window.location.search)
    const authorizationCode = queryParameters.get('code')
    const returnedState = queryParameters.get('state')
    const oauthErrorCode = queryParameters.get('error')

    if (oauthErrorCode) {
      setCallbackFailureMessage(
        `Google sign-in was cancelled or rejected (${oauthErrorCode}).`,
      )
      return
    }
    if (!authorizationCode || !returnedState) {
      setCallbackFailureMessage('Missing authorization code or state in the callback URL.')
      return
    }

    const exchangePromise = getOrStartGoogleOAuthAuthorizationCodeExchange({
      authorizationCode,
      apiBaseUrl: optionsRef.current.apiBaseUrl,
    })

    void exchangePromise.then((result) => {
      if (cancelled) {
        return
      }
      if (result.kind === 'success') {
        optionsRef.current.onAuthenticatedWithAccessToken(result.accessToken)
        setCallbackStatusMessage('Signed in. Redirecting…')
        return
      }
      setCallbackFailureMessage(result.message)
    })

    return () => {
      cancelled = true
    }
  }, [options.apiBaseUrl])

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-5 text-center">
        <h1 className="text-3xl font-bold text-emerald-400 tracking-tight">FishSniper</h1>
        {callbackFailureMessage ? (
          <>
            <p className="text-sm text-red-400">{callbackFailureMessage}</p>
            <button
              type="button"
              className="rounded-md bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-semibold px-4 py-2 text-sm"
              onClick={() => options.onReturnToSignIn()}
            >
              Back to sign-in
            </button>
          </>
        ) : (
          <p className="text-sm text-gray-400 animate-pulse">{callbackStatusMessage}</p>
        )}
      </div>
    </div>
  )
}
