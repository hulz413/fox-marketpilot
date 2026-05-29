"""create research tasks

Revision ID: 20260529_0001
Revises:
Create Date: 2026-05-29 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("brief", sa.String(length=2000), nullable=False),
        sa.Column("budget", sa.String(length=120), nullable=True),
        sa.Column("target_channels", sa.JSON(), nullable=False),
        sa.Column("preferred_categories", sa.JSON(), nullable=False),
        sa.Column("excluded_categories", sa.JSON(), nullable=False),
        sa.Column("target_audience", sa.String(length=240), nullable=True),
        sa.Column("expected_profit", sa.String(length=120), nullable=True),
        sa.Column("supply_preferences", sa.JSON(), nullable=False),
        sa.Column("constraints", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_stage", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=120), nullable=True),
        sa.Column("trace_id", sa.String(length=120), nullable=True),
        sa.Column("failure_reason", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_research_tasks_status",
        "research_tasks",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_research_tasks_created_at",
        "research_tasks",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_tasks_deleted_at",
        "research_tasks",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_tasks_deleted_at_created_at",
        "research_tasks",
        ["deleted_at", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_research_tasks_deleted_at_created_at", table_name="research_tasks")
    op.drop_index("ix_research_tasks_deleted_at", table_name="research_tasks")
    op.drop_index("ix_research_tasks_created_at", table_name="research_tasks")
    op.drop_index("ix_research_tasks_status", table_name="research_tasks")
    op.drop_table("research_tasks")
