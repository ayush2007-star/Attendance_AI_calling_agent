"""add class scopes

Revision ID: c2e8a1d4f907
Revises: b7f4d2a8c901
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2e8a1d4f907"
down_revision: Union[str, Sequence[str], None] = "b7f4d2a8c901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_SCOPE_ID = "20000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.add_column(
        "classes",
        sa.Column("scope_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_classes_scope_id",
        "classes",
        ["scope_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_classes_scope_id_scopes",
        "classes",
        "scopes",
        ["scope_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute(
        sa.text(
            """
            INSERT INTO scopes (id, scope_type, scope_value)
            VALUES (CAST(:scope_id AS uuid), 'college', 'default')
            ON CONFLICT (scope_type, scope_value) DO NOTHING
            """
        ).bindparams(scope_id=DEFAULT_SCOPE_ID)
    )

    op.execute(
        sa.text(
            """
            INSERT INTO user_scopes (user_id, scope_id)
            SELECT u.id, s.id
            FROM users AS u
            CROSS JOIN scopes AS s
            WHERE s.scope_type = 'college'
              AND s.scope_value = 'default'
            ON CONFLICT DO NOTHING
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE classes
            SET scope_id = s.id
            FROM scopes AS s
            WHERE s.scope_type = 'college'
              AND s.scope_value = 'default'
              AND classes.scope_id IS NULL
            """
        )
    )

    op.alter_column(
        "classes",
        "scope_id",
        existing_type=sa.UUID(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_classes_scope_id_scopes",
        "classes",
        type_="foreignkey",
    )
    op.drop_index("ix_classes_scope_id", table_name="classes")
    op.drop_column("classes", "scope_id")
    op.execute(
        sa.text(
            """
            DELETE FROM user_scopes
            WHERE scope_id IN (
                SELECT id FROM scopes
                WHERE scope_type = 'college'
                  AND scope_value = 'default'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM scopes
            WHERE scope_type = 'college'
              AND scope_value = 'default'
            """
        )
    )
