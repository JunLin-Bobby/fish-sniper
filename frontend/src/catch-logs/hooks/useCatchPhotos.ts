import { useEffect, useState } from 'react'
import { HttpStatusError } from '../../api/http.ts'
import { fetchCatchPhotos } from '../api/catchLogApi.ts'
import type { CatchPhoto } from '../api/catchLogTypes.ts'

// 載入照片並在短效連結到期前更新；離開詳情即中止請求與計時器。
export function useCatchPhotos(apiBaseUrl: string, logId: string, onUnauthorized: () => void) {
  const [photos, setPhotos] = useState<CatchPhoto[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | undefined
    // 保留登入錯誤的既有處理，照片失敗只影響照片區，不隱藏文字魚獲。
    async function load(): Promise<void> {
      try {
        const data = await fetchCatchPhotos(apiBaseUrl, logId, controller.signal)
        if (controller.signal.aborted) return
        setPhotos(data)
        setStatus('ready')
        if (data.length) {
          const expiry = Math.min(...data.map((photo) => new Date(photo.expires_at).getTime()))
          timer = setTimeout(() => void load(), Math.max(10_000, expiry - Date.now() - 30_000))
        }
      } catch (error) {
        if (controller.signal.aborted) return
        if (error instanceof HttpStatusError && error.status === 401) onUnauthorized()
        setStatus('error')
      }
    }
    setStatus('loading')
    void load()
    return () => { controller.abort(); if (timer) clearTimeout(timer) }
  }, [apiBaseUrl, logId, onUnauthorized, revision])

  // 刪除或顯示錯誤後明確重新取得伺服器狀態，不猜測檔案是否已刪除。
  function refresh(): void { setRevision((value) => value + 1) }
  return { photos, status, refresh }
}
