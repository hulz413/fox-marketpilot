"""create generation evaluation tables

Revision ID: 20260607_0016
Revises: 20260601_0015
Create Date: 2026-06-07 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260607_0016"
down_revision: Union[str, None] = "20260601_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generation_evaluation_cases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=48), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("input_constraints", sa.JSON(), nullable=False),
        sa.Column("expected_signals", sa.JSON(), nullable=False),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("grading_rubric", sa.String(length=1200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_generation_evaluation_cases_category_deleted_at",
        "generation_evaluation_cases",
        ["category", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_generation_evaluation_cases_enabled_deleted_at",
        "generation_evaluation_cases",
        ["enabled", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_generation_evaluation_cases_deleted_at",
        "generation_evaluation_cases",
        ["deleted_at"],
        unique=False,
    )

    op.create_table(
        "generation_evaluation_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("overall_status", sa.String(length=32), nullable=False),
        sa.Column("research_run_id", sa.String(length=120), nullable=True),
        sa.Column("trace_id", sa.String(length=120), nullable=True),
        sa.Column("trace_url", sa.String(length=500), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("summary_metrics", sa.JSON(), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("case_total", sa.Integer(), nullable=False),
        sa.Column("case_passed_count", sa.Integer(), nullable=False),
        sa.Column("case_warning_count", sa.Integer(), nullable=False),
        sa.Column("case_failed_count", sa.Integer(), nullable=False),
        sa.Column("case_skipped_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.String(length=1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["research_task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_generation_evaluation_runs_task_deleted_at",
        "generation_evaluation_runs",
        ["research_task_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_generation_evaluation_runs_task_run_deleted_at",
        "generation_evaluation_runs",
        ["research_task_id", "research_run_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_generation_evaluation_runs_status_deleted_at",
        "generation_evaluation_runs",
        ["status", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_generation_evaluation_runs_overall_deleted_at",
        "generation_evaluation_runs",
        ["overall_status", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_generation_evaluation_runs_deleted_at",
        "generation_evaluation_runs",
        ["deleted_at"],
        unique=False,
    )

    op.create_table(
        "generation_evaluation_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("evaluation_run_id", sa.Integer(), nullable=False),
        sa.Column("evaluation_case_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=48), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("case_snapshot", sa.JSON(), nullable=False),
        sa.Column("target_scope", sa.String(length=48), nullable=False),
        sa.Column("affected_opportunity_uuids", sa.JSON(), nullable=False),
        sa.Column("rubric_scores", sa.JSON(), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("scoring_notes", sa.Text(), nullable=False),
        sa.Column("error_summary", sa.String(length=1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["evaluation_case_id"],
            ["generation_evaluation_cases.id"],
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            ["generation_evaluation_runs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_generation_evaluation_results_run_deleted_at",
        "generation_evaluation_results",
        ["evaluation_run_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_generation_evaluation_results_case_deleted_at",
        "generation_evaluation_results",
        ["evaluation_case_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_generation_evaluation_results_status_deleted_at",
        "generation_evaluation_results",
        ["status", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_generation_evaluation_results_deleted_at",
        "generation_evaluation_results",
        ["deleted_at"],
        unique=False,
    )
    op.add_column(
        "research_quality_readiness_runs",
        sa.Column("generation_evaluation_run_uuid", sa.Uuid(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column(
        "research_quality_readiness_runs",
        "generation_evaluation_run_uuid",
    )
    op.drop_index(
        "ix_generation_evaluation_results_deleted_at",
        table_name="generation_evaluation_results",
    )
    op.drop_index(
        "ix_generation_evaluation_results_status_deleted_at",
        table_name="generation_evaluation_results",
    )
    op.drop_index(
        "ix_generation_evaluation_results_case_deleted_at",
        table_name="generation_evaluation_results",
    )
    op.drop_index(
        "ix_generation_evaluation_results_run_deleted_at",
        table_name="generation_evaluation_results",
    )
    op.drop_table("generation_evaluation_results")

    op.drop_index(
        "ix_generation_evaluation_runs_deleted_at",
        table_name="generation_evaluation_runs",
    )
    op.drop_index(
        "ix_generation_evaluation_runs_overall_deleted_at",
        table_name="generation_evaluation_runs",
    )
    op.drop_index(
        "ix_generation_evaluation_runs_status_deleted_at",
        table_name="generation_evaluation_runs",
    )
    op.drop_index(
        "ix_generation_evaluation_runs_task_run_deleted_at",
        table_name="generation_evaluation_runs",
    )
    op.drop_index(
        "ix_generation_evaluation_runs_task_deleted_at",
        table_name="generation_evaluation_runs",
    )
    op.drop_table("generation_evaluation_runs")

    op.drop_index(
        "ix_generation_evaluation_cases_deleted_at",
        table_name="generation_evaluation_cases",
    )
    op.drop_index(
        "ix_generation_evaluation_cases_enabled_deleted_at",
        table_name="generation_evaluation_cases",
    )
    op.drop_index(
        "ix_generation_evaluation_cases_category_deleted_at",
        table_name="generation_evaluation_cases",
    )
    op.drop_table("generation_evaluation_cases")
