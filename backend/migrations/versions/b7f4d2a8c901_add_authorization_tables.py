"""add authorization tables

Revision ID: b7f4d2a8c901
Revises: 668cfee1d9d3
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7f4d2a8c901"
down_revision: Union[str, Sequence[str], None] = "668cfee1d9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLE_IDS = {
    "SUPER_ADMIN": "00000000-0000-0000-0000-000000000001",
    "ADMIN": "00000000-0000-0000-0000-000000000002",
    "STAFF": "00000000-0000-0000-0000-000000000003",
    "VIEWER": "00000000-0000-0000-0000-000000000004",
}

PERMISSION_IDS = {
    "student.read": "10000000-0000-0000-0000-000000000001",
    "student.create": "10000000-0000-0000-0000-000000000002",
    "class.read": "10000000-0000-0000-0000-000000000003",
    "class.create": "10000000-0000-0000-0000-000000000004",
    "attendance.read": "10000000-0000-0000-0000-000000000005",
    "attendance.create": "10000000-0000-0000-0000-000000000006",
    "attendance.import": "10000000-0000-0000-0000-000000000007",
    "campaign.read": "10000000-0000-0000-0000-000000000008",
    "campaign.create": "10000000-0000-0000-0000-000000000009",
    "user.create": "10000000-0000-0000-0000-000000000010",
}


ROLE_PERMISSION_NAMES = {
    "SUPER_ADMIN": set(PERMISSION_IDS),
    "ADMIN": {
        "student.read",
        "student.create",
        "class.read",
        "class.create",
        "attendance.read",
        "attendance.create",
        "attendance.import",
        "campaign.read",
        "campaign.create",
        "user.create",
    },
    "STAFF": {
        "student.read",
        "class.read",
        "attendance.read",
        "attendance.create",
        "attendance.import",
        "campaign.read",
        "campaign.create",
    },
    "VIEWER": {
        "student.read",
        "class.read",
        "attendance.read",
        "campaign.read",
    },
}


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=False)

    op.create_table(
        "permissions",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        "ix_permissions_name",
        "permissions",
        ["name"],
        unique=False,
    )

    op.create_table(
        "scopes",
        sa.Column("scope_type", sa.String(length=50), nullable=False),
        sa.Column("scope_value", sa.String(length=150), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.ForeignKeyConstraint(["parent_id"], ["scopes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scope_type",
            "scope_value",
            name="uq_scope_type_value",
        ),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("permission_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    op.create_table(
        "user_scopes",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("scope_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["scope_id"], ["scopes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "scope_id"),
    )

    for role_name, role_id in ROLE_IDS.items():
        op.execute(
            sa.text(
                """
                INSERT INTO roles (id, name, description, is_system)
                VALUES (CAST(:id AS uuid), :name, :description, true)
                ON CONFLICT (name) DO NOTHING
                """
            ).bindparams(
                id=role_id,
                name=role_name,
                description=f"System role: {role_name}",
            )
        )

    for permission_name, permission_id in PERMISSION_IDS.items():
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

    for role_name, permission_names in ROLE_PERMISSION_NAMES.items():
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
            INSERT INTO user_roles (user_id, role_id)
            SELECT u.id, r.id
            FROM users AS u
            JOIN roles AS r ON r.name = upper(u.role)
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_table("user_scopes")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("scopes")
    op.drop_index("ix_permissions_name", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
