import { useTranslation } from 'react-i18next'

// 顯示目前仍為示意資料的地圖與建議釣點。
export function TacticalMapPreview() {
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
    <article
      className="relative min-h-[318px] overflow-hidden rounded-[18px] border border-(--fs-line) bg-[#04111c] shadow-[inset_0_1px_rgba(255,255,255,0.04)]"
      aria-label={t('mapPreview.positionsLabel')}
    >
      <div className="relative z-10 p-[18px]">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-(--fs-faint)">
          {t('mapPreview.section')}
        </p>
        <h2 className="mt-1 text-[17px] font-semibold">{t('mapPreview.title')}</h2>
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

      <div className="absolute inset-x-4 bottom-4 flex flex-wrap items-center justify-between gap-3 text-xs text-(--fs-muted)">
        <span>{t('mapPreview.northReeds')}</span>
        <span className="inline-flex min-h-7 items-center rounded-full border border-[rgba(61,255,138,0.36)] bg-black/30 px-3 text-xs font-bold text-(--fs-green-soft)">
          {t('mapPreview.bestCastLine')}
        </span>
      </div>
    </article>
  )
}
