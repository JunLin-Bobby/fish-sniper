import type { ReactNode } from 'react'

export function TacticalShell(props: { children: ReactNode; actions?: ReactNode }) {
  const navItems = ['Forecast', 'Map', 'Logs', 'Report']
  const railItems = [
    ['FX', 'Forecast'],
    ['MP', 'Map'],
    ['LG', 'Logs'],
    ['ST', 'Settings'],
  ]

  return (
    <main className="relative mx-auto min-h-dvh w-full max-w-[1440px] p-3 text-[var(--fs-ink)] sm:p-5">
      <section
        className="min-h-[calc(100dvh-1.5rem)] overflow-hidden rounded-[1.5rem] border border-[var(--fs-line)] bg-[rgba(2,6,23,0.72)] shadow-[0_32px_90px_rgba(0,0,0,0.46)] backdrop-blur-2xl sm:min-h-[calc(100dvh-2.5rem)]"
        aria-label="FishSniper tactical dashboard"
      >
        <header className="flex min-h-[72px] flex-wrap items-center justify-between gap-4 border-b border-white/10 bg-[rgba(2,6,23,0.55)] px-5 py-4">
          <div className="flex min-w-48 items-center gap-3">
            <div className="grid h-[38px] w-[38px] place-items-center rounded-[10px] border border-[rgba(61,255,138,0.46)] bg-[linear-gradient(145deg,rgba(61,255,138,0.2),rgba(56,214,255,0.08))] text-sm font-extrabold text-[var(--fs-green)]">
              FS
            </div>
            <div>
              <strong className="block leading-tight">FishSniper</strong>
              <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--fs-faint)]">
                Control Room
              </span>
            </div>
          </div>

          <nav
            className="hidden items-center gap-1 rounded-full border border-white/10 bg-black/25 p-1 md:flex"
            aria-label="Dashboard sections"
          >
            {navItems.map((item, index) => (
              <button
                key={item}
                type="button"
                className={`min-h-9 cursor-pointer rounded-full px-4 text-[11px] font-bold uppercase tracking-[0.1em] transition-colors duration-200 ${
                  index === 0
                    ? 'bg-[rgba(61,255,138,0.16)] text-[var(--fs-green-soft)]'
                    : 'text-[var(--fs-muted)] hover:text-slate-100'
                }`}
              >
                {item}
              </button>
            ))}
          </nav>

          <div className="flex flex-wrap items-center justify-end gap-3">
            <div className="flex items-center gap-2 whitespace-nowrap text-sm text-[var(--fs-muted)]">
              <span className="h-2.5 w-2.5 rounded-full bg-[var(--fs-green)] shadow-[0_0_18px_rgba(61,255,138,0.85)]" />
              Session armed · Dev auth
            </div>
            {props.actions}
          </div>
        </header>

        <div className="grid min-h-[calc(100dvh-94px)] md:grid-cols-[82px_minmax(0,1fr)]">
          <aside
            className="hidden flex-col items-center gap-3 border-r border-white/10 bg-black/20 px-3 py-5 md:flex"
            aria-label="Primary actions"
          >
            {railItems.map(([label, name], index) => (
              <button
                key={name}
                type="button"
                aria-label={name}
                aria-current={index === 0 ? 'page' : undefined}
                className={`grid h-11 w-11 cursor-pointer place-items-center rounded-[14px] border text-[11px] font-extrabold transition-colors duration-200 ${
                  index === 0
                    ? 'border-[rgba(61,255,138,0.5)] bg-[rgba(61,255,138,0.14)] text-[var(--fs-green)]'
                    : 'border-white/10 bg-white/[0.04] text-[var(--fs-muted)] hover:border-white/20 hover:text-slate-100'
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
