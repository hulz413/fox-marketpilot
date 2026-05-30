"""rename legacy demand insight tables

Revision ID: 20260530_0007
Revises: 20260530_0006
Create Date: 2026-05-30 21:15:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260530_0007"
down_revision: Union[str, None] = "20260530_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGACY_INSIGHTS_TABLE = "opportunity_demand_insights"
LEGACY_SOURCES_TABLE = "opportunity_demand_insight_sources"
INSIGHTS_TABLE = "demand_insights"
SOURCES_TABLE = "demand_insight_sources"

def table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def rename_index_if_needed(
    inspector: sa.Inspector,
    dialect_name: str,
    table_name: str,
    old_name: str,
    new_name: str,
) -> None:
    if not index_exists(inspector, table_name, old_name):
        return

    if dialect_name == "postgresql":
        op.execute(sa.text(f'ALTER INDEX "{old_name}" RENAME TO "{new_name}"'))
        return

    # SQLite cannot rename indexes consistently across supported versions.
    # Index names are not part of runtime behavior, so non-Postgres databases can
    # safely leave legacy names in place after the compatibility table rename.


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    has_legacy_insights = table_exists(inspector, LEGACY_INSIGHTS_TABLE)
    has_legacy_sources = table_exists(inspector, LEGACY_SOURCES_TABLE)
    has_new_insights = table_exists(inspector, INSIGHTS_TABLE)
    has_new_sources = table_exists(inspector, SOURCES_TABLE)

    if has_legacy_insights and not has_new_insights:
        op.rename_table(LEGACY_INSIGHTS_TABLE, INSIGHTS_TABLE)
        has_new_insights = True

    if has_legacy_sources and not has_new_sources:
        op.rename_table(LEGACY_SOURCES_TABLE, SOURCES_TABLE)
        has_new_sources = True

    inspector = sa.inspect(bind)
    dialect_name = bind.dialect.name

    if has_new_insights:
        rename_index_if_needed(
            inspector,
            dialect_name,
            INSIGHTS_TABLE,
            "ix_opportunity_demand_insights_task_deleted_at",
            "ix_demand_insights_task_deleted_at",
        )
        rename_index_if_needed(
            inspector,
            dialect_name,
            INSIGHTS_TABLE,
            "ix_opportunity_demand_insights_opportunity_deleted_at",
            "ix_demand_insights_opportunity_deleted_at",
        )
        rename_index_if_needed(
            inspector,
            dialect_name,
            INSIGHTS_TABLE,
            "ix_opportunity_demand_insights_deleted_at",
            "ix_demand_insights_deleted_at",
        )

    if has_new_sources:
        rename_index_if_needed(
            inspector,
            dialect_name,
            SOURCES_TABLE,
            "ix_opportunity_demand_insight_sources_insight_deleted_at",
            "ix_demand_insight_sources_insight_deleted_at",
        )
        rename_index_if_needed(
            inspector,
            dialect_name,
            SOURCES_TABLE,
            "ix_opportunity_demand_insight_sources_source_deleted_at",
            "ix_demand_insight_sources_source_deleted_at",
        )
        rename_index_if_needed(
            inspector,
            dialect_name,
            SOURCES_TABLE,
            "ix_opportunity_demand_insight_sources_deleted_at",
            "ix_demand_insight_sources_deleted_at",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if table_exists(inspector, SOURCES_TABLE) and not table_exists(
        inspector,
        LEGACY_SOURCES_TABLE,
    ):
        op.rename_table(SOURCES_TABLE, LEGACY_SOURCES_TABLE)

    if table_exists(inspector, INSIGHTS_TABLE) and not table_exists(
        inspector,
        LEGACY_INSIGHTS_TABLE,
    ):
        op.rename_table(INSIGHTS_TABLE, LEGACY_INSIGHTS_TABLE)
