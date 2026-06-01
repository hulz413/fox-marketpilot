"""create research quality readiness runs

Revision ID: 20260601_0015
Revises: 20260531_0014
Create Date: 2026-06-01 09:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260601_0015"
down_revision: Union[str, None] = "20260531_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_quality_readiness_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("research_run_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("overall_status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("rag_evaluation_run_uuid", sa.Uuid(), nullable=True),
        sa.Column("trace_id", sa.String(length=120), nullable=True),
        sa.Column("trace_url", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["research_task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_research_quality_readiness_runs_task_deleted_at",
        "research_quality_readiness_runs",
        ["research_task_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_quality_readiness_runs_task_run_deleted_at",
        "research_quality_readiness_runs",
        ["research_task_id", "research_run_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_quality_readiness_runs_overall_deleted_at",
        "research_quality_readiness_runs",
        ["overall_status", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_quality_readiness_runs_deleted_at",
        "research_quality_readiness_runs",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_research_quality_readiness_runs_deleted_at",
        table_name="research_quality_readiness_runs",
    )
    op.drop_index(
        "ix_research_quality_readiness_runs_overall_deleted_at",
        table_name="research_quality_readiness_runs",
    )
    op.drop_index(
        "ix_research_quality_readiness_runs_task_run_deleted_at",
        table_name="research_quality_readiness_runs",
    )
    op.drop_index(
        "ix_research_quality_readiness_runs_task_deleted_at",
        table_name="research_quality_readiness_runs",
    )
    op.drop_table("research_quality_readiness_runs")
