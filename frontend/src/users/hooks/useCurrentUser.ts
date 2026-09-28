import { useEffect, useState } from 'react'

import { HttpStatusError } from '../../api/http.ts'
import { fetchCurrentUser } from '../api/userApi.ts'
import type { CurrentUser } from '../api/userTypes.ts'

interface CurrentUserState {
  user: CurrentUser | null
  isLoading: boolean
  errorMessage: string | null
}

// 在 dashboard 啟動時載入 /me，並在 token 失效時通知 auth session 登出。
export function useCurrentUser(apiBaseUrl: string, onUnauthorized: () => void): CurrentUserState {
  const [state, setState] = useState<CurrentUserState>({
    user: null,
    isLoading: true,
    errorMessage: null,
  })

  useEffect(() => {
    let isCancelled = false

    // 執行單次 current-user request，並避免 component unmount 後更新 state。
    async function loadCurrentUser(): Promise<void> {
      try {
        const user = await fetchCurrentUser(apiBaseUrl)
        if (!isCancelled) {
          setState({ user, isLoading: false, errorMessage: null })
        }
      } catch (error) {
        if (error instanceof HttpStatusError && error.status === 401) {
          onUnauthorized()
          return
        }
        if (!isCancelled) {
          setState({
            user: null,
            isLoading: false,
            errorMessage: 'User profile is temporarily unavailable.',
          })
        }
      }
    }

    void loadCurrentUser()
    return () => {
      isCancelled = true
    }
  }, [apiBaseUrl, onUnauthorized])

  return state
}
