import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { LanguageSwitcher } from '../../i18n/LanguageSwitcher.tsx'
import { useDashboardNavigation } from '../hooks/useDashboardNavigation.ts'
import { DashboardNavigation } from './DashboardNavigation.tsx'
import '../dashboard.css'

// 提供桌面黏附導覽、手機底部導覽與帳號選單，不再重複顯示左側導覽列。
export function TacticalShell(props: {
  children: ReactNode
  actions?: ReactNode
  sessionLabel?: string
  submissionStatus?: ReactNode
}) {
  const { t } = useTranslation()
  const { activeSection, setActiveSection } = useDashboardNavigation()
  const headerRef = useRef<HTMLElement>(null)
  const accountRef = useRef<HTMLDetailsElement>(null)
  const [headerHeight, setHeaderHeight] = useState(72)

  useEffect(() => {
    const header = headerRef.current
    if (!header) return
    const observedHeader = header

    // 依實際 header 高度更新錨點間距，英文或換行時也不遮住區塊標題。
    function updateHeaderHeight(): void {
      setHeaderHeight(observedHeader.getBoundingClientRect().height)
    }

    updateHeaderHeight()
    const observer = new ResizeObserver(updateHeaderHeight)
    observer.observe(header)
    return () => observer.disconnect()
  }, [])

  // 點選選單外或按 Escape 時關閉帳號資訊，避免它一直覆蓋頁面。
  useEffect(() => {
    // 只收合帳號選單，不影響天氣圖表或策略的其他 details。
    function closeOnOutside(event: PointerEvent): void {
      const menu = accountRef.current
      if (menu?.open && event.target instanceof Node && !menu.contains(event.target)) menu.open = false
    }

    // Escape 關閉後將鍵盤焦點還給帳號入口。
    function closeOnEscape(event: KeyboardEvent): void {
      const menu = accountRef.current
      if (event.key === 'Escape' && menu?.open) {
        menu.open = false
        menu.querySelector('summary')?.focus()
      }
    }

    document.addEventListener('pointerdown', closeOnOutside)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutside)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [])

  return (
    <div className="relative mx-auto min-h-dvh w-full max-w-[1440px] p-2 text-(--fs-ink) sm:p-5"
      style={{ '--dashboard-header-offset': `${headerHeight + 16}px` } as CSSProperties}>
      <div className="min-h-dvh rounded-2xl border border-(--fs-line) bg-[rgba(2,6,23,0.72)] shadow-[0_32px_90px_rgba(0,0,0,0.35)]" aria-label={t('dashboard.tacticalDashboard')}>
        <header ref={headerRef} data-dashboard-header className="dashboard-header flex min-h-[64px] flex-wrap items-center justify-between gap-3 rounded-t-2xl border-b border-white/10 bg-[#07101f] px-3 py-3 sm:px-5">
          <a href="#overview" onClick={() => setActiveSection('overview')} className="flex items-center gap-2 font-bold" aria-label="FishSniper">
            <span aria-hidden="true" className="hidden h-8 w-8 place-items-center rounded-lg border border-[rgba(61,255,138,.35)] text-xs text-(--fs-green) min-[380px]:grid">FS</span>
            <span className="text-sm sm:text-base">FishSniper</span>
          </a>
          <DashboardNavigation placement="desktop" activeSection={activeSection} onNavigate={setActiveSection} />
          <div className="flex items-center gap-2">
            <LanguageSwitcher compact />
            <details ref={accountRef}>
              <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 rounded-lg border border-white/15 px-2.5 text-xs font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-(--fs-green)">
                <span aria-hidden="true" className="h-2 w-2 rounded-full bg-(--fs-green)" />
                {t('dashboardLayout.account')}
              </summary>
              <div className="absolute right-3 top-full z-50 mt-2 grid w-[min(20rem,calc(100vw-2rem))] gap-3 rounded-xl border border-white/15 bg-[#0b1727] p-4 shadow-xl sm:right-5">
                <p className="break-all text-sm text-(--fs-muted)">{props.sessionLabel ?? t('dashboard.sessionArmed')}</p>
                {props.actions}
              </div>
            </details>
          </div>
          {props.submissionStatus ? <div className="basis-full">{props.submissionStatus}</div> : null}
        </header>
        <main className="dashboard-content min-w-0 p-3 sm:p-5">{props.children}</main>
      </div>
      <DashboardNavigation placement="mobile" activeSection={activeSection} onNavigate={setActiveSection} />
    </div>
  )
}
