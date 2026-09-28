import { AppRoutes } from './routes.tsx'
import { useAuthSession } from '../auth/hooks/useAuthSession.ts'
import { readApiBaseUrl } from '../config/env.ts'

// 組合 auth session、runtime API URL 與應用程式 routes。
export default function App() {
  const authSession = useAuthSession()
  const apiBaseUrl = readApiBaseUrl()

  return <AppRoutes apiBaseUrl={apiBaseUrl} authSession={authSession} />
}
