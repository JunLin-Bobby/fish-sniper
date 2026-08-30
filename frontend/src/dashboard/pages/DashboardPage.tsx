import { BiteCurvePanel, TacticalMapPreview } from '../components/TacticalMapPreview.tsx'
import { TacticalShell } from '../components/TacticalShell.tsx'
import { SignOutButton } from '../../auth/components/SignOutButton.tsx'

const catchTargets = [
  ['A', 'Largemouth bass', 'Structure ambush pattern.', '72%'],
  ['B', 'Smallmouth bass', 'Secondary rocky point.', '18%'],
  ['C', 'Yellow perch', 'Bycatch near grass edge.', '10%'],
]

const recommendations = [
  ['01', 'Spinnerbait near reed edge', 'Slow roll with 2-3 pause beats.', 'High'],
  ['02', 'Weightless worm over flats', 'Work the shadow line after sunrise.', 'Med'],
  ['03', 'Jig on outside drop', 'Use if wind pushes bait deeper.', 'Med'],
]

const recentLogs = [
  ['Jul 08', 'West dock pocket', '2 bass · green pumpkin jig · cloudy', 'Matched'],
  ['Jul 05', 'North reeds', '4 bass · spinnerbait · wind NE', 'RAG'],
  ['Jun 29', 'Point dropoff', '1 bass · deep crank · high sun', 'Older'],
]

function RankRow(props: {
  marker: string
  title: string
  description: string
  value: string
}) {
  return (
    <div className="grid grid-cols-[38px_1fr_auto] items-center gap-3 rounded-[14px] border border-white/10 bg-white/[0.04] p-3">
      <span className="grid h-[34px] w-[34px] place-items-center rounded-[10px] bg-[rgba(61,255,138,0.14)] text-[11px] font-extrabold uppercase text-[var(--fs-green-soft)]">
        {props.marker}
      </span>
      <div className="min-w-0">
        <h3 className="text-sm font-semibold">{props.title}</h3>
        <p className="mt-0.5 text-xs text-[var(--fs-muted)]">{props.description}</p>
      </div>
      <b className="text-sm">{props.value}</b>
    </div>
  )
}

