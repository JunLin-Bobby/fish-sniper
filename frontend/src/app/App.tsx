import { AppRoutes } from './routes.tsx'
import { useAuthSession } from '../auth/hooks/useAuthSession.ts'
import { readApiBaseUrl } from '../config/env.ts'

export default function App() {
  const authSession = useAuthSession()
  const apiBaseUrl = readApiBaseUrl()

  return <AppRoutes apiBaseUrl={apiBaseUrl} authSession={authSession} />
}
