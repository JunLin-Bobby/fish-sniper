import { Route, Routes } from 'react-router-dom'

import type { AuthSession } from '../auth/hooks/useAuthSession.ts'
import { GoogleOAuthCallbackPage } from '../auth/pages/GoogleOAuthCallbackPage.tsx'
import { SignInPage } from '../auth/pages/SignInPage.tsx'
import { DashboardPage } from '../dashboard/pages/DashboardPage.tsx'

// 依 FishSniper access token 是否存在，切換登入流程與 protected dashboard。
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
      <Route
        path="*"
        element={
          <DashboardPage
            apiBaseUrl={props.apiBaseUrl}
            onSignOut={props.authSession.signOut}
          />
        }
      />
    </Routes>
  )
}
