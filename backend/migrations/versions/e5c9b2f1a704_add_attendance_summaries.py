"""add attendance summaries

Revision ID: e5c9b2f1a704
Revises: c2e8a1d4f907
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5c9b2f1a704"
down_revision: Union[str, Sequence[str], None] = "c2e8a1d4f907"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attendance_summaries",
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("import_batch_id", sa.UUID(), nullable=False),
        sa.Column("attendance_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("calculation_method", sa.String(length=50), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["attendance_import_batches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id",
            "import_batch_id",
            name="uq_attendance_summary_student_import",
        ),
    )
    op.create_index(
        "ix_attendance_summaries_student_id",
        "attendance_summaries",
        ["student_id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_summaries_import_batch_id",
        "attendance_summaries",
        ["import_batch_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_attendance_summaries_import_batch_id",
        table_name="attendance_summaries",
    )
    op.drop_index(
        "ix_attendance_summaries_student_id",
        table_name="attendance_summaries",
    )
    op.drop_table("attendance_summaries")
