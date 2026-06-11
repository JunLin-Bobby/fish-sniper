import type {
  BassStrategyRecommendationPayload,
  GenerateBassStrategySuccessResponsePayload,
  HoldingZoneItemPayload,
  ReferencedLogPayload,
  TodaysPatternPayload,
} from '../../api/fishSniperApiTypes.ts'
import { getBassStrategyTacticalRoleDisplay } from '../bassStrategyTacticalRoleDisplay.ts'
import { formatStrategyReportTimestamp } from '../formatStrategyReportTimestamp.ts'
import type { StrategyReportRequestSummary } from '../strategyReportSessionStorage.ts'
import {
  fishSniperTacticalBodyTextClassName,
  fishSniperTacticalChipClassName,
  fishSniperTacticalEyebrowClassName,
  fishSniperTacticalMutedTextClassName,
  fishSniperTacticalPageTitleClassName,
  fishSniperTacticalPanelClassName,
  fishSniperTacticalSectionTitleClassName,
} from '../../ui/fishSniperTacticalUi.ts'

const glassPanelClassName = fishSniperTacticalPanelClassName
const sectionTitleClassName = `${fishSniperTacticalSectionTitleClassName} mb-4`
const metaChipClassName = fishSniperTacticalChipClassName
const bodyTextClassName = fishSniperTacticalBodyTextClassName

function ReferenceLogSidebarPanel(options: { referencedLog: ReferencedLogPayload }) {
  const { referencedLog } = options
  return (
    <section
      className={`${glassPanelClassName} border-sky-500/25 bg-sky-950/25`}
      aria-label="Reference log"
    >
      <p className={`${fishSniperTacticalSectionTitleClassName} mb-4 text-sky-200/90`}>Reference log</p>
      <p className={`${bodyTextClassName} text-slate-300`}>
        <strong className="font-medium text-slate-100">{referencedLog.log_date}</strong>
        <br />
        {referencedLog.lure_type} · {referencedLog.lure_color}
        <br />
        {referencedLog.retrieve_speed} · {referencedLog.caught_count} caught
      </p>
    </section>
  )
}

