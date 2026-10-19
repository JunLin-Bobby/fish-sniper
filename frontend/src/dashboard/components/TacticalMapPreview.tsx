import { useTranslation } from 'react-i18next'
import type { SelectedLocation } from '../../weather/api/weatherTypes.ts'

// 顯示目前仍為示意資料的地圖與建議釣點。
export function TacticalMapPreview(props: { location: SelectedLocation | null }) {
  const { t } = useTranslation()
  const pins = [
    ['1', 'left-[31%] top-[44%] border-[rgba(61,255,138,0.52)] text-(--fs-green)'],
    ['2', 'right-[24%] top-[33%] border-[rgba(56,214,255,0.52)] text-(--fs-cyan)'],
    [
      '3',
      'bottom-[25%] right-[33%] border-[rgba(251,191,36,0.52)] text-(--fs-amber)',
    ],
  ]

  return (
    <section id="spots" tabIndex={-1}
      className="dashboard-map dashboard-anchor relative min-h-[340px] overflow-hidden rounded-[18px] border border-(--fs-line) bg-[#04111c] sm:min-h-[380px]"
      aria-labelledby="spots-heading"
    >
      <div className="relative z-10 p-[18px]">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="spots-heading" className="text-base font-semibold">{t('dashboardLayout.mapTitle')}</h2>
          <span className="rounded-full border border-white/15 bg-[#04111c] px-2.5 py-1 text-xs text-(--fs-muted)">{t('dashboardLayout.previewBadge')}</span>
        </div>
        <p className="mt-2 text-xs text-(--fs-muted)">{props.location?.name || t('dashboardLayout.mapPlaceholder')}</p>
      </div>

      <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_28%,rgba(56,214,255,0.18),transparent_13rem),linear-gradient(135deg,rgba(5,150,105,0.17),transparent_48%)]" />
      <div className="absolute inset-x-8 bottom-10 top-14 rounded-[42%_58%_50%_44%] border border-[rgba(56,214,255,0.26)] bg-[radial-gradient(circle_at_34%_34%,rgba(155,255,208,0.22),transparent_5rem),linear-gradient(135deg,rgba(56,214,255,0.34),rgba(6,78,59,0.56))] shadow-[inset_0_0_48px_rgba(0,0,0,0.42)] [clip-path:polygon(8%_35%,18%_14%,42%_10%,54%_24%,77%_16%,92%_34%,85%_58%,96%_75%,73%_92%,48%_78%,30%_91%,10%_72%)]" />

      {pins.map(([label, className]) => (
        <span
          key={label} aria-hidden="true"
          className={`absolute grid h-[34px] w-[34px] place-items-center rounded-full border bg-[rgba(3,16,7,0.74)] text-xs font-extrabold shadow-[0_0_24px_rgba(61,255,138,0.26)] ${className}`}
        >
          {label}
        </span>
      ))}

      <div className="absolute inset-x-4 bottom-4 rounded-xl border border-white/10 bg-[#04111c] p-3 text-xs leading-relaxed text-(--fs-muted)">
        {t('dashboardLayout.mapDisclaimer')}
      </div>
    </section>
  )
}
