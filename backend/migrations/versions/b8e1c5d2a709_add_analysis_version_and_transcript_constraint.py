"""add analysis version and transcript constraint

Revision ID: b8e1c5d2a709
Revises: a7d2e9c4f108
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8e1c5d2a709"
down_revision: Union[str, Sequence[str], None] = "a7d2e9c4f108"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_analyses",
        sa.Column("model_version", sa.String(length=100), nullable=True),
    )
    op.create_unique_constraint(
        "uq_transcript_conversation_sequence",
        "transcripts",
        ["conversation_id", "sequence_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_transcript_conversation_sequence",
        "transcripts",
        type_="unique",
    )
    op.drop_column("ai_analyses", "model_version")
