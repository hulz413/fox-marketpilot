"""create supply candidates

Revision ID: 20260530_0006
Revises: 20260530_0005
Create Date: 2026-05-30 14:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260530_0006"
down_revision: Union[str, None] = "20260530_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "supply_candidates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("candidate_name", sa.String(length=200), nullable=False),
        sa.Column("supply_market", sa.String(length=240), nullable=False),
        sa.Column("search_keywords", sa.JSON(), nullable=False),
        sa.Column("price_range", sa.String(length=160), nullable=False),
        sa.Column("minimum_order_quantity", sa.String(length=240), nullable=False),
        sa.Column("specification_notes", sa.JSON(), nullable=False),
        sa.Column("supplier_questions", sa.JSON(), nullable=False),
        sa.Column("recommendation_note", sa.String(length=1000), nullable=False),
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
        "ix_supply_candidates_task_deleted_at",
        "supply_candidates",
        ["research_task_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_supply_candidates_opportunity_rank",
        "supply_candidates",
        ["opportunity_id", "rank"],
        unique=False,
    )
    op.create_index(
        "ix_supply_candidates_opportunity_deleted_at",
        "supply_candidates",
        ["opportunity_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_supply_candidates_deleted_at",
        "supply_candidates",
        ["deleted_at"],
        unique=False,
    )

    op.create_table(
        "supply_candidate_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("supply_candidate_id", sa.Integer(), nullable=False),
        sa.Column("research_source_id", sa.Integer(), nullable=False),
        sa.Column("relevance_note", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["supply_candidate_id"],
            ["supply_candidates.id"],
        ),
        sa.ForeignKeyConstraint(["research_source_id"], ["research_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_supply_candidate_sources_candidate_deleted_at",
        "supply_candidate_sources",
        ["supply_candidate_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_supply_candidate_sources_source_deleted_at",
        "supply_candidate_sources",
        ["research_source_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_supply_candidate_sources_deleted_at",
        "supply_candidate_sources",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_supply_candidate_sources_deleted_at",
        table_name="supply_candidate_sources",
    )
    op.drop_index(
        "ix_supply_candidate_sources_source_deleted_at",
        table_name="supply_candidate_sources",
    )
    op.drop_index(
        "ix_supply_candidate_sources_candidate_deleted_at",
        table_name="supply_candidate_sources",
    )
    op.drop_table("supply_candidate_sources")
    op.drop_index(
        "ix_supply_candidates_deleted_at",
        table_name="supply_candidates",
    )
    op.drop_index(
        "ix_supply_candidates_opportunity_deleted_at",
        table_name="supply_candidates",
    )
    op.drop_index(
        "ix_supply_candidates_opportunity_rank",
        table_name="supply_candidates",
    )
    op.drop_index(
        "ix_supply_candidates_task_deleted_at",
        table_name="supply_candidates",
    )
    op.drop_table("supply_candidates")
