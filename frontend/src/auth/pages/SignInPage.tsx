import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { GoogleSignInButton } from '../components/GoogleSignInButton.tsx'
import { readGoogleOAuthPublicConfig } from '../../config/env.ts'
import { beginGoogleOAuthAuthorizationFlowFromBrowser } from '../lib/googleOAuthPkce.ts'
import { LanguageSwitcher } from '../../i18n/LanguageSwitcher.tsx'

// 顯示登入入口，使用者點擊後開始 Google OAuth 授權流程。
export function SignInPage() {
  const { t } = useTranslation()
  const [failureKey, setFailureKey] = useState<string | null>(null)
  const googleOAuthConfig = useMemo(() => readGoogleOAuthPublicConfig(), [])

  // 確認前端環境設定完整，再將瀏覽器導向 Google 登入與同意畫面。
  const handleContinueWithGoogle = async (): Promise<void> => {
    setFailureKey(null)
    if (!googleOAuthConfig) {
      setFailureKey('auth.notConfigured')
      return
    }

    try {
      await beginGoogleOAuthAuthorizationFlowFromBrowser(googleOAuthConfig)
    } catch {
      setFailureKey('auth.couldNotStart')
    }
  }

  return (
    <main className="relative grid min-h-dvh place-items-center px-4 py-10 text-[var(--fs-ink)]">
      <section className="w-full max-w-md rounded-[1.5rem] border border-[var(--fs-line)] bg-[rgba(2,6,23,0.72)] p-6 shadow-[0_32px_90px_rgba(0,0,0,0.46)] backdrop-blur-2xl sm:p-8">
        <div className="mb-5 flex justify-end"><LanguageSwitcher /></div>
        <div className="mb-6 text-center">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-[14px] border border-[rgba(61,255,138,0.46)] bg-[linear-gradient(145deg,rgba(61,255,138,0.2),rgba(56,214,255,0.08))] text-sm font-extrabold text-[var(--fs-green)]">
            FS
          </div>
          <p className="mt-5 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--fs-faint)]">
            FishSniper · {t('auth.tacticalCommand')}
          </p>
          <h1 className="mt-2 text-3xl font-extrabold text-[var(--fs-green-soft)]">
            FishSniper
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-[var(--fs-muted)]">
            {t('auth.intro')}
          </p>
        </div>

        <GoogleSignInButton onSignIn={handleContinueWithGoogle} />

        {failureKey ? (
          <p className="mt-4 rounded-xl border border-rose-500/45 bg-rose-950/30 px-4 py-3 text-sm leading-relaxed text-rose-100">
            {t(failureKey)}
          </p>
        ) : null}
      </section>
    </main>
  )
}
