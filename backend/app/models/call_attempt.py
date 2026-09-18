from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.absence import AbsenceEvent
    from app.models.campaign import CallCampaign
    from app.models.campaign_target import CampaignTarget
    from app.models.parent import Parent


class CallAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "call_attempts"

    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("call_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    campaign_target_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaign_targets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    absence_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("absence_events.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    parent_id: Mapped[UUID] = mapped_column(
        ForeignKey("parents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    phone_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="QUEUED",
    )

    provider_call_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )