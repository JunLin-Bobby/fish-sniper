import { useCallback, useEffect, useState } from 'react'
import { HttpStatusError } from '../../api/http.ts'
import { fetchDailyWeather } from '../api/weatherApi.ts'
import type { DailyWeather, SelectedLocation } from '../api/weatherTypes.ts'

type LoadState<T> = { status: 'idle' | 'loading' | 'ready' | 'error'; data: T | null }
export type DailyWeatherLoadState = LoadState<DailyWeather>

// 在首頁共用一份預報載入與重試狀態，呈現元件不各自呼叫 API。
export function useDailyConditions(
  apiBaseUrl: string,
  location: SelectedLocation | null,
  date: string,
  onUnauthorized: () => void,
) {
  const [weather, setWeather] = useState<LoadState<DailyWeather>>({ status: 'idle', data: null })
  const [refreshCount, setRefreshCount] = useState(0)

  // 讓使用者在供應商暫時失敗後，重新發起預報請求。
  const retry = useCallback(() => setRefreshCount((count) => count + 1), [])

  // 地點、日期或重試次數改變時重新查詢，並中止已過期的請求。
  useEffect(() => {
    if (!location) return
    const controller = new AbortController()
    setWeather({ status: 'loading', data: null })

    // 載入逐時天氣，並單獨更新天氣面板狀態。
    async function loadWeather(selected: SelectedLocation): Promise<void> {
      try {
        const data = await fetchDailyWeather(apiBaseUrl, selected, date, controller.signal)
        if (!controller.signal.aborted) setWeather({ status: 'ready', data })
      } catch (error) {
        if (controller.signal.aborted) return
        if (error instanceof HttpStatusError && error.status === 401) onUnauthorized()
        else setWeather({ status: 'error', data: null })
      }
    }

    void loadWeather(location)
    return () => controller.abort()
  }, [apiBaseUrl, location?.latitude, location?.longitude, date, refreshCount, onUnauthorized])

  return { weather, retry }
}
