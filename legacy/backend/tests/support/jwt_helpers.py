"""JWT bearer token helpers for API tests."""

from __future__ import annotations

from app.auth.jwt import issue_access_token
from app.core.settings import get_settings
from tests.doubles.in_memory_db import InMemoryPersistenceAdapter


def bearer_token_for_user(
    *,
    persistence: InMemoryPersistenceAdapter,
    email: str,
) -> str:
    normalized_email = email.strip().lower()
    user_row = persistence.fetch_user_row_by_normalized_email(
        normalized_email_address=normalized_email,
    )
    if user_row is None:
        user_row = persistence.insert_user_row_for_normalized_email(
            normalized_email_address=normalized_email,
        )
    settings = get_settings()
    return issue_access_token(
        user_id=user_row.user_id,
        normalized_email_address=normalized_email,
        settings=settings,
    )
