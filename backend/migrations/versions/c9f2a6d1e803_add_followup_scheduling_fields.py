"""add follow-up scheduling fields

Revision ID: c9f2a6d1e803
Revises: b8e1c5d2a709
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9f2a6d1e803"
down_revision: Union[str, Sequence[str], None] = "b8e1c5d2a709"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "followups",
        sa.Column("campaign_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "followups",
        sa.Column("campaign_target_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "followups",
        sa.Column("parent_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "followups",
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "followups",
        sa.Column(
            "timezone_name",
            sa.String(length=64),
            server_default="UTC",
            nullable=False,
        ),
    )
    op.add_column(
        "followups",
        sa.Column(
            "retry_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "followups",
        sa.Column("last_error", sa.String(length=500), nullable=True),
    )

    op.create_index("ix_followups_campaign_id", "followups", ["campaign_id"])
    op.create_index(
        "ix_followups_campaign_target_id",
        "followups",
        ["campaign_target_id"],
    )
    op.create_index("ix_followups_parent_id", "followups", ["parent_id"])
    op.create_index(
        "ix_followups_scheduled_for",
        "followups",
        ["scheduled_for"],
    )
    op.create_foreign_key(
        "fk_followups_campaign_id",
        "followups",
        "call_campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_followups_campaign_target_id",
        "followups",
        "campaign_targets",
        ["campaign_target_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_followups_parent_id",
        "followups",
        "parents",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_followups_parent_id", "followups", type_="foreignkey")
    op.drop_constraint(
        "fk_followups_campaign_target_id",
        "followups",
        type_="foreignkey",
    )
    op.drop_constraint("fk_followups_campaign_id", "followups", type_="foreignkey")
    op.drop_index("ix_followups_scheduled_for", table_name="followups")
    op.drop_index("ix_followups_parent_id", table_name="followups")
    op.drop_index("ix_followups_campaign_target_id", table_name="followups")
    op.drop_index("ix_followups_campaign_id", table_name="followups")
    op.drop_column("followups", "last_error")
    op.drop_column("followups", "retry_count")
    op.drop_column("followups", "timezone_name")
    op.drop_column("followups", "scheduled_for")
    op.drop_column("followups", "parent_id")
    op.drop_column("followups", "campaign_target_id")
    op.drop_column("followups", "campaign_id")
