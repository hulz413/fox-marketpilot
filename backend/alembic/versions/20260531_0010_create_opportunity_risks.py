"""create opportunity risks

Revision ID: 20260531_0010
Revises: 20260531_0009
Create Date: 2026-05-31 11:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260531_0010"
down_revision: Union[str, None] = "20260531_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunity_risks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("overall_risk_level", sa.String(length=32), nullable=False),
        sa.Column("risk_summary", sa.String(length=1000), nullable=False),
        sa.Column("quality_risk", sa.String(length=1000), nullable=False),
        sa.Column("fulfillment_risk", sa.String(length=1000), nullable=False),
        sa.Column("after_sales_risk", sa.String(length=1000), nullable=False),
        sa.Column("compliance_risk", sa.String(length=1000), nullable=False),
        sa.Column("inventory_risk", sa.String(length=1000), nullable=False),
        sa.Column("competition_risk", sa.String(length=1000), nullable=False),
        sa.Column("platform_risk", sa.String(length=1000), nullable=False),
        sa.Column("risk_triggers", sa.JSON(), nullable=False),
        sa.Column("mitigation_suggestions", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"]),
        sa.ForeignKeyConstraint(["research_task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_opportunity_risks_task_deleted_at",
        "opportunity_risks",
        ["research_task_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_opportunity_risks_opportunity_deleted_at",
        "opportunity_risks",
        ["opportunity_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_opportunity_risks_deleted_at",
        "opportunity_risks",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_opportunity_risks_deleted_at",
        table_name="opportunity_risks",
    )
    op.drop_index(
        "ix_opportunity_risks_opportunity_deleted_at",
        table_name="opportunity_risks",
    )
    op.drop_index(
        "ix_opportunity_risks_task_deleted_at",
        table_name="opportunity_risks",
    )
    op.drop_table("opportunity_risks")
