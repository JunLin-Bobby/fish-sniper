import { NavLink, Outlet, useOutletContext } from 'react-router-dom'

import type { FishSniperSignedInOutletContextValue } from '../../layout/fishSniperSignedInOutletContext.ts'

function settingsNavLinkClassName(isActive: boolean, isDestructive = false): string {
  const base =
    'block rounded-md px-3 py-2 text-sm font-medium transition-colors border-l-2'
  if (isDestructive) {
    return `${base} ${
      isActive
        ? 'border-red-500 bg-red-500/10 text-red-300'
        : 'border-transparent text-red-400 hover:bg-red-500/5 hover:text-red-300'
    }`
  }
  return `${base} ${
    isActive
      ? 'border-emerald-500 bg-gray-900 text-gray-100'
      : 'border-transparent text-gray-300 hover:bg-gray-900 hover:text-gray-100'
  }`
}

export function FishSniperSettingsLayoutPage() {
  const outletContext = useOutletContext<FishSniperSignedInOutletContextValue>()

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-xl font-semibold text-gray-100 mb-6">Settings</h1>
      <div className="flex flex-col md:flex-row gap-8">
        <nav className="md:w-52 shrink-0 space-y-1" aria-label="Settings sections">
          <NavLink
            to="/settings/profile"
            className={({ isActive }) => settingsNavLinkClassName(isActive)}
          >
            Profile
          </NavLink>
          <NavLink
            to="/settings/delete-account"
            className={({ isActive }) => settingsNavLinkClassName(isActive, true)}
          >
            Delete Account
          </NavLink>
        </nav>
        <div className="min-w-0 flex-1">
          <Outlet context={outletContext} />
        </div>
      </div>
    </div>
  )
}
