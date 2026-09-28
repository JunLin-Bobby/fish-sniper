import { getJson } from '../../api/http.ts'

import type { CurrentUser } from './userTypes.ts'

// 讀取目前 Bearer token 所代表的 FishSniper 使用者資料。
export async function fetchCurrentUser(apiBaseUrl: string): Promise<CurrentUser> {
  return getJson<CurrentUser>({
    apiBaseUrl,
    path: '/api/v1/me',
  })
}
