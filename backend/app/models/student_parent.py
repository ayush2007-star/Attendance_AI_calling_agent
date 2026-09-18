from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.parent import Parent
    from app.models.student import Student


class StudentParent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "student_parents"

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    parent_id: Mapped[UUID] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    relationship_type: Mapped[str] = mapped_column(
        "relationship",
        String(50),
        nullable=False,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    student: Mapped["Student"] = relationship(
        "Student",
        back_populates="parent_links",
    )

    parent: Mapped["Parent"] = relationship(
        "Parent",
        back_populates="student_links",
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "parent_id",
            name="uq_student_parent",
        ),
    )