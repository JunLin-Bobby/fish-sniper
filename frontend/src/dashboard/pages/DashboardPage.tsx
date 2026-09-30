import { BiteCurvePanel, TacticalMapPreview } from '../components/TacticalMapPreview.tsx'
import { TacticalShell } from '../components/TacticalShell.tsx'
import { SignOutButton } from '../../auth/components/SignOutButton.tsx'
import { useCurrentUser } from '../../users/hooks/useCurrentUser.ts'
import { useTranslation } from 'react-i18next'

// 顯示排名、推薦或魚種機率的共用資訊列。
function RankRow(props: {
  marker: string
  title: string
  description: string
  value: string
}) {
  return (
    <div className="grid grid-cols-[38px_1fr_auto] items-center gap-3 rounded-[14px] border border-white/10 bg-white/4 p-3">
      <span className="grid h-[34px] w-[34px] place-items-center rounded-[10px] bg-[rgba(61,255,138,0.14)] text-[11px] font-extrabold uppercase text-(--fs-green-soft)">
        {props.marker}
      </span>
      <div className="min-w-0">
        <h3 className="text-sm font-semibold">{props.title}</h3>
        <p className="mt-0.5 text-xs text-(--fs-muted)">{props.description}</p>
      </div>
      <b className="text-sm">{props.value}</b>
    </div>
  )
}

