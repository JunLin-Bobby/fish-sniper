"""與儲存技術無關的快取介面。"""

from typing import Protocol


class ForecastCache(Protocol):
    """以 JSON 相容物件存取限時預報結果。"""

    async def get(self, key: str) -> dict | None:
        """回傳尚未過期的資料，未命中時回傳 None。"""

        ...

    async def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        """將資料保存指定秒數。"""

        ...
