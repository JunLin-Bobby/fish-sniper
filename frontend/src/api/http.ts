export class HttpStatusError extends Error {
  public readonly status: number
  public readonly responseText: string

  constructor(status: number, responseText: string) {
    super(`HTTP ${status}`)
    this.name = 'HttpStatusError'
    this.status = status
    this.responseText = responseText
  }
}

export async function getJson<TResponse>(options: {
  apiBaseUrl: string
  path: string
}): Promise<TResponse> {
  const response = await fetch(`${options.apiBaseUrl}${options.path}`)
  const responseText = await response.text()

  if (!response.ok) {
    throw new HttpStatusError(response.status, responseText)
  }

  return JSON.parse(responseText) as TResponse
}
