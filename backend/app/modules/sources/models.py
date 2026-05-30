from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResearchSource(Base):
    __tablename__ = "research_sources"
    __table_args__ = (
        Index(
            "ix_research_sources_research_task_id_deleted_at",
            "research_task_id",
            "deleted_at",
        ),
        Index(
            "ix_research_sources_opportunity_id_deleted_at",
            "opportunity_id",
            "deleted_at",
        ),
        Index(
            "ix_research_sources_task_type_deleted_at",
            "research_task_id",
            "source_type",
            "deleted_at",
        ),
        Index("ix_research_sources_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_pkg.uuid4,
    )
    research_task_id: Mapped[int] = mapped_column(
        ForeignKey("research_tasks.id"),
        nullable=False,
    )
    opportunity_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("opportunities.id"),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    summary: Mapped[str] = mapped_column(String(1200), nullable=False)
    snippet: Mapped[str] = mapped_column(String(1200), nullable=False)
    publisher: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    query: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    linked_claim: Mapped[str] = mapped_column(String(1000), nullable=False)
    support_level: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
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
