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

  return JSON.parse(responseText) as TResponse
}

// 對 FishSniper API 發送 GET request，登入後會自動攜帶 Bearer token。
export async function getJson<TResponse>(options: {
  apiBaseUrl: string
  path: string
}): Promise<TResponse> {
  const response = await fetch(`${options.apiBaseUrl}${options.path}`, {
    headers: buildRequestHeaders(),
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
