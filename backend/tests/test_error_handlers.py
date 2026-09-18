from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.error_handlers import register_exception_handlers


def test_exception_handlers_return_safe_payloads() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/validation")
    def validation(value: int) -> int:
        return value

    @app.get("/conflict")
    def conflict() -> None:
        raise IntegrityError("duplicate", {}, Exception("secret sql detail"))

    @app.get("/unexpected")
    def unexpected() -> None:
        raise RuntimeError("secret internal detail")

    client = TestClient(app, raise_server_exceptions=False)

    validation_response = client.post("/validation", json={"value": "wrong"})
    assert validation_response.status_code == 422
    assert validation_response.json()["detail"] == "Request validation failed"

    conflict_response = client.get("/conflict")
    assert conflict_response.status_code == 409
    assert "secret sql detail" not in conflict_response.text

    unexpected_response = client.get("/unexpected")
    assert unexpected_response.status_code == 500
    assert "secret internal detail" not in unexpected_response.text
