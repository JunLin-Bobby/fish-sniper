import { useTranslation } from 'react-i18next'

// 將最近紀錄獨立為全寬區塊，標示範例資料並停用尚未開發的新增操作。
export function CatchLogPanel() {
  const { t } = useTranslation()
  const logs = [
    ['log1Date', 'log1Place', 'log1Note'],
    ['log2Date', 'log2Place', 'log2Note'],
    ['log3Date', 'log3Place', 'log3Note'],
  ]
  return (
    <section id="logs" tabIndex={-1} aria-labelledby="logs-heading" className="dashboard-logs dashboard-anchor grid gap-4 rounded-[18px] border border-(--fs-line) bg-(--fs-panel) p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="logs-heading" className="text-base font-semibold">{t('dashboardLayout.recentLogs')}</h2>
          <span className="rounded-full border border-white/15 px-2.5 py-1 text-xs text-(--fs-muted)">{t('dashboardLayout.previewBadge')}</span>
        </div>
        <button type="button" disabled className="min-h-11 rounded-lg border border-white/15 px-3 text-sm text-(--fs-muted) disabled:cursor-not-allowed">{t('dashboardLayout.addLogUnavailable')}</button>
      </div>
      <p className="text-xs text-(--fs-muted)">{t('dashboardLayout.logsDisclaimer')}</p>
      <ul className="grid gap-2">
        {logs.map(([date, place, note], index) => (
          <li key={date} className={`${index === 2 ? 'hidden sm:grid' : 'grid'} gap-2 rounded-xl border border-white/10 bg-white/4 p-3 sm:grid-cols-[80px_minmax(0,1fr)] sm:items-center`}>
            <span className="text-sm font-semibold text-(--fs-green-soft)">{t(`dashboard.${date}`)}</span>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold">{t(`dashboard.${place}`)}</h3>
              <p className="mt-1 text-xs leading-relaxed text-(--fs-muted)">{t(`dashboard.${note}`)}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
