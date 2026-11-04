from datetime import datetime, timezone

from app.integrations.calling.base import (
    CallRequest,
    ProviderCallResult,
)


class LocalCallingProvider:
    """
    Development-only calling provider.

    This does not place a real phone call.
    """

    def start_call(self, request: CallRequest) -> ProviderCallResult:
        return ProviderCallResult(
            provider_call_id=f"local-{request.attempt_id}",
            status="RINGING",
            started_at=datetime.now(timezone.utc),
        )

    def end_call(self, provider_call_id: str) -> None:
        return None