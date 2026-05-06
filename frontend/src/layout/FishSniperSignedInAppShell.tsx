import { NavLink, Outlet } from 'react-router-dom'

import type { FishSniperSignedInOutletContextValue } from './fishSniperSignedInOutletContext.ts'

export function FishSniperSignedInAppShell(options: {
  fishSniperApiBaseUrl: string
  fishSniperAccessTokenJwt: string
  onSignOut: () => void
}) {
  const outletContext: FishSniperSignedInOutletContextValue = {
    fishSniperApiBaseUrl: options.fishSniperApiBaseUrl,
    fishSniperAccessTokenJwt: options.fishSniperAccessTokenJwt,
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      <header className="sticky top-0 z-20 flex items-center justify-between gap-2 border-b border-gray-800 bg-gray-950/95 px-4 py-2 backdrop-blur-sm">
        <span className="text-sm font-semibold tracking-tight text-emerald-400">FishSniper</span>
        <button
          type="button"
          className="text-xs text-gray-500 hover:text-gray-300"
          onClick={() => options.onSignOut()}
        >
          Sign out
        </button>
      </header>

      <main className="flex-1 overflow-y-auto px-4 pb-24 pt-4">
        <Outlet context={outletContext} />
      </main>

      <nav className="fixed bottom-0 inset-x-0 z-20 border-t border-gray-800 bg-gray-950/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-lg">
          <NavLink
            to="/strategy"
            className={({ isActive }) =>
              `flex-1 py-3 text-center text-sm font-semibold ${
                isActive ? 'text-emerald-400' : 'text-gray-500 hover:text-gray-300'
              }`
            }
          >
            Strategy
          </NavLink>
          <NavLink
            to="/logs"
            className={({ isActive }) =>
              `flex-1 py-3 text-center text-sm font-semibold ${
                isActive ? 'text-emerald-400' : 'text-gray-500 hover:text-gray-300'
              }`
            }
          >
            My Logs
          </NavLink>
        </div>
      </nav>
    </div>
  )
}
