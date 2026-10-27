import { deleteResource, getJson, patchJson, postJson, postForm, requestTimeouts } from '../../api/http.ts'
import type { CatchLog, CatchLogInput, CatchLogPage, CatchPhoto } from './catchLogTypes.ts'

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
export function updateCatchLog(apiBaseUrl: string, id: string, body: Partial<CatchLogInput>): Promise<CatchLog> {
  return patchJson({ apiBaseUrl, path: `${path}/${encodeURIComponent(id)}`, body })
}

// 刪除自己的紀錄，成功時 API 不回傳 JSON。
export function deleteCatchLog(apiBaseUrl: string, id: string): Promise<void> {
  return deleteResource({ apiBaseUrl, path: `${path}/${encodeURIComponent(id)}` })
}

// 一次提交魚獲與照片，識別碼在不確定結果的重試中保持不變。
export function createCatchLogWithPhotos(apiBaseUrl: string, input: CatchLogInput, files: File[], submissionId: string, signal?: AbortSignal): Promise<CatchLog> {
  const body = new FormData()
  body.set('payload', JSON.stringify(input))
  body.set('submission_id', submissionId)
  for (const file of files) body.append('photos', file)
  return postForm({ apiBaseUrl, path: `${path}/with-photos`, body, signal, idempotencyKey: submissionId, timeoutMs: requestTimeouts.submission })
}

export type SubmissionResult = {
  status: 'pending' | 'ready' | 'failed' | 'deleted'
  log_id: string | null
  retry_after_ms: number
}

// 只在失聯後恢復；後端可能終結操作，所以使用 POST 而非 GET。
export async function resolveCatchSubmission(apiBaseUrl: string, id: string, signal: AbortSignal, timeoutMs: number): Promise<SubmissionResult> {
  const result = await postJson<SubmissionResult>({ apiBaseUrl, path: `${path}/submissions/${encodeURIComponent(id)}/resolve`, body: {}, signal, timeoutMs })
  if (!['pending', 'ready', 'failed', 'deleted'].includes(result.status)
    || !Number.isFinite(result.retry_after_ms) || result.retry_after_ms < 0
    || (result.status === 'ready' && typeof result.log_id !== 'string')) {
    throw new SyntaxError('Invalid submission result.')
  }
  return result
}

// 每次重讀取得新 signed URLs；不把短效網址當成永久照片位置。
export function fetchCatchPhotos(apiBaseUrl: string, id: string, signal?: AbortSignal): Promise<CatchPhoto[]> {
  return getJson({ apiBaseUrl, path: `${path}/${encodeURIComponent(id)}/photos`, signal })
}

// 照片 ID 與魚獲 ID 由後端驗證，不允許前端任意指定 Storage 路徑。
export function deleteCatchPhoto(apiBaseUrl: string, logId: string, photoId: string): Promise<void> {
  return deleteResource({ apiBaseUrl, path: `${path}/${encodeURIComponent(logId)}/photos/${encodeURIComponent(photoId)}` })
}
