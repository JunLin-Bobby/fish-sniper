import type { ReactNode } from 'react'

import { StrategyTacticalBackdrop } from '../strategy/console/StrategyTacticalBackdrop.tsx'

export function FishSniperTacticalPageShell(options: {
  children: ReactNode
  className?: string
  contentClassName?: string
}) {
  return (
    <div className="relative -mx-4 min-h-[calc(100dvh-3.5rem)] w-[calc(100%+2rem)] lg:mx-0 lg:w-full">
      <StrategyTacticalBackdrop />
      <div
        className={`relative mx-auto w-full max-w-7xl px-5 py-8 sm:px-8 lg:py-10 ${options.contentClassName ?? ''}`}
      >
        <div className={options.className}>{options.children}</div>
      </div>
    </div>
  )
}
