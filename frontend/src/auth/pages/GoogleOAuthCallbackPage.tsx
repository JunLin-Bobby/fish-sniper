import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

import { exchangeGoogleOAuthAuthorizationCode } from '../api/authApi.ts'
import {
  clearStoredGoogleOAuthRequest,
  readStoredGoogleOAuthRequest,
} from '../lib/googleOAuthPkce.ts'
import { LanguageSwitcher } from '../../i18n/LanguageSwitcher.tsx'

// 處理 Google 導回的 callback URL，驗證 state 後將授權碼交給後端完成登入。
export function GoogleOAuthCallbackPage(props: {
  apiBaseUrl: string
  persistAccessToken: (accessToken: string) => void
}) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const hasStartedExchange = useRef(false)
  const [failure, setFailure] = useState<{ key: string; code?: string } | null>(null)
  const [statusKey, setStatusKey] = useState('auth.completing')

  useEffect(() => {
    if (hasStartedExchange.current) {
      return
    }
    hasStartedExchange.current = true

    // 讀取 callback 查詢參數，並以授權碼和 code_verifier 向後端交換 FishSniper token。
    const completeSignIn = async (): Promise<void> => {
      const queryParameters = new URLSearchParams(window.location.search)
      const oauthErrorCode = queryParameters.get('error')
      const authorizationCode = queryParameters.get('code')
      const returnedState = queryParameters.get('state')
      const storedRequest = readStoredGoogleOAuthRequest()

      if (oauthErrorCode) {
        setFailure({ key: 'auth.cancelled', code: oauthErrorCode })
        clearStoredGoogleOAuthRequest()
        return
      }
      if (!authorizationCode || !returnedState) {
        setFailure({ key: 'auth.missingCallback' })
        clearStoredGoogleOAuthRequest()
        return
      }
      if (!storedRequest || storedRequest.state !== returnedState) {
        setFailure({ key: 'auth.stateMismatch' })
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
        setStatusKey('auth.signedIn')
        navigate('/', { replace: true })
      } catch {
        // TODO: 依 400、401、503 等狀態碼顯示更明確且不洩漏敏感資訊的登入錯誤訊息。
        setFailure({ key: 'auth.exchangeFailed' })
        clearStoredGoogleOAuthRequest()
      }
    }

    void completeSignIn()
  }, [navigate, props])

  return (
    <main className="relative grid min-h-dvh place-items-center px-4 py-10 text-(--fs-ink)">
      <section className="w-full max-w-md rounded-3xl border border-(--fs-line) bg-black/40 p-6 text-center shadow-[0_32px_90px_rgba(0,0,0,0.46)] backdrop-blur-md sm:p-8">
        <div className="mb-5 flex justify-end"><LanguageSwitcher /></div>
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-(--fs-faint)">
          FishSniper · Google OAuth
        </p>
        <h1 className="mt-2 text-3xl font-extrabold text-(--fs-green-soft)">
          {failure ? t('auth.signInPaused') : t('auth.authenticating')}
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-(--fs-muted)">
          {failure ? t(failure.key, { code: failure.code }) : t(statusKey)}
        </p>
        {failure ? (
          <button
            type="button"
            className="mt-6 w-full cursor-pointer rounded-xl border border-white/20 bg-white py-3.5 text-sm font-bold text-[#010409] transition-colors duration-200 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--fs-green)"
            onClick={() => navigate('/', { replace: true })}
          >
            {t('auth.returnToSignIn')}
          </button>
        ) : null}
      </section>
    </main>
  )
}
