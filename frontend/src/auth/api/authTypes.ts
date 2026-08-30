export interface GoogleOAuthExchangeRequestPayload {
  code: string
  code_verifier: string
  redirect_uri: string
}

export interface GoogleOAuthExchangeResponsePayload {
  access_token: string
  token_type: 'bearer'
}
