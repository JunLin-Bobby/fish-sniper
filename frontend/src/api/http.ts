import { readAccessTokenFromStorage } from '../auth/lib/tokenStorage.ts'

// 正常 POST 不輪詢；期限到期後才恢復結果，不直接判定儲存失敗。
export const requestTimeouts = { default: 15_000, submission: 60_000, receipt: 10_000 } as const

export type RequestOptions = {
  apiBaseUrl: string
  path: string
  signal?: AbortSignal
  timeoutMs?: number
  idempotencyKey?: string
}

export class RequestTimeoutError extends Error {
  public readonly timeoutMs: number

  // 等待期限來自前端，不假造 HTTP 408／504，也不代表後端已 rollback。
  constructor(timeoutMs: number) {
    super('The request exceeded its waiting deadline.')
    this.name = 'RequestTimeoutError'
    this.timeoutMs = timeoutMs
  }
}

export class NetworkRequestError extends Error {
  // 網路、DNS 或 CORS 等傳輸問題無法只靠瀏覽器錯誤精確區分，保留 cause 供除錯。
  constructor(cause: unknown) {
    super('The network request could not be completed.', { cause })
    this.name = 'NetworkRequestError'
  }
}

export class RequestAbortedError extends Error {
  // 呼叫端取消和期限到期分開，離開讀取畫面時不顯示誤導性的逾時警告。
  constructor() {
    super('The caller cancelled the request.')
    this.name = 'AbortError'
  }
}

export class HttpStatusError extends Error {
  public readonly status: number
  public readonly responseText: string

  // 保存 HTTP status 與原始 response，讓 feature hook 能判斷 401 等錯誤。
  constructor(status: number, responseText: string) {
    super(`HTTP ${status}`)
    this.name = 'HttpStatusError'
    this.status = status
    this.responseText = responseText
  }
}

// 建立共用 request headers，並在已登入時自動附加 FishSniper Bearer token。
function buildRequestHeaders(options?: { includeJsonContentType?: boolean }): HeadersInit {
  const headers: Record<string, string> = {}
  const accessToken = readAccessTokenFromStorage()

  if (options?.includeJsonContentType) {
    headers['Content-Type'] = 'application/json'
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  return headers
}

// 解析成功的 JSON response，並將非 2xx response 統一轉成 HttpStatusError。
async function parseJsonResponse<TResponse>(response: Response): Promise<TResponse> {
  const responseText = await response.text()

  if (!response.ok) {
    throw new HttpStatusError(response.status, responseText)
  }

  if (response.status === 204) return undefined as TResponse
  return JSON.parse(responseText) as TResponse
}

// 全部 HTTP 方法共用同一個期限，直到 response body 解析完成才清除 timer。
async function requestJson<TResponse>(options: RequestOptions, init: RequestInit): Promise<TResponse> {
  const timeoutMs = options.timeoutMs ?? requestTimeouts.default
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) throw new RangeError('timeoutMs must be positive.')
  const controller = new AbortController()

  // 不直接覆蓋呼叫端 signal，保留原有卸載／切換頁面的取消能力。
  function cancelFromCaller(): void { controller.abort(new RequestAbortedError()) }

  if (options.signal?.aborted) cancelFromCaller()
  else options.signal?.addEventListener('abort', cancelFromCaller, { once: true })
  const timer = setTimeout(() => controller.abort(new RequestTimeoutError(timeoutMs)), timeoutMs)
  try {
    if (controller.signal.aborted) throw controller.signal.reason
    const response = await fetch(`${options.apiBaseUrl}${options.path}`, {
      ...init, signal: controller.signal,
    })
    // await is essential: finally must not clear the deadline while the body is still streaming.
    return await parseJsonResponse<TResponse>(response)
  } catch (error) {
    if (controller.signal.aborted) throw controller.signal.reason
    if (error instanceof TypeError) throw new NetworkRequestError(error)
    throw error
  } finally {
    clearTimeout(timer)
    options.signal?.removeEventListener('abort', cancelFromCaller)
  }
}

// 對 FishSniper API 發送 GET request，登入後會自動攜帶 Bearer token。
export async function getJson<TResponse>(options: RequestOptions): Promise<TResponse> {
  return requestJson<TResponse>(options, {
    headers: buildRequestHeaders(),
  })
}

// 對 FishSniper API 發送 JSON POST request，登入後會自動攜帶 Bearer token。
export async function postJson<TResponse>(options: RequestOptions & { body: unknown }): Promise<TResponse> {
  return requestJson<TResponse>(options, {
    method: 'POST',
    headers: buildRequestHeaders({ includeJsonContentType: true }),
    body: JSON.stringify(options.body),
  })
}

// 讓瀏覽器產生 multipart boundary；只加 Bearer token，不手動指定 Content-Type。
export async function postForm<TResponse>(options: RequestOptions & { body: FormData }): Promise<TResponse> {
  const headers = new Headers(buildRequestHeaders())
  if (options.idempotencyKey) headers.set('Idempotency-Key', options.idempotencyKey)
  return requestJson<TResponse>(options, {
    method: 'POST', headers, body: options.body,
  })
}

// 以 JSON PATCH 修改指定資源，沿用 Bearer token 與 HTTP 錯誤格式。
export async function patchJson<TResponse>(options: RequestOptions & { body: unknown }): Promise<TResponse> {
  return requestJson<TResponse>(options, {
    method: 'PATCH',
    headers: buildRequestHeaders({ includeJsonContentType: true }),
    body: JSON.stringify(options.body),
  })
}

// 刪除指定資源並接受沒有 body 的 204 response，不嘗試解析空 JSON。
export async function deleteResource(options: RequestOptions): Promise<void> {
  await requestJson<unknown>(options, {
    method: 'DELETE', headers: buildRequestHeaders(),
  })
}
