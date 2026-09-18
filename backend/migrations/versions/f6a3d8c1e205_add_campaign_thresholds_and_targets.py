"""add campaign thresholds and targets

Revision ID: f6a3d8c1e205
Revises: e5c9b2f1a704
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a3d8c1e205"
down_revision: Union[str, Sequence[str], None] = "e5c9b2f1a704"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_THRESHOLD = "75"
DEFAULT_SETTING_ID = "30000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.add_column(
        "call_campaigns",
        sa.Column("attendance_period_start", sa.Date(), nullable=True),
    )
    op.add_column(
        "call_campaigns",
        sa.Column("attendance_period_end", sa.Date(), nullable=True),
    )
    op.add_column(
        "call_campaigns",
        sa.Column("threshold_used", sa.Numeric(5, 2), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE call_campaigns
            SET attendance_period_start = attendance_date,
                attendance_period_end = attendance_date,
                threshold_used = CAST(:threshold AS numeric)
            WHERE attendance_period_start IS NULL
               OR attendance_period_end IS NULL
               OR threshold_used IS NULL
            """
        ).bindparams(threshold=DEFAULT_THRESHOLD)
    )

    op.alter_column(
        "call_campaigns",
        "attendance_period_start",
        existing_type=sa.Date(),
        nullable=False,
    )
    op.alter_column(
        "call_campaigns",
        "attendance_period_end",
        existing_type=sa.Date(),
        nullable=False,
    )
    op.alter_column(
        "call_campaigns",
        "threshold_used",
        existing_type=sa.Numeric(5, 2),
        nullable=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO system_settings (id, key, value, description)
            VALUES (
                CAST(:setting_id AS uuid),
                'attendance_threshold_default',
                :threshold,
                'Default percentage threshold for campaign eligibility'
            )
            ON CONFLICT (key) DO NOTHING
            """
        ).bindparams(
            setting_id=DEFAULT_SETTING_ID,
            threshold=DEFAULT_THRESHOLD,
        )
    )

    op.create_table(
        "campaign_targets",
        sa.Column("campaign_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("attendance_percentage_used", sa.Numeric(5, 2), nullable=False),
        sa.Column("threshold_used", sa.Numeric(5, 2), nullable=False),
        sa.Column("eligibility_reason", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("selected_phone_number", sa.String(length=30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["call_campaigns.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["parents.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "student_id",
            "parent_id",
            name="uq_campaign_target_student_parent",
        ),
    )
    op.create_index(
        "ix_campaign_targets_campaign_id",
        "campaign_targets",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_campaign_targets_student_id",
        "campaign_targets",
        ["student_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_campaign_targets_student_id",
        table_name="campaign_targets",
    )
    op.drop_index(
        "ix_campaign_targets_campaign_id",
        table_name="campaign_targets",
    )
    op.drop_table("campaign_targets")
    op.drop_column("call_campaigns", "threshold_used")
    op.drop_column("call_campaigns", "attendance_period_end")
    op.drop_column("call_campaigns", "attendance_period_start")
