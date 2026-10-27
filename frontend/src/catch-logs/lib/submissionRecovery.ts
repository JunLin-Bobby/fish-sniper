import { HttpStatusError, requestTimeouts } from '../../api/http.ts'
import type { SubmissionResult } from '../api/catchLogApi.ts'

export const recoveryPolicy = { maxAttempts: 3, budgetMs: 30_000, backoffMs: [2_000, 5_000] } as const

// 等待可隨帳號切換／卸載取消；結束後移除 listener，避免下一輪收到舊事件。
export function waitForRecovery(milliseconds: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) { reject(signal.reason); return }
    // 取消時同時清理計時器及自己的事件監聽。
    function abort(): void { clearTimeout(timer); signal.removeEventListener('abort', abort); reject(signal.reason) }
    const timer = setTimeout(() => { signal.removeEventListener('abort', abort); resolve() }, milliseconds)
    signal.addEventListener('abort', abort, { once: true })
  })
}

// 一輪最多三次／三十秒；永遠不持有照片，也不會呼叫建立 API。
export async function recoverSubmission(options: {
  signal: AbortSignal
  resolve: (signal: AbortSignal, timeoutMs: number) => Promise<SubmissionResult>
  now?: () => number
  wait?: (milliseconds: number, signal: AbortSignal) => Promise<void>
}): Promise<SubmissionResult | null> {
  const now = options.now ?? (() => performance.now())
  const wait = options.wait ?? waitForRecovery
  const deadline = now() + recoveryPolicy.budgetMs
  let delay = 0
  for (let attempt = 0; attempt < recoveryPolicy.maxAttempts; attempt++) {
    if (options.signal.aborted) return null
    const remaining = deadline - now()
    if (remaining <= delay) return null
    if (delay) await wait(delay, options.signal)
    if (deadline <= now() || options.signal.aborted) return null
    try {
      const result = await options.resolve(options.signal, Math.min(requestTimeouts.receipt, deadline - now()))
      if (options.signal.aborted) return null
      if (result.status !== 'pending') return result
      // 已知截止時間超過本輪預算時交還呼叫端，僅安排一次到期喚醒，不固定輪詢。
      if (result.retry_after_ms >= deadline - now()) return result
      delay = Math.max(250, result.retry_after_ms)
    } catch (error) {
      if (options.signal.aborted) return null
      if (error instanceof HttpStatusError && error.status === 401) throw error
      delay = recoveryPolicy.backoffMs[attempt] ?? 0
    }
  }
  return null
}
