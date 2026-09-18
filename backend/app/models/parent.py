from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.student_parent import StudentParent


class Parent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "parents"

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    primary_phone: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    alternate_phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    preferred_language: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="en",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    student_links: Mapped[list["StudentParent"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
    )