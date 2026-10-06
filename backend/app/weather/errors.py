"""供應商介接與資料驗證的可辨識錯誤。"""


class ProviderError(RuntimeError):
    """供應商不可用、額度不足或回傳非預期資料。"""

    def __init__(self, provider: str, category: str) -> None:
        """保存安全的供應商與錯誤類型，不包含金鑰或完整 URL。"""

        super().__init__(f"{provider}: {category}")
        self.provider = provider
        self.category = category
