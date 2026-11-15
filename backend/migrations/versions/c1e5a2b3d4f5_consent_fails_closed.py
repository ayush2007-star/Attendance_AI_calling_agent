"""Enforce fail-closed defaults for guardian call consent and campaign target authorization.

Revision ID: c1e5a2b3d4f5
Revises: 0b4c8e1f2a33
Create Date: 2026-11-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1e5a2b3d4f5"
down_revision: Union[str, Sequence[str], None] = "0b4c8e1f2a33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Change server defaults to FALSE so new records fail closed
    op.alter_column(
        "parents",
        "call_consent",
        server_default=sa.false(),
    )
    op.alter_column(
        "campaign_targets",
        "contact_authorized",
        server_default=sa.false(),
    )

    # 2. Existing records must not automatically receive consent merely because
    # a previous migration assigned a default true value. Reset unverified consents to false.
    op.execute(
        sa.text(
            """
            UPDATE parents
            SET call_consent = false
            WHERE call_consent IS NULL OR call_consent = true;
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE campaign_targets
            SET contact_authorized = false;
            """
        )
    )


def downgrade() -> None:
    op.alter_column(
        "campaign_targets",
        "contact_authorized",
        server_default=sa.true(),
    )
    op.alter_column(
        "parents",
        "call_consent",
        server_default=sa.true(),
    )
