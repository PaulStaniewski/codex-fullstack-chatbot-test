"""add conversation mode

Revision ID: 0002_add_conversation_mode
Revises: 0001_create_chatbot_tables
Create Date: 2026-04-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_add_conversation_mode"
down_revision: Union[str, None] = "0001_create_chatbot_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("mode", sa.String(length=20), server_default="chat", nullable=False),
    )
    op.alter_column("conversations", "mode", server_default=None)


def downgrade() -> None:
    op.drop_column("conversations", "mode")
