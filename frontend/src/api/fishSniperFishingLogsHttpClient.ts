/**
 * Fishing logs HTTP client (P3): conditional GET, POST, PATCH, DELETE.
 */

import type { FishingLogResponsePayload } from './fishSniperApiTypes.ts'
import {
  FishSniperHttpTimeoutError,
  FishSniperHttpStatusError,
  parseFishSniperErrorMessageFromResponseBody,
} from './fishSniperJsonHttpClient.ts'

export type GetFishSniperFishingLogsListResult =
  | { outcome: 'full'; etag: string; logs: FishingLogResponsePayload[] }
  | { outcome: 'not_modified'; etag: string }
  | { outcome: 'error'; httpStatusCode: number; message: string }

const DEFAULT_TIMEOUT_MS = 15_000

export async function getFishSniperFishingLogsListWithEtag(options: {
  apiBaseUrl: string
  accessTokenJwt: string
  ifNoneMatch: string | null
  timeoutMs?: number
}): Promise<GetFishSniperFishingLogsListResult> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${options.accessTokenJwt}`,
    }
    if (options.ifNoneMatch) {
      headers['If-None-Match'] = options.ifNoneMatch
    }
    const httpResponse = await fetch(`${options.apiBaseUrl}/logs`, {
      method: 'GET',
      headers,
      signal: controller.signal,
    })
    const etagHeader = httpResponse.headers.get('etag') ?? ''

    if (httpResponse.status === 304) {
      return { outcome: 'not_modified', etag: etagHeader }
    }

    const responseBodyText = await httpResponse.text()
    if (!httpResponse.ok) {
      const friendlyMessage = await parseFishSniperErrorMessageFromResponseBody(responseBodyText)
      return { outcome: 'error', httpStatusCode: httpResponse.status, message: friendlyMessage }
    }

    const parsedUnknown: unknown = JSON.parse(responseBodyText)
    const logs = parsedUnknown as FishingLogResponsePayload[]
    return { outcome: 'full', etag: etagHeader, logs }
  } catch (unknownError) {
    if (unknownError instanceof DOMException && unknownError.name === 'AbortError') {
      return {
        outcome: 'error',
        httpStatusCode: 0,
        message: 'Request timed out. Check your connection and try again.',
      }
    }
    throw unknownError
  } finally {
    window.clearTimeout(timeoutId)
  }
}

export async function postFishSniperFishingLog(options: {
  apiBaseUrl: string
  accessTokenJwt: string
  requestBody: unknown
  timeoutMs?: number
}): Promise<{ log_id: string }> {
  return postJsonAuthorized<{ log_id: string }>({
    apiBaseUrl: options.apiBaseUrl,
    path: '/logs',
    accessTokenJwt: options.accessTokenJwt,
    requestBody: options.requestBody,
    timeoutMs: options.timeoutMs,
  })
}

export async function patchFishSniperFishingLog(options: {
  apiBaseUrl: string
  accessTokenJwt: string
  logId: string
  requestBody: unknown
  timeoutMs?: number
}): Promise<FishingLogResponsePayload> {
  return patchJsonAuthorized<FishingLogResponsePayload>({
    apiBaseUrl: options.apiBaseUrl,
    path: `/logs/${encodeURIComponent(options.logId)}`,
    accessTokenJwt: options.accessTokenJwt,
    requestBody: options.requestBody,
    timeoutMs: options.timeoutMs,
  })
}

export async function deleteFishSniperFishingLog(options: {
  apiBaseUrl: string
  accessTokenJwt: string
  logId: string
  timeoutMs?: number
}): Promise<void> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const httpResponse = await fetch(
      `${options.apiBaseUrl}/logs/${encodeURIComponent(options.logId)}`,
      {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${options.accessTokenJwt}`,
        },
        signal: controller.signal,
      },
    )
    if (httpResponse.status === 204) {
      return
    }
    const responseBodyText = await httpResponse.text()
    const friendlyMessage = await parseFishSniperErrorMessageFromResponseBody(responseBodyText)
    throw new FishSniperHttpStatusError(httpResponse.status, friendlyMessage)
  } catch (unknownError) {
    if (unknownError instanceof DOMException && unknownError.name === 'AbortError') {
      throw new FishSniperHttpTimeoutError('Request timed out. Check your connection and try again.')
    }
    throw unknownError
  } finally {
    window.clearTimeout(timeoutId)
  }
}

async function postJsonAuthorized<TResponse>(options: {
  apiBaseUrl: string
  path: string
  accessTokenJwt: string
  requestBody: unknown
  timeoutMs?: number
}): Promise<TResponse> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const httpResponse = await fetch(`${options.apiBaseUrl}${options.path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${options.accessTokenJwt}`,
      },
      body: JSON.stringify(options.requestBody),
      signal: controller.signal,
    })
    const responseBodyText = await httpResponse.text()
    if (!httpResponse.ok) {
      const friendlyMessage = await parseFishSniperErrorMessageFromResponseBody(responseBodyText)
      throw new FishSniperHttpStatusError(httpResponse.status, friendlyMessage)
    }
    return JSON.parse(responseBodyText) as TResponse
  } catch (unknownError) {
    if (unknownError instanceof DOMException && unknownError.name === 'AbortError') {
      throw new FishSniperHttpTimeoutError('Request timed out. Check your connection and try again.')
    }
    throw unknownError
  } finally {
    window.clearTimeout(timeoutId)
  }
}

async function patchJsonAuthorized<TResponse>(options: {
  apiBaseUrl: string
  path: string
  accessTokenJwt: string
  requestBody: unknown
  timeoutMs?: number
}): Promise<TResponse> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const httpResponse = await fetch(`${options.apiBaseUrl}${options.path}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${options.accessTokenJwt}`,
      },
      body: JSON.stringify(options.requestBody),
      signal: controller.signal,
    })
    const responseBodyText = await httpResponse.text()
    if (!httpResponse.ok) {
      const friendlyMessage = await parseFishSniperErrorMessageFromResponseBody(responseBodyText)
      throw new FishSniperHttpStatusError(httpResponse.status, friendlyMessage)
    }
    return JSON.parse(responseBodyText) as TResponse
  } catch (unknownError) {
    if (unknownError instanceof DOMException && unknownError.name === 'AbortError') {
      throw new FishSniperHttpTimeoutError('Request timed out. Check your connection and try again.')
    }
    throw unknownError
  } finally {
    window.clearTimeout(timeoutId)
  }
}
