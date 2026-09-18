"""add reports permission

Revision ID: e3a8c1d5f907
Revises: d1f7a3c9e602
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3a8c1d5f907"
down_revision: Union[str, Sequence[str], None] = "d1f7a3c9e602"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSION_ID = "50000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO permissions (id, name, description)
            VALUES (
                CAST(:id AS uuid),
                'reports.read',
                'Permission: reports.read'
            )
            ON CONFLICT (name) DO NOTHING
            """
        ).bindparams(id=PERMISSION_ID)
    )
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles AS r, permissions AS p
            WHERE r.name IN ('SUPER_ADMIN', 'ADMIN', 'STAFF', 'VIEWER')
              AND p.name = 'reports.read'
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id = (
                SELECT id FROM permissions WHERE name = 'reports.read'
            )
            """
        )
    )
    op.execute(
        sa.text("DELETE FROM permissions WHERE name = 'reports.read'")
    )
