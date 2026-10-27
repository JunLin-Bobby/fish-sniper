import { CatchLogsWorkspace } from '../../catch-logs/components/CatchLogsWorkspace.tsx'
import type { CatchLogSubmission } from '../../catch-logs/hooks/useCatchLogSubmission.ts'

// 將真實私人漁獲功能接到首頁紀錄區，取代無法儲存的範例清單。
export function CatchLogPanel(props: { apiBaseUrl: string; onUnauthorized: () => void; submission: CatchLogSubmission }) {
  return <CatchLogsWorkspace {...props} />
}
