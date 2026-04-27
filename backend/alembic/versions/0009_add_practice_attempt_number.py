"""add practice attempt number

Revision ID: 0009_add_practice_attempt_number
Revises: 0008_practice_score
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "0009_add_practice_attempt_number"
down_revision: Union[str, None] = "0008_practice_score"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.add_column(
        "practice_submissions",
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("practice_submissions", "attempt_number")
