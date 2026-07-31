import type {
  GoogleOAuthExchangeRequestPayload,
  GoogleOAuthExchangeResponsePayload,
} from './authTypes.ts'
import { postJson } from '../../api/jsonHttpClient.ts'

export async function exchangeGoogleOAuthAuthorizationCode(options: {
  apiBaseUrl: string
  requestBody: GoogleOAuthExchangeRequestPayload
}): Promise<GoogleOAuthExchangeResponsePayload> {
  return postJson<GoogleOAuthExchangeResponsePayload>({
    apiBaseUrl: options.apiBaseUrl,
    path: '/auth/google/exchange',
    requestBody: options.requestBody,
  })
}