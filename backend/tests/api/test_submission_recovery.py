"""恢復協定整合測試：使用真正 route/service/repository 與可觀察的 provider 邊界。"""

# Pytest fixture is intentionally imported for discovery.
# ruff: noqa: F401 F811
import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from app.catch_logs.dependencies import get_catch_logs_repository, get_catch_photo_service
from app.catch_logs.photo_service import CatchPhotoService
from app.catch_logs.service import CatchLogService
from tests.api.test_catch_logs import BASE_PAYLOAD, USER_A, USER_B, auth, catch_client
from tests.api.test_catch_photos import image_bytes, submit


def resolve(client, settings, submission_id, user=USER_A):
    """透過正式恢復入口詢問 owner 的結果，不重送照片。"""

    return client.post(
        f"/api/v1/catch-logs/submissions/{submission_id}/resolve", headers=auth(settings, user)
    )


def test_normal_post_never_resolves_or_polls(catch_client):
    """正常 POST 自行完成；只有異常恢復才呼叫 resolve RPC。"""

    client, settings, store = catch_client
    assert submit(client, settings).status_code == 201
    paths = [request.url.path for request in store.requests]
    assert paths.index("/rest/v1/rpc/register_catch_submission") < paths.index(
        "/rest/v1/rpc/begin_catch_submission"
    )
    assert not any("resolve_catch_submission" in path for path in paths)


def test_missing_receipt_is_fenced_and_late_upload_is_rejected(catch_client):
    """沒有到達的舊 POST 也有持久失敗墓碑，不能在 UI 已失敗後晚到建立。"""

    client, settings, store = catch_client
    submission_id = uuid4()
    result = resolve(client, settings, submission_id)
    assert result.json() == {"status": "failed", "log_id": None, "retry_after_ms": 0}
    assert submit(client, settings, submission_id=submission_id).status_code == 409
    assert not store.rows and not store.objects


def test_recovery_is_owner_scoped_and_preserves_committed_success(catch_client):
    """另一帳號的同 ID 恢復不改動擁有者成功結果，也不能取得 log ID。"""

    client, settings, store = catch_client
    submission_id = uuid4()
    record = submit(client, settings, submission_id=submission_id).json()
    assert resolve(client, settings, submission_id, USER_B).json()["status"] == "failed"
    result = resolve(client, settings, submission_id).json()
    assert result["status"] == "ready" and result["log_id"] == record["id"]
    assert store.rows[record["id"]]["status"] == "ready" and store.objects


def test_active_pending_returns_deadline_then_expires_without_catch_row(catch_client):
    """只收到 header 的操作也會過期；pending 提供再次確認時間而不是永久等待。"""

    client, settings, store = catch_client
    submission_id = uuid4()
    store.receipts[str(USER_A.id) + str(submission_id)] = {
        "status": "pending",
        "log_id": None,
        "fingerprint": None,
        "attempt_id": str(uuid4()),
        "deadline": datetime.now(UTC) + timedelta(seconds=5),
    }
    result = resolve(client, settings, submission_id).json()
    assert result["status"] == "pending" and 0 < result["retry_after_ms"] <= 5100
    next(iter(store.receipts.values()))["deadline"] = datetime.now(UTC) - timedelta(seconds=1)
    assert resolve(client, settings, submission_id).json()["status"] == "failed"


def test_header_body_mismatch_ends_reservation_without_creating_catch(catch_client):
    """header 是提早登記用的 ID，body 不一致必須拒絕並終結自己的 reservation。"""

    client, settings, store = catch_client
    response = client.post(
        "/api/v1/catch-logs/with-photos",
        headers={**auth(settings), "Idempotency-Key": str(uuid4())},
        data={"submission_id": str(uuid4()), "payload": json.dumps(BASE_PAYLOAD)},
    )
    assert response.status_code == 422
    assert not store.rows
    assert next(iter(store.receipts.values()))["status"] == "failed"


def test_processing_timeout_is_terminal_and_never_publishes(catch_client, monkeypatch):
    """處理期限到期先記錄失敗；使用真正 asyncio timeout，不依賴前端介入。"""

    client, settings, store = catch_client
    settings.catch_upload_processing_seconds = 0.01

    async def stall(self, files):
        """模擬圖片處理等待不回應，必須被整體後端期限中止。"""

        await asyncio.Event().wait()

    monkeypatch.setattr(CatchPhotoService, "validate_and_prepare", stall)
    submission_id = uuid4()
    assert submit(client, settings, submission_id=submission_id).status_code == 503
    assert resolve(client, settings, submission_id).json()["status"] == "failed"
    assert not store.rows and not store.objects


def test_expiry_worker_covers_reservations_without_a_log(catch_client):
    """程序中斷在建立 catch 之前，恢復工作仍會找到並終結過期收據。"""

    client, settings, store = catch_client
    store.receipts["expired"] = {
        "status": "pending",
        "log_id": None,
        "fingerprint": None,
        "deadline": datetime.now(UTC) - timedelta(seconds=1),
    }
    service = CatchLogService(
        client.app.dependency_overrides[get_catch_logs_repository](),
        client.app.dependency_overrides[get_catch_photo_service](),
    )
    asyncio.run(service.recover_pending())
    assert store.receipts["expired"]["status"] == "failed"


def test_invalid_image_leaves_only_terminal_receipt(catch_client):
    """驗證失敗沒有 catch 或 Storage，但保留最小失敗收據阻擋舊請求。"""

    client, settings, store = catch_client
    submission_id = uuid4()
    assert (
        submit(
            client, settings, photos=[image_bytes(), b"bad"], submission_id=submission_id
        ).status_code
        == 422
    )
    assert resolve(client, settings, submission_id).json()["status"] == "failed"
    assert not store.rows and not store.objects


def test_stalled_body_is_registered_before_receive_timeout(catch_client):
    """真正非同步串流卡在收檔階段，仍先登記並由後端期限終結，不需前端查詢。"""

    client, settings, store = catch_client
    settings.catch_upload_receive_seconds = 0.01
    submission_id = uuid4()

    async def stalled_body():
        """模擬手機連線存在但沒有再送出 body bytes。"""

        yield b"--x\r\n"
        await asyncio.Event().wait()

    async def exercise():
        """走真實 ASGI receive 路徑，驗證登記不必等 multipart 完整送達。"""

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=client.app), base_url="http://test"
        ) as http:
            return await http.post(
                "/api/v1/catch-logs/with-photos",
                headers={
                    **auth(settings),
                    "Idempotency-Key": str(submission_id),
                    "Content-Type": "multipart/form-data; boundary=x",
                },
                content=stalled_body(),
            )

    response = asyncio.run(exercise())
    assert response.status_code == 503
    assert next(iter(store.receipts.values()))["status"] == "failed"
    assert not store.rows
