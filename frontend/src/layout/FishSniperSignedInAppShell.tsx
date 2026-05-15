import { NavLink, Outlet } from 'react-router-dom'

import type { UserPreferencesResponsePayload } from '../api/fishSniperApiTypes.ts'
import type { FishSniperSignedInOutletContextValue } from './fishSniperSignedInOutletContext.ts'

function FishSniperSettingsGearIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4 shrink-0"
      aria-hidden
    >
      <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.604.852.997 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </svg>
  )
}

const NAV_LINK_BASE =
  'rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors duration-200 cursor-pointer'

function primaryNavLinkClassName(isActive: boolean): string {
  return `${NAV_LINK_BASE} ${
    isActive
      ? 'bg-emerald-500/15 text-emerald-400'
      : 'text-gray-300 hover:bg-gray-800/80 hover:text-gray-100'
  }`
}

function settingsNavLinkClassName(isActive: boolean): string {
  return `${NAV_LINK_BASE} inline-flex items-center gap-1.5 border ${
    isActive
      ? 'border-gray-600 bg-gray-800 text-gray-100'
      : 'border-transparent text-gray-300 hover:border-gray-700 hover:bg-gray-800/80 hover:text-gray-100'
  }`
}

export function FishSniperSignedInAppShell(options: {
  fishSniperApiBaseUrl: string
  fishSniperAccessTokenJwt: string
  userPreferences: UserPreferencesResponsePayload
  reloadUserPreferences: () => Promise<void>
  onSignOut: () => void
}) {
  const outletContext: FishSniperSignedInOutletContextValue = {
    fishSniperApiBaseUrl: options.fishSniperApiBaseUrl,
    fishSniperAccessTokenJwt: options.fishSniperAccessTokenJwt,
    userPreferences: options.userPreferences,
    reloadUserPreferences: options.reloadUserPreferences,
    onSignOut: options.onSignOut,
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      <header className="sticky top-0 z-20 border-b border-gray-800 bg-gray-950/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-2.5">
          <div className="flex min-w-0 flex-1 items-center gap-5">
            <span className="shrink-0 text-sm font-semibold tracking-tight text-emerald-400">
              FishSniper
            </span>
            <nav className="flex items-center gap-1" aria-label="Primary">
              <NavLink
                to="/strategy"
                className={({ isActive }) => primaryNavLinkClassName(isActive)}
              >
                Strategy
              </NavLink>
              <NavLink to="/logs" className={({ isActive }) => primaryNavLinkClassName(isActive)}>
                My Logs
              </NavLink>
            </nav>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <NavLink
              to="/settings/profile"
              className={({ isActive }) => settingsNavLinkClassName(isActive)}
              aria-label="Settings"
            >
              <FishSniperSettingsGearIcon />
              <span className="hidden sm:inline">Settings</span>
            </NavLink>
            <button
              type="button"
              className={`${NAV_LINK_BASE} text-gray-300 hover:bg-gray-800/80 hover:text-gray-100`}
              onClick={() => options.onSignOut()}
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-4">
        <Outlet context={outletContext} />
      </main>
    </div>
  )
}
