"""create validation budgets

Revision ID: 20260531_0009
Revises: 20260530_0008
Create Date: 2026-05-31 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260531_0009"
down_revision: Union[str, None] = "20260530_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "validation_budgets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("estimated_unit_cost", sa.String(length=160), nullable=False),
        sa.Column("estimated_selling_price", sa.String(length=160), nullable=False),
        sa.Column("rough_gross_margin", sa.String(length=160), nullable=False),
        sa.Column("first_batch_quantity", sa.String(length=160), nullable=False),
        sa.Column("first_batch_budget", sa.String(length=160), nullable=False),
        sa.Column("key_assumptions", sa.JSON(), nullable=False),
        sa.Column("calculation_note", sa.String(length=1000), nullable=False),
        sa.Column("estimate_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"]),
        sa.ForeignKeyConstraint(["research_task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_validation_budgets_task_deleted_at",
        "validation_budgets",
        ["research_task_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_validation_budgets_opportunity_deleted_at",
        "validation_budgets",
        ["opportunity_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_validation_budgets_deleted_at",
        "validation_budgets",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_validation_budgets_deleted_at",
        table_name="validation_budgets",
    )
    op.drop_index(
        "ix_validation_budgets_opportunity_deleted_at",
        table_name="validation_budgets",
    )
    op.drop_index(
        "ix_validation_budgets_task_deleted_at",
        table_name="validation_budgets",
    )
    op.drop_table("validation_budgets")
