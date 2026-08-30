export function BiteCurvePanel() {
  const stats = [
    ['Pressure', '1017', 'hPa rising slowly'],
    ['Wind', '3.8', 'm/s NE bank'],
    ['Water', '1.7m', 'target depth'],
  ]

  return (
    <section
      className="grid min-h-[270px] gap-[18px] rounded-[18px] border border-[var(--fs-line)] bg-[var(--fs-panel)] p-[18px] shadow-[inset_0_1px_rgba(255,255,255,0.04)] backdrop-blur-[18px] lg:grid-cols-[1fr_210px]"
      aria-label="Weather graph"
    >
      <div>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--fs-faint)]">
              01 · Air / pressure / activity
            </p>
            <h2 className="mt-1 text-[17px] font-semibold">Today's bite curve</h2>
          </div>
          <span className="inline-flex min-h-7 items-center rounded-full border border-[rgba(61,255,138,0.36)] bg-black/30 px-3 text-xs font-bold text-[var(--fs-green-soft)]">
            Prime window · 06:10-09:00
          </span>
        </div>

        <div className="relative min-h-[220px] rounded-[14px] border border-white/[0.08] bg-[linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px),rgba(0,0,0,0.22)] bg-[length:100%_25%,16.666%_100%,auto]">
          <div className="absolute inset-x-3.5 top-3 flex justify-between text-[11px] font-bold text-[var(--fs-faint)]">
            <span>00:00</span>
            <span>06:00</span>
            <span>12:00</span>
            <span>18:00</span>
          </div>
          <svg viewBox="0 0 720 220" role="img" aria-label="Bite prediction line chart">
            <path
              d="M0 168 C80 158 92 116 154 122 C222 128 222 58 292 68 C366 80 390 132 458 118 C540 101 565 136 626 116 C674 101 690 82 720 72"
              fill="none"
              stroke="rgba(61,255,138,.95)"
              strokeWidth="4"
            />
            <path
              d="M0 168 C80 158 92 116 154 122 C222 128 222 58 292 68 C366 80 390 132 458 118 C540 101 565 136 626 116 C674 101 690 82 720 72 L720 220 L0 220 Z"
              fill="url(#bite-glow)"
              opacity=".75"
            />
            <path
              d="M0 118 C88 112 126 142 190 134 C270 124 310 152 382 132 C466 108 522 86 598 96 C660 104 690 124 720 112"
              fill="none"
              stroke="rgba(56,214,255,.68)"
              strokeDasharray="8 8"
              strokeWidth="2"
            />
            <defs>
              <linearGradient id="bite-glow" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="rgba(61,255,138,.32)" />
                <stop offset="100%" stopColor="rgba(61,255,138,0)" />
              </linearGradient>
            </defs>
          </svg>
        </div>
      </div>

      <div className="grid gap-2.5 sm:grid-cols-3 lg:grid-cols-1">
        {stats.map(([label, value, note]) => (
          <div key={label} className="rounded-[14px] border border-white/10 bg-white/[0.04] p-3">
            <small className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--fs-faint)]">
              {label}
            </small>
            <strong className="mt-2 block text-[28px] leading-none">{value}</strong>
            <span className="mt-2 block text-xs leading-relaxed text-[var(--fs-muted)]">{note}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

export function TacticalMapPreview() {
  const pins = [
    ['1', 'left-[31%] top-[44%] border-[rgba(61,255,138,0.52)] text-[var(--fs-green)]'],
    ['2', 'right-[24%] top-[33%] border-[rgba(56,214,255,0.52)] text-[var(--fs-cyan)]'],
    [
      '3',
      'bottom-[25%] right-[33%] border-[rgba(251,191,36,0.52)] text-[var(--fs-amber)]',
    ],
  ]

  return (
    <article
      className="relative min-h-[318px] overflow-hidden rounded-[18px] border border-[var(--fs-line)] bg-[#04111c] shadow-[inset_0_1px_rgba(255,255,255,0.04)]"
      aria-label="Recommended map positions"
    >
      <div className="relative z-10 p-[18px]">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--fs-faint)]">
          03 · Hot zones
        </p>
        <h2 className="mt-1 text-[17px] font-semibold">Map-first recommendation</h2>
      </div>

      <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_28%,rgba(56,214,255,0.18),transparent_13rem),linear-gradient(135deg,rgba(5,150,105,0.17),transparent_48%)]" />
      <div className="absolute inset-x-8 bottom-10 top-14 rounded-[42%_58%_50%_44%] border border-[rgba(56,214,255,0.26)] bg-[radial-gradient(circle_at_34%_34%,rgba(155,255,208,0.22),transparent_5rem),linear-gradient(135deg,rgba(56,214,255,0.34),rgba(6,78,59,0.56))] shadow-[inset_0_0_48px_rgba(0,0,0,0.42)] [clip-path:polygon(8%_35%,18%_14%,42%_10%,54%_24%,77%_16%,92%_34%,85%_58%,96%_75%,73%_92%,48%_78%,30%_91%,10%_72%)]" />

      {pins.map(([label, className]) => (
        <span
          key={label}
          className={`absolute grid h-[34px] w-[34px] place-items-center rounded-full border bg-[rgba(3,16,7,0.74)] text-xs font-extrabold shadow-[0_0_24px_rgba(61,255,138,0.26)] ${className}`}
        >
          {label}
        </span>
      ))}

      <div className="absolute inset-x-4 bottom-4 flex flex-wrap items-center justify-between gap-3 text-xs text-[var(--fs-muted)]">
        <span>North reed pocket · 1.2-1.8m</span>
        <span className="inline-flex min-h-7 items-center rounded-full border border-[rgba(61,255,138,0.36)] bg-black/30 px-3 text-xs font-bold text-[var(--fs-green-soft)]">
          Best cast line
        </span>
      </div>
    </article>
  )
}
