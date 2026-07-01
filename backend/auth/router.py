"""Authentication routes (Google OAuth)."""

from fastapi import APIRouter, HTTPException, Request, status

from auth.deps import GoogleJwksKeyResolverDep, GoogleOAuthTokenExchangeCallableDep
from auth.google_oauth_service import (
    GoogleIdTokenInvalidError,
    GoogleOAuthCodeRejectedError,
    GoogleOAuthExchangeConfigurationError,
    GoogleOAuthExchangeEmailNotVerifiedError,
    GoogleOAuthExchangeRedirectUriRejectedError,
    GoogleOAuthIdentityServiceUnavailableError,
    perform_google_oauth_exchange_for_fish_sniper_user,
)
from auth.schemas import (
    AuthErrorResponseBody,
    GoogleOAuthExchangeRequestBody,
    LoginResponseBody,
)
from persistence.deps import PersistenceDep
from persistence.errors import FishSniperPersistenceUnavailableError
from shared_infras.rate_limiting import enforce_google_oauth_exchange_ip_rate_limit_or_raise_429
from shared_infras.settings import SettingsDep
from shared_infras.time import ReferenceTimeUtcCallableDep

router = APIRouter()


@router.post(
    "/google/exchange",
    summary="Exchange a Google OAuth authorization code for a FishSniper JWT",
    description=(
        "Accepts the `code` + PKCE `code_verifier` from the SPA's Google callback, "
        "verifies the resulting Google `id_token`, and returns a FishSniper JWT."
    ),
    response_model=LoginResponseBody,
    response_description="Returns a FishSniper JWT and whether a new users row was created.",
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
    fish_sniper_persistence: PersistenceDep,
    fish_sniper_backend_settings: SettingsDep,
    reference_time_utc_callable: ReferenceTimeUtcCallableDep,
    google_oauth_token_exchange_callable: GoogleOAuthTokenExchangeCallableDep,
    google_jwks_key_resolver: GoogleJwksKeyResolverDep,
) -> LoginResponseBody:
    enforce_google_oauth_exchange_ip_rate_limit_or_raise_429(
        fish_sniper_backend_settings=fish_sniper_backend_settings,
        client_ip_address=request.client.host if request.client else "__no_client__",
    )
    reference_time_utc = reference_time_utc_callable()
    try:
        return perform_google_oauth_exchange_for_fish_sniper_user(
            authorization_code=request_body.code,
            pkce_code_verifier=request_body.code_verifier,
            redirect_uri=request_body.redirect_uri,
            fish_sniper_backend_settings=fish_sniper_backend_settings,
            fish_sniper_persistence=fish_sniper_persistence,
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
    except FishSniperPersistenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Database is temporarily unavailable"},
        ) from exc
