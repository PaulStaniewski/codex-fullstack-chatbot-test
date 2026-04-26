"""add progress xp and level

Revision ID: 0005_add_progress_xp_level
Revises: 0004_add_learning_progress
Create Date: 2026-04-26 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005_add_progress_xp_level"
down_revision: Union[str, None] = "0004_add_learning_progress"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.add_column(
        "user_progress",
        sa.Column("xp_points", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_progress",
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("user_progress", "level")
    op.drop_column("user_progress", "xp_points")
