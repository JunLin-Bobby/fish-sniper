import type { ReactNode } from 'react'

import { TacticalBackdrop } from './TacticalBackdrop.tsx'
import {
  tacticalEyebrowClassName,
  tacticalMutedTextClassName,
  tacticalPageTitleClassName,
} from './tacticalUi.ts'

export function TacticalAuthShell(options: {
  children: ReactNode
  eyebrow?: string
  title: string
  subtitle?: string
}) {
  return (
    <div className="relative flex min-h-screen items-center justify-center px-4 py-10 text-slate-100">
      <TacticalBackdrop />
      <div className="relative w-full max-w-md space-y-6">
        <div className="space-y-2 text-center">
          <p className={tacticalEyebrowClassName}>
            {options.eyebrow ?? 'FishSniper · Tactical command'}
          </p>
          <h1 className={`${tacticalPageTitleClassName} text-[#5dff9a]`}>
            {options.title}
          </h1>
          {options.subtitle ? (
            <p className={tacticalMutedTextClassName}>{options.subtitle}</p>
          ) : null}
        </div>
        {options.children}
      </div>
    </div>
  )
}
