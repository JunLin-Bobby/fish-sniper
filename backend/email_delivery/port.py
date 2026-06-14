"""Transactional email delivery port.

[暫時棄用 — Email OTP / Resend]
  OTP 寄信介面；需 Resend 與寄件網域，目前未開通，待有 email 服務後可恢復。
"""

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
