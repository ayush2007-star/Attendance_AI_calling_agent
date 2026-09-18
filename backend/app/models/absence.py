from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.attendance import AttendanceRecord
    from app.models.student import Student


class AbsenceEvent(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "absence_events"

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    attendance_record_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "attendance_records.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        unique=True,
    )

    absence_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
    )

    eligible_for_call: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )