"""create opportunities

Revision ID: 20260529_0002
Revises: 20260529_0001
Create Date: 2026-05-29 00:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0002"
down_revision: Union[str, None] = "20260529_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("product_direction", sa.String(length=240), nullable=False),
        sa.Column("target_audience", sa.String(length=240), nullable=False),
        sa.Column("recommendation_reason", sa.String(length=1000), nullable=False),
        sa.Column("suitable_channels", sa.JSON(), nullable=False),
        sa.Column("price_band", sa.String(length=120), nullable=False),
        sa.Column("rough_margin", sa.String(length=120), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("priority_label", sa.String(length=120), nullable=False),
        sa.Column("next_step_summary", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["research_task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_opportunities_research_task_id_rank",
        "opportunities",
        ["research_task_id", "rank"],
        unique=False,
    )
    op.create_index(
        "ix_opportunities_deleted_at",
        "opportunities",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_opportunities_research_task_id_deleted_at",
        "opportunities",
        ["research_task_id", "deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunities_research_task_id_deleted_at",
        table_name="opportunities",
    )
    op.drop_index("ix_opportunities_deleted_at", table_name="opportunities")
    op.drop_index("ix_opportunities_research_task_id_rank", table_name="opportunities")
    op.drop_table("opportunities")
