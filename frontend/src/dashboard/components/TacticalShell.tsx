import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { LanguageSwitcher } from '../../i18n/LanguageSwitcher.tsx'

// 提供 dashboard 共用導覽、session 狀態與主要內容版面。
export function TacticalShell(props: {
  children: ReactNode
  actions?: ReactNode
  sessionLabel?: string
}) {
  const { t } = useTranslation()
  const navItems = [t('dashboard.forecast'), t('dashboard.map'), t('dashboard.logs'), t('dashboard.report')]
  const railItems = [
    ['FX', t('dashboard.forecast')],
    ['MP', t('dashboard.map')],
    ['LG', t('dashboard.logs')],
    ['ST', t('dashboard.settings')],
  ]

  return (
    <main className="relative mx-auto min-h-dvh w-full max-w-[1440px] p-3 text-(--fs-ink) sm:p-5">
      <section
        className="min-h-[calc(100dvh-1.5rem)] overflow-hidden rounded-3xl border border-(--fs-line) bg-[rgba(2,6,23,0.72)] shadow-[0_32px_90px_rgba(0,0,0,0.46)] backdrop-blur-2xl sm:min-h-[calc(100dvh-2.5rem)]"
        aria-label={t('dashboard.tacticalDashboard')}
      >
        <header className="flex min-h-[72px] flex-wrap items-center justify-between gap-4 border-b border-white/10 bg-[rgba(2,6,23,0.55)] px-5 py-4">
          <div className="flex min-w-48 items-center gap-3">
            <div className="grid h-[38px] w-[38px] place-items-center rounded-[10px] border border-[rgba(61,255,138,0.46)] bg-[linear-gradient(145deg,rgba(61,255,138,0.2),rgba(56,214,255,0.08))] text-sm font-extrabold text-(--fs-green)">
              FS
            </div>
            <div>
              <strong className="block leading-tight">FishSniper</strong>
              <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-(--fs-faint)">
                {t('dashboard.controlRoom')}
              </span>
            </div>
          </div>

          <nav
            className="hidden items-center gap-1 rounded-full border border-white/10 bg-black/25 p-1 md:flex"
            aria-label={t('dashboard.sections')}
          >
            {navItems.map((item, index) => (
              <button
                key={item}
                type="button"
                className={`min-h-9 cursor-pointer rounded-full px-4 text-[11px] font-bold uppercase tracking-widest transition-colors duration-200 ${
                  index === 0
                    ? 'bg-[rgba(61,255,138,0.16)] text-(--fs-green-soft)'
                    : 'text-(--fs-muted) hover:text-slate-100'
                }`}
              >
                {item}
              </button>
            ))}
          </nav>

          <div className="flex flex-wrap items-center justify-end gap-3">
            <LanguageSwitcher />
            <div className="flex items-center gap-2 whitespace-nowrap text-sm text-(--fs-muted)">
              <span className="h-2.5 w-2.5 rounded-full bg-(--fs-green) shadow-[0_0_18px_rgba(61,255,138,0.85)]" />
              {props.sessionLabel ?? t('dashboard.sessionArmed')}
            </div>
            {props.actions}
          </div>
        </header>

        <div className="grid min-h-[calc(100dvh-94px)] md:grid-cols-[82px_minmax(0,1fr)]">
          <aside
            className="hidden flex-col items-center gap-3 border-r border-white/10 bg-black/20 px-3 py-5 md:flex"
            aria-label={t('dashboard.primaryActions')}
          >
            {railItems.map(([label, name], index) => (
              <button
                key={name}
                type="button"
                aria-label={name}
                aria-current={index === 0 ? 'page' : undefined}
                className={`grid h-11 w-11 cursor-pointer place-items-center rounded-[14px] border text-[11px] font-extrabold transition-colors duration-200 ${
                  index === 0
                    ? 'border-[rgba(61,255,138,0.5)] bg-[rgba(61,255,138,0.14)] text-(--fs-green)'
                    : 'border-white/10 bg-white/4 text-(--fs-muted) hover:border-white/20 hover:text-slate-100'
                }`}
              >
                {label}
              </button>
            ))}
          </aside>

          <div className="min-w-0 p-4 sm:p-5">{props.children}</div>
        </div>
      </section>
    </main>
  )
}
