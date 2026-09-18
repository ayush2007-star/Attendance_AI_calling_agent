"""add call and follow-up permissions

Revision ID: d1f7a3c9e602
Revises: c9f2a6d1e803
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1f7a3c9e602"
down_revision: Union[str, Sequence[str], None] = "c9f2a6d1e803"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = {
    "calls.read": "40000000-0000-0000-0000-000000000001",
    "calls.manage": "40000000-0000-0000-0000-000000000002",
    "followup.read": "40000000-0000-0000-0000-000000000003",
    "followup.manage": "40000000-0000-0000-0000-000000000004",
}

ROLE_PERMISSIONS = {
    "SUPER_ADMIN": set(PERMISSIONS),
    "ADMIN": set(PERMISSIONS),
    "STAFF": {
        "calls.read",
        "followup.read",
        "followup.manage",
    },
    "VIEWER": {
        "calls.read",
        "followup.read",
    },
}


def upgrade() -> None:
    for permission_name, permission_id in PERMISSIONS.items():
        op.execute(
            sa.text(
                """
                INSERT INTO permissions (id, name, description)
                VALUES (CAST(:id AS uuid), :name, :description)
                ON CONFLICT (name) DO NOTHING
                """
            ).bindparams(
                id=permission_id,
                name=permission_name,
                description=f"Permission: {permission_name}",
            )
        )

    for role_name, permission_names in ROLE_PERMISSIONS.items():
        for permission_name in permission_names:
            op.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT r.id, p.id
                    FROM roles AS r, permissions AS p
                    WHERE r.name = :role_name
                      AND p.name = :permission_name
                    ON CONFLICT DO NOTHING
                    """
                ).bindparams(
                    role_name=role_name,
                    permission_name=permission_name,
                )
            )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions
                WHERE name IN ('calls.read', 'calls.manage', 'followup.read', 'followup.manage')
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name IN ('calls.read', 'calls.manage', 'followup.read', 'followup.manage')
            """
        )
    )
