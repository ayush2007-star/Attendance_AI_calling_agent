from uuid import UUID

from app.contracts.call_context import CallContext
from app.integrations.backend_client import BackendClient


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_login_uses_oauth_form_and_call_context_route(monkeypatch) -> None:
    calls = []

    def fake_post(url: str, **kwargs) -> FakeResponse:
        calls.append(("post", url, kwargs))
        return FakeResponse({"access_token": "test-token"})

    def fake_get(url: str, **kwargs) -> FakeResponse:
        calls.append(("get", url, kwargs))
        return FakeResponse(
            {
                "campaign_target_id": "00000000-0000-0000-0000-000000000001",
                "campaign_id": "00000000-0000-0000-0000-000000000002",
                "student_id": "00000000-0000-0000-0000-000000000003",
                "student_name": "Aarav Sharma",
                "student_code": "STU001",
                "parent_id": "00000000-0000-0000-0000-000000000004",
                "parent_name": "Parent Name",
                "phone_number": "9999999999",
                "preferred_language": "Hindi",
                "attendance_percentage": 68.5,
                "threshold": 75.0,
                "eligibility_reason": "BELOW_THRESHOLD",
                "attendance_date": "2026-11-04",
                "attendance_period_start": "2026-10-01",
                "attendance_period_end": "2026-10-31",
            }
        )

    monkeypatch.setattr("app.integrations.backend_client.requests.post", fake_post)
    monkeypatch.setattr("app.integrations.backend_client.requests.get", fake_get)

    client = BackendClient()
    assert client.login("agent-user", "agent-password") == "test-token"
    context = client.get_call_context(
        UUID("00000000-0000-0000-0000-000000000001")
    )

    assert isinstance(context, CallContext)
    assert calls[0][2]["data"] == {
        "username": "agent-user",
        "password": "agent-password",
    }
    assert "json" not in calls[0][2]
    assert calls[1][1].endswith(
        "/api/v1/calls/targets/00000000-0000-0000-0000-000000000001/context"
    )
    assert calls[1][2]["headers"] == {
        "Authorization": "Bearer test-token"
    }
