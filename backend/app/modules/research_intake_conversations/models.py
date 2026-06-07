from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResearchIntakeConversation(Base):
    __tablename__ = "research_intake_conversations"
    __table_args__ = (
        Index(
            "ix_research_intake_conversations_status_deleted_at",
            "status",
            "deleted_at",
        ),
        Index(
            "ix_research_intake_conversations_task_deleted_at",
            "research_task_id",
            "deleted_at",
        ),
        Index("ix_research_intake_conversations_deleted_at", "deleted_at"),
        Index("ix_research_intake_conversations_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_pkg.uuid4,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    draft_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    missing_fields: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    assumptions: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    readiness_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="needs_clarification",
    )
    can_create_task: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    research_task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("research_tasks.id"),
        nullable=True,
    )
    trace_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    trace_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class ResearchIntakeMessage(Base):
    __tablename__ = "research_intake_messages"
    __table_args__ = (
        Index(
            "ix_research_intake_messages_conversation_deleted_at",
            "conversation_id",
            "deleted_at",
        ),
        Index(
            "ix_research_intake_messages_role_deleted_at",
            "role",
            "deleted_at",
        ),
        Index("ix_research_intake_messages_deleted_at", "deleted_at"),
        Index("ix_research_intake_messages_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_pkg.uuid4,
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("research_intake_conversations.id"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_delta: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    processing_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
