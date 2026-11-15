from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_reports_running_service() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "attendance-ai-agent",
    }


def test_development_api_documentation_is_enabled() -> None:
    assert app.docs_url == "/docs"
