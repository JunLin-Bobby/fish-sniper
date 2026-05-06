import { useCallback, useEffect, useState } from 'react'

import type { CurrentWeatherResponsePayload } from '../api/fishSniperApiTypes.ts'
import {
  FishSniperHttpStatusError,
  getJsonWithFishSniperApi,
} from '../api/fishSniperJsonHttpClient.ts'

export type FishSniperAutoWeatherRemoteStatus = 'idle' | 'loading' | 'success' | 'error'

export function useFishSniperAutoWeatherSnapshotRemoteState(options: {
  fishSniperApiBaseUrl: string
  fishSniperAccessTokenJwt: string
  isAutoWeatherEnabled: boolean
}) {
  const [remoteStatus, setRemoteStatus] = useState<FishSniperAutoWeatherRemoteStatus>('idle')
  const [weatherSnapshotPayload, setWeatherSnapshotPayload] =
    useState<CurrentWeatherResponsePayload | null>(null)
  const [lastHttpStatusCode, setLastHttpStatusCode] = useState<number | null>(null)

  const reloadAutoWeatherSnapshot = useCallback(async () => {
    if (!options.isAutoWeatherEnabled) {
      setRemoteStatus('idle')
      setWeatherSnapshotPayload(null)
      setLastHttpStatusCode(null)
      return
    }
    setRemoteStatus('loading')
    setLastHttpStatusCode(null)
    try {
      const payload = await getJsonWithFishSniperApi<CurrentWeatherResponsePayload>({
        apiBaseUrl: options.fishSniperApiBaseUrl,
        path: '/weather/current',
        accessTokenJwt: options.fishSniperAccessTokenJwt,
      })
      setWeatherSnapshotPayload(payload)
      setRemoteStatus('success')
    } catch (unknownError) {
      setWeatherSnapshotPayload(null)
      setRemoteStatus('error')
      if (unknownError instanceof FishSniperHttpStatusError) {
        setLastHttpStatusCode(unknownError.httpStatusCode)
      }
    }
  }, [
    options.fishSniperApiBaseUrl,
    options.fishSniperAccessTokenJwt,
    options.isAutoWeatherEnabled,
  ])

  useEffect(() => {
    void reloadAutoWeatherSnapshot()
  }, [reloadAutoWeatherSnapshot])

  return {
    autoWeatherRemoteStatus: remoteStatus,
    autoWeatherSnapshotPayload: weatherSnapshotPayload,
    autoWeatherLastHttpStatusCode: lastHttpStatusCode,
    reloadAutoWeatherSnapshot,
  }
}
