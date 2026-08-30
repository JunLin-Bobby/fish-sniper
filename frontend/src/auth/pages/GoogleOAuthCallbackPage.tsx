import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { exchangeGoogleOAuthAuthorizationCode } from '../api/authApi.ts'
import {
  clearStoredGoogleOAuthRequest,
  readStoredGoogleOAuthRequest,
} from '../lib/googleOAuthPkce.ts'

export function GoogleOAuthCallbackPage(props: {
  apiBaseUrl: string
  persistAccessToken: (accessToken: string) => void
}) {
  const navigate = useNavigate()
  const hasStartedExchange = useRef(false)
  const [failureMessage, setFailureMessage] = useState<string | null>(null)
  const [statusMessage, setStatusMessage] = useState('Completing Google sign-in...')

  useEffect(() => {
    if (hasStartedExchange.current) {
      return
    }
    hasStartedExchange.current = true

    const completeSignIn = async (): Promise<void> => {
      const queryParameters = new URLSearchParams(window.location.search)
      const oauthErrorCode = queryParameters.get('error')
      const authorizationCode = queryParameters.get('code')
      const returnedState = queryParameters.get('state')
      const storedRequest = readStoredGoogleOAuthRequest()

      if (oauthErrorCode) {
        setFailureMessage(`Google sign-in was cancelled or rejected (${oauthErrorCode}).`)
        clearStoredGoogleOAuthRequest()
        return
      }
      if (!authorizationCode || !returnedState) {
        setFailureMessage('Missing authorization code or state in the callback URL.')
        clearStoredGoogleOAuthRequest()
        return
      }
      if (!storedRequest || storedRequest.state !== returnedState) {
        setFailureMessage('Sign-in state mismatch. Please start again from the sign-in page.')
        clearStoredGoogleOAuthRequest()
        return
      }

      try {
        const exchangeResponse = await exchangeGoogleOAuthAuthorizationCode({
          apiBaseUrl: props.apiBaseUrl,
          requestBody: {
            code: authorizationCode,
            code_verifier: storedRequest.codeVerifier,
            redirect_uri: storedRequest.redirectUri,
          },
        })
        props.persistAccessToken(exchangeResponse.access_token)
        clearStoredGoogleOAuthRequest()
        setStatusMessage('Signed in. Redirecting...')
        navigate('/', { replace: true })
      } catch {
        setFailureMessage('Google sign-in could not be completed. Please try again.')
        clearStoredGoogleOAuthRequest()
      }
    }

    void completeSignIn()
  }, [navigate, props])

  return (
    <main className="relative grid min-h-dvh place-items-center px-4 py-10 text-[var(--fs-ink)]">
      <section className="w-full max-w-md rounded-[1.5rem] border border-[var(--fs-line)] bg-black/40 p-6 text-center shadow-[0_32px_90px_rgba(0,0,0,0.46)] backdrop-blur-md sm:p-8">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--fs-faint)]">
          FishSniper · Google OAuth
        </p>
        <h1 className="mt-2 text-3xl font-extrabold text-[var(--fs-green-soft)]">
          {failureMessage ? 'Sign-in paused' : 'Authenticating'}
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-[var(--fs-muted)]">
          {failureMessage ?? statusMessage}
        </p>
        {failureMessage ? (
          <button
            type="button"
            className="mt-6 w-full cursor-pointer rounded-xl border border-white/20 bg-white py-3.5 text-sm font-bold text-[#010409] transition-colors duration-200 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--fs-green)]"
            onClick={() => navigate('/', { replace: true })}
          >
            Return to sign in
          </button>
        ) : null}
      </section>
    </main>
  )
}
