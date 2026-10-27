from fastapi import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class CatchUploadLimitMiddleware:
    """在 multipart parser 之前限制實際讀取 bytes，包含沒有 Content-Length 的上傳。"""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        """保存總請求上限；單張限制仍由照片 service 獨立驗證。"""

        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """只限制照片建立入口，不影響健康檢查、OAuth 與一般 JSON CRUD。"""

        if scope["type"] != "http" or scope.get("path") != "/api/v1/catch-logs/with-photos":
            await self.app(scope, receive, send)
            return
        received = 0

        async def limited_receive() -> Message:
            """累計串流 body bytes，超限時在解析前中止並回覆 413。"""

            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > self.max_bytes:
                raise HTTPException(413, detail="Upload request is too large.")
            return message

        await self.app(scope, limited_receive, send)
