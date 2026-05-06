import { useCallback, useState } from 'react'

import type {
  GenerateBassStrategyRequestPayload,
  GenerateBassStrategyFallbackResponsePayload,
  GenerateBassStrategySuccessResponsePayload,
} from '../api/fishSniperApiTypes.ts'
import { postJsonWithFishSniperApi, FishSniperHttpStatusError } from '../api/fishSniperJsonHttpClient.ts'
import { isFishSniperGenerateBassStrategyFallbackResponsePayload } from '../api/fishSniperStrategyResponseGuards.ts'

const STRATEGY_REQUEST_TIMEOUT_MS = 120_000

export type FishSniperSubmitBassStrategyResult =
  | { outcome: 'success'; successPayload: GenerateBassStrategySuccessResponsePayload }
  | { outcome: 'fallback'; fallbackPayload: GenerateBassStrategyFallbackResponsePayload }
  | { outcome: 'http_error'; userVisibleMessage: string }
  | { outcome: 'unexpected_response' }

export function useFishSniperSubmitBassStrategyMutation(options: {
  fishSniperApiBaseUrl: string
  fishSniperAccessTokenJwt: string
}) {
  const [isSubmittingBassStrategy, setIsSubmittingBassStrategy] = useState(false)

  const submitBassStrategyRequest = useCallback(
    async (
      requestPayload: GenerateBassStrategyRequestPayload,
    ): Promise<FishSniperSubmitBassStrategyResult> => {
      setIsSubmittingBassStrategy(true)
      try {
        const rawUnknown: unknown = await postJsonWithFishSniperApi<unknown>({
          apiBaseUrl: options.fishSniperApiBaseUrl,
          path: '/agent/strategy',
          requestBody: requestPayload,
          accessTokenJwt: options.fishSniperAccessTokenJwt,
          timeoutMs: STRATEGY_REQUEST_TIMEOUT_MS,
        })

        if (isFishSniperGenerateBassStrategyFallbackResponsePayload(rawUnknown)) {
          return { outcome: 'fallback', fallbackPayload: rawUnknown }
        }

        if (typeof rawUnknown !== 'object' || rawUnknown === null) {
          return { outcome: 'unexpected_response' }
        }

        const record = rawUnknown as Record<string, unknown>
        if (record.fallback === true) {
          return { outcome: 'unexpected_response' }
        }

        return {
          outcome: 'success',
          successPayload: rawUnknown as GenerateBassStrategySuccessResponsePayload,
        }
      } catch (unknownError) {
        if (unknownError instanceof FishSniperHttpStatusError) {
          return { outcome: 'http_error', userVisibleMessage: unknownError.responseBodyText }
        }
        if (unknownError instanceof Error) {
          return { outcome: 'http_error', userVisibleMessage: unknownError.message }
        }
        return { outcome: 'http_error', userVisibleMessage: 'Request failed' }
      } finally {
        setIsSubmittingBassStrategy(false)
      }
    },
    [options.fishSniperApiBaseUrl, options.fishSniperAccessTokenJwt],
  )

  return { submitBassStrategyRequest, isSubmittingBassStrategy }
}
