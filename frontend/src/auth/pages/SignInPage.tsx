import { useMemo, useState } from 'react'

import { GoogleSignInButton } from '../components/GoogleSignInButton.tsx'
import { readGoogleOAuthPublicConfig } from '../../config/env.ts'
import { beginGoogleOAuthAuthorizationFlowFromBrowser } from '../lib/googleOAuthPkce.ts'

export function SignInPage() {
  const [failureMessage, setFailureMessage] = useState<string | null>(null)
  const googleOAuthConfig = useMemo(() => readGoogleOAuthPublicConfig(), [])

  const handleContinueWithGoogle = async (): Promise<void> => {
    setFailureMessage(null)
    if (!googleOAuthConfig) {
      setFailureMessage('Google sign-in is not configured for this environment.')
      return
    }

    try {
      await beginGoogleOAuthAuthorizationFlowFromBrowser(googleOAuthConfig)
    } catch {
      setFailureMessage('Could not start Google sign-in. Please try again.')
    }
  }

  return (
    <main className="relative grid min-h-dvh place-items-center px-4 py-10 text-[var(--fs-ink)]">
      <section className="w-full max-w-md rounded-[1.5rem] border border-[var(--fs-line)] bg-[rgba(2,6,23,0.72)] p-6 shadow-[0_32px_90px_rgba(0,0,0,0.46)] backdrop-blur-2xl sm:p-8">
        <div className="mb-6 text-center">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-[14px] border border-[rgba(61,255,138,0.46)] bg-[linear-gradient(145deg,rgba(61,255,138,0.2),rgba(56,214,255,0.08))] text-sm font-extrabold text-[var(--fs-green)]">
            FS
          </div>
          <p className="mt-5 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--fs-faint)]">
            FishSniper · Tactical command
          </p>
          <h1 className="mt-2 text-3xl font-extrabold text-[var(--fs-green-soft)]">
            FishSniper
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-[var(--fs-muted)]">
            Continue with your Google account.
          </p>
        </div>

        <GoogleSignInButton onSignIn={handleContinueWithGoogle} />

        {failureMessage ? (
          <p className="mt-4 rounded-xl border border-rose-500/45 bg-rose-950/30 px-4 py-3 text-sm leading-relaxed text-rose-100">
            {failureMessage}
          </p>
        ) : null}
      </section>
    </main>
  )
}
