"""add campaign target to calls

Revision ID: a7d2e9c4f108
Revises: f6a3d8c1e205
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7d2e9c4f108"
down_revision: Union[str, Sequence[str], None] = "f6a3d8c1e205"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "call_attempts",
        sa.Column("campaign_target_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_call_attempts_campaign_target_id",
        "call_attempts",
        ["campaign_target_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_call_attempts_campaign_target_id",
        "call_attempts",
        "campaign_targets",
        ["campaign_target_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column(
        "call_attempts",
        "absence_event_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "call_attempts",
        "absence_event_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
    op.drop_constraint(
        "fk_call_attempts_campaign_target_id",
        "call_attempts",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_call_attempts_campaign_target_id",
        table_name="call_attempts",
    )
    op.drop_column("call_attempts", "campaign_target_id")
