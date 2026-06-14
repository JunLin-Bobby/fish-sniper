"""OTP generation helpers.

[暫時棄用 — Email OTP / Resend]
  尚未開通 Resend 與寄件網域；僅供 send-otp 使用，待有 email 服務後可恢復。
"""

import secrets


def generate_six_digit_otp_code_from_secrets() -> str:
    """Return a six-digit numeric OTP string, including leading zeros."""

    return f"{secrets.randbelow(1_000_000):06d}"
