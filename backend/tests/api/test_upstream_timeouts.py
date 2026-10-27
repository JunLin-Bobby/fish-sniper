import asyncio
import logging

import httpx
import pytest

from app.core.config import Settings
from app.db.client import SupabaseRestClient
from app.db.errors import DatabaseUnavailableError
from app.storage.client import StorageUnavailableError, SupabaseStorageClient


@pytest.mark.parametrize("provider", ["database", "storage"])
@pytest.mark.parametrize(
    "error_type",
    [
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
        httpx.ConnectError,
    ],
)
def test_provider_failures_log_safe_categories(provider, error_type, caplog):
    """區分上游 timeout 與網路問題，記錄類型但不洩漏 URL、憑證或上游錯誤內容。"""

    def handle(request):
        """上游錯誤故意帶私密字串，驗證不會直接寫進 log。"""

        raise error_type("private-upstream-detail", request=request)

    transport = httpx.MockTransport(handle)
    if provider == "database":
        client = SupabaseRestClient(
            supabase_url="https://private-host.test",
            secret_key="private-server-key",
            transport=transport,
        )
        operation = client.request("GET", "users")
        expected = DatabaseUnavailableError
    else:
        client = SupabaseStorageClient(
            Settings(
                _env_file=None,
                supabase_url="https://private-host.test",
                supabase_secret_key="private-server-key",
            ),
            transport=transport,
        )
        operation = client.upload("catch-photos", "private-photo-location.jpg", b"photo")
        expected = StorageUnavailableError
    with caplog.at_level(logging.WARNING), pytest.raises(expected) as failure:
        asyncio.run(operation)
    assert isinstance(failure.value.__cause__, error_type)
    category = "timeout" if issubclass(error_type, httpx.TimeoutException) else "network"
    assert f"provider={provider} category={category}" in caplog.text
    if category == "timeout":
        assert f"type={error_type.__name__}" in caplog.text
    for private in [
        "private-upstream-detail",
        "private-host",
        "private-server-key",
        "private-photo",
    ]:
        assert private not in caplog.text
