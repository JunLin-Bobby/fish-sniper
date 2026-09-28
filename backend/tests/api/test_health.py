from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok() -> None:
    """確認未受 auth 保護的 health endpoint 保持可用。"""

    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
