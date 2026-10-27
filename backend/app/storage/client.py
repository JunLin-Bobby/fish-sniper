import logging
from urllib.parse import quote, urljoin, urlparse

import httpx

from app.core.config import Settings
from app.db.errors import DatabaseConfigurationError

logger = logging.getLogger(__name__)


class StorageUnavailableError(RuntimeError):
    """檔案供應商暫時無法完成操作，對外不得暴露憑證或原始回應。"""

    def __init__(self, message: str, http_status: int | None = None) -> None:
        """保存可安全記錄的供應商 HTTP 狀態，不保存完整 headers 或 response。"""

        super().__init__(message)
        self.http_status = http_status


class SupabaseStorageClient:
    """只處理 Storage HTTP 通訊，不決定魚獲權限或照片數量。"""

    def __init__(
        self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        """保存後端憑證與可測試傳輸；不在建構時發送網路請求。"""

        if not settings.supabase_url or not settings.supabase_secret_key:
            raise DatabaseConfigurationError("Supabase storage is not configured.")
        self._base = settings.supabase_url.rstrip("/") + "/storage/v1"
        self._headers = {
            "apikey": settings.supabase_secret_key,
            "Authorization": f"Bearer {settings.supabase_secret_key}",
        }
        self._transport = transport

    async def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        """以有期限的請求執行操作，不將原始錯誤內容傳給使用者。"""

        try:
            async with httpx.AsyncClient(timeout=30, transport=self._transport) as client:
                headers = dict(self._headers)
                if "content" in kwargs:
                    headers["Content-Type"] = "image/jpeg"
                response = await client.request(
                    method, self._base + path, headers=headers, **kwargs
                )
        except httpx.TimeoutException as error:
            logger.warning(
                "Supabase request failed: provider=storage category=timeout type=%s",
                type(error).__name__,
            )
            raise StorageUnavailableError("Storage request timed out.") from error
        except httpx.HTTPError as error:
            logger.warning("Supabase request failed: provider=storage category=network")
            raise StorageUnavailableError("Storage request failed.") from error
        if response.status_code >= 400:
            logger.warning(
                "Supabase request failed: provider=storage category=http status=%s",
                response.status_code,
            )
            raise StorageUnavailableError("Storage HTTP failure.", response.status_code)
        return response

    async def upload(self, bucket: str, path: str, content: bytes) -> None:
        """以唯一物件路徑上傳處理後的 JPEG，不覆蓋既有檔案。"""

        await self._request(
            "POST",
            f"/object/{quote(bucket, safe='')}/{quote(path, safe='/')}",
            content=content,
        )

    async def delete(self, bucket: str, paths: list[str]) -> None:
        """透過批次刪除移除已存在物件；不存在的路徑可安全重試。"""

        if paths:
            await self._request(
                "DELETE", f"/object/{quote(bucket, safe='')}", json={"prefixes": paths}
            )

    async def signed_url(self, bucket: str, path: str, seconds: int) -> str:
        """建立短效連結並驗證回傳來源，避免將錯誤供應商網址交給前端。"""

        response = await self._request(
            "POST",
            f"/object/sign/{quote(bucket, safe='')}/{quote(path, safe='/')}",
            json={"expiresIn": seconds},
        )
        try:
            value = response.json()["signedURL"]
            if not isinstance(value, str):
                raise ValueError()
            origin = self._base.split("/storage/v1")[0]
            url = urljoin(origin + "/storage/v1/", value.lstrip("/"))
            if value.startswith("/storage/v1/"):
                url = origin + value
            if urlparse(url).netloc != urlparse(origin).netloc:
                raise ValueError()
            return url
        except (KeyError, ValueError, TypeError) as error:
            raise StorageUnavailableError("Storage returned an invalid signed URL.") from error
