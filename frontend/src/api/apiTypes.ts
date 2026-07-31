export interface TopLevelErrorPayload {
  error: string
}

export interface HttpDetailEnvelopePayload {
  detail: string | Record<string, unknown>
}