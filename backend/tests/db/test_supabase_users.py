import asyncio
import json
from uuid import UUID

import httpx

from app.db.client import SupabaseRestClient
from app.db.supabase_users import SupabaseUsersRepository


def test_find_or_create_google_user_uses_atomic_supabase_upsert() -> None:
    """確認 repository 以 google_sub upsert，並解析 Supabase 回傳的內部 UUID。"""

    user_id = UUID("8aef95ae-16df-4d32-99d9-730b945b34ac")

    async def handle_request(request: httpx.Request) -> httpx.Response:
        """攔截 Supabase request，驗證 headers、query 與送出的 identity payload。"""

        assert request.method == "POST"
        assert request.url.path == "/rest/v1/users"
        assert request.url.params["on_conflict"] == "google_sub"
        assert request.headers["apikey"] == "test-secret-key"
        assert request.headers["prefer"] == "resolution=merge-duplicates,return=representation"

        request_payload = json.loads(request.content)
        assert request_payload["google_sub"] == "google-account-123"
        assert request_payload["email"] == "angler@example.com"
        return httpx.Response(
            201,
            json=[
                {
                    "id": str(user_id),
                    "google_sub": "google-account-123",
                    "email": "angler@example.com",
                    "display_name": "Test Angler",
                    "avatar_url": None,
                }
            ],
        )

    client = SupabaseRestClient(
        supabase_url="https://example.supabase.co",
        secret_key="test-secret-key",
        transport=httpx.MockTransport(handle_request),
    )
    repository = SupabaseUsersRepository(client)
    user = asyncio.run(
        repository.find_or_create_google_user(
            google_sub="google-account-123",
            email="ANGLER@EXAMPLE.COM",
            display_name="Test Angler",
            avatar_url=None,
        )
    )

    assert user.id == user_id
    assert user.email == "angler@example.com"