// 載入已驗證的使用者資料，並呈現目前的 dashboard rebuild baseline。
export function DashboardPage(props: { apiBaseUrl: string; onSignOut: () => void }) {
  const { t } = useTranslation()
  const currentUser = useCurrentUser(props.apiBaseUrl, props.onSignOut)
  const catchTargets = [
    ['A', t('dashboard.largemouthBass'), t('dashboard.largemouthNote'), '72%'],
    ['B', t('dashboard.smallmouthBass'), t('dashboard.smallmouthNote'), '18%'],
    ['C', t('dashboard.yellowPerch'), t('dashboard.yellowPerchNote'), '10%'],
  ]
  const recommendations = [
    ['01', t('dashboard.spinnerbait'), t('dashboard.spinnerbaitNote'), t('dashboard.high')],
    ['02', t('dashboard.weightlessWorm'), t('dashboard.weightlessWormNote'), t('dashboard.medium')],
    ['03', t('dashboard.jig'), t('dashboard.jigNote'), t('dashboard.medium')],
  ]
  const recentLogs = [
    { id: '1', date: t('dashboard.log1Date'), title: t('dashboard.log1Place'), description: t('dashboard.log1Note'), state: 'matched' },
    { id: '2', date: t('dashboard.log2Date'), title: t('dashboard.log2Place'), description: t('dashboard.log2Note'), state: 'rag' },
    { id: '3', date: t('dashboard.log3Date'), title: t('dashboard.log3Place'), description: t('dashboard.log3Note'), state: 'older' },
  ] as const
  const sessionLabel = currentUser.isLoading
    ? t('dashboard.validatingSession')
    : currentUser.user
      ? t('dashboard.signedInAs', { email: currentUser.user.email })
      : currentUser.hasError ? t('dashboard.userUnavailable') : t('dashboard.sessionUnavailable')

  return (
    <TacticalShell
      actions={<SignOutButton onSignOut={props.onSignOut} />}
      sessionLabel={sessionLabel}
    >
      <div className="mb-5 grid items-end gap-5 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-(--fs-faint)">
            {t('dashboard.forecastEyebrow')}
          </p>
          <h1 className="mt-2 max-w-[780px] text-[clamp(2rem,4.2vw,3.625rem)] font-extrabold leading-[0.96]">
            {t('dashboard.headline')}
          </h1>
          <p className="mt-4 max-w-[660px] text-[15px] leading-relaxed text-(--fs-muted)">
            {t('dashboard.description')}
          </p>
        </div>
        <div className="flex flex-wrap gap-2.5">
          <button
            type="button"
            className="min-h-[42px] cursor-pointer rounded-xl border border-white/15 bg-white/5 px-4 text-sm font-bold text-slate-100 transition-colors duration-200 hover:border-white/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--fs-green)"
          >
            {t('dashboard.tuneInputs')}
          </button>
          <button
            type="button"
            className="min-h-[42px] cursor-pointer rounded-xl border border-[rgba(61,255,138,0.52)] bg-(--fs-green) px-4 text-sm font-bold text-[#031007] shadow-[0_0_36px_rgba(61,255,138,0.28)] transition-opacity duration-200 hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--fs-green)"
          >
            {t('dashboard.generatePlan')}
          </button>
        </div>
      </div>

      <section className="grid gap-[18px] xl:grid-cols-[minmax(0,1.08fr)_minmax(360px,0.92fr)]">
        <div className="grid gap-[18px]">
          <BiteCurvePanel />

          <section className="grid gap-[18px] lg:grid-cols-[minmax(0,0.88fr)_minmax(300px,1.12fr)]">
            <article className="grid min-h-[318px] grid-rows-[auto_1fr_auto] gap-4 rounded-[18px] border border-(--fs-line) bg-(--fs-panel) p-[18px] shadow-[inset_0_1px_rgba(255,255,255,0.04)] backdrop-blur-[18px]">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-(--fs-faint)">
                    {t('dashboard.predictionSection')}
                  </p>
                  <h2 className="mt-1 text-[17px] font-semibold">{t('dashboard.missionScore')}</h2>
                </div>
                <span className="inline-flex min-h-7 items-center rounded-full border border-white/10 bg-black/30 px-3 text-xs font-bold text-(--fs-muted)">
                  {t('dashboard.largemouth')}
                </span>
              </div>

              <div className="grid min-h-[130px] place-items-center rounded-2xl border border-[rgba(61,255,138,0.2)] bg-[radial-gradient(circle,rgba(61,255,138,0.16),rgba(0,0,0,0.16)_62%)] text-center">
                <div>
                  <strong className="block text-[62px] leading-none">87</strong>
                  <span className="text-sm text-(--fs-muted)">{t('dashboard.biteConfidence')}</span>
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
          <section className="rounded-[18px] border border-(--fs-line) bg-(--fs-panel) p-[18px] shadow-[inset_0_1px_rgba(255,255,255,0.04)] backdrop-blur-[18px]">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-(--fs-faint)">
                  {t('dashboard.speciesRank')}
                </p>
                <h2 className="mt-1 text-[17px] font-semibold">{t('dashboard.likelyCatches')}</h2>
              </div>
              <span className="inline-flex min-h-7 items-center rounded-full border border-white/10 bg-black/30 px-3 text-xs font-bold text-(--fs-muted)">
                {t('dashboard.targetCount')}
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

          <section className="rounded-[18px] border border-(--fs-line) bg-(--fs-panel) p-[18px] shadow-[inset_0_1px_rgba(255,255,255,0.04)] backdrop-blur-[18px]">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-(--fs-faint)">
                  {t('dashboard.catchingLogs')}
                </p>
                <h2 className="mt-1 text-[17px] font-semibold">{t('dashboard.feedbackLoop')}</h2>
              </div>
              <button
                type="button"
                className="min-h-[42px] cursor-pointer rounded-xl border border-[rgba(61,255,138,0.52)] bg-(--fs-green) px-4 text-sm font-bold text-[#031007] shadow-[0_0_36px_rgba(61,255,138,0.28)] transition-opacity duration-200 hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--fs-green)"
              >
                {t('dashboard.addLog')}
              </button>
            </div>
            <div className="grid gap-2.5">
              {recentLogs.map(({ id, date, title, description, state }) => (
                <div
                  key={id}
                  className="grid gap-3 rounded-[14px] border border-white/10 bg-white/[0.035] p-3 sm:grid-cols-[76px_1fr_auto] sm:items-center"
                >
                  <span className="text-sm font-extrabold text-(--fs-green-soft)">{date}</span>
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold">{title}</h3>
                    <p className="mt-1 text-xs text-(--fs-muted)">{description}</p>
                  </div>
                  <span
                    className={`inline-flex min-h-7 w-fit items-center rounded-full border px-3 text-xs font-bold ${
                      state === 'matched'
                        ? 'border-[rgba(61,255,138,0.36)] text-(--fs-green-soft)'
                        : 'border-white/10 text-(--fs-muted)'
                    }`}
                  >
                    {t(`dashboard.${state}`)}
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
