"""add stream tokens

Revision ID: 0013_add_stream_tokens
Revises: 0012_add_refresh_sessions
Create Date: 2026-05-03 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "0013_add_stream_tokens"
down_revision: Union[str, None] = "0012_add_refresh_sessions"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.create_table(
        "stream_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stream_tokens_token_hash"), "stream_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_stream_tokens_user_id"), "stream_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_stream_tokens_user_id"), table_name="stream_tokens")
    op.drop_index(op.f("ix_stream_tokens_token_hash"), table_name="stream_tokens")
    op.drop_table("stream_tokens")
