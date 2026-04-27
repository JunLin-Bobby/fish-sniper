"""Transactional email delivery port."""

from typing import Protocol


class TransactionalEmailSenderPort(Protocol):
    """Sends transactional emails (OTP codes) without exposing provider details to routes."""

    def send_fish_sniper_email_otp_message(
        self,
        *,
        recipient_email_address: str,
        otp_code_six_digits: str,
    ) -> None:
        """Send the OTP email. Raises on delivery failure."""
