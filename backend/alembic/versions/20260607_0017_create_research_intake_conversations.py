"""create research intake conversations

Revision ID: 20260607_0017
Revises: 20260607_0016
Create Date: 2026-06-07 11:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260607_0017"
down_revision: Union[str, None] = "20260607_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_intake_conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("draft_payload", sa.JSON(), nullable=False),
        sa.Column("missing_fields", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("readiness_status", sa.String(length=32), nullable=False),
        sa.Column("can_create_task", sa.Boolean(), nullable=False),
        sa.Column("research_task_id", sa.Integer(), nullable=True),
        sa.Column("trace_id", sa.String(length=120), nullable=True),
        sa.Column("trace_url", sa.String(length=500), nullable=True),
        sa.Column("error_summary", sa.String(length=1000), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["research_task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_research_intake_conversations_status_deleted_at",
        "research_intake_conversations",
        ["status", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_intake_conversations_task_deleted_at",
        "research_intake_conversations",
        ["research_task_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_intake_conversations_deleted_at",
        "research_intake_conversations",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_intake_conversations_created_at",
        "research_intake_conversations",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "research_intake_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("structured_delta", sa.JSON(), nullable=False),
        sa.Column("processing_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["research_intake_conversations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        "ix_research_intake_messages_conversation_deleted_at",
        "research_intake_messages",
        ["conversation_id", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_intake_messages_role_deleted_at",
        "research_intake_messages",
        ["role", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_intake_messages_deleted_at",
        "research_intake_messages",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_research_intake_messages_created_at",
        "research_intake_messages",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_research_intake_messages_created_at",
        table_name="research_intake_messages",
    )
    op.drop_index(
        "ix_research_intake_messages_deleted_at",
        table_name="research_intake_messages",
    )
    op.drop_index(
        "ix_research_intake_messages_role_deleted_at",
        table_name="research_intake_messages",
    )
    op.drop_index(
        "ix_research_intake_messages_conversation_deleted_at",
        table_name="research_intake_messages",
    )
    op.drop_table("research_intake_messages")

    op.drop_index(
        "ix_research_intake_conversations_created_at",
        table_name="research_intake_conversations",
    )
    op.drop_index(
        "ix_research_intake_conversations_deleted_at",
        table_name="research_intake_conversations",
    )
    op.drop_index(
        "ix_research_intake_conversations_task_deleted_at",
        table_name="research_intake_conversations",
    )
    op.drop_index(
        "ix_research_intake_conversations_status_deleted_at",
        table_name="research_intake_conversations",
    )
    op.drop_table("research_intake_conversations")
