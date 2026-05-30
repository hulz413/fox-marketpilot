"""create demand insights

Revision ID: 20260530_0005
Revises: 20260530_0004
Create Date: 2026-05-30 13:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260530_0005"
down_revision: Union[str, None] = "20260530_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunity_demand_insights",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.String(length=1200), nullable=False),
        sa.Column("audience_profile", sa.String(length=800), nullable=False),
        sa.Column("use_cases", sa.JSON(), nullable=False),
        sa.Column("purchase_motivations", sa.JSON(), nullable=False),
        sa.Column("content_angles", sa.JSON(), nullable=False),
        sa.Column("trend_signals", sa.JSON(), nullable=False),
        sa.Column("seasonality_notes", sa.String(length=800), nullable=False),
        sa.Column("source_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"]),
        sa.ForeignKeyConstraint(["research_task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_demand_insights_task_deleted_at",
        "opportunity_demand_insights",
        ["research_task_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_demand_insights_opportunity_deleted_at",
        "opportunity_demand_insights",
        ["opportunity_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_demand_insights_deleted_at",
        "opportunity_demand_insights",
        ["deleted_at"],
        unique=False,
    )

    op.create_table(
        "opportunity_demand_insight_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("demand_insight_id", sa.Integer(), nullable=False),
        sa.Column("research_source_id", sa.Integer(), nullable=False),
        sa.Column("relevance_note", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["demand_insight_id"],
            ["opportunity_demand_insights.id"],
        ),
        sa.ForeignKeyConstraint(["research_source_id"], ["research_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_demand_insight_sources_insight_deleted_at",
        "opportunity_demand_insight_sources",
        ["demand_insight_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_demand_insight_sources_source_deleted_at",
        "opportunity_demand_insight_sources",
        ["research_source_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_demand_insight_sources_deleted_at",
        "opportunity_demand_insight_sources",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_demand_insight_sources_deleted_at",
        table_name="opportunity_demand_insight_sources",
    )
    op.drop_index(
        "ix_demand_insight_sources_source_deleted_at",
        table_name="opportunity_demand_insight_sources",
    )
    op.drop_index(
        "ix_demand_insight_sources_insight_deleted_at",
        table_name="opportunity_demand_insight_sources",
    )
    op.drop_table("opportunity_demand_insight_sources")
    op.drop_index(
        "ix_demand_insights_deleted_at",
        table_name="opportunity_demand_insights",
    )
    op.drop_index(
        "ix_demand_insights_opportunity_deleted_at",
        table_name="opportunity_demand_insights",
    )
    op.drop_index(
        "ix_demand_insights_task_deleted_at",
        table_name="opportunity_demand_insights",
    )
    op.drop_table("opportunity_demand_insights")
