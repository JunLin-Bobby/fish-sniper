import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth.jwt import create_access_token
from app.catch_logs.dependencies import get_catch_logs_repository
from app.catch_logs.supabase_repository import SupabaseCatchLogsRepository
from app.core.config import Settings, get_settings
from app.db.client import SupabaseRestClient
from app.main import create_app
from app.users.dependencies import get_users_repository
from app.users.schemas import UserRecord
from tests.fakes import InMemoryUsersRepository

USER_A = UserRecord(id=uuid4(), google_sub="catch-test-a", email="a@example.com")
USER_B = UserRecord(id=uuid4(), google_sub="catch-test-b", email="b@example.com")
BASE_PAYLOAD = {"species_name": "大口黑鱸", "caught_at": "2026-10-20T07:30:00+08:00"}


class PostgrestCatchStore:
    """模擬 PostgREST 邊界而非替換 service，驗證真實 repository 的 HTTP filters。"""

    def __init__(self) -> None:
        """保存測試資料、實際 HTTP requests 與可切換的供應商失敗模式。"""

        self.rows: dict[str, dict[str, Any]] = {}
        self.requests: list[httpx.Request] = []
        self.failure = False
        self.invalid_response = False
        self.tick = 0

    def handle(self, request: httpx.Request) -> httpx.Response:
        """以 request 的 owner filter 實際篩選資料，並保留 JSON 值而不執行任何 SQL。"""

        self.requests.append(request)
        assert request.url.path == "/rest/v1/catch_logs"
        assert request.headers["apikey"] == "catch-test-server-key"
        if self.failure:
            return httpx.Response(403, json={"code": "42501", "message": "private provider error"})
        if self.invalid_response:
            return httpx.Response(200, json={"unexpected": "not a list"})
        self.tick += 1
        now = (datetime(2026, 10, 20, tzinfo=UTC) + timedelta(seconds=self.tick)).isoformat()
        if request.method == "POST":
            payload = json.loads(request.content)
            assert "id" not in payload and "created_at" not in payload
            row = {**payload, "id": str(uuid4()), "created_at": now, "updated_at": now}
            self.rows[row["id"]] = row
            assert request.headers["prefer"] == "return=representation"
            return httpx.Response(201, json=[row])

        params = request.url.params
        assert params["user_id"].startswith("eq.")
        owner = str(UUID(params["user_id"][3:]))
        rows = [row for row in self.rows.values() if row["user_id"] == owner]
        if "id" in params:
            log_id = str(UUID(params["id"][3:]))
            rows = [row for row in rows if row["id"] == log_id]
        else:
            assert request.method == "GET"
            assert params["order"] == "caught_at.desc,id.desc"
            rows.sort(
                key=lambda row: (
                    datetime.fromisoformat(row["caught_at"]),
                    row["id"],
                ),
                reverse=True,
            )
        if request.method == "PATCH":
            assert "id" in params
            payload = json.loads(request.content)
            assert not {"user_id", "id", "created_at", "updated_at"} & payload.keys()
            for row in rows:
                row.update({**payload, "updated_at": now})
        elif request.method == "DELETE":
            assert "id" in params
            for row in rows:
                del self.rows[row["id"]]
        if "limit" in params:
            offset, limit = int(params.get("offset", "0")), int(params["limit"])
            rows = rows[offset : offset + limit]
        return httpx.Response(200, json=rows)


@pytest.fixture
def catch_client() -> tuple[TestClient, Settings, PostgrestCatchStore]:
    """組合真正 API、service 與 repository，只替換 Google users 與 Supabase 網路邊界。"""

    settings = Settings(_env_file=None, jwt_secret_key="catch-test-secret-with-at-least-32-bytes")
    store = PostgrestCatchStore()
    repository = SupabaseCatchLogsRepository(
        SupabaseRestClient(
            supabase_url="https://example.supabase.co",
            secret_key="catch-test-server-key",
            transport=httpx.MockTransport(store.handle),
        )
    )
    users = InMemoryUsersRepository([USER_A, USER_B])
    app = create_app()

    def override_settings() -> Settings:
        """避免測試依賴本機私密環境變數。"""

        return settings

    def override_users() -> InMemoryUsersRepository:
        """提供兩個可登入帳號，驗證跨帳號紀錄隔離。"""

        return users

    def override_catches() -> SupabaseCatchLogsRepository:
        """將正式資料存取程式接到可觀察的 HTTP 測試邊界。"""

        return repository

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_users_repository] = override_users
    app.dependency_overrides[get_catch_logs_repository] = override_catches
    return TestClient(app), settings, store


