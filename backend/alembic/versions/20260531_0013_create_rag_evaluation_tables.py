"""create rag evaluation tables

Revision ID: 20260531_0013
Revises: 20260531_0012
Create Date: 2026-05-31 20:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260531_0013"
down_revision: Union[str, None] = "20260531_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_evaluation_cases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("question", sa.String(length=800), nullable=False),
        sa.Column("expected_source_types", sa.JSON(), nullable=False),
        sa.Column("expected_keywords", sa.JSON(), nullable=False),
        sa.Column("expected_claims", sa.JSON(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
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
        "ix_rag_evaluation_cases_category_deleted_at",
        "rag_evaluation_cases",
        ["category", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_evaluation_cases_enabled_deleted_at",
        "rag_evaluation_cases",
        ["enabled", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_evaluation_cases_deleted_at",
        "rag_evaluation_cases",
        ["deleted_at"],
        unique=False,
    )

    op.create_table(
        "rag_evaluation_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("run_id", sa.String(length=120), nullable=True),
        sa.Column("trace_id", sa.String(length=120), nullable=True),
        sa.Column("trace_url", sa.String(length=500), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("summary_metrics", sa.JSON(), nullable=False),
        sa.Column("case_total", sa.Integer(), nullable=False),
        sa.Column("case_completed_count", sa.Integer(), nullable=False),
        sa.Column("case_failed_count", sa.Integer(), nullable=False),
        sa.Column("case_skipped_count", sa.Integer(), nullable=False),
        sa.Column("average_hit_rate", sa.Float(), nullable=False),
        sa.Column("average_recall", sa.Float(), nullable=False),
        sa.Column("average_precision", sa.Float(), nullable=False),
        sa.Column("average_mrr", sa.Float(), nullable=False),
        sa.Column("average_ndcg", sa.Float(), nullable=False),
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
        "ix_rag_evaluation_runs_task_deleted_at",
        "rag_evaluation_runs",
        ["research_task_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_evaluation_runs_status_deleted_at",
        "rag_evaluation_runs",
        ["status", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_evaluation_runs_deleted_at",
        "rag_evaluation_runs",
        ["deleted_at"],
        unique=False,
    )

    op.create_table(
        "rag_evaluation_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("evaluation_run_id", sa.Integer(), nullable=False),
        sa.Column("evaluation_case_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("question", sa.String(length=800), nullable=False),
        sa.Column("case_snapshot", sa.JSON(), nullable=False),
        sa.Column("retrieval_query", sa.String(length=1200), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("retrieval_status", sa.String(length=32), nullable=False),
        sa.Column("retrieved_evidence", sa.JSON(), nullable=False),
        sa.Column("relevant_count", sa.Integer(), nullable=False),
        sa.Column("expected_count", sa.Integer(), nullable=False),
        sa.Column("hit_rate", sa.Float(), nullable=False),
        sa.Column("recall", sa.Float(), nullable=False),
        sa.Column("precision", sa.Float(), nullable=False),
        sa.Column("mrr", sa.Float(), nullable=False),
        sa.Column("ndcg", sa.Float(), nullable=False),
        sa.Column("scoring_notes", sa.Text(), nullable=False),
        sa.Column("error_summary", sa.String(length=1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["evaluation_case_id"],
            ["rag_evaluation_cases.id"],
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            ["rag_evaluation_runs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_rag_evaluation_results_run_deleted_at",
        "rag_evaluation_results",
        ["evaluation_run_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_evaluation_results_case_deleted_at",
        "rag_evaluation_results",
        ["evaluation_case_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_evaluation_results_status_deleted_at",
        "rag_evaluation_results",
        ["status", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_rag_evaluation_results_deleted_at",
        "rag_evaluation_results",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rag_evaluation_results_deleted_at",
        table_name="rag_evaluation_results",
    )
    op.drop_index(
        "ix_rag_evaluation_results_status_deleted_at",
        table_name="rag_evaluation_results",
    )
    op.drop_index(
        "ix_rag_evaluation_results_case_deleted_at",
        table_name="rag_evaluation_results",
    )
    op.drop_index(
        "ix_rag_evaluation_results_run_deleted_at",
        table_name="rag_evaluation_results",
    )
    op.drop_table("rag_evaluation_results")

    op.drop_index(
        "ix_rag_evaluation_runs_deleted_at",
        table_name="rag_evaluation_runs",
    )
    op.drop_index(
        "ix_rag_evaluation_runs_status_deleted_at",
        table_name="rag_evaluation_runs",
    )
    op.drop_index(
        "ix_rag_evaluation_runs_task_deleted_at",
        table_name="rag_evaluation_runs",
    )
    op.drop_table("rag_evaluation_runs")

    op.drop_index(
        "ix_rag_evaluation_cases_deleted_at",
        table_name="rag_evaluation_cases",
    )
    op.drop_index(
        "ix_rag_evaluation_cases_enabled_deleted_at",
        table_name="rag_evaluation_cases",
    )
    op.drop_index(
        "ix_rag_evaluation_cases_category_deleted_at",
        table_name="rag_evaluation_cases",
    )
    op.drop_table("rag_evaluation_cases")
