"""Normalize user-provided text for stable lookups."""


def normalize_email_address_for_otp_login(raw_email_address: str) -> str:
    """Normalize email for OTP send/verify (case-insensitive mailbox semantics).

    [暫時棄用 — Email OTP / Resend] OTP 路由專用；JWT 限流 key 仍共用此正規化。
    """

    return raw_email_address.strip().lower()
