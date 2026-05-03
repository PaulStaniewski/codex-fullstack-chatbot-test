"""add ai usage records

Revision ID: 0014_add_ai_usage_records
Revises: 0013_add_stream_tokens
Create Date: 2026-05-03 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "0014_add_ai_usage_records"
down_revision: Union[str, None] = "0013_add_stream_tokens"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("feature", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("total_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, default=0.0),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_usage_records_created_at"), "ai_usage_records", ["created_at"], unique=False)
    op.create_index(op.f("ix_ai_usage_records_feature"), "ai_usage_records", ["feature"], unique=False)
    op.create_index(op.f("ix_ai_usage_records_id"), "ai_usage_records", ["id"], unique=False)
    op.create_index(op.f("ix_ai_usage_records_model"), "ai_usage_records", ["model"], unique=False)
    op.create_index(op.f("ix_ai_usage_records_request_id"), "ai_usage_records", ["request_id"], unique=False)
    op.create_index(op.f("ix_ai_usage_records_user_id"), "ai_usage_records", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_usage_records_user_id"), table_name="ai_usage_records")
    op.drop_index(op.f("ix_ai_usage_records_request_id"), table_name="ai_usage_records")
    op.drop_index(op.f("ix_ai_usage_records_model"), table_name="ai_usage_records")
    op.drop_index(op.f("ix_ai_usage_records_id"), table_name="ai_usage_records")
    op.drop_index(op.f("ix_ai_usage_records_feature"), table_name="ai_usage_records")
    op.drop_index(op.f("ix_ai_usage_records_created_at"), table_name="ai_usage_records")
    op.drop_table("ai_usage_records")
