from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResearchTask(Base):
    __tablename__ = "research_tasks"
    __table_args__ = (
        Index("ix_research_tasks_status", "status"),
        Index("ix_research_tasks_created_at", "created_at"),
        Index("ix_research_tasks_deleted_at", "deleted_at"),
        Index("ix_research_tasks_deleted_at_created_at", "deleted_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_pkg.uuid4,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    brief: Mapped[str] = mapped_column(String(2000), nullable=False)
    budget: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    target_channels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    preferred_categories: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    excluded_categories: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    target_audience: Mapped[Optional[str]] = mapped_column(String(240), nullable=True)
    expected_profit: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    supply_preferences: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    constraints: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False, default="intake")
    run_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    trace_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
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
