"""Authentication routes (Google OAuth + legacy email OTP).

[暫時棄用 — Email OTP / Resend]
  尚未購買 Resend 等付費 email 服務，也無已驗證寄件網域，無法實際寄送 OTP。
  登入請走 POST /auth/google/exchange。程式保留，待開通 email 服務與網域後可恢復。
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, status

from auth.google_oauth_service import (
    GoogleIdTokenInvalidError,
    GoogleOAuthCodeRejectedError,
    GoogleOAuthExchangeConfigurationError,
    GoogleOAuthExchangeEmailNotVerifiedError,
    GoogleOAuthExchangeRedirectUriRejectedError,
    GoogleOAuthIdentityServiceUnavailableError,
    perform_google_oauth_exchange_for_fish_sniper_user,
)
from auth.jwt_tokens import issue_access_token_jwt_for_fish_sniper_user_id
from deps import (
    FishSniperPersistenceDep,
    FishSniperSettingsDep,
    GoogleJwksKeyResolverDep,
    GoogleOAuthTokenExchangeCallableDep,
    OtpCodeGeneratorDep,
    ReferenceTimeUtcCallableDep,
    TransactionalEmailSenderDep,
)
from persistence.errors import FishSniperPersistenceUnavailableError
from rate_limiting import (
    enforce_google_oauth_exchange_ip_rate_limit_or_raise_429,
    enforce_send_otp_email_rate_limit_or_raise_429,
    enforce_verify_otp_email_rate_limit_or_raise_429,
)
from schemas.auth_schemas import (
    GoogleOAuthExchangeRequestBody,
    OtpErrorResponseBody,
    SendEmailOtpRequestBody,
    SendEmailOtpResponseBody,
    VerifyEmailOtpRequestBody,
    VerifyEmailOtpResponseBody,
)
from text_normalization import normalize_email_address_for_otp_login

router = APIRouter()


# ---------------------------------------------------------------------------
# [暫時棄用 — Email OTP / Resend] 見模組 docstring；OpenAPI 標 deprecated=True。
# ---------------------------------------------------------------------------


@router.post(
    "/send-otp",
    deprecated=True,
    summary="[Deprecated] Send a six-digit email OTP for sign-in",
    description=(
        "Generates a one-time passcode, stores it in `otp_codes` with a 10-minute expiry, "
        "and sends it via Resend. Enforces a 60-second per-email send cooldown."
    ),
    response_model=SendEmailOtpResponseBody,
    response_description="Confirms the OTP email was handed off to the email provider.",
    responses={
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": OtpErrorResponseBody,
            "description": "The email is in a 60-second cooldown window between OTP sends.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": OtpErrorResponseBody,
            "description": "The transactional email provider rejected or failed the send.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": OtpErrorResponseBody,
            "description": "Database is not configured or could not persist the OTP challenge.",
        },
    },
)
def handle_send_email_otp_request(
    request_body: SendEmailOtpRequestBody,
    fish_sniper_persistence: FishSniperPersistenceDep,
    transactional_email_sender: TransactionalEmailSenderDep,
    otp_code_generator: OtpCodeGeneratorDep,
    reference_time_utc_callable: ReferenceTimeUtcCallableDep,
    fish_sniper_backend_settings: FishSniperSettingsDep,
) -> SendEmailOtpResponseBody:
    normalized_email_address = normalize_email_address_for_otp_login(str(request_body.email))
    enforce_send_otp_email_rate_limit_or_raise_429(
        fish_sniper_backend_settings=fish_sniper_backend_settings,
        normalized_email_address=normalized_email_address,
    )
    reference_time_utc = reference_time_utc_callable()
    try:
        seconds_since_last_send = (
            fish_sniper_persistence.fetch_seconds_since_last_otp_send_for_email(
                normalized_email_address=normalized_email_address,
                reference_time_utc=reference_time_utc,
            )
        )
        if seconds_since_last_send is not None and seconds_since_last_send < 60:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "Too many requests, please wait 60 seconds"},
            )

        otp_code_six_digits = otp_code_generator()
        otp_expires_at_utc = reference_time_utc + timedelta(minutes=10)
        fish_sniper_persistence.insert_pending_otp_challenge_for_email(
            normalized_email_address=normalized_email_address,
            otp_code_six_digits=otp_code_six_digits,
            otp_expires_at_utc=otp_expires_at_utc,
            otp_created_at_utc=reference_time_utc,
        )
        try:
            transactional_email_sender.send_fish_sniper_email_otp_message(
                recipient_email_address=normalized_email_address,
                otp_code_six_digits=otp_code_six_digits,
            )
        except Exception as exc:  # noqa: BLE001 — provider errors are surfaced as 502
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"error": "Email delivery failed"},
            ) from exc
    except HTTPException:
        raise
    except FishSniperPersistenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Database is temporarily unavailable"},
        ) from exc

    return SendEmailOtpResponseBody(message="OTP sent")


@router.post(
    "/verify-otp",
    deprecated=True,
    summary="[Deprecated] Verify email OTP and issue a JWT access token",
    description=(
        "Validates the OTP challenge, deletes the consumed OTP row, ensures a `users` row exists, "
        "and returns a signed JWT used for `Authorization: Bearer` on protected endpoints."
    ),
    response_model=VerifyEmailOtpResponseBody,
    response_description="Returns a JWT access token and whether a new user row was created.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": OtpErrorResponseBody,
            "description": "OTP is missing, expired, or does not match the stored challenge.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": OtpErrorResponseBody,
            "description": "Database is not configured or could not complete verification.",
        },
    },
)
def handle_verify_email_otp_request(
    request_body: VerifyEmailOtpRequestBody,
    fish_sniper_persistence: FishSniperPersistenceDep,
    fish_sniper_backend_settings: FishSniperSettingsDep,
    reference_time_utc_callable: ReferenceTimeUtcCallableDep,
) -> VerifyEmailOtpResponseBody:
    normalized_email_address = normalize_email_address_for_otp_login(str(request_body.email))
    enforce_verify_otp_email_rate_limit_or_raise_429(
        fish_sniper_backend_settings=fish_sniper_backend_settings,
        normalized_email_address=normalized_email_address,
    )
    reference_time_utc = reference_time_utc_callable()
    try:
        otp_consumed = fish_sniper_persistence.delete_matching_unexpired_otp_or_noop(
            normalized_email_address=normalized_email_address,
            otp_code_six_digits=request_body.otp,
            reference_time_utc=reference_time_utc,
        )
        if not otp_consumed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid or expired OTP"},
            )

        existing_user_row = fish_sniper_persistence.fetch_user_row_by_normalized_email(
            normalized_email_address=normalized_email_address,
        )
        if existing_user_row is None:
            created_user_row = fish_sniper_persistence.insert_user_row_for_normalized_email(
                normalized_email_address=normalized_email_address,
            )
            fish_sniper_user_id = created_user_row.fish_sniper_user_id
            is_new_user = True
        else:
            fish_sniper_user_id = existing_user_row.fish_sniper_user_id
            is_new_user = False

        access_token = issue_access_token_jwt_for_fish_sniper_user_id(
            fish_sniper_user_id=fish_sniper_user_id,
            normalized_email_address=normalized_email_address,
            fish_sniper_backend_settings=fish_sniper_backend_settings,
        )
    except HTTPException:
        raise
    except FishSniperPersistenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Database is temporarily unavailable"},
        ) from exc

    return VerifyEmailOtpResponseBody(access_token=access_token, is_new_user=is_new_user)


# ---------------------------------------------------------------------------
# 使用中：Google OAuth 兌換 JWT
# ---------------------------------------------------------------------------


@router.post(
    "/google/exchange",
    summary="Exchange a Google OAuth authorization code for a FishSniper JWT",
    description=(
        "Accepts the `code` + PKCE `code_verifier` from the SPA's Google callback, "
        "verifies the resulting Google `id_token`, and returns a FishSniper JWT that "
        "is interchangeable with the JWT issued by `/auth/verify-otp`."
    ),
    response_model=VerifyEmailOtpResponseBody,
    response_description="Returns a FishSniper JWT and whether a new users row was created.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": OtpErrorResponseBody,
            "description": "Missing fields or redirect_uri not in whitelist.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": OtpErrorResponseBody,
            "description": "Google rejected the code or the id_token failed verification.",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": OtpErrorResponseBody,
            "description": "Google account email is not verified.",
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": OtpErrorResponseBody,
            "description": "Per-IP rate limit exceeded for the Google exchange endpoint.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": OtpErrorResponseBody,
            "description": "Backend is missing required Google OAuth configuration.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": OtpErrorResponseBody,
            "description": "Google identity service was unreachable or returned 5xx.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": OtpErrorResponseBody,
            "description": "Database is temporarily unavailable.",
        },
    },
)
def handle_google_oauth_exchange_request(
    request: Request,
    request_body: GoogleOAuthExchangeRequestBody,
    fish_sniper_persistence: FishSniperPersistenceDep,
    fish_sniper_backend_settings: FishSniperSettingsDep,
    reference_time_utc_callable: ReferenceTimeUtcCallableDep,
    google_oauth_token_exchange_callable: GoogleOAuthTokenExchangeCallableDep,
    google_jwks_key_resolver: GoogleJwksKeyResolverDep,
) -> VerifyEmailOtpResponseBody:
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
