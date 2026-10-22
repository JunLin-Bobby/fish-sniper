import { CatchLogsWorkspace } from '../../catch-logs/components/CatchLogsWorkspace.tsx'

// 將真實私人漁獲功能接到首頁紀錄區，取代無法儲存的範例清單。
export function CatchLogPanel(props: { apiBaseUrl: string; onUnauthorized: () => void }) {
  return <CatchLogsWorkspace {...props} />
}
