class DatabaseError(RuntimeError):
    """所有 FishSniper database 錯誤的共同基底類型。"""


class DatabaseConfigurationError(DatabaseError):
    """Supabase URL 或 secret key 尚未正確設定。"""


class DatabaseUnavailableError(DatabaseError):
    """Supabase 請求失敗或回傳無法解析的資料。"""
