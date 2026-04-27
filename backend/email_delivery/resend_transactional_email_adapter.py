"""Resend-backed transactional email sender."""

from __future__ import annotations

import logging

import resend

from settings import FishSniperBackendSettings

logger = logging.getLogger(__name__)


class ResendTransactionalEmailSenderAdapter:
    """Sends OTP messages through Resend."""

    def __init__(self, fish_sniper_backend_settings: FishSniperBackendSettings) -> None:
        api_key = fish_sniper_backend_settings.resend_api_key or ""
        resend.api_key = api_key
        self._resend_from_header = fish_sniper_backend_settings.resend_from_email

    def send_fish_sniper_email_otp_message(
        self,
        *,
        recipient_email_address: str,
        otp_code_six_digits: str,
    ) -> None:
        email_body_text = (
            "Hi there,\n\n"
            f"Your FishSniper verification code is: {otp_code_six_digits}\n\n"
            "This code expires in 10 minutes.\n"
            "If you didn't request this, you can safely ignore this email.\n\n"
            "— The FishSniper Team\n"
        )
        try:
            params: dict[str, object] = {
                "from": self._resend_from_header,
                "to": recipient_email_address,
                "subject": f"Your FishSniper verification code: {otp_code_six_digits}",
                "text": email_body_text,
            }
            resend.Emails.send(params)
        except Exception:
            logger.exception("Resend email send failed")
            raise
