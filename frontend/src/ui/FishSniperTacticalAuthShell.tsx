import type { ReactNode } from 'react'

import { StrategyTacticalBackdrop } from '../strategy/console/StrategyTacticalBackdrop.tsx'
import {
  fishSniperTacticalEyebrowClassName,
  fishSniperTacticalMutedTextClassName,
  fishSniperTacticalPageTitleClassName,
} from './fishSniperTacticalUi.ts'

export function FishSniperTacticalAuthShell(options: {
  children: ReactNode
  eyebrow?: string
  title: string
  subtitle?: string
}) {
  return (
    <div className="relative flex min-h-screen items-center justify-center px-4 py-10 text-slate-100">
      <StrategyTacticalBackdrop />
      <div className="relative w-full max-w-md space-y-6">
        <div className="space-y-2 text-center">
          <p className={fishSniperTacticalEyebrowClassName}>
            {options.eyebrow ?? 'FishSniper · Tactical command'}
          </p>
          <h1 className={`${fishSniperTacticalPageTitleClassName} text-[#5dff9a]`}>
            {options.title}
          </h1>
          {options.subtitle ? (
            <p className={fishSniperTacticalMutedTextClassName}>{options.subtitle}</p>
          ) : null}
        </div>
        {options.children}
      </div>
    </div>
  )
}
