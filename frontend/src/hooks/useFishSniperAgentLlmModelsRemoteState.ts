import { useCallback, useEffect, useState } from 'react'

import type { ListAgentLlmModelsResponsePayload } from '../api/fishSniperApiTypes.ts'
import { getJsonWithFishSniperApi } from '../api/fishSniperJsonHttpClient.ts'

export type FishSniperAgentLlmModelsRemoteStatus = 'idle' | 'loading' | 'success' | 'error'

export function useFishSniperAgentLlmModelsRemoteState(options: {
  fishSniperApiBaseUrl: string
  fishSniperAccessTokenJwt: string
}) {
  const [remoteStatus, setRemoteStatus] = useState<FishSniperAgentLlmModelsRemoteStatus>('idle')
  const [modelsPayload, setModelsPayload] = useState<ListAgentLlmModelsResponsePayload | null>(null)

  const reloadAgentLlmModels = useCallback(async () => {
    setRemoteStatus('loading')
    try {
      const payload = await getJsonWithFishSniperApi<ListAgentLlmModelsResponsePayload>({
        apiBaseUrl: options.fishSniperApiBaseUrl,
        path: '/agent/models',
        accessTokenJwt: options.fishSniperAccessTokenJwt,
      })
      setModelsPayload(payload)
      setRemoteStatus('success')
    } catch {
      setModelsPayload(null)
      setRemoteStatus('error')
    }
  }, [options.fishSniperApiBaseUrl, options.fishSniperAccessTokenJwt])

  useEffect(() => {
    void reloadAgentLlmModels()
  }, [reloadAgentLlmModels])

  return {
    agentLlmModelsRemoteStatus: remoteStatus,
    agentLlmModelsPayload: modelsPayload,
    reloadAgentLlmModels,
  }
}
