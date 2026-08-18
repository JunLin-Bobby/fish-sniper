"""Authentication routes (Google OAuth)."""

from fastapi import APIRouter, HTTPException, Request, status

from app.auth.deps import GoogleJwksKeyResolverDep, GoogleOAuthTokenExchangeCallableDep
from app.auth.schemas import (
    AuthErrorResponseBody,
    GoogleOAuthExchangeRequestBody,
    LoginResponseBody,
)
from app.auth.service import (
    GoogleIdTokenInvalidError,
    GoogleOAuthCodeRejectedError,
    GoogleOAuthExchangeConfigurationError,
    GoogleOAuthExchangeEmailNotVerifiedError,
    GoogleOAuthExchangeRedirectUriRejectedError,
    GoogleOAuthIdentityServiceUnavailableError,
    perform_google_oauth_exchange,
)
from app.core.rate_limit import enforce_google_oauth_exchange_ip_rate_limit_or_raise_429
from app.core.settings import SettingsDep
from app.core.time import ReferenceTimeUtcCallableDep
from app.db.deps import PersistenceDep
from app.db.errors import PersistenceUnavailableError

router = APIRouter()


@router.post(
    "/google/exchange",
    summary="Exchange a Google OAuth authorization code for an access JWT",
    description=(
        "Accepts the `code` + PKCE `code_verifier` from the SPA's Google callback, "
        "verifies the resulting Google `id_token`, and returns an access JWT."
    ),
    response_model=LoginResponseBody,
    response_description="Returns an access JWT and whether a new users row was created.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": AuthErrorResponseBody,
            "description": "Missing fields or redirect_uri not in whitelist.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": AuthErrorResponseBody,
            "description": "Google rejected the code or the id_token failed verification.",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": AuthErrorResponseBody,
            "description": "Google account email is not verified.",
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": AuthErrorResponseBody,
            "description": "Per-IP rate limit exceeded for the Google exchange endpoint.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": AuthErrorResponseBody,
            "description": "Backend is missing required Google OAuth configuration.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": AuthErrorResponseBody,
            "description": "Google identity service was unreachable or returned 5xx.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": AuthErrorResponseBody,
            "description": "Database is temporarily unavailable.",
        },
    },
)
def handle_google_oauth_exchange_request(
    request: Request,
    request_body: GoogleOAuthExchangeRequestBody,
    persistence: PersistenceDep,
    settings: SettingsDep,
    reference_time_utc_callable: ReferenceTimeUtcCallableDep,
    google_oauth_token_exchange_callable: GoogleOAuthTokenExchangeCallableDep,
    google_jwks_key_resolver: GoogleJwksKeyResolverDep,
) -> LoginResponseBody:
    enforce_google_oauth_exchange_ip_rate_limit_or_raise_429(
        settings=settings,
        client_ip_address=request.client.host if request.client else "__no_client__",
    )
    reference_time_utc = reference_time_utc_callable()
    try:
        return perform_google_oauth_exchange(
            authorization_code=request_body.code,
            pkce_code_verifier=request_body.code_verifier,
            redirect_uri=request_body.redirect_uri,
            settings=settings,
            persistence=persistence,
            reference_time_utc=reference_time_utc,
            google_oauth_token_exchange_callable=google_oauth_token_exchange_callable,
            google_jwks_key_resolver=google_jwks_key_resolver,
        )
    except GoogleOAuthExchangeConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Google OAuth is not configured"},
        ) from exc
    except GoogleOAuthExchangeRedirectUriRejectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid Google OAuth exchange request"},
        ) from exc
    except GoogleOAuthCodeRejectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Google authorization rejected"},
        ) from exc
    except GoogleIdTokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Google authorization rejected"},
        ) from exc
    except GoogleOAuthExchangeEmailNotVerifiedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Google account email is not verified"},
        ) from exc
    except GoogleOAuthIdentityServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "Google identity service unavailable"},
        ) from exc
    except PersistenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Database is temporarily unavailable"},
        ) from exc
