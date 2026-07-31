"""Supabase-backed persistence for Google OAuth user find-or-create."""

from __future__ import annotations

import logging
from uuid import UUID

from supabase import Client, create_client

from app.core.settings import AppSettings
from app.db.errors import PersistenceUnavailableError
from app.db.ports import UserRow

logger = logging.getLogger(__name__)


class SupabasePersistenceAdapter:
    """Implements `PersistencePort` using Supabase PostgREST."""

    def __init__(self, settings: AppSettings) -> None:
        supabase_url = settings.supabase_url or ""
        service_role_key = settings.supabase_service_role_key or ""
        self._client: Client = create_client(supabase_url, service_role_key)

    def fetch_user_row_by_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> UserRow | None:
        try:
            response = (
                self._client.table("users")
                .select("id,email")
                .eq("email", normalized_email_address)
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            row = response.data[0]
            return UserRow(
                user_id=UUID(str(row["id"])),
                normalized_email_address=str(row["email"]),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase user lookup failed")
            raise PersistenceUnavailableError("user lookup failed") from exc

    def insert_user_row_for_normalized_email(
        self,
        *,
        normalized_email_address: str,
    ) -> UserRow:
        try:
            insert_response = (
                self._client.table("users").insert({"email": normalized_email_address}).execute()
            )
            if not insert_response.data:
                raise PersistenceUnavailableError("user insert returned no row")
            row = insert_response.data[0]
            return UserRow(
                user_id=UUID(str(row["id"])),
                normalized_email_address=str(row["email"]),
            )
        except PersistenceUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase user insert failed")
            raise PersistenceUnavailableError("user insert failed") from exc

    def fetch_user_row_for_user_id(
        self,
        *,
        user_id: UUID,
    ) -> UserRow | None:
        try:
            response = (
                self._client.table("users")
                .select("id,email")
                .eq("id", str(user_id))
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            row = response.data[0]
            return UserRow(
                user_id=UUID(str(row["id"])),
                normalized_email_address=str(row["email"]),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Supabase user lookup by id failed")
            raise PersistenceUnavailableError("user lookup failed") from exc
