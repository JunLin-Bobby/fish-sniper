import { useMemo, useState } from 'react'

import { GoogleSignInButton } from '../components/GoogleSignInButton.tsx'
import { beginGoogleOAuthAuthorizationFlowFromBrowser } from '../lib/googleOAuthPkce.ts'
import { readGoogleOAuthPublicConfigFromEnvOrNull } from '../../config/readPublicEnv.ts'
import { TacticalAuthShell } from '../../ui/TacticalAuthShell.tsx'
import {
  tacticalAuthCardClassName,
  tacticalErrorBannerClassName,
} from '../../ui/tacticalUi.ts'

export function SignInPage() {
  const [googleSignInHardFailureMessage, setGoogleSignInHardFailureMessage] = useState<
    string | null
  >(null)
  const googleOAuthPublicConfig = useMemo(
    () => readGoogleOAuthPublicConfigFromEnvOrNull(),
    [],
  )

  const handleClickContinueWithGoogle = async (): Promise<void> => {
    setGoogleSignInHardFailureMessage(null)
    if (!googleOAuthPublicConfig) {
      setGoogleSignInHardFailureMessage('Google sign-in is not configured for this environment.')
      return
    }
    try {
      await beginGoogleOAuthAuthorizationFlowFromBrowser({
        clientId: googleOAuthPublicConfig.clientId,
        redirectUri: googleOAuthPublicConfig.redirectUri,
      })
    } catch {
      setGoogleSignInHardFailureMessage('Could not start the Google sign-in flow. Please try again.')
    }
  }

  return (
    <TacticalAuthShell title="FishSniper" subtitle="Continue with your Google account.">
      <div className={`${tacticalAuthCardClassName} space-y-3`}>
        {googleOAuthPublicConfig ? (
          <GoogleSignInButton onContinueWithGoogle={handleClickContinueWithGoogle} />
        ) : (
          <p className={tacticalErrorBannerClassName}>
            Google sign-in is not configured for this environment.
          </p>
        )}
        {googleSignInHardFailureMessage ? (
          <p className={tacticalErrorBannerClassName}>{googleSignInHardFailureMessage}</p>
        ) : null}
      </div>
    </TacticalAuthShell>
  )
}