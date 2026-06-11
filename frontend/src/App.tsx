import { useMemo } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'

import { readFishSniperApiBaseUrlFromPublicEnv } from './config/readFishSniperPublicEnv.ts'
import { useFishSniperAuthSessionState } from './hooks/useFishSniperAuthSessionState.ts'
import { useFishSniperUserPreferencesRemoteState } from './hooks/useFishSniperUserPreferencesRemoteState.ts'
import { FishSniperSignedInAppShell } from './layout/FishSniperSignedInAppShell.tsx'
import { FishSniperEmailOtpSignInPage } from './pages/FishSniperEmailOtpSignInPage.tsx'
import { FishSniperGoogleOAuthCallbackPage } from './pages/FishSniperGoogleOAuthCallbackPage.tsx'
import { FishSniperMyLogsPage } from './pages/FishSniperMyLogsPage.tsx'
import { FishSniperOnboardingRegionPage } from './pages/FishSniperOnboardingRegionPage.tsx'
import { FishSniperStrategyPage } from './pages/FishSniperStrategyPage.tsx'
import { FishSniperStrategyReportPage } from './pages/FishSniperStrategyReportPage.tsx'
import { FishSniperSettingsDeleteAccountPanel } from './pages/settings/FishSniperSettingsDeleteAccountPanel.tsx'
import { FishSniperSettingsLayoutPage } from './pages/settings/FishSniperSettingsLayoutPage.tsx'
import { FishSniperSettingsProfilePanel } from './pages/settings/FishSniperSettingsProfilePanel.tsx'
import { FishSniperTacticalAuthShell } from './ui/FishSniperTacticalAuthShell.tsx'
import {
  fishSniperTacticalAuthCardClassName,
  fishSniperTacticalErrorBannerClassName,
  fishSniperTacticalGhostButtonClassName,
  fishSniperTacticalMutedTextClassName,
  fishSniperTacticalPrimaryButtonClassName,
} from './ui/fishSniperTacticalUi.ts'

function FishSniperGoogleOAuthCallbackRoute(options: {
  apiBaseUrl: string
  persistAccessTokenJwt: (accessTokenJwt: string) => void
}) {
  const navigate = useNavigate()
  return (
    <FishSniperGoogleOAuthCallbackPage
      apiBaseUrl={options.apiBaseUrl}
      onAuthenticatedWithAccessToken={(accessTokenJwt) => {
        options.persistAccessTokenJwt(accessTokenJwt)
        navigate('/', { replace: true })
      }}
      onReturnToSignIn={() => navigate('/', { replace: true })}
    />
  )
}

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
      <Routes>
        <Route
          path="/auth/google/callback"
          element={
            <FishSniperGoogleOAuthCallbackRoute
              apiBaseUrl={fishSniperApiBaseUrl}
              persistAccessTokenJwt={fishSniperAuthSession.persistAccessTokenJwt}
            />
          }
        />
        <Route
          path="*"
          element={
            <FishSniperEmailOtpSignInPage
              apiBaseUrl={fishSniperApiBaseUrl}
              onAuthenticatedWithAccessToken={fishSniperAuthSession.persistAccessTokenJwt}
            />
          }
        />
      </Routes>
    )
  }

  if (
    fishSniperUserPreferencesRemote.remoteStatus === 'idle' ||
    fishSniperUserPreferencesRemote.remoteStatus === 'loading'
  ) {
    return (
      <FishSniperTacticalAuthShell title="FishSniper" subtitle="Loading your profile…">
        <div className={`${fishSniperTacticalAuthCardClassName} text-center`}>
          <p className={`${fishSniperTacticalMutedTextClassName} motion-safe:animate-pulse motion-reduce:animate-none`}>
            Syncing mission data…
          </p>
        </div>
      </FishSniperTacticalAuthShell>
    )
  }

  if (fishSniperUserPreferencesRemote.remoteStatus === 'error') {
    return (
      <FishSniperTacticalAuthShell title="FishSniper" subtitle="Could not load your profile">
        <div className={`${fishSniperTacticalAuthCardClassName} space-y-3 text-center`}>
          <p className={fishSniperTacticalErrorBannerClassName}>
            {fishSniperUserPreferencesRemote.hardFailureMessage}
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            <button
              type="button"
              className={fishSniperTacticalPrimaryButtonClassName}
              onClick={() => void fishSniperUserPreferencesRemote.reloadUserPreferences()}
            >
              Retry
            </button>
            <button
              type="button"
              className={fishSniperTacticalGhostButtonClassName}
              onClick={() => fishSniperAuthSession.clearAccessTokenJwt()}
            >
              Sign out
            </button>
          </div>
        </div>
      </FishSniperTacticalAuthShell>
    )
  }

  const loadedUserPreferences = fishSniperUserPreferencesRemote.userPreferences
  if (!loadedUserPreferences) {
    return (
      <FishSniperTacticalAuthShell title="FishSniper" subtitle="Loading your profile…">
        <div className={`${fishSniperTacticalAuthCardClassName} text-center`}>
          <p className={`${fishSniperTacticalMutedTextClassName} motion-safe:animate-pulse motion-reduce:animate-none`}>
            Syncing mission data…
          </p>
        </div>
      </FishSniperTacticalAuthShell>
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
    <Routes>
      <Route
        element={
          <FishSniperSignedInAppShell
            fishSniperApiBaseUrl={fishSniperApiBaseUrl}
            fishSniperAccessTokenJwt={fishSniperAuthSession.accessTokenJwt}
            userPreferences={loadedUserPreferences}
            reloadUserPreferences={fishSniperUserPreferencesRemote.reloadUserPreferences}
            onSignOut={fishSniperAuthSession.clearAccessTokenJwt}
          />
        }
      >
        <Route index element={<Navigate to="/strategy" replace />} />
        <Route path="strategy" element={<FishSniperStrategyPage />} />
        <Route path="strategy/report" element={<FishSniperStrategyReportPage />} />
        <Route path="logs" element={<FishSniperMyLogsPage />} />
        <Route path="settings" element={<FishSniperSettingsLayoutPage />}>
          <Route index element={<Navigate to="profile" replace />} />
          <Route path="profile" element={<FishSniperSettingsProfilePanel />} />
          <Route path="delete-account" element={<FishSniperSettingsDeleteAccountPanel />} />
        </Route>
      </Route>
    </Routes>
  )
}
