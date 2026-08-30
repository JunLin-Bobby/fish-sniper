import { Route, Routes } from 'react-router-dom'

import type { AuthSession } from '../auth/hooks/useAuthSession.ts'
import { GoogleOAuthCallbackPage } from '../auth/pages/GoogleOAuthCallbackPage.tsx'
import { SignInPage } from '../auth/pages/SignInPage.tsx'
import { DashboardPage } from '../dashboard/pages/DashboardPage.tsx'

export function AppRoutes(props: { apiBaseUrl: string; authSession: AuthSession }) {
  if (!props.authSession.accessToken) {
    return (
      <Routes>
        <Route
          path="/auth/google/callback"
          element={
            <GoogleOAuthCallbackPage
              apiBaseUrl={props.apiBaseUrl}
              persistAccessToken={props.authSession.persistAccessToken}
            />
          }
        />
        <Route path="*" element={<SignInPage />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route path="*" element={<DashboardPage onSignOut={props.authSession.signOut} />} />
    </Routes>
  )
}
