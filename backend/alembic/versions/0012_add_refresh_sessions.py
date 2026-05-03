"""add refresh sessions

Revision ID: 0012_add_refresh_sessions
Revises: 0011_lessons_completed
Create Date: 2026-05-03 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "0012_add_refresh_sessions"
down_revision: Union[str, None] = "0011_lessons_completed"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_session_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_sessions_token_hash"), "refresh_sessions", ["token_hash"], unique=True)
    op.create_index(op.f("ix_refresh_sessions_user_id"), "refresh_sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_refresh_sessions_user_id"), table_name="refresh_sessions")
    op.drop_index(op.f("ix_refresh_sessions_token_hash"), table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
