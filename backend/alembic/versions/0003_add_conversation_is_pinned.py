"""add conversation is_pinned

Revision ID: 0003_add_conversation_is_pinned
Revises: 0002_add_conversation_mode
Create Date: 2026-04-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_add_conversation_is_pinned"
down_revision: Union[str, None] = "0002_add_conversation_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.alter_column("conversations", "is_pinned", server_default=None)


def downgrade() -> None:
    op.drop_column("conversations", "is_pinned")
