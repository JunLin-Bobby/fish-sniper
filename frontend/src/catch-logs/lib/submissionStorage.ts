import { readAccessTokenFromStorage } from '../../auth/lib/tokenStorage.ts'

// JWT sub 只用於區分本機帳號的儲存 key，不作為權限依據；後端仍驗證簽章。
export function readSubmissionOwner(): string | null {
  try {
    const token = readAccessTokenFromStorage()
    const encoded = (token ?? '').split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const subject = JSON.parse(atob(encoded.padEnd(Math.ceil(encoded.length / 4) * 4, '='))).sub
    return typeof subject === 'string' && subject ? subject : null
  } catch { return null }
}

// 只保存隨機提交識別碼，不把照片、GPS、文字或 token 寫進 sessionStorage。
export function readPendingSubmission(owner = readSubmissionOwner()): string | null {
  if (!owner) return null
  try {
    const key = `fishsniper.pending-catch-submission.${owner}`
    const stored = window.localStorage.getItem(key)
    if (stored) return stored
    // 升級前只存 sessionStorage 的收據也要保留；只遷移識別碼，不遷移任何表單或照片。
    const legacy = window.sessionStorage?.getItem(key)
    if (legacy) { window.localStorage.setItem(key, legacy); window.sessionStorage.removeItem(key) }
    return legacy ?? null
  } catch { return null }
}

// 只存識別碼；晚到結果不能清掉別的帳號或新提交。
export function storePendingSubmission(id: string | null, owner = readSubmissionOwner(), expectedId?: string): void {
  if (!owner) return
  try {
    const key = `fishsniper.pending-catch-submission.${owner}`
    if (id) window.localStorage.setItem(key, id)
    else if (!expectedId || window.localStorage.getItem(key) === expectedId) window.localStorage.removeItem(key)
  } catch { /* Disabled storage supports in-page recovery, but not reload recovery. */ }
}