def auth(settings: Settings, user: UserRecord = USER_A) -> dict[str, str]:
    """簽發正式格式的 FishSniper JWT，不跳過 authentication dependency。"""

    return {
        "Authorization": "Bearer "
        + create_access_token(
            settings,
            user_id=user.id,
            email=user.email,
        )
    }


def test_catch_log_crud_and_optional_field_clearing(catch_client: tuple) -> None:
    """走完整新增、詳情、部分修改、清空、刪除流程，確認未傳入欄位不被清空。"""

    client, settings, store = catch_client
    headers = auth(settings)
    response = client.post(
        "/api/v1/catch-logs",
        headers=headers,
        json={
            **BASE_PAYLOAD,
            "species_name": "  大口黑鱸  ",
            "length_cm": 32.5,
            "weight_g": 900,
            "fishing_method": "fly_fishing",
            "notes": "  released  ",
        },
    )
    assert response.status_code == 201
    record = response.json()
    assert record["user_id"] == str(USER_A.id)
    assert record["species_name"] == "大口黑鱸" and record["notes"] == "released"
    path = f"/api/v1/catch-logs/{record['id']}"
    assert client.get(path, headers=headers).json() == record
    updated = client.patch(path, headers=headers, json={"length_cm": None, "notes": " "})
    assert updated.status_code == 200
    assert updated.json()["length_cm"] is None and updated.json()["notes"] is None
    assert updated.json()["fishing_method"] == "fly_fishing"
    assert updated.json()["caught_at"] == record["caught_at"]
    assert updated.json()["updated_at"] > record["updated_at"]
    deleted = client.delete(path, headers=headers)
    assert deleted.status_code == 204 and deleted.content == b""
    assert client.get(path, headers=headers).status_code == 404
    assert client.delete(path, headers=headers).status_code == 404
    assert store.rows == {}


def test_users_cannot_read_edit_or_delete_other_users_catches(catch_client: tuple) -> None:
    """即使知道 log UUID，另一帳號也只能得到 404，列表也不會洩漏他人資料。"""

    client, settings, store = catch_client
    record = client.post("/api/v1/catch-logs", headers=auth(settings), json=BASE_PAYLOAD).json()
    path = f"/api/v1/catch-logs/{record['id']}"
    other = auth(settings, USER_B)
    assert client.get("/api/v1/catch-logs", headers=other).json()["items"] == []
    assert client.get(path, headers=other).status_code == 404
    assert client.patch(path, headers=other, json={"species_name": "stolen"}).status_code == 404
    assert client.delete(path, headers=other).status_code == 404
    assert store.rows[record["id"]]["species_name"] == BASE_PAYLOAD["species_name"]


def test_list_paginates_with_stable_tie_breaker_and_has_more(catch_client: tuple) -> None:
    """相同釣獲時間以 UUID 排序，分頁不重複，且不會將第二使用者的紀錄計入。"""

    client, settings, _store = catch_client
    headers = auth(settings)
    ids = [
        client.post("/api/v1/catch-logs", headers=headers, json=BASE_PAYLOAD).json()["id"]
        for _ in range(3)
    ]
    client.post("/api/v1/catch-logs", headers=auth(settings, USER_B), json=BASE_PAYLOAD)
    first = client.get("/api/v1/catch-logs?limit=2", headers=headers).json()
    second = client.get("/api/v1/catch-logs?limit=2&offset=2", headers=headers).json()
    assert first["has_more"] is True and second["has_more"] is False
    assert [row["id"] for row in first["items"] + second["items"]] == sorted(ids, reverse=True)
    assert second["offset"] == 2


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", ""),
        ("POST", ""),
        ("GET", f"/{uuid4()}"),
        ("PATCH", f"/{uuid4()}"),
        ("DELETE", f"/{uuid4()}"),
    ],
)
def test_all_catch_routes_require_valid_login(catch_client: tuple, method: str, path: str) -> None:
    """每個端點在沒有登入時都回 401，且不向漁獲資料庫發出請求。"""

    client, settings, store = catch_client
    for headers in ({}, {"Authorization": "Bearer invalid"}):
        response = client.request(
            method, "/api/v1/catch-logs" + path, headers=headers, json=BASE_PAYLOAD
        )
        assert response.status_code == 401
    assert store.requests == []


