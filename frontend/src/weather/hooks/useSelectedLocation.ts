import { useCallback, useEffect, useState } from 'react'
import type { SelectedLocation } from '../api/weatherTypes.ts'

export type LocationStatus = 'requesting' | 'ready' | 'needs_selection' | 'unsupported'

// 管理當次使用中的釣點；定位失敗時保留手動選擇能力。
export function useSelectedLocation() {
  const [location, setLocation] = useState<SelectedLocation | null>(null)
  const [status, setStatus] = useState<LocationStatus>('requesting')

  // 向瀏覽器請求一次定位；不儲存座標到 localStorage。
  const requestBrowserLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setStatus('unsupported')
      return
    }
    setStatus('requesting')
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          name: '',
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        })
        setStatus('ready')
      },
      () => setStatus('needs_selection'),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
    )
  }, [])

  // 首次進入 dashboard 時嘗試定位，拒絕後改由使用者搜尋地點。
  useEffect(() => {
    requestBrowserLocation()
  }, [requestBrowserLocation])

  // 將搜尋結果設定為目前釣點，後續資料查詢會使用它的座標。
  const selectLocation = useCallback((value: SelectedLocation) => {
    setLocation(value)
    setStatus('ready')
  }, [])

  return { location, status, requestBrowserLocation, selectLocation }
}
