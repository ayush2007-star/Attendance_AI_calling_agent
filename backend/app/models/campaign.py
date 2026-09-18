from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.class_model import ClassModel
    from app.models.user import User


class CallCampaign(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "call_campaigns"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    attendance_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    attendance_period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    attendance_period_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    threshold_used: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    class_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("classes.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="DRAFT",
    )

    total_targets: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    completed_calls: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    failed_calls: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )