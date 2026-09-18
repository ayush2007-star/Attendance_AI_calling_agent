from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.campaign import CallCampaign
    from app.models.parent import Parent
    from app.models.student import Student


class CampaignTarget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "campaign_targets"

    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("call_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parents.id", ondelete="SET NULL"),
        nullable=True,
    )

    attendance_percentage_used: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    threshold_used: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    eligibility_reason: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
    )

    selected_phone_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "student_id",
            "parent_id",
            name="uq_campaign_target_student_parent",
        ),
    )
