"""Email normalization for auth and rate limiting."""


def normalize_email(raw: str) -> str:
    """Normalize email (strip + lowercase) for storage and rate-limit keys."""

    return raw.strip().lower()
