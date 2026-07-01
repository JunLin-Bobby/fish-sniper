from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_returns_200_with_correct_body():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_cors_header_returned_for_allowed_origin():
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_health_cors_header_absent_for_unknown_origin():
    response = client.get(
        "/health",
        headers={"Origin": "http://evil.example.com"},
    )
    assert response.status_code == 200
    # CORS header must not be set for origins not in the allowlist
    assert response.headers.get("access-control-allow-origin") is None
