"""add lesson step progress

Revision ID: 0010_lesson_step_progress
Revises: 0009_add_practice_attempt_number
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "0010_lesson_step_progress"
down_revision: Union[str, None] = "0009_add_practice_attempt_number"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.create_table(
        "lesson_step_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.String(length=120), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(length=50), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "lesson_id",
            "step_index",
            name="uq_lesson_step_progress_user_lesson_step",
        ),
    )
    op.create_index(
        op.f("ix_lesson_step_progress_id"),
        "lesson_step_progress",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lesson_step_progress_lesson_id"),
        "lesson_step_progress",
        ["lesson_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_lesson_step_progress_lesson_id"), table_name="lesson_step_progress")
    op.drop_index(op.f("ix_lesson_step_progress_id"), table_name="lesson_step_progress")
    op.drop_table("lesson_step_progress")
