from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.class_model import ClassModel
    from app.models.student_parent import StudentParent


class Student(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "students"

    student_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    roll_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    class_room: Mapped["ClassModel"] = relationship(
        back_populates="students",
    )

    parent_links: Mapped[list["StudentParent"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )

    @property
    def _primary_parent_link(self) -> "StudentParent | None":
        return next(
            (link for link in self.parent_links if link.is_primary),
            None,
        )

    @property
    def parent_name(self) -> str | None:
        link = self._primary_parent_link
        return link.parent.name if link else None

    @property
    def parent_phone(self) -> str | None:
        link = self._primary_parent_link
        return link.parent.primary_phone if link else None

    @property
    def relationship(self) -> str | None:
        link = self._primary_parent_link
        return link.relationship_type if link else None