@pytest.mark.parametrize(
    "change",
    [
        {"species_name": "   "},
        {"species_name": "x" * 101},
        {"species_name": None},
        {"caught_at": "2026-10-20T07:30:00"},
        {"caught_at": "invalid"},
        {"caught_at": None},
        {"length_cm": 0},
        {"length_cm": -1},
        {"length_cm": "Infinity"},
        {"weight_g": "NaN"},
        {"weight_g": -2},
        {"fishing_method": "invented"},
        {"notes": "x" * 2001},
        {"user_id": str(USER_B.id)},
        {"id": str(uuid4())},
        {"latitude": 25},
        {"longitude": 121},
        {"photos": []},
        {"quantity": 2},
    ],
)
def test_create_rejects_invalid_or_out_of_scope_fields(catch_client: tuple, change: dict) -> None:
    """拒絕不合法尺寸、無時區時間、照片、位置及企圖指定其他 owner 的輸入。"""

    client, settings, store = catch_client
    response = client.post(
        "/api/v1/catch-logs", headers=auth(settings), json={**BASE_PAYLOAD, **change}
    )
    assert response.status_code == 422
    assert store.requests == []


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"species_name": None},
        {"caught_at": None},
        {"user_id": str(USER_B.id)},
        {"created_at": "2026-10-20T00:00:00Z"},
        {"length_cm": 0},
    ],
)
def test_patch_rejects_empty_required_null_and_system_fields(
    catch_client: tuple, payload: dict
) -> None:
    """PATCH 必須有可修改欄位，不能清空必填值或改寫擁有者與系統時間。"""

    client, settings, store = catch_client
    response = client.patch(f"/api/v1/catch-logs/{uuid4()}", headers=auth(settings), json=payload)
    assert response.status_code == 422
    assert store.requests == []


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
def test_list_rejects_invalid_page_bounds(catch_client: tuple, query: str) -> None:
    """限制單次回傳大小與分頁範圍，避免無界限的資料查詢。"""

    client, settings, store = catch_client
    assert client.get(f"/api/v1/catch-logs?{query}", headers=auth(settings)).status_code == 422
    assert store.requests == []


@pytest.mark.parametrize("mode", ["failure", "invalid_response"])
def test_provider_errors_return_safe_503(catch_client: tuple, mode: str) -> None:
    """資料庫 permission denied 或異常回應都回傳安全錯誤，而不是假裝空列表。"""

    client, settings, store = catch_client
    setattr(store, mode, True)
    response = client.get("/api/v1/catch-logs", headers=auth(settings))
    assert response.status_code == 503
    assert response.json() == {"detail": "Catch logs are temporarily unavailable."}


def test_sql_like_notes_are_sent_as_json_data(catch_client: tuple) -> None:
    """帶有 SQL 符號的備註保持 JSON 資料，不會被用來組成 table 或 filter。"""

    client, settings, store = catch_client
    notes = "O'Reilly; DROP TABLE users; --"
    response = client.post(
        "/api/v1/catch-logs", headers=auth(settings), json={**BASE_PAYLOAD, "notes": notes}
    )
    assert response.status_code == 201 and response.json()["notes"] == notes
    assert json.loads(store.requests[0].content)["notes"] == notes
    assert notes not in str(store.requests[0].url)


def test_missing_database_configuration_returns_safe_503(catch_client: tuple) -> None:
    """沒有 Supabase 設定仍提供安全提示，不洩漏 key 或讓缺少 migration 被當成成功。"""

    client, settings, _store = catch_client
    settings.supabase_url = ""
    settings.supabase_secret_key = ""
    del client.app.dependency_overrides[get_catch_logs_repository]
    response = client.get("/api/v1/catch-logs", headers=auth(settings))
    assert response.status_code == 503
    assert response.json() == {"detail": "Catch logs are temporarily unavailable."}
