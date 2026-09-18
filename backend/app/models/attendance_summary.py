from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.attendance_import import AttendanceImportBatch
    from app.models.student import Student


class AttendanceSummary(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "attendance_summaries"

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    import_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("attendance_import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    attendance_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    period_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    calculation_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "import_batch_id",
            name="uq_attendance_summary_student_import",
        ),
    )
