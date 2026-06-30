"""Auth domain FastAPI dependency providers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends


def get_google_oauth_token_exchange_callable() -> Callable[..., dict]:
    """Return the production token-exchange callable (overridable in tests)."""

    from auth.google_oauth_client import exchange_authorization_code_for_token_response

    return exchange_authorization_code_for_token_response


def get_google_jwks_key_resolver():
    """Return the production Google JWKS key resolver (overridable in tests)."""

    from auth.google_id_token_verification import build_default_google_jwks_key_resolver

    return build_default_google_jwks_key_resolver()


GoogleOAuthTokenExchangeCallableDep = Annotated[
    Callable[..., dict],
    Depends(get_google_oauth_token_exchange_callable),
]
GoogleJwksKeyResolverDep = Annotated[
    object,
    Depends(get_google_jwks_key_resolver),
]
