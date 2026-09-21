import { postJson } from '../../api/http.ts'

import type {
  GoogleOAuthExchangeRequestPayload,
  GoogleOAuthExchangeResponsePayload,
} from './authTypes.ts'

// 將 Google 授權碼與 PKCE code_verifier 傳給後端，換取 FishSniper access token。
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
