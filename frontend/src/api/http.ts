import { readAccessTokenFromStorage } from '../auth/lib/tokenStorage.ts'

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

// 對 FishSniper API 發送 GET request，登入後會自動攜帶 Bearer token。
export async function getJson<TResponse>(options: {
  apiBaseUrl: string
  path: string
  signal?: AbortSignal
}): Promise<TResponse> {
  const response = await fetch(`${options.apiBaseUrl}${options.path}`, {
    headers: buildRequestHeaders(),
    signal: options.signal,
  })
  return parseJsonResponse<TResponse>(response)
}

// 對 FishSniper API 發送 JSON POST request，登入後會自動攜帶 Bearer token。
export async function postJson<TResponse>(options: {
  apiBaseUrl: string
  path: string
  body: unknown
}): Promise<TResponse> {
  const response = await fetch(`${options.apiBaseUrl}${options.path}`, {
    method: 'POST',
    headers: buildRequestHeaders({ includeJsonContentType: true }),
    body: JSON.stringify(options.body),
  })
  return parseJsonResponse<TResponse>(response)
}

// 以 JSON PATCH 修改指定資源，沿用 Bearer token 與 HTTP 錯誤格式。
export async function patchJson<TResponse>(options: {
  apiBaseUrl: string
  path: string
  body: unknown
}): Promise<TResponse> {
  const response = await fetch(`${options.apiBaseUrl}${options.path}`, {
    method: 'PATCH',
    headers: buildRequestHeaders({ includeJsonContentType: true }),
    body: JSON.stringify(options.body),
  })
  return parseJsonResponse<TResponse>(response)
}

// 刪除指定資源並接受沒有 body 的 204 response，不嘗試解析空 JSON。
export async function deleteResource(options: { apiBaseUrl: string; path: string }): Promise<void> {
  const response = await fetch(`${options.apiBaseUrl}${options.path}`, {
    method: 'DELETE', headers: buildRequestHeaders(),
  })
  await parseJsonResponse<unknown>(response)
}
