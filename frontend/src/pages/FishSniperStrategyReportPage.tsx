import { Link, Navigate } from 'react-router-dom'

import { StrategyReportFieldManualDocument } from '../strategy/report/StrategyReportFieldManualDocument.tsx'
import { readStrategyReportFromSessionStorage } from '../strategy/strategyReportSessionStorage.ts'
import { FishSniperTacticalPageShell } from '../ui/FishSniperTacticalPageShell.tsx'
import { fishSniperTacticalGhostButtonClassName } from '../ui/fishSniperTacticalUi.ts'

export function FishSniperStrategyReportPage() {
  const storedReport = readStrategyReportFromSessionStorage()
  if (storedReport === null) {
    return <Navigate to="/strategy?report=missing" replace />
  }

  return (
    <FishSniperTacticalPageShell contentClassName="py-6 lg:py-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <Link to="/strategy" className={fishSniperTacticalGhostButtonClassName}>
          ← Back to mission brief
        </Link>
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Tactical readout
        </p>
      </div>

      <StrategyReportFieldManualDocument
        requestSummary={storedReport.requestSummary}
        successPayload={storedReport.successPayload}
      />
    </FishSniperTacticalPageShell>
  )
}
