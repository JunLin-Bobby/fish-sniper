import { useCallback, useEffect, useState } from 'react'
import { HttpStatusError } from '../../api/http.ts'
import { catchLogPageSize, fetchCatchLog, fetchCatchLogs } from '../api/catchLogApi.ts'
import type { CatchLog, CatchLogPage } from '../api/catchLogTypes.ts'

type LoadState<T> = { status: 'loading' | 'ready' | 'error'; data: T | null; missing?: boolean }

// 管理私人紀錄分頁、重試與寫入後的列表更新，並中止已過期的請求。
export function useCatchLogs(apiBaseUrl: string, onUnauthorized: () => void) {
  const [offset, setOffset] = useState(0)
  const [revision, setRevision] = useState(0)
  const [page, setPage] = useState<LoadState<CatchLogPage>>({ status: 'loading', data: null })

  // 寫入後回第一頁，避免刪除該頁最後一筆後卡在空頁。
  const refresh = useCallback(() => {
    setOffset(0)
    setRevision((value) => value + 1)
  }, [])

  // 每次切頁建立獨立中止控制，防止慢速舊頁覆蓋新頁。
  useEffect(() => {
    const controller = new AbortController()
    setPage({ status: 'loading', data: null })

    // 將 401 交給登入流程，其他錯誤保留在紀錄面板並允許重試。
    async function load(): Promise<void> {
      try {
        const data = await fetchCatchLogs(apiBaseUrl, offset, controller.signal)
        if (!controller.signal.aborted) setPage({ status: 'ready', data })
      } catch (error) {
        if (controller.signal.aborted) return
        if (error instanceof HttpStatusError && error.status === 401) onUnauthorized()
        else setPage({ status: 'error', data: null })
      }
    }

    void load()
    return () => controller.abort()
  }, [apiBaseUrl, offset, revision, onUnauthorized])

  return { page, offset, setOffset, refresh, pageSize: catchLogPageSize }
}

// 以單筆 GET 載入詳情，快速切換或關閉詳情時不再接受舊請求的結果。
export function useCatchLogDetail(apiBaseUrl: string, id: string | null, onUnauthorized: () => void) {
  const [detail, setDetail] = useState<LoadState<CatchLog>>({ status: 'loading', data: null })
  const [revision, setRevision] = useState(0)

  // 暫時性讀取失敗時可在原紀錄上重試。
  const retry = useCallback(() => setRevision((value) => value + 1), [])

  // 每個紀錄 ID 都有獨立請求生命週期，避免顯示上一筆紀錄。
  useEffect(() => {
    if (!id) return
    const controller = new AbortController()
    setDetail({ status: 'loading', data: null })

    // 重新取得由後端驗證 ownership 的完整資料，不把列表快照當成權限依據。
    async function load(logId: string): Promise<void> {
      try {
        const data = await fetchCatchLog(apiBaseUrl, logId, controller.signal)
        if (!controller.signal.aborted) setDetail({ status: 'ready', data })
      } catch (error) {
        if (controller.signal.aborted) return
        if (error instanceof HttpStatusError && error.status === 401) onUnauthorized()
        else setDetail({ status: 'error', data: null, missing: error instanceof HttpStatusError && error.status === 404 })
      }
    }

    void load(id)
    return () => controller.abort()
  }, [apiBaseUrl, id, revision, onUnauthorized])

  return { detail, retry }
}
