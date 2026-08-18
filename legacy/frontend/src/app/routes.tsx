import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'

import { SignOutButton } from '../auth/components/SignOutButton.tsx'
import { GoogleOAuthCallbackPage } from '../auth/pages/GoogleOAuthCallbackPage.tsx'
import { SignInPage } from '../auth/pages/SignInPage.tsx'
import type { AuthSessionState } from '../auth/hooks/useAuthSession.ts'

function GoogleOAuthCallbackRoute(options: {
  apiBaseUrl: string
  persistAccessTokenJwt: (accessTokenJwt: string) => void
}) {
  const navigate = useNavigate()
  return (
    <GoogleOAuthCallbackPage
      apiBaseUrl={options.apiBaseUrl}
      onAuthenticatedWithAccessToken={(accessTokenJwt) => {
        options.persistAccessTokenJwt(accessTokenJwt)
        navigate('/', { replace: true })
      }}
      onReturnToSignIn={() => navigate('/', { replace: true })}
    />
  )
}

function SignedInExplorationPage(options: { onSignOut: () => void }) {
  return (
    <div className="relative h-dvh w-full bg-[#010409]">
      <div className="absolute right-3 top-3 z-10">
        <SignOutButton onSignOut={options.onSignOut} />
      </div>
      <iframe
        title="FishSniper UI exploration"
        src="/ui-exploration/index.html"
        className="h-full w-full border-0"
      />
    </div>
  )
}

export function AppRoutes(options: {
  apiBaseUrl: string
  authSession: AuthSessionState
}) {
  if (!options.authSession.accessTokenJwt) {
    return (
      <Routes>
        <Route
          path="/auth/google/callback"
          element={
            <GoogleOAuthCallbackRoute
              apiBaseUrl={options.apiBaseUrl}
              persistAccessTokenJwt={options.authSession.persistAccessTokenJwt}
            />
          }
        />
        <Route path="*" element={<SignInPage />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route
        path="/"
        element={<SignedInExplorationPage onSignOut={options.authSession.clearAccessTokenJwt} />}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}