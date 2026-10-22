import { deleteResource, getJson, patchJson, postJson } from '../../api/http.ts'
import type { CatchLog, CatchLogInput, CatchLogPage } from './catchLogTypes.ts'

const path = '/api/v1/catch-logs'
export const catchLogPageSize = 10

// 從 FishSniper API 載入私人紀錄的一頁資料，不直接連接 Supabase。
export function fetchCatchLogs(apiBaseUrl: string, offset: number, signal?: AbortSignal): Promise<CatchLogPage> {
  const query = new URLSearchParams({ limit: String(catchLogPageSize), offset: String(offset) })
  return getJson({ apiBaseUrl, path: `${path}?${query}`, signal })
}

// 開啟詳情時重新讀取紀錄，處理已被其他分頁修改或刪除的資料。
export function fetchCatchLog(apiBaseUrl: string, id: string, signal?: AbortSignal): Promise<CatchLog> {
  return getJson({ apiBaseUrl, path: `${path}/${encodeURIComponent(id)}`, signal })
}

// 建立純文字紀錄；擁有者、UUID 與系統時間一律交給後端決定。
export function createCatchLog(apiBaseUrl: string, body: CatchLogInput): Promise<CatchLog> {
  return postJson({ apiBaseUrl, path, body })
}

// 修改可編輯欄位，以 null 清空選填值，不傳入任何擁有者資料。
export function updateCatchLog(apiBaseUrl: string, id: string, body: CatchLogInput): Promise<CatchLog> {
  return patchJson({ apiBaseUrl, path: `${path}/${encodeURIComponent(id)}`, body })
}

// 刪除自己的紀錄，成功時 API 不回傳 JSON。
export function deleteCatchLog(apiBaseUrl: string, id: string): Promise<void> {
  return deleteResource({ apiBaseUrl, path: `${path}/${encodeURIComponent(id)}` })
}
