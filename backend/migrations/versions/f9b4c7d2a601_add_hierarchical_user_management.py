"""Add scoped user management and temporary password setup.

Revision ID: f9b4c7d2a601
Revises: e3a8c1d5f907
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9b4c7d2a601"
down_revision: Union[str, Sequence[str], None] = "a2d6f9c4e107"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = {
    "users.read": "70000000-0000-0000-0000-000000000001",
    "users.manage": "70000000-0000-0000-0000-000000000002",
    "scopes.read": "70000000-0000-0000-0000-000000000003",
    "scopes.manage": "70000000-0000-0000-0000-000000000004",
}

ROLE_PERMISSIONS = {
    "SUPER_ADMIN": set(PERMISSIONS),
    "ADMIN": {"users.read", "users.manage", "scopes.read"},
}


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )

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

    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id = (SELECT id FROM roles WHERE name = 'STAFF')
              AND permission_id = (
                  SELECT id FROM permissions WHERE name = 'campaign.create'
              )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles AS r, permissions AS p
            WHERE r.name = 'STAFF' AND p.name = 'campaign.create'
            ON CONFLICT DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions
                WHERE name IN ('users.read', 'users.manage', 'scopes.read', 'scopes.manage')
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name IN ('users.read', 'users.manage', 'scopes.read', 'scopes.manage')
            """
        )
    )
    op.drop_column("users", "must_change_password")
