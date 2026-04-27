"""add practice submissions

Revision ID: 0007_add_practice_submissions
Revises: 0006_add_lesson_progress
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "0007_add_practice_submissions"
down_revision: Union[str, None] = "0006_add_lesson_progress"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.create_table(
        "practice_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.String(length=120), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_practice_submissions_id"), "practice_submissions", ["id"], unique=False)
    op.create_index(
        op.f("ix_practice_submissions_lesson_id"),
        "practice_submissions",
        ["lesson_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_practice_submissions_lesson_id"), table_name="practice_submissions")
    op.drop_index(op.f("ix_practice_submissions_id"), table_name="practice_submissions")
    op.drop_table("practice_submissions")