function LikelyHoldingZonesPanel(options: {
  holdingZones: [
    HoldingZoneItemPayload,
    HoldingZoneItemPayload,
    HoldingZoneItemPayload,
  ]
}) {
  const { holdingZones } = options

  return (
    <section className={`${glassPanelClassName} border-amber-500/20 bg-amber-950/10`} aria-label="Likely holding zone">
      <p className={`${sectionTitleClassName} text-amber-200/90`}>Likely holding zone</p>
      <ul className="flex list-none flex-col gap-4 p-0">
        {holdingZones.map((zone) => (
          <li key={zone.label}>
            <div className="mb-2 flex items-baseline justify-between gap-3 text-sm">
              <span className="font-medium text-slate-200">{zone.label}</span>
              <span className="shrink-0 tabular-nums text-amber-200/90">{zone.weight_pct}%</span>
            </div>
            <div
              className="h-1.5 overflow-hidden rounded-full bg-white/10"
              role="presentation"
              aria-hidden="true"
            >
              <div
                className="h-full rounded-full bg-gradient-to-r from-amber-500/80 to-amber-300/70"
                style={{ width: `${zone.weight_pct}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

function PatternStrategyCard(options: {
  roleTitle: string
  roleSubtitle: string
  recommendation: BassStrategyRecommendationPayload
  isLocatorPhase: boolean
}) {
  const { roleTitle, roleSubtitle, recommendation, isLocatorPhase } = options
  const borderClassName = isLocatorPhase
    ? 'border-[#3dff8a]/35 bg-[#3dff8a]/[0.06] shadow-[0_0_32px_rgba(61,255,138,0.08)]'
    : 'border-white/15 bg-slate-950/55'

  return (
    <article className={`rounded-xl border p-6 ${borderClassName}`}>
      <p
        className={`mb-3 text-[10px] font-bold uppercase tracking-[0.2em] ${
          isLocatorPhase ? 'text-[#5dff9a]' : 'text-amber-400/90'
        }`}
      >
        {roleTitle}
      </p>
      <p className={`${fishSniperTacticalMutedTextClassName} mb-4 text-sm`}>{roleSubtitle}</p>
      <h3 className="text-xl font-bold tracking-tight text-slate-50">{recommendation.lure_type}</h3>
      <p className="mt-1 text-sm text-slate-400">{recommendation.lure_color}</p>
      <div className="mt-4 border-t border-white/10 pt-4">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          Reason
        </p>
        <p className={`${bodyTextClassName} text-slate-300`}>{recommendation.reason}</p>
      </div>
      <div className="mt-4 border-t border-white/10 pt-4">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          Retrieve
        </p>
        <p className={`${bodyTextClassName} text-slate-300`}>{recommendation.retrieve_technique}</p>
      </div>
    </article>
  )
}

function TodaysPatternHeroCard(options: {
  todaysPattern: TodaysPatternPayload
  targetSpecies: string
  confidencePct: number
  confidenceNote: string
}) {
  const { todaysPattern, targetSpecies, confidencePct, confidenceNote } = options

  return (
    <section
      className="rounded-2xl border border-[#3dff8a]/25 bg-gradient-to-br from-[#3dff8a]/10 via-black/40 to-amber-500/5 p-6 sm:p-8"
      aria-label="Today's pattern"
    >
      <p className={`${fishSniperTacticalEyebrowClassName} mb-4`}>Today&apos;s pattern</p>
      <h2 className="mt-2 text-2xl font-bold leading-tight tracking-tight text-slate-50 sm:text-3xl">
        {todaysPattern.headline}
      </h2>
      <p className="mt-2 text-base font-medium text-amber-200/90">{todaysPattern.subline}</p>
      <p className="mt-1 text-sm text-slate-400">{targetSpecies}</p>
      <div className="mt-5 flex flex-wrap items-baseline gap-x-4 gap-y-1 border-t border-white/10 pt-5">
        <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Confidence
        </span>
        <span className="text-2xl font-bold tabular-nums text-[#5dff9a]">{confidencePct}%</span>
        <p className="text-sm leading-relaxed text-slate-300">{confidenceNote}</p>
      </div>
    </section>
  )
}

export function StrategyReportFieldManualDocument(options: {
  requestSummary: StrategyReportRequestSummary
  successPayload: GenerateBassStrategySuccessResponsePayload
}) {
  const { requestSummary, successPayload } = options
  const { weather_snapshot: weather } = successPayload
  const hasReferenceLog = successPayload.rag_logs_used > 0 && successPayload.referenced_log != null

  return (
    <article
      className="flex w-full flex-col gap-6 rounded-[1.25rem] border border-white/15 bg-white/[0.04] p-6 shadow-[0_24px_70px_-34px_rgba(2,6,23,0.95)] backdrop-blur-2xl sm:p-8"
      aria-labelledby="strategy-report-title"
    >
      <header className="border-b border-white/10 pb-5">
        <p className={`mb-1 ${fishSniperTacticalMutedTextClassName} text-xs uppercase tracking-widest text-slate-400`}>
          FishSniper · Field Manual
        </p>
        <h1 id="strategy-report-title" className={fishSniperTacticalPageTitleClassName}>
          Tactical Readout
        </h1>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className={metaChipClassName}>{requestSummary.fishing_location}</span>
          <span className={metaChipClassName}>{requestSummary.target_species}</span>
          <span className={metaChipClassName}>
            {hasReferenceLog ? 'RAG: 1 log' : 'RAG: general'}
          </span>
        </div>
      </header>

      <TodaysPatternHeroCard
        todaysPattern={successPayload.todays_pattern}
        targetSpecies={requestSummary.target_species}
        confidencePct={successPayload.confidence_pct}
        confidenceNote={successPayload.confidence_note}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
        <aside className="flex flex-col gap-4 lg:col-span-4" aria-label="Situation summary">
          <section className={glassPanelClassName}>
            <p className={`${sectionTitleClassName} text-slate-500`}>Conditions</p>
            <ul className="grid w-full list-none gap-2 p-0 text-xs text-slate-400">
              <li className="flex justify-between gap-3">
                <span>Region</span>
                <strong className="text-right font-medium text-slate-200">{requestSummary.region}</strong>
              </li>
              <li className="flex justify-between gap-3">
                <span>Scene</span>
                <strong className="text-right font-medium text-slate-200">
                  {requestSummary.fishing_scene}
                </strong>
              </li>
              <li className="flex justify-between gap-3">
                <span>Depth</span>
                <strong className="text-right font-medium text-slate-200">
                  {requestSummary.water_depth_m} m
                </strong>
              </li>
              <li className="flex justify-between gap-3 border-t border-white/10 pt-2">
                <span>Temp</span>
                <strong className="text-right font-medium text-slate-200">
                  {weather.temperature_c}°C
                </strong>
              </li>
              <li className="flex justify-between gap-3">
                <span>Sky</span>
                <strong className="text-right font-medium text-slate-200">
                  {weather.condition_code}
                </strong>
              </li>
              <li className="flex justify-between gap-3">
                <span>Wind</span>
                <strong className="text-right font-medium text-slate-200">
                  {weather.wind_speed_ms} m/s
                </strong>
              </li>
              <li className="flex justify-between gap-3">
                <span>Pressure</span>
                <strong className="text-right font-medium text-slate-200">
                  {weather.pressure_hpa} hPa
                </strong>
              </li>
            </ul>
          </section>

          <LikelyHoldingZonesPanel holdingZones={successPayload.holding_zones} />

          <section className={`${glassPanelClassName} border-emerald-500/20 bg-emerald-950/15`}>
            <p className={sectionTitleClassName}>Fish state</p>
            <p className={`text-sm leading-relaxed text-slate-300`}>{successPayload.fish_state}</p>
          </section>

          {hasReferenceLog && successPayload.referenced_log ? (
            <ReferenceLogSidebarPanel referencedLog={successPayload.referenced_log} />
          ) : null}
        </aside>

        <section className="lg:col-span-8" aria-label="Tactical presentations">
          <p className={`${sectionTitleClassName} mb-4 text-base tracking-[0.12em] text-slate-200 sm:text-lg`}>
            Recommended presentations
          </p>
          <div className="flex flex-col gap-5">
            {successPayload.recommendations.map((recommendation, index) => {
              const roleDisplay = getBassStrategyTacticalRoleDisplay(recommendation.tactical_role)
              return (
                <PatternStrategyCard
                  key={`pattern-${recommendation.tactical_role}-${index}`}
                  roleTitle={roleDisplay.title}
                  roleSubtitle={roleDisplay.subtitle}
                  recommendation={recommendation}
                  isLocatorPhase={recommendation.tactical_role === 'locator_bait'}
                />
              )
            })}
          </div>
        </section>
      </div>

      <footer className="border-t border-white/10 pt-5 text-xs leading-relaxed text-slate-500">
        Generated {formatStrategyReportTimestamp(successPayload.generated_at)} · FishSniper strategy
        report
      </footer>
    </article>
  )
}
