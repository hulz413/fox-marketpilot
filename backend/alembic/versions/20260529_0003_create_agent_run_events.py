"""create agent run events

Revision ID: 20260529_0003
Revises: 20260529_0002
Create Date: 2026-05-29 00:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0003"
down_revision: Union[str, None] = "20260529_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "research_tasks",
        sa.Column("trace_url", sa.String(length=500), nullable=True),
    )
    op.create_table(
        "agent_run_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=120), nullable=False),
        sa.Column("trace_id", sa.String(length=120), nullable=True),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_summary", sa.String(length=1000), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["research_task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_agent_run_events_research_task_id_run_id",
        "agent_run_events",
        ["research_task_id", "run_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_run_events_run_id_stage",
        "agent_run_events",
        ["run_id", "stage"],
        unique=False,
    )
    op.create_index(
        "ix_agent_run_events_deleted_at",
        "agent_run_events",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_agent_run_events_research_task_id_deleted_at",
        "agent_run_events",
        ["research_task_id", "deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_run_events_research_task_id_deleted_at",
        table_name="agent_run_events",
    )
    op.drop_index("ix_agent_run_events_deleted_at", table_name="agent_run_events")
    op.drop_index("ix_agent_run_events_run_id_stage", table_name="agent_run_events")
    op.drop_index(
        "ix_agent_run_events_research_task_id_run_id",
        table_name="agent_run_events",
    )
    op.drop_table("agent_run_events")
    op.drop_column("research_tasks", "trace_url")
