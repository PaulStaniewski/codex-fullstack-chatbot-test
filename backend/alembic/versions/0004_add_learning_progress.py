"""add learning progress

Revision ID: 0004_add_learning_progress
Revises: 0003_add_conversation_is_pinned
Create Date: 2026-04-26 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "0004_add_learning_progress"
down_revision: Union[str, None] = "0003_add_conversation_is_pinned"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.create_table(
        "user_progress",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sessions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("messages_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_answers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("incorrect_answers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_streak_date", sa.Date(), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("icon", sa.String(length=20), nullable=False),
        sa.Column("condition_type", sa.String(length=50), nullable=False),
        sa.Column("condition_value", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_achievements_id"), "achievements", ["id"], unique=False)
    op.create_table(
        "user_achievements",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("achievement_id", sa.Integer(), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["achievement_id"], ["achievements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "achievement_id"),
    )


def downgrade() -> None:
    op.drop_table("user_achievements")
    op.drop_index(op.f("ix_achievements_id"), table_name="achievements")
    op.drop_table("achievements")
    op.drop_table("user_progress")
