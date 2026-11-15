import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.integrations.calling.base import CallRequest, ProviderCallResult

logger = logging.getLogger("attendance_backend.calling.mock")


class MockCallingProvider:
    """
    Deterministic college-demonstration calling provider.
    Simulates call initiation without placing real telephone calls,
    allowing complete end-to-end evaluation of the campaign and call lifecycle.
    """

    def __init__(self, mode: str = "DEMO") -> None:
        self.mode = mode

    def start_call(self, request: CallRequest) -> ProviderCallResult:
        logger.info(
            "Mock calling provider initiated call attempt %s for phone %s",
            request.attempt_id,
            request.phone_number,
        )
        return ProviderCallResult(
            provider_call_id=f"demo-{request.attempt_id}",
            status="RINGING",
            started_at=datetime.now(timezone.utc),
        )

    def end_call(self, provider_call_id: str) -> None:
        logger.info("Mock provider ended call %s", provider_call_id)
