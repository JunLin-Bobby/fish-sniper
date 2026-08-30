import { postJson } from '../../api/http.ts'

import type {
  GoogleOAuthExchangeRequestPayload,
  GoogleOAuthExchangeResponsePayload,
} from './authTypes.ts'

export async function exchangeGoogleOAuthAuthorizationCode(options: {
  apiBaseUrl: string
  requestBody: GoogleOAuthExchangeRequestPayload
}): Promise<GoogleOAuthExchangeResponsePayload> {
  return postJson<GoogleOAuthExchangeResponsePayload>({
    apiBaseUrl: options.apiBaseUrl,
    path: '/auth/google/exchange',
    body: options.requestBody,
  })
}
