"""Tests for P3 fishing logs API (TDD)."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from auth.jwt_tokens import issue_access_token_jwt_for_fish_sniper_user_id
from deps import (
    get_fish_sniper_embedding_client,
    get_persistence,
    get_reference_time_utc_callable,
)
from embedding.port import (
    FishSniperEmbeddingClient,
    FishSniperEmbeddingUnavailableError,
)
from main import create_fish_sniper_app
from persistence.errors import FishSniperPersistenceUnavailableError
from settings import get_settings
from tests.doubles import FakeFishSniperEmbeddingClient, InMemoryFishSniperPersistenceAdapter

_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


def _load_json_fixture(filename: str) -> dict:
    return json.loads((_FIXTURES_DIR / filename).read_text(encoding="utf-8"))


def _install_logs_dependency_overrides(
    app,
    *,
    fish_sniper_persistence: InMemoryFishSniperPersistenceAdapter,
    reference_time_utc_callable: Callable[[], datetime],
    embedding_client: FishSniperEmbeddingClient | None = None,
) -> None:
    """Install in-memory dependencies, falling back to a happy-path fake embedding client.

    Tests that need a specific embedding behaviour (transient failure, custom
    vector) pass an explicit ``embedding_client``; everything else gets a
    deterministic fake so no test hits the real Gemini API.
    """

    app.dependency_overrides[get_persistence] = lambda: fish_sniper_persistence
    app.dependency_overrides[get_reference_time_utc_callable] = lambda: reference_time_utc_callable
    chosen_embedding_client = embedding_client or FakeFishSniperEmbeddingClient()
    app.dependency_overrides[get_fish_sniper_embedding_client] = lambda: chosen_embedding_client


def _bearer_headers_for_user(
    *,
    fish_sniper_user_id: UUID,
    normalized_email_address: str,
) -> dict[str, str]:
    settings = get_settings()
    token = issue_access_token_jwt_for_fish_sniper_user_id(
        fish_sniper_user_id=fish_sniper_user_id,
        normalized_email_address=normalized_email_address,
        fish_sniper_backend_settings=settings,
    )
    return {"Authorization": f"Bearer {token}"}


def test_post_fishing_log_returns_201_with_log_id(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _advance = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="logs@example.com",
    )
    app = create_fish_sniper_app()
    _install_logs_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
    )
    client = TestClient(app)
    body = _load_json_fixture("sample_fishing_log_create.json")

    response = client.post(
        "/logs",
        headers=_bearer_headers_for_user(
            fish_sniper_user_id=user_row.fish_sniper_user_id,
            normalized_email_address=user_row.normalized_email_address,
        ),
        json=body,
    )

    assert response.status_code == 201
    payload = response.json()
    assert "log_id" in payload
    UUID(str(payload["log_id"]))


def test_get_fishing_logs_returns_current_user_rows_ordered_by_date_desc(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _advance = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="sort@example.com",
    )
    app = create_fish_sniper_app()
    _install_logs_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
    )
    client = TestClient(app)
    headers = _bearer_headers_for_user(
        fish_sniper_user_id=user_row.fish_sniper_user_id,
        normalized_email_address=user_row.normalized_email_address,
    )
    older = _load_json_fixture("sample_fishing_log_minimal.json")
    newer = _load_json_fixture("sample_fishing_log_create.json")
    assert client.post("/logs", headers=headers, json=older).status_code == 201
    assert client.post("/logs", headers=headers, json=newer).status_code == 201

    list_response = client.get("/logs", headers=headers)

    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 2
    assert rows[0]["date"] == "2026-04-20"
    assert rows[1]["date"] == "2026-04-15"


def test_get_fishing_log_by_id_returns_404_for_other_user(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _advance = frozen_clock
    owner = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="owner@example.com",
    )
    other = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="other@example.com",
    )
    app = create_fish_sniper_app()
    _install_logs_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
    )
    client = TestClient(app)
    create_resp = client.post(
        "/logs",
        headers=_bearer_headers_for_user(
            fish_sniper_user_id=owner.fish_sniper_user_id,
            normalized_email_address=owner.normalized_email_address,
        ),
        json=_load_json_fixture("sample_fishing_log_create.json"),
    )
    assert create_resp.status_code == 201
    log_id = create_resp.json()["log_id"]

    probe = client.get(
        f"/logs/{log_id}",
        headers=_bearer_headers_for_user(
            fish_sniper_user_id=other.fish_sniper_user_id,
            normalized_email_address=other.normalized_email_address,
        ),
    )
    assert probe.status_code == 404


def test_patch_fishing_log_updates_row_and_returns_full_object(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, advance = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="patch@example.com",
    )
    app = create_fish_sniper_app()
    _install_logs_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
    )
    client = TestClient(app)
    headers = _bearer_headers_for_user(
        fish_sniper_user_id=user_row.fish_sniper_user_id,
        normalized_email_address=user_row.normalized_email_address,
    )
    create_resp = client.post(
        "/logs",
        headers=headers,
        json=_load_json_fixture("sample_fishing_log_create.json"),
    )
    log_id = create_resp.json()["log_id"]
    advance(5.0)

    updated_body = _load_json_fixture("sample_fishing_log_create.json")
    updated_body["notes"] = "Updated notes"
    updated_body["caught_count"] = 5

    patch_resp = client.patch(f"/logs/{log_id}", headers=headers, json=updated_body)
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["notes"] == "Updated notes"
    assert updated["caught_count"] == 5
    assert "pinecone_synced" not in updated
    assert updated["embedding_status"] in {"pending", "done"}
    assert updated["embedding_text_version"] == 1


def test_delete_fishing_log_returns_204(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _advance = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="delete@example.com",
    )
    app = create_fish_sniper_app()
    _install_logs_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
    )
    client = TestClient(app)
    headers = _bearer_headers_for_user(
        fish_sniper_user_id=user_row.fish_sniper_user_id,
        normalized_email_address=user_row.normalized_email_address,
    )
    create_resp = client.post(
        "/logs",
        headers=headers,
        json=_load_json_fixture("sample_fishing_log_create.json"),
    )
    log_id = create_resp.json()["log_id"]

    delete_resp = client.delete(f"/logs/{log_id}", headers=headers)
    assert delete_resp.status_code == 204
    assert delete_resp.content == b""

    missing = client.get(f"/logs/{log_id}", headers=headers)
    assert missing.status_code == 404


def test_get_fishing_logs_returns_304_when_if_none_match_matches_etag(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    now_utc, _advance = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="etag@example.com",
    )
    app = create_fish_sniper_app()
    _install_logs_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
    )
    client = TestClient(app)
    headers = _bearer_headers_for_user(
        fish_sniper_user_id=user_row.fish_sniper_user_id,
        normalized_email_address=user_row.normalized_email_address,
    )
    create_resp = client.post(
        "/logs",
        headers=headers,
        json=_load_json_fixture("sample_fishing_log_create.json"),
    )
    assert create_resp.status_code == 201

    first = client.get("/logs", headers=headers)
    assert first.status_code == 200
    etag = first.headers.get("etag")
    assert etag is not None

    second = client.get("/logs", headers={**headers, "If-None-Match": etag})
    assert second.status_code == 304
    assert second.content == b""


def test_post_fishing_log_with_successful_embedding_marks_status_done(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    """Successful Gemini call → embedding_status='done' on the persisted row."""

    now_utc, _advance = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="embed-ok@example.com",
    )
    app = create_fish_sniper_app()
    _install_logs_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
        embedding_client=FakeFishSniperEmbeddingClient(),
    )
    client = TestClient(app)
    headers = _bearer_headers_for_user(
        fish_sniper_user_id=user_row.fish_sniper_user_id,
        normalized_email_address=user_row.normalized_email_address,
    )

    create_resp = client.post(
        "/logs",
        headers=headers,
        json=_load_json_fixture("sample_fishing_log_create.json"),
    )
    assert create_resp.status_code == 201
    log_id = create_resp.json()["log_id"]

    detail = client.get(f"/logs/{log_id}", headers=headers).json()
    assert detail["embedding_status"] == "done"
    assert detail["embedding_text_version"] == 1
    assert "pinecone_synced" not in detail


def test_post_fishing_log_with_transient_embedding_failure_returns_201_pending(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    """Gemini transient failure must NOT surface to the user; row persists with pending status."""

    now_utc, _advance = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="embed-down@example.com",
    )
    failing_client = FakeFishSniperEmbeddingClient(
        error_factory=lambda: FishSniperEmbeddingUnavailableError("gemini is down"),
    )
    app = create_fish_sniper_app()
    _install_logs_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
        embedding_client=failing_client,
    )
    client = TestClient(app)
    headers = _bearer_headers_for_user(
        fish_sniper_user_id=user_row.fish_sniper_user_id,
        normalized_email_address=user_row.normalized_email_address,
    )

    create_resp = client.post(
        "/logs",
        headers=headers,
        json=_load_json_fixture("sample_fishing_log_create.json"),
    )
    assert create_resp.status_code == 201
    log_id = create_resp.json()["log_id"]
    assert failing_client.call_count >= 1

    detail = client.get(f"/logs/{log_id}", headers=headers).json()
    assert detail["embedding_status"] == "pending"


class _AlwaysFailingPersistenceProxy:
    """Wraps an in-memory adapter and forces insert/update to always raise."""

    def __init__(self, *, wrapped: InMemoryFishSniperPersistenceAdapter) -> None:
        self._wrapped = wrapped

    def __getattr__(self, name: str):
        return getattr(self._wrapped, name)

    def insert_fishing_log_for_user_id(self, **_kwargs):
        raise FishSniperPersistenceUnavailableError("simulated supabase outage")

    def update_fishing_log_for_user_id(self, **_kwargs):
        raise FishSniperPersistenceUnavailableError("simulated supabase outage")


def test_post_fishing_log_returns_503_envelope_when_database_fails(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    """Persistence failures (post-retry) surface as 503 SERVICE_TEMPORARILY_UNAVAILABLE."""

    now_utc, _advance = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="db-down@example.com",
    )
    failing_persistence = _AlwaysFailingPersistenceProxy(wrapped=in_memory_persistence_adapter)
    app = create_fish_sniper_app()
    _install_logs_dependency_overrides(
        app,
        fish_sniper_persistence=failing_persistence,  # type: ignore[arg-type]
        reference_time_utc_callable=now_utc,
    )
    client = TestClient(app)
    headers = _bearer_headers_for_user(
        fish_sniper_user_id=user_row.fish_sniper_user_id,
        normalized_email_address=user_row.normalized_email_address,
    )

    response = client.post(
        "/logs",
        headers=headers,
        json=_load_json_fixture("sample_fishing_log_create.json"),
    )

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "SERVICE_TEMPORARILY_UNAVAILABLE"
    assert body["retryAfter"] == 30
    assert response.headers.get("retry-after") == "30"


def test_post_fishing_log_with_invalid_payload_returns_400_invalid_payload_envelope(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    """Validation failures (e.g. caught_count negative) become 400 INVALID_PAYLOAD."""

    now_utc, _advance = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="bad-payload@example.com",
    )
    app = create_fish_sniper_app()
    _install_logs_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
    )
    client = TestClient(app)
    headers = _bearer_headers_for_user(
        fish_sniper_user_id=user_row.fish_sniper_user_id,
        normalized_email_address=user_row.normalized_email_address,
    )
    body = _load_json_fixture("sample_fishing_log_create.json")
    body["caught_count"] = -1

    response = client.post("/logs", headers=headers, json=body)

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "INVALID_PAYLOAD"
    assert isinstance(payload.get("errors"), list)
    assert len(payload["errors"]) >= 1


def test_get_current_weather_accepts_region_query_without_saved_preferences(
    in_memory_persistence_adapter: InMemoryFishSniperPersistenceAdapter,
    frozen_clock: tuple[Callable[[], datetime], Callable[[float], None]],
) -> None:
    """Region query bypasses empty profile; may still be 503 if OWM is unavailable."""
    now_utc, _advance = frozen_clock
    user_row = in_memory_persistence_adapter.insert_user_row_for_normalized_email(
        normalized_email_address="wx@example.com",
    )
    app = create_fish_sniper_app()
    _install_logs_dependency_overrides(
        app,
        fish_sniper_persistence=in_memory_persistence_adapter,
        reference_time_utc_callable=now_utc,
    )
    client = TestClient(app)
    response = client.get(
        "/weather/current",
        params={"region": "Boston"},
        headers=_bearer_headers_for_user(
            fish_sniper_user_id=user_row.fish_sniper_user_id,
            normalized_email_address=user_row.normalized_email_address,
        ),
    )
    assert response.status_code != 400
    assert response.json().get("error") != "User region is not configured"
