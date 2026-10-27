# Pytest imports this reusable fixture; test argument names intentionally match it.
# ruff: noqa: F811
import json
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image

from app.catch_logs.dependencies import get_catch_logs_repository, get_catch_photo_service
from app.catch_logs.photo_processing import prepare_photo
from app.catch_logs.photo_schemas import CatchPhotoValidationError
from app.catch_logs.service import CatchLogService
from app.core.config import Settings
from tests.api.test_catch_logs import BASE_PAYLOAD, USER_B, auth, catch_client  # noqa: F401


def image_bytes(format: str = "JPEG", *, metadata: bool = False) -> bytes:
    """產生真實可解碼照片，必要時附加拍攝時間與方向測試 EXIF。"""

    image = Image.new("RGB", (80, 40), "orange")
    output = BytesIO()
    exif = Image.Exif()
    if metadata:
        exif[274] = 6
        exif[34665] = {36867: "2026:10:20 07:30:00", 36881: "+08:00"}
        exif[34853] = {1: "N", 2: (25, 3, 0), 3: "E", 4: (121, 30, 0)}
    image.save(output, format=format, exif=exif)
    return output.getvalue()


def submit(client, settings, *, photos=None, submission_id=None, payload=None):
    """經由正式 multipart 入口同時送出魚獲與照片，不跳過登入或圖片處理。"""

    submission_id = submission_id or uuid4()
    return client.post(
        "/api/v1/catch-logs/with-photos",
        headers={**auth(settings), "Idempotency-Key": str(submission_id)},
        data={
            "payload": json.dumps(payload or BASE_PAYLOAD),
            "submission_id": str(submission_id),
        },
        files=[
            ("photos", ("fish.heic", content, "application/octet-stream"))
            for content in (photos if photos is not None else [image_bytes()])
        ],
    )


def test_photo_submission_publishes_all_and_is_idempotent(catch_client):
    """兩張成功後才一起發布；相同內容重送只回原魚獲，不重複上傳。"""

    client, settings, store = catch_client
    submission_id = uuid4()
    photos = [image_bytes(metadata=True), image_bytes("PNG")]
    response = submit(client, settings, photos=photos, submission_id=submission_id)
    assert response.status_code == 201, response.text
    record = response.json()
    assert store.rows[record["id"]]["status"] == "ready"
    assert len(store.objects) == 2 and all(p["status"] == "ready" for p in store.photos.values())
    assert submit(client, settings, photos=photos, submission_id=submission_id).json() == record
    assert store.upload_count == 2 and len(store.rows) == 1
    changed = submit(
        client,
        settings,
        photos=photos,
        submission_id=submission_id,
        payload={**BASE_PAYLOAD, "species_name": "different"},
    )
    assert changed.status_code == 409
    path = f"/api/v1/catch-logs/{record['id']}/photos"
    result = client.get(path, headers=auth(settings))
    assert result.status_code == 200
    assert len(result.json()) == 2
    assert result.json()[0]["metadata"]["captured_at"] == "2026-10-20T07:30:00+08:00"
    assert result.json()[0]["metadata"]["latitude"] == 25.05
    assert "object_path" not in result.json()[0]
    assert client.get(path, headers=auth(settings, USER_B)).status_code == 404


@pytest.mark.parametrize("failure", ["upload", "publish", "cleanup"])
def test_failure_hides_entire_catch_and_preserves_cleanup_manifest(catch_client, failure):
    """第二張或 DB 發布失敗不留下可見魚獲；清理失敗仍保留所有物件路徑。"""

    client, settings, store = catch_client
    store.fail_upload_number = 2 if failure != "publish" else 0
    store.fail_publish = failure == "publish"
    store.fail_cleanup = failure == "cleanup"
    response = submit(client, settings, photos=[image_bytes(), image_bytes()])
    assert response.status_code == 503
    assert client.get("/api/v1/catch-logs", headers=auth(settings)).json()["items"] == []
    row = next(iter(store.rows.values()))
    assert row["status"] == "cleanup_pending"
    assert client.get(f"/api/v1/catch-logs/{row['id']}", headers=auth(settings)).status_code == 404
    assert (
        client.patch(
            f"/api/v1/catch-logs/{row['id']}",
            headers=auth(settings),
            json={"notes": "should not edit draft"},
        ).status_code
        == 404
    )
    assert len(store.photos) == 2
    assert len(store.objects) == (1 if failure == "cleanup" else 0)


def test_lost_publish_response_does_not_delete_committed_photos(catch_client):
    """交易已 COMMIT 但回應遺失，補償不可刪除 ready 檔案，重試讀回同筆。"""

    client, settings, store = catch_client
    store.lose_publish_response = True
    submission_id = uuid4()
    assert submit(client, settings, submission_id=submission_id).status_code == 201
    assert len(store.objects) == 1
    assert next(iter(store.rows.values()))["status"] == "ready"
    assert submit(client, settings, submission_id=submission_id).status_code == 201
    assert store.upload_count == 1
    receipt = client.get(f"/api/v1/catch-logs/submissions/{submission_id}", headers=auth(settings))
    assert receipt.json()["status"] == "ready"
    other = client.get(
        f"/api/v1/catch-logs/submissions/{submission_id}", headers=auth(settings, USER_B)
    )
    assert other.json() == {"status": "not_found", "log_id": None}