export function DashboardPage(props: { onSignOut: () => void }) {
  return (
    <TacticalShell actions={<SignOutButton onSignOut={props.onSignOut} />}>
      <div className="mb-5 grid items-end gap-5 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--fs-faint)]">
            Prediction graph · tactical forecast
          </p>
          <h1 className="mt-2 max-w-[780px] text-[clamp(2rem,4.2vw,3.625rem)] font-extrabold leading-[0.96]">
            Choose the window, spot, and lure before the bite moves.
          </h1>
          <p className="mt-4 max-w-[660px] text-[15px] leading-relaxed text-[var(--fs-muted)]">
            Pressure rhythm on top, prediction and map in the center, catching logs as the
            feedback loop below. This is the rebuild baseline before Google auth returns.
          </p>
        </div>
        <div className="flex flex-wrap gap-2.5">
          <button
            type="button"
            className="min-h-[42px] cursor-pointer rounded-xl border border-white/15 bg-white/[0.05] px-4 text-sm font-bold text-slate-100 transition-colors duration-200 hover:border-white/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--fs-green)]"
          >
            Tune inputs
          </button>
          <button
            type="button"
            className="min-h-[42px] cursor-pointer rounded-xl border border-[rgba(61,255,138,0.52)] bg-[var(--fs-green)] px-4 text-sm font-bold text-[#031007] shadow-[0_0_36px_rgba(61,255,138,0.28)] transition-opacity duration-200 hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--fs-green)]"
          >
            Generate plan
          </button>
        </div>
      </div>

      <section className="grid gap-[18px] xl:grid-cols-[minmax(0,1.08fr)_minmax(360px,0.92fr)]">
        <div className="grid gap-[18px]">
          <BiteCurvePanel />

          <section className="grid gap-[18px] lg:grid-cols-[minmax(0,0.88fr)_minmax(300px,1.12fr)]">
            <article className="grid min-h-[318px] grid-rows-[auto_1fr_auto] gap-4 rounded-[18px] border border-[var(--fs-line)] bg-[var(--fs-panel)] p-[18px] shadow-[inset_0_1px_rgba(255,255,255,0.04)] backdrop-blur-[18px]">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--fs-faint)]">
                    02 · Prediction
                  </p>
                  <h2 className="mt-1 text-[17px] font-semibold">Mission score</h2>
                </div>
                <span className="inline-flex min-h-7 items-center rounded-full border border-white/10 bg-black/30 px-3 text-xs font-bold text-[var(--fs-muted)]">
                  Largemouth
                </span>
              </div>

              <div className="grid min-h-[130px] place-items-center rounded-2xl border border-[rgba(61,255,138,0.2)] bg-[radial-gradient(circle,rgba(61,255,138,0.16),rgba(0,0,0,0.16)_62%)] text-center">
                <div>
                  <strong className="block text-[62px] leading-none">87</strong>
                  <span className="text-sm text-[var(--fs-muted)]">/100 bite confidence</span>
                </div>
              </div>

              <div className="grid gap-2.5">
                {recommendations.map(([marker, title, description, value]) => (
                  <RankRow
                    key={marker}
                    marker={marker}
                    title={title}
                    description={description}
                    value={value}
                  />
                ))}
              </div>
            </article>

            <TacticalMapPreview />
          </section>
        </div>

        <aside className="grid content-start gap-[18px]">
          <section className="rounded-[18px] border border-[var(--fs-line)] bg-[var(--fs-panel)] p-[18px] shadow-[inset_0_1px_rgba(255,255,255,0.04)] backdrop-blur-[18px]">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--fs-faint)]">
                  Species rank
                </p>
                <h2 className="mt-1 text-[17px] font-semibold">Likely catches</h2>
              </div>
              <span className="inline-flex min-h-7 items-center rounded-full border border-white/10 bg-black/30 px-3 text-xs font-bold text-[var(--fs-muted)]">
                3 targets
              </span>
            </div>
            <div className="grid gap-2.5">
              {catchTargets.map(([marker, title, description, value]) => (
                <RankRow
                  key={marker}
                  marker={marker}
                  title={title}
                  description={description}
                  value={value}
                />
              ))}
            </div>
          </section>

          <section className="rounded-[18px] border border-[var(--fs-line)] bg-[var(--fs-panel)] p-[18px] shadow-[inset_0_1px_rgba(255,255,255,0.04)] backdrop-blur-[18px]">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--fs-faint)]">
                  Catching logs
                </p>
                <h2 className="mt-1 text-[17px] font-semibold">Feedback loop</h2>
              </div>
              <button
                type="button"
                className="min-h-[42px] cursor-pointer rounded-xl border border-[rgba(61,255,138,0.52)] bg-[var(--fs-green)] px-4 text-sm font-bold text-[#031007] shadow-[0_0_36px_rgba(61,255,138,0.28)] transition-opacity duration-200 hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--fs-green)]"
              >
                Add log
              </button>
            </div>
            <div className="grid gap-2.5">
              {recentLogs.map(([date, title, description, state]) => (
                <div
                  key={`${date}-${title}`}
                  className="grid gap-3 rounded-[14px] border border-white/10 bg-white/[0.035] p-3 sm:grid-cols-[76px_1fr_auto] sm:items-center"
                >
                  <span className="text-sm font-extrabold text-[var(--fs-green-soft)]">{date}</span>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold">{title}</h3>
                    <p className="mt-1 text-xs text-[var(--fs-muted)]">{description}</p>
                  </div>
                  <span
                    className={`inline-flex min-h-7 w-fit items-center rounded-full border px-3 text-xs font-bold ${
                      state === 'Matched'
                        ? 'border-[rgba(61,255,138,0.36)] text-[var(--fs-green-soft)]'
                        : 'border-white/10 text-[var(--fs-muted)]'
                    }`}
                  >
                    {state}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </section>
    </TacticalShell>
  )
}
