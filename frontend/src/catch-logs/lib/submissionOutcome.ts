import { HttpStatusError } from '../../api/http.ts'

// 只在有明確拒絕／取消證據時允許丟棄收據；逾時、斷線、取消等待都不證明 rollback。
export function isDefinitiveSubmissionError(error: unknown): boolean {
  if (!(error instanceof HttpStatusError)) return false
  if ([400, 413, 422].includes(error.status)) return true
  if (error.status === 409) {
    try {
      const code = JSON.parse(error.responseText).detail?.code
      return ['submission_failed', 'submission_deleted'].includes(code)
    } catch { return false }
  }
  return false
}
