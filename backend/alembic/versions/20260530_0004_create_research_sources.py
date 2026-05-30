"""create research sources

Revision ID: 20260530_0004
Revises: 20260529_0003
Create Date: 2026-05-30 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260530_0004"
down_revision: Union[str, None] = "20260529_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("summary", sa.String(length=1200), nullable=False),
        sa.Column("snippet", sa.String(length=1200), nullable=False),
        sa.Column("publisher", sa.String(length=200), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("query", sa.String(length=500), nullable=True),
        sa.Column("linked_claim", sa.String(length=1000), nullable=False),
        sa.Column("support_level", sa.String(length=32), nullable=False),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"]),
        sa.ForeignKeyConstraint(["research_task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_research_sources_research_task_id_deleted_at",
        "research_sources",
        ["research_task_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_sources_opportunity_id_deleted_at",
        "research_sources",
        ["opportunity_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_sources_task_type_deleted_at",
        "research_sources",
        ["research_task_id", "source_type", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_sources_deleted_at",
        "research_sources",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_research_sources_deleted_at", table_name="research_sources")
    op.drop_index(
        "ix_research_sources_task_type_deleted_at",
        table_name="research_sources",
    )
    op.drop_index(
        "ix_research_sources_opportunity_id_deleted_at",
        table_name="research_sources",
    )
    op.drop_index(
        "ix_research_sources_research_task_id_deleted_at",
        table_name="research_sources",
    )
    op.drop_table("research_sources")
