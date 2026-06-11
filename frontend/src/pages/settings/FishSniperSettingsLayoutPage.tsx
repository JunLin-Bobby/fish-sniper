import { NavLink, Outlet, useOutletContext } from 'react-router-dom'

import type { FishSniperSignedInOutletContextValue } from '../../layout/fishSniperSignedInOutletContext.ts'
import { FishSniperTacticalPageShell } from '../../ui/FishSniperTacticalPageShell.tsx'
import {
  fishSniperTacticalPageTitleClassName,
  fishSniperTacticalSettingsSideNavLinkClassName,
} from '../../ui/fishSniperTacticalUi.ts'

export function FishSniperSettingsLayoutPage() {
  const outletContext = useOutletContext<FishSniperSignedInOutletContextValue>()

  return (
    <FishSniperTacticalPageShell>
      <h1 className={`mb-6 ${fishSniperTacticalPageTitleClassName}`}>Settings</h1>
      <div className="flex flex-col gap-8 md:flex-row">
        <nav className="shrink-0 space-y-1 md:w-52" aria-label="Settings sections">
          <NavLink
            to="/settings/profile"
            className={({ isActive }) => fishSniperTacticalSettingsSideNavLinkClassName(isActive)}
          >
            Profile
          </NavLink>
          <NavLink
            to="/settings/delete-account"
            className={({ isActive }) => fishSniperTacticalSettingsSideNavLinkClassName(isActive, true)}
          >
            Delete Account
          </NavLink>
        </nav>
        <div className="min-w-0 flex-1">
          <Outlet context={outletContext} />
        </div>
      </div>
    </FishSniperTacticalPageShell>
  )
}
