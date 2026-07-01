"""JWT bearer token helpers for API tests."""

from __future__ import annotations

from auth.jwt_tokens import issue_access_token_jwt_for_fish_sniper_user_id
from shared_infras.settings import get_settings
from tests.doubles.in_memory_db import InMemoryFishSniperPersistenceAdapter


def bearer_token_for_user(
    *,
    persistence: InMemoryFishSniperPersistenceAdapter,
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
    return issue_access_token_jwt_for_fish_sniper_user_id(
        fish_sniper_user_id=user_row.fish_sniper_user_id,
        normalized_email_address=normalized_email,
        fish_sniper_backend_settings=settings,
    )
