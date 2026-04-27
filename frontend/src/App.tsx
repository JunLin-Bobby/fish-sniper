import { useMemo } from 'react'

import { readFishSniperApiBaseUrlFromPublicEnv } from './config/readFishSniperPublicEnv.ts'
import { useFishSniperAuthSessionState } from './hooks/useFishSniperAuthSessionState.ts'
import { useFishSniperUserPreferencesRemoteState } from './hooks/useFishSniperUserPreferencesRemoteState.ts'
import { FishSniperEmailOtpSignInPage } from './pages/FishSniperEmailOtpSignInPage.tsx'
import { FishSniperHomePlaceholderPage } from './pages/FishSniperHomePlaceholderPage.tsx'
import { FishSniperOnboardingRegionPage } from './pages/FishSniperOnboardingRegionPage.tsx'

export default function App() {
  const fishSniperApiBaseUrl = useMemo(() => readFishSniperApiBaseUrlFromPublicEnv(), [])

  const fishSniperAuthSession = useFishSniperAuthSessionState()
  const fishSniperUserPreferencesRemote = useFishSniperUserPreferencesRemoteState({
    apiBaseUrl: fishSniperApiBaseUrl,
    accessTokenJwt: fishSniperAuthSession.accessTokenJwt,
    onUnauthorizedAccessToken: fishSniperAuthSession.clearAccessTokenJwt,
  })

  if (!fishSniperAuthSession.accessTokenJwt) {
    return (
      <FishSniperEmailOtpSignInPage
        apiBaseUrl={fishSniperApiBaseUrl}
        onAuthenticatedWithAccessToken={fishSniperAuthSession.persistAccessTokenJwt}
      />
    )
  }

  if (
    fishSniperUserPreferencesRemote.remoteStatus === 'idle' ||
    fishSniperUserPreferencesRemote.remoteStatus === 'loading'
  ) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-400 text-sm">
        Loading your profile…
      </div>
    )
  }

  if (fishSniperUserPreferencesRemote.remoteStatus === 'error') {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
        <div className="w-full max-w-md space-y-3 text-center">
          <p className="text-sm text-red-400">
            {fishSniperUserPreferencesRemote.hardFailureMessage}
          </p>
          <div className="flex gap-2 justify-center">
            <button
              type="button"
              className="rounded-md bg-emerald-500 hover:bg-emerald-400 text-gray-950 font-semibold px-3 py-2 text-sm"
              onClick={() => void fishSniperUserPreferencesRemote.reloadUserPreferences()}
            >
              Retry
            </button>
            <button
              type="button"
              className="rounded-md border border-gray-800 px-3 py-2 text-sm text-gray-200"
              onClick={() => fishSniperAuthSession.clearAccessTokenJwt()}
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    )
  }

  const loadedUserPreferences = fishSniperUserPreferencesRemote.userPreferences
  if (!loadedUserPreferences) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-400 text-sm">
        Loading your profile…
      </div>
    )
  }

  if (!loadedUserPreferences.onboarding_completed) {
    return (
      <FishSniperOnboardingRegionPage
        apiBaseUrl={fishSniperApiBaseUrl}
        accessTokenJwt={fishSniperAuthSession.accessTokenJwt}
        onOnboardingCompleted={() => void fishSniperUserPreferencesRemote.reloadUserPreferences()}
      />
    )
  }

  return (
    <FishSniperHomePlaceholderPage onSignOut={fishSniperAuthSession.clearAccessTokenJwt} />
  )
}