def test_cleanup_command_retries_storage_failure(catch_client):
    """即時清理失敗後，可由恢復流程重跑同一份 manifest，成功前不遺失路徑。"""

    import asyncio

    client, settings, store = catch_client
    store.fail_upload_number = 2
    store.fail_cleanup = True
    assert submit(client, settings, photos=[image_bytes(), image_bytes()]).status_code == 503
    service = CatchLogService(
        client.app.dependency_overrides[get_catch_logs_repository](),
        client.app.dependency_overrides[get_catch_photo_service](),
    )
    failed = asyncio.run(service.recover_pending())
    assert failed["errors"] == 1 and store.objects
    store.fail_cleanup = False
    recovered = asyncio.run(service.recover_pending())
    assert recovered["errors"] == 0 and recovered["retained"] == 1 and not store.objects


def test_streamed_request_limit_rejects_before_database(catch_client):
    """不依賴 Content-Length，分塊超出總請求限制會回 413 並且不建立草稿。"""

    client, settings, store = catch_client
    response = client.post(
        "/api/v1/catch-logs/with-photos",
        headers={
            **auth(settings),
            "Idempotency-Key": str(uuid4()),
            "Content-Type": "multipart/form-data; boundary=x",
        },
        content=iter(
            [
                b'--x\r\nContent-Disposition: form-data; name="payload"\r\n\r\n',
                b"x" * (2 * settings.catch_photo_max_bytes + 65_537),
            ]
        ),
    )
    assert response.status_code == 413
    assert not store.rows


def test_all_validation_happens_before_database_draft(catch_client):
    """任一張不是有效圖片、超過張數或魚獲欄位錯誤，不建立任何草稿或上傳。"""

    client, settings, store = catch_client
    for files in ([image_bytes(), b"not an image"], [image_bytes()] * 3):
        assert submit(client, settings, photos=files).status_code in (400, 422)
    assert (
        submit(client, settings, payload={**BASE_PAYLOAD, "species_name": " "}).status_code == 422
    )
    assert not store.rows and not store.objects


def test_photo_delete_and_whole_catch_delete_cleanup_storage(catch_client):
    """其他帳號不能刪照片；刪單張保留魚獲，刪整筆會清除所有剩餘物件。"""

    client, settings, store = catch_client
    record = submit(client, settings, photos=[image_bytes(), image_bytes()]).json()
    photo = next(iter(store.photos.values()))
    path = f"/api/v1/catch-logs/{record['id']}/photos/{photo['id']}"
    assert client.delete(path, headers=auth(settings, USER_B)).status_code == 404
    store.fail_cleanup = True
    assert client.delete(path, headers=auth(settings)).status_code == 503
    assert photo["status"] == "deleting" and len(store.objects) == 2
    store.fail_cleanup = False
    assert client.delete(path, headers=auth(settings)).status_code == 204
    assert len(store.objects) == len(store.photos) == 1
    assert (
        client.delete(f"/api/v1/catch-logs/{record['id']}", headers=auth(settings)).status_code
        == 204
    )
    assert not store.objects and not store.photos and not store.rows


@pytest.mark.parametrize("format", ["JPEG", "PNG", "HEIF"])
def test_real_image_formats_convert_to_metadata_free_jpeg(format):
    """實際編解碼 HEIC/JPEG/PNG，而非僅測副檔名；輸出不包含原始 EXIF。"""

    output = prepare_photo(image_bytes(format, metadata=True), Settings(_env_file=None))
    assert output.metadata.captured_at is not None
    with Image.open(BytesIO(output.content)) as image:
        assert image.format == "JPEG" and not image.getexif()
    assert max(output.width, output.height) <= 2048


def test_size_pixel_and_format_limits():
    """限制原檔 bytes、解碼像素與格式，防止只改 MIME 或副檔名繞過驗證。"""

    for raw, settings in [
        (image_bytes(), Settings(_env_file=None, catch_photo_max_bytes=2)),
        (image_bytes(), Settings(_env_file=None, catch_photo_max_pixels=2)),
        (image_bytes("GIF"), Settings(_env_file=None)),
    ]:
        with pytest.raises(CatchPhotoValidationError):
            prepare_photo(raw, settings)


def test_optional_no_photo_submission_publishes_without_storage(catch_client):
    """照片選填，零張也沿用同一套去重與發布流程，不要求 Storage 上傳。"""

    client, settings, store = catch_client
    response = submit(client, settings, photos=[])
    assert response.status_code == 201
    assert store.rows[response.json()["id"]]["status"] == "ready"
    assert store.upload_count == 0


def test_missing_exif_does_not_block_upload():
    """無 metadata 的有效照片仍可使用，候選時間與座標皆保持未提供。"""

    output = prepare_photo(image_bytes(), Settings(_env_file=None))
    assert output.metadata.model_dump() == {
        "captured_at": None,
        "local_captured_at": None,
        "latitude": None,
        "longitude": None,
    }
