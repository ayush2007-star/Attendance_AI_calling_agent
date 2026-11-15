"""Add call consent and opt out fields for parents and campaign targets.

Revision ID: 0b4c8e1f2a33
Revises: f9b4c7d2a601
Create Date: 2026-11-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0b4c8e1f2a33"
down_revision: Union[str, Sequence[str], None] = "f9b4c7d2a601"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "parents",
        sa.Column(
            "call_consent",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )
    op.add_column(
        "parents",
        sa.Column(
            "call_opt_out",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "campaign_targets",
        sa.Column(
            "contact_authorized",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("campaign_targets", "contact_authorized")
    op.drop_column("parents", "call_opt_out")
    op.drop_column("parents", "call_consent")
