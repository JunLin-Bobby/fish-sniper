/** Passed from `FishSniperSignedInAppShell` to child routes via React Router `<Outlet />`. */

import type { UserPreferencesResponsePayload } from '../api/fishSniperApiTypes.ts'

export interface FishSniperSignedInOutletContextValue {
  fishSniperApiBaseUrl: string
  fishSniperAccessTokenJwt: string
  userPreferences: UserPreferencesResponsePayload | null
  reloadUserPreferences: () => Promise<void>
  onSignOut: () => void
}
