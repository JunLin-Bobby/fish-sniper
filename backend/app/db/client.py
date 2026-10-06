from typing import Any

import httpx

from app.core.config import Settings
from app.db.errors import DatabaseConfigurationError, DatabaseUnavailableError


class SupabaseRestClient:
    """使用 Supabase Data API 存取 PostgreSQL 的輕量非同步 client。"""

    def __init__(
        self,
        *,
        supabase_url: str,
        secret_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """驗證必要設定，並保存每次 REST 請求需要的連線資訊。"""

        normalized_url = supabase_url.rstrip("/")
        if not normalized_url or not secret_key:
            raise DatabaseConfigurationError("Supabase database is not configured.")

        self._rest_base_url = f"{normalized_url}/rest/v1"
        self._secret_key = secret_key
        self._transport = transport

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        prefer: str | None = None,
    ) -> Any:
        """送出已授權的 Supabase REST 請求，並將失敗統一轉成 database 錯誤。"""

        headers = {
            "apikey": self._secret_key,
            "Authorization": f"Bearer {self._secret_key}",
            "Accept": "application/json",
        }
        if json is not None:
            headers["Content-Type"] = "application/json"
        if prefer:
            headers["Prefer"] = prefer

        try:
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                response = await client.request(
                    method,
                    f"{self._rest_base_url}/{path.lstrip('/')}",
                    params=params,
                    json=json,
                    headers=headers,
                )
        except httpx.HTTPError as error:
            raise DatabaseUnavailableError("Supabase request could not be completed.") from error

        if response.status_code >= 400:
            # TODO: 在後端記錄不含 secret 的 Supabase 狀態碼與錯誤類別，
            # 方便區分設定、schema 與服務故障。
            raise DatabaseUnavailableError(
                f"Supabase request failed with HTTP {response.status_code}."
            )

        if response.status_code == 204 or not response.content:
            return None

        try:
            return response.json()
        except ValueError as error:
            raise DatabaseUnavailableError("Supabase returned invalid JSON.") from error


def create_supabase_rest_client(settings: Settings) -> SupabaseRestClient:
    """依目前環境設定建立只能在 backend 使用的 Supabase REST client。"""

    return SupabaseRestClient(
        supabase_url=settings.supabase_url,
        secret_key=settings.supabase_secret_key,
    )
