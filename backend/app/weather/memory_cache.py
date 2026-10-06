"""第一版的單一後端 process 記憶體快取。"""

from copy import deepcopy
from time import monotonic


class MemoryForecastCache:
    """限制容量的 TTL 快取；多個 backend process 不共享內容。"""

    def __init__(self, max_entries: int = 512) -> None:
        """建立每個 process 共用的有限大小快取。"""

        self._entries: dict[str, tuple[float, dict]] = {}
        self._max_entries = max_entries

    async def get(self, key: str) -> dict | None:
        """只回傳未過期的獨立資料副本。"""

        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at <= monotonic():
            self._entries.pop(key, None)
            return None
        return deepcopy(value)

    async def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        """保存資料副本，並在達容量上限時移除最早過期的資料。"""

        if ttl_seconds <= 0:
            return
        if len(self._entries) >= self._max_entries and key not in self._entries:
            oldest_key = min(self._entries, key=lambda item: self._entries[item][0])
            self._entries.pop(oldest_key, None)
        self._entries[key] = (monotonic() + ttl_seconds, deepcopy(value))
