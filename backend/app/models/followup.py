from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.campaign import CallCampaign
    from app.models.campaign_target import CampaignTarget
    from app.models.parent import Parent
    from app.models.student import Student
    from app.models.user import User


class Followup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "followups"

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )

    campaign_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("call_campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    campaign_target_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaign_targets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    assigned_to: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="MEDIUM",
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
    )

    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    timezone_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="UTC",
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_error: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )