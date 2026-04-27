"""OTP generation helpers."""

import secrets


def generate_six_digit_otp_code_from_secrets() -> str:
    """Return a six-digit numeric OTP string, including leading zeros."""

    return f"{secrets.randbelow(1_000_000):06d}"
