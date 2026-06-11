import { useEffect, useRef, useState } from 'react'

import { getOrStartGoogleOAuthAuthorizationCodeExchange } from '../auth/fishSniperGoogleOAuthExchangeDedupe.ts'
import { FishSniperTacticalAuthShell } from '../ui/FishSniperTacticalAuthShell.tsx'
import {
  fishSniperTacticalAuthCardClassName,
  fishSniperTacticalErrorBannerClassName,
  fishSniperTacticalGhostButtonClassName,
  fishSniperTacticalMutedTextClassName,
} from '../ui/fishSniperTacticalUi.ts'

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
    <FishSniperTacticalAuthShell title="FishSniper" subtitle="Completing sign-in">
      <div className={`${fishSniperTacticalAuthCardClassName} text-center`}>
        {callbackFailureMessage ? (
          <>
            <p className={fishSniperTacticalErrorBannerClassName}>{callbackFailureMessage}</p>
            <button
              type="button"
              className={fishSniperTacticalGhostButtonClassName}
              onClick={() => options.onReturnToSignIn()}
            >
              Back to sign-in
            </button>
          </>
        ) : (
          <p className={`${fishSniperTacticalMutedTextClassName} motion-safe:animate-pulse motion-reduce:animate-none`}>
            {callbackStatusMessage}
          </p>
        )}
      </div>
    </FishSniperTacticalAuthShell>
  )
}
