from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResearchQualityReadinessRun(Base):
    __tablename__ = "research_quality_readiness_runs"
    __table_args__ = (
        Index(
            "ix_research_quality_readiness_runs_task_deleted_at",
            "research_task_id",
            "deleted_at",
        ),
        Index(
            "ix_research_quality_readiness_runs_task_run_deleted_at",
            "research_task_id",
            "research_run_id",
            "deleted_at",
        ),
        Index(
            "ix_research_quality_readiness_runs_overall_deleted_at",
            "overall_status",
            "deleted_at",
        ),
        Index("ix_research_quality_readiness_runs_deleted_at", "deleted_at"),
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
    research_run_id: Mapped[Optional[str]] = mapped_column(
        String(120),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    overall_status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    rag_evaluation_run_uuid: Mapped[Optional[uuid_pkg.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    trace_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    trace_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_summary: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
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
