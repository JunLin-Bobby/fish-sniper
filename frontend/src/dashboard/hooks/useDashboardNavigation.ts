import { useEffect, useState } from 'react'

export const dashboardSections = ['overview', 'spots', 'strategy', 'logs'] as const
export type DashboardSection = typeof dashboardSections[number]

// 驗證 URL hash 是否指向目前首頁的實際區塊，不建立不存在的功能頁。
function sectionFromHash(): DashboardSection {
  const hash = window.location.hash.slice(1)
  return dashboardSections.find((section) => section === hash) ?? 'overview'
}

// 桌面與手機共用目前區塊狀態，隨錨點導覽及手動捲動更新。
export function useDashboardNavigation() {
  const [activeSection, setActiveSection] = useState<DashboardSection>(sectionFromHash)

  useEffect(() => {
    let frame: number | null = null

    // 以導覽列下方為閱讀位置，選擇已到達且最接近的區塊。
    function updateFromScroll(): void {
      frame = null
      const header = document.querySelector<HTMLElement>('[data-dashboard-header]')
      const offset = window.matchMedia('(min-width: 1024px)').matches
        ? (header?.getBoundingClientRect().height ?? 72) + 24 : 24
      const candidates = dashboardSections.flatMap((id) => {
        const element = document.getElementById(id)
        return element ? [{ id, top: element.getBoundingClientRect().top }] : []
      }).filter((section) => section.top <= offset).sort((first, second) => second.top - first.top)
      const atBottom = window.scrollY > 0 && window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2
      setActiveSection(atBottom ? 'logs' : candidates[0]?.id ?? 'overview')
    }

    // 將頻繁的 scroll/resize 事件合併到單一動畫幀，避免反覆讀取版面。
    function scheduleUpdate(): void {
      if (frame === null) frame = window.requestAnimationFrame(updateFromScroll)
    }

    // 保留使用者點選的區塊，原生錨點負責捲動與瀏覽器歷史。
    function handleHashChange(): void {
      setActiveSection(sectionFromHash())
    }

    window.addEventListener('scroll', scheduleUpdate, { passive: true })
    window.addEventListener('resize', scheduleUpdate)
    window.addEventListener('hashchange', handleHashChange)
    return () => {
      if (frame !== null) window.cancelAnimationFrame(frame)
      window.removeEventListener('scroll', scheduleUpdate)
      window.removeEventListener('resize', scheduleUpdate)
      window.removeEventListener('hashchange', handleHashChange)
    }
  }, [])

  return { activeSection, setActiveSection }
}
