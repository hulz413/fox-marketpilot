"""create action plans

Revision ID: 20260531_0011
Revises: 20260531_0010
Create Date: 2026-05-31 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260531_0011"
down_revision: Union[str, None] = "20260531_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "action_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("validation_goal", sa.String(length=1000), nullable=False),
        sa.Column("first_batch_plan", sa.String(length=1000), nullable=False),
        sa.Column("product_validation_method", sa.String(length=1000), nullable=False),
        sa.Column("content_angles", sa.JSON(), nullable=False),
        sa.Column("title_suggestions", sa.JSON(), nullable=False),
        sa.Column("selling_point_suggestions", sa.JSON(), nullable=False),
        sa.Column("supplier_inquiry_script", sa.String(length=1200), nullable=False),
        sa.Column("prelaunch_checklist", sa.JSON(), nullable=False),
        sa.Column("plan_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"]),
        sa.ForeignKeyConstraint(["research_task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_action_plans_task_deleted_at",
        "action_plans",
        ["research_task_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_action_plans_opportunity_deleted_at",
        "action_plans",
        ["opportunity_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_action_plans_deleted_at",
        "action_plans",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_action_plans_deleted_at",
        table_name="action_plans",
    )
    op.drop_index(
        "ix_action_plans_opportunity_deleted_at",
        table_name="action_plans",
    )
    op.drop_index(
        "ix_action_plans_task_deleted_at",
        table_name="action_plans",
    )
    op.drop_table("action_plans")
