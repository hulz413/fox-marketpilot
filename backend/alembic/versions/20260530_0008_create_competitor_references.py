"""create competitor references

Revision ID: 20260530_0008
Revises: 20260530_0007
Create Date: 2026-05-30 22:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260530_0008"
down_revision: Union[str, None] = "20260530_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "competitor_references",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("reference_name", sa.String(length=200), nullable=False),
        sa.Column("reference_market", sa.String(length=240), nullable=False),
        sa.Column("price_range", sa.String(length=160), nullable=False),
        sa.Column("common_selling_points", sa.JSON(), nullable=False),
        sa.Column("homogenization_level", sa.String(length=32), nullable=False),
        sa.Column("differentiation_angles", sa.JSON(), nullable=False),
        sa.Column("reference_note", sa.String(length=1000), nullable=False),
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
        "ix_competitor_references_task_deleted_at",
        "competitor_references",
        ["research_task_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_competitor_references_opportunity_rank",
        "competitor_references",
        ["opportunity_id", "rank"],
        unique=False,
    )
    op.create_index(
        "ix_competitor_references_opportunity_deleted_at",
        "competitor_references",
        ["opportunity_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_competitor_references_deleted_at",
        "competitor_references",
        ["deleted_at"],
        unique=False,
    )

    op.create_table(
        "competitor_reference_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("competitor_reference_id", sa.Integer(), nullable=False),
        sa.Column("research_source_id", sa.Integer(), nullable=False),
        sa.Column("relevance_note", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["competitor_reference_id"],
            ["competitor_references.id"],
        ),
        sa.ForeignKeyConstraint(["research_source_id"], ["research_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_competitor_reference_sources_reference_deleted_at",
        "competitor_reference_sources",
        ["competitor_reference_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_competitor_reference_sources_source_deleted_at",
        "competitor_reference_sources",
        ["research_source_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_competitor_reference_sources_deleted_at",
        "competitor_reference_sources",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_competitor_reference_sources_deleted_at",
        table_name="competitor_reference_sources",
    )
    op.drop_index(
        "ix_competitor_reference_sources_source_deleted_at",
        table_name="competitor_reference_sources",
    )
    op.drop_index(
        "ix_competitor_reference_sources_reference_deleted_at",
        table_name="competitor_reference_sources",
    )
    op.drop_table("competitor_reference_sources")
    op.drop_index(
        "ix_competitor_references_deleted_at",
        table_name="competitor_references",
    )
    op.drop_index(
        "ix_competitor_references_opportunity_deleted_at",
        table_name="competitor_references",
    )
    op.drop_index(
        "ix_competitor_references_opportunity_rank",
        table_name="competitor_references",
    )
    op.drop_index(
        "ix_competitor_references_task_deleted_at",
        table_name="competitor_references",
    )
    op.drop_table("competitor_references")
