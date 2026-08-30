from pydantic import BaseModel


class GoogleOAuthExchangeRequest(BaseModel):
    code: str
    code_verifier: str
    redirect_uri: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
