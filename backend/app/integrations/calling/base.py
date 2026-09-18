from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CallRequest:
    attempt_id: UUID
    phone_number: str
    campaign_id: UUID


@dataclass(frozen=True)
class ProviderCallResult:
    provider_call_id: str
    status: str
    started_at: datetime | None = None


class CallingProvider(Protocol):
    def start_call(self, request: CallRequest) -> ProviderCallResult:
        """Start a call through a concrete provider adapter."""

    def end_call(self, provider_call_id: str) -> None:
        """Request termination of a provider call."""
