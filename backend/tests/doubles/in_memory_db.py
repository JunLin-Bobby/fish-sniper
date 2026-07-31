"""In-memory persistence test double (auth users only)."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.db.ports import UserRow


class InMemoryPersistenceAdapter:
    """In-memory persistence for fast, deterministic API tests."""

    def __init__(self) -> None:
        self._user_row_by_normalized_email: dict[str, UserRow] = {}

    def fetch_user_row_by_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> UserRow | None:
        return self._user_row_by_normalized_email.get(normalized_email_address)

    def insert_user_row_for_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> UserRow:
        new_user_id = uuid4()
        row = UserRow(
            user_id=new_user_id,
            normalized_email_address=normalized_email_address,
        )
        self._user_row_by_normalized_email[normalized_email_address] = row
        return row

    def fetch_user_row_for_user_id(
        self,
        *,
        user_id: UUID,
    ) -> UserRow | None:
        for row in self._user_row_by_normalized_email.values():
            if row.user_id == user_id:
                return row
        return None
