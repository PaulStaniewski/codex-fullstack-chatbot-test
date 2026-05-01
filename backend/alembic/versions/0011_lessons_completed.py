"""add lessons completed progress

Revision ID: 0011_lessons_completed
Revises: 0010_lesson_step_progress
Create Date: 2026-04-29 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "0011_lessons_completed"
down_revision: Union[str, None] = "0010_lesson_step_progress"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.add_column(
        "user_progress",
        sa.Column("lessons_completed", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("user_progress", "lessons_completed", server_default=None)


def downgrade() -> None:
    op.drop_column("user_progress", "lessons_completed")
