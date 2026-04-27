"""add practice submission score metadata

Revision ID: 0008_practice_score
Revises: 0007_add_practice_submissions
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "0008_practice_score"
down_revision: Union[str, None] = "0007_add_practice_submissions"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.add_column("practice_submissions", sa.Column("score", sa.Integer(), nullable=True))
    op.add_column("practice_submissions", sa.Column("strengths", sa.JSON(), nullable=True))
    op.add_column("practice_submissions", sa.Column("improvements", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("practice_submissions", "improvements")
    op.drop_column("practice_submissions", "strengths")
    op.drop_column("practice_submissions", "score")