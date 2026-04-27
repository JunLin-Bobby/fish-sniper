"""Normalize user-provided text for stable lookups."""


def normalize_email_address_for_otp_login(raw_email_address: str) -> str:
    """Normalize email for OTP send/verify (case-insensitive mailbox semantics)."""

    return raw_email_address.strip().lower()
