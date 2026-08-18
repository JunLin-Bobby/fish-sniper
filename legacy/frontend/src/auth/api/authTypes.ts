/** Typed auth API payloads. */

export interface GoogleOAuthExchangeRequestPayload {
  code: string
  code_verifier: string
  redirect_uri: string
}

export interface GoogleOAuthExchangeResponsePayload {
  access_token: string
  is_new_user: boolean
}