import { useEffect, useRef, useState } from 'react'
import { HttpStatusError } from '../../api/http.ts'
import { createCatchLogWithPhotos, resolveCatchSubmission } from '../api/catchLogApi.ts'
import type { CatchLogInput } from '../api/catchLogTypes.ts'
import { readPendingSubmission, readSubmissionOwner, storePendingSubmission } from '../lib/submissionStorage.ts'
import { isDefinitiveSubmissionError } from '../lib/submissionOutcome.ts'
import { recoverSubmission, recoveryPolicy } from '../lib/submissionRecovery.ts'

type SubmissionState = { phase: 'idle' | 'sending' | 'recovering' | 'waiting' | 'success' | 'failed'; logId?: string; revision: number }

// 只保存識別碼與狀態，不保存 input／File[] 快照；正常 POST 期間完全不查詢。
export function useCatchLogSubmission(apiBaseUrl: string, onUnauthorized: () => void) {
  const owner = readSubmissionOwner()
  const [state, setState] = useState<SubmissionState>({ phase: 'idle', revision: 0 })
  const receipt = useRef<string | null>(null)
  const active = useRef<AbortController | null>(null)
  const generation = useRef(0)
  const lastRound = useRef(-Infinity)
  const deferred = useRef<ReturnType<typeof setTimeout> | null>(null)
  const deferredOnce = useRef(false)
  const unauthorized = useRef(onUnauthorized)
  unauthorized.current = onUnauthorized
  const recoverRef = useRef<() => void>(() => {})

  // 終局才清除追蹤；舊結果不得刪除另一分頁新寫入的識別碼。
  function finish(id: string, phase: 'success' | 'failed', logId?: string): void {
    if (deferred.current) clearTimeout(deferred.current)
    deferred.current = null
    storePendingSubmission(null, owner, id)
    receipt.current = null
    setState((previous) => ({ phase, logId, revision: previous.revision + 1 }))
  }

  // 有限次恢復；仍失聯只等待下次連線／進入事件，絕不假稱上傳失敗。
  async function recover(): Promise<void> {
    if (!owner || readSubmissionOwner() !== owner || active.current || !receipt.current || navigator.onLine === false) return
    if (performance.now() - lastRound.current < recoveryPolicy.budgetMs) return
    const id = receipt.current
    const epoch = generation.current
    const controller = new AbortController()
    active.current = controller
    lastRound.current = performance.now()
    setState((previous) => ({ ...previous, phase: 'recovering' }))
    try {
      const result = await recoverSubmission({ signal: controller.signal,
        resolve: (signal, timeoutMs) => resolveCatchSubmission(apiBaseUrl, id, signal, timeoutMs) })
      if (controller.signal.aborted || generation.current !== epoch || receipt.current !== id || readSubmissionOwner() !== owner) return
      if (result && result.status !== 'pending') finish(id, result.status === 'ready' ? 'success' : 'failed', result.log_id ?? undefined)
      else {
        setState((previous) => ({ ...previous, phase: 'waiting' }))
        if (result?.status === 'pending' && !deferredOnce.current) {
          deferredOnce.current = true
          const wait = Math.max(result.retry_after_ms, recoveryPolicy.budgetMs - (performance.now() - lastRound.current))
          deferred.current = setTimeout(() => { deferred.current = null; recoverRef.current() }, wait)
        }
      }
    } catch (error) {
      if (controller.signal.aborted || generation.current !== epoch || readSubmissionOwner() !== owner) return
      setState((previous) => ({ ...previous, phase: 'waiting' }))
      if (error instanceof HttpStatusError && error.status === 401) unauthorized.current()
    } finally { if (active.current === controller) active.current = null }
  }
  recoverRef.current = () => { void recover() }

  // 登入後啟動恢復，不依賴表單是否開啟；世代檢查隔離換帳號／卸載後的回應。
  useEffect(() => {
    generation.current++
    active.current?.abort()
    active.current = null
    lastRound.current = -Infinity
    deferredOnce.current = false
    receipt.current = readPendingSubmission(owner)
    setState((previous) => ({ phase: receipt.current ? 'waiting' : 'idle', revision: previous.revision + 1 }))
    const epoch = generation.current
    // StrictMode 的測試性掛載會立即卸載；等微任務再發送，避免兩次啟動查詢。
    queueMicrotask(() => { if (generation.current === epoch) recoverRef.current() })
    // 事件只喚醒一輪；正常上傳中不啟動結果查詢。
    function resume(event: Event): void {
      if (document.visibilityState === 'hidden') return
      if (readSubmissionOwner() !== owner) { active.current?.abort(); return }
      // 真正恢復連線時允許新一輪；focus/storage 事件仍受冷卻保護，不能形成請求風暴。
      if (event.type === 'online' && !active.current) lastRound.current = -Infinity
      if (!active.current) receipt.current = receipt.current ?? readPendingSubmission(owner)
      recoverRef.current()
    }
    window.addEventListener('online', resume)
    window.addEventListener('focus', resume)
    window.addEventListener('storage', resume)
    document.addEventListener('visibilitychange', resume)
    return () => {
      generation.current++
      if (deferred.current) clearTimeout(deferred.current)
      deferred.current = null
      active.current?.abort()
      active.current = null
      window.removeEventListener('online', resume)
      window.removeEventListener('focus', resume)
      window.removeEventListener('storage', resume)
      document.removeEventListener('visibilitychange', resume)
    }
  }, [owner, apiBaseUrl])

  // 每次新操作只送一次 POST；失聯後不保存／重傳內容，僅恢復識別碼的結果。
  async function submit(input: CatchLogInput, files: File[]): Promise<void> {
    if (!owner || readSubmissionOwner() !== owner || active.current) return
    receipt.current ??= readPendingSubmission(owner)
    if (receipt.current) { recoverRef.current(); return }
    const id = crypto.randomUUID()
    lastRound.current = -Infinity
    deferredOnce.current = false
    const epoch = generation.current
    const controller = new AbortController()
    receipt.current = id
    storePendingSubmission(id, owner)
    active.current = controller
    setState((previous) => ({ ...previous, phase: 'sending' }))
    let needsRecovery = false
    try {
      const record = await createCatchLogWithPhotos(apiBaseUrl, input, files, id, controller.signal)
      if (controller.signal.aborted || generation.current !== epoch || readSubmissionOwner() !== owner) return
      if (!record?.id) throw new SyntaxError('Missing saved record.')
      finish(id, 'success', record.id)
    } catch (error) {
      if (controller.signal.aborted || generation.current !== epoch || readSubmissionOwner() !== owner) return
      if (isDefinitiveSubmissionError(error)) finish(id, 'failed')
      else {
        setState((previous) => ({ ...previous, phase: 'waiting' }))
        needsRecovery = true
        if (error instanceof HttpStatusError && error.status === 401) { needsRecovery = false; unauthorized.current() }
      }
    } finally {
      if (active.current === controller) active.current = null
      if (needsRecovery && generation.current === epoch) recoverRef.current()
    }
  }

  return { ...state, submit, unresolved: ['sending', 'recovering', 'waiting'].includes(state.phase) }
}

export type CatchLogSubmission = ReturnType<typeof useCatchLogSubmission>
