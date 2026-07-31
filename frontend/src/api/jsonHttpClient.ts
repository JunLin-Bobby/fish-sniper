/**
 * Minimal JSON HTTP helpers with timeouts and typed errors.
 * All secrets stay server-side; this client only talks to the FastAPI backend.
 */

import type { TopLevelErrorPayload } from './apiTypes.ts'

export class HttpTimeoutError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'HttpTimeoutError'
  }
}

export class HttpStatusError extends Error {
  public readonly httpStatusCode: number
  public readonly responseBodyText: string

  constructor(httpStatusCode: number, responseBodyText: string) {
    super(`HTTP ${httpStatusCode}`)
    this.name = 'HttpStatusError'
    this.httpStatusCode = httpStatusCode
    this.responseBodyText = responseBodyText
  }
}

const DEFAULT_JSON_REQUEST_TIMEOUT_MS = 15_000

export async function parseErrorMessageFromResponseBody(
  responseBodyText: string,
): Promise<string> {
  try {
    const parsedUnknown: unknown = JSON.parse(responseBodyText)
    if (
      typeof parsedUnknown === 'object' &&
      parsedUnknown !== null &&
      'error' in parsedUnknown &&
      typeof (parsedUnknown as TopLevelErrorPayload).error === 'string'
    ) {
      return (parsedUnknown as TopLevelErrorPayload).error
    }
    if (
      typeof parsedUnknown === 'object' &&
      parsedUnknown !== null &&
      'detail' in parsedUnknown
    ) {
      const detailValue = (parsedUnknown as { detail: unknown }).detail
      if (typeof detailValue === 'string') {
        return detailValue
      }
    }
  } catch {
    // fall through
  }
  return responseBodyText.length > 0 ? responseBodyText : 'Request failed'
}

export async function postJson<TResponse>(options: {
  apiBaseUrl: string
  path: string
  requestBody: unknown
  accessTokenJwt?: string | null
  timeoutMs?: number
}): Promise<TResponse> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_JSON_REQUEST_TIMEOUT_MS
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (options.accessTokenJwt) {
      requestHeaders.Authorization = `Bearer ${options.accessTokenJwt}`
    }

    const httpResponse = await fetch(`${options.apiBaseUrl}${options.path}`, {
      method: 'POST',
      headers: requestHeaders,
      body: JSON.stringify(options.requestBody),
      signal: controller.signal,
    })

    const responseBodyText = await httpResponse.text()
    if (!httpResponse.ok) {
      const friendlyMessage = await parseErrorMessageFromResponseBody(responseBodyText)
      throw new HttpStatusError(httpResponse.status, friendlyMessage)
    }

    return JSON.parse(responseBodyText) as TResponse
  } catch (unknownError) {
    if (unknownError instanceof DOMException && unknownError.name === 'AbortError') {
      throw new HttpTimeoutError('Request timed out. Check your connection and try again.')
    }
    throw unknownError
  } finally {
    window.clearTimeout(timeoutId)
  }
}

export async function deleteJson(options: {
  apiBaseUrl: string
  path: string
  requestBody: unknown
  accessTokenJwt: string
  timeoutMs?: number
}): Promise<void> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_JSON_REQUEST_TIMEOUT_MS
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const httpResponse = await fetch(`${options.apiBaseUrl}${options.path}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${options.accessTokenJwt}`,
      },
      body: JSON.stringify(options.requestBody),
      signal: controller.signal,
    })
    const responseBodyText = await httpResponse.text()
    if (!httpResponse.ok) {
      const friendlyMessage = await parseErrorMessageFromResponseBody(responseBodyText)
      throw new HttpStatusError(httpResponse.status, friendlyMessage)
    }
  } catch (unknownError) {
    if (unknownError instanceof DOMException && unknownError.name === 'AbortError') {
      throw new HttpTimeoutError('Request timed out. Check your connection and try again.')
    }
    throw unknownError
  } finally {
    window.clearTimeout(timeoutId)
  }
}

export async function getJson<TResponse>(options: {
  apiBaseUrl: string
  path: string
  accessTokenJwt: string
  timeoutMs?: number
}): Promise<TResponse> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_JSON_REQUEST_TIMEOUT_MS
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const httpResponse = await fetch(`${options.apiBaseUrl}${options.path}`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${options.accessTokenJwt}`,
      },
      signal: controller.signal,
    })
    const responseBodyText = await httpResponse.text()
    if (!httpResponse.ok) {
      const friendlyMessage = await parseErrorMessageFromResponseBody(responseBodyText)
      throw new HttpStatusError(httpResponse.status, friendlyMessage)
    }
    return JSON.parse(responseBodyText) as TResponse
  } catch (unknownError) {
    if (unknownError instanceof DOMException && unknownError.name === 'AbortError') {
      throw new HttpTimeoutError('Request timed out. Check your connection and try again.')
    }
    throw unknownError
  } finally {
    window.clearTimeout(timeoutId)
  }
}
