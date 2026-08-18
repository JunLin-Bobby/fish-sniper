import { useMemo } from 'react'

import { AppRoutes } from './routes.tsx'
import { readApiBaseUrlFromPublicEnv } from '../config/readPublicEnv.ts'
import { useAuthSession } from '../auth/hooks/useAuthSession.ts'

export default function App() {
  const apiBaseUrl = useMemo(() => readApiBaseUrlFromPublicEnv(), [])
  const authSession = useAuthSession()

  return <AppRoutes apiBaseUrl={apiBaseUrl} authSession={authSession} />
}