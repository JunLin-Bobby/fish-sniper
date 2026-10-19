import { useTranslation } from 'react-i18next'
import { dashboardSections, type DashboardSection } from '../hooks/useDashboardNavigation.ts'

// 使用同一組簡單圖示辨識四個主要目的地，文字標籤仍保持可見。
function NavigationIcon(props: { section: DashboardSection }) {
  const paths: Record<DashboardSection, string> = {
    overview: 'M3 10 12 3l9 7M5 9v12h5v-7h4v7h5V9',
    spots: 'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0ZM12 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6',
    strategy: 'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z',
    logs: 'M5 3h14v18H5ZM8 7h8M8 12h8M8 17h5',
  }
  return <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d={paths[props.section]} /></svg>
}

// 共用桌面頂部與手機底部導覽；目前連到首頁區塊，而非尚未開發的路由。
export function DashboardNavigation(props: {
  placement: 'desktop' | 'mobile'
  activeSection: DashboardSection
  onNavigate: (section: DashboardSection) => void
}) {
  const { t } = useTranslation()
  return (
    <nav aria-label={t('dashboardLayout.navigation')} className={`dashboard-navigation dashboard-navigation--${props.placement}`}>
      {dashboardSections.map((section) => (
        <a key={section} href={`#${section}`} aria-current={props.activeSection === section ? 'location' : undefined}
          onClick={() => props.onNavigate(section)} className="dashboard-navigation-link">
          <NavigationIcon section={section} />
          <span>{t(`dashboardLayout.${section}`)}</span>
        </a>
      ))}
    </nav>
  )
}
