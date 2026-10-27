import asyncio

from app.catch_logs import recovery
from app.core.config import Settings


def test_recovery_worker_is_cancelled_on_shutdown(monkeypatch):
    """app 關閉會取消背景等待，不遺留工作；此測試不讀私密設定或呼叫 Supabase。"""

    settings = Settings(
        _env_file=None,
        supabase_url="https://example.test",
        supabase_secret_key="test-only",
        catch_cleanup_interval_seconds=60,
    )
    started, cancelled = asyncio.Event(), asyncio.Event()

    async def fake_worker():
        """模擬等待中的恢復 worker，記錄確實收到取消。"""

        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    async def exercise():
        """使用真實 lifespan 建立與關閉 worker，避免依賴不穩定的 sleep。"""

        async with recovery.catch_cleanup_lifespan(None):
            await asyncio.wait_for(started.wait(), 1)
        assert cancelled.is_set()

    monkeypatch.setattr(recovery, "get_settings", lambda: settings)
    monkeypatch.setattr(recovery, "retry_cleanup", fake_worker)
    asyncio.run(exercise())
