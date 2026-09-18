"""add leave permissions

Revision ID: a2d6f9c4e107
Revises: f4a9c2d7e108
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2d6f9c4e107"
down_revision: Union[str, Sequence[str], None] = "f4a9c2d7e108"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = {
    "leave.read": "60000000-0000-0000-0000-000000000001",
    "leave.create": "60000000-0000-0000-0000-000000000002",
    "leave.approve": "60000000-0000-0000-0000-000000000003",
    "leave.reject": "60000000-0000-0000-0000-000000000004",
}

ROLE_PERMISSIONS = {
    "SUPER_ADMIN": set(PERMISSIONS),
    "ADMIN": set(PERMISSIONS),
    "STAFF": {"leave.read", "leave.create"},
    "VIEWER": {"leave.read"},
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
                WHERE name IN ('leave.read', 'leave.create', 'leave.approve', 'leave.reject')
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name IN ('leave.read', 'leave.create', 'leave.approve', 'leave.reject')
            """
        )
    )
