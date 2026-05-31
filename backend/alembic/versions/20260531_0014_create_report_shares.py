"""create report shares

Revision ID: 20260531_0014
Revises: 20260531_0013
Create Date: 2026-05-31 21:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260531_0014"
down_revision: Union[str, None] = "20260531_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_shares",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=False),
        sa.Column("share_token", sa.String(length=96), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["research_task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_token"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_report_shares_task_deleted_at",
        "report_shares",
        ["research_task_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_report_shares_status_deleted_at",
        "report_shares",
        ["status", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_report_shares_deleted_at",
        "report_shares",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_report_shares_deleted_at", table_name="report_shares")
    op.drop_index("ix_report_shares_status_deleted_at", table_name="report_shares")
    op.drop_index("ix_report_shares_task_deleted_at", table_name="report_shares")
    op.drop_table("report_shares")
