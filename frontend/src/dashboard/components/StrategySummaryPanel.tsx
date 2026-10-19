import { useTranslation } from 'react-i18next'
import type { SelectedLocation } from '../../weather/api/weatherTypes.ts'

// 顯示示意的魚種或釣法資訊，不將尚未驗證的數字當成真實成功率。
function RecommendationRow(props: { title: string; description: string }) {
  return (
    <li className="rounded-xl border border-white/10 bg-white/4 p-3">
      <h4 className="text-sm font-semibold">{props.title}</h4>
      <p className="mt-1 text-xs leading-relaxed text-(--fs-muted)">{props.description}</p>
    </li>
  )
}

// 提供簡短策略區與可展開的示意內容；真實 AI 尚未接上，不啟用假操作。
export function StrategySummaryPanel(props: { location: SelectedLocation | null; date: string }) {
  const { t } = useTranslation()
  const species = [
    ['largemouthBass', 'largemouthNote'], ['smallmouthBass', 'smallmouthNote'], ['yellowPerch', 'yellowPerchNote'],
  ]
  const lures = [
    ['spinnerbait', 'spinnerbaitNote'], ['weightlessWorm', 'weightlessWormNote'], ['jig', 'jigNote'],
  ]
  return (
    <section id="strategy" tabIndex={-1} aria-labelledby="strategy-heading" className="dashboard-strategy dashboard-anchor grid gap-4 rounded-[18px] border border-(--fs-line) bg-(--fs-panel) p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="strategy-heading" className="text-base font-semibold">{t('dashboardLayout.strategyTitle')}</h2>
        <span className="rounded-full border border-white/15 px-2.5 py-1 text-xs text-(--fs-muted)">{t('dashboardLayout.previewBadge')}</span>
      </div>
      <p className="text-xs leading-relaxed text-(--fs-muted)">
        {props.location ? t('dashboardLayout.selectedContext', { date: props.date, location: props.location.name || `${props.location.latitude.toFixed(3)}, ${props.location.longitude.toFixed(3)}` }) : t('liveWeather.choosePrompt')}
      </p>
      <div className="rounded-xl border border-white/10 bg-black/20 p-4">
        <p className="text-xs text-(--fs-muted)">{t('dashboardLayout.strategyStatus')}</p>
        <p className="mt-2 text-lg font-semibold">{t('dashboardLayout.notGenerated')}</p>
        <p className="mt-2 text-sm leading-relaxed text-(--fs-muted)">{t('dashboardLayout.strategyDisclaimer')}</p>
      </div>
      <button type="button" disabled className="min-h-11 rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm font-semibold text-(--fs-muted) disabled:cursor-not-allowed">
        {t('dashboardLayout.generateUnavailable')}
      </button>
      <details className="rounded-xl border border-white/10">
        <summary className="min-h-11 cursor-pointer px-3 py-3 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-(--fs-green)">{t('dashboardLayout.exampleRecommendations')}</summary>
        <div className="grid gap-4 px-3 pb-3">
          <div>
            <h3 className="mb-2 text-sm font-semibold">{t('dashboardLayout.exampleSpecies')}</h3>
            <ul className="grid gap-2">{species.map(([title, note]) => <RecommendationRow key={title} title={t(`dashboard.${title}`)} description={t(`dashboard.${note}`)} />)}</ul>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold">{t('dashboardLayout.exampleLures')}</h3>
            <ul className="grid gap-2">{lures.map(([title, note]) => <RecommendationRow key={title} title={t(`dashboard.${title}`)} description={t(`dashboard.${note}`)} />)}</ul>
          </div>
        </div>
      </details>
    </section>
  )
}
