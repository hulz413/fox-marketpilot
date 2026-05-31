from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RagEvaluationCase(Base):
    __tablename__ = "rag_evaluation_cases"
    __table_args__ = (
        Index("ix_rag_evaluation_cases_category_deleted_at", "category", "deleted_at"),
        Index("ix_rag_evaluation_cases_enabled_deleted_at", "enabled", "deleted_at"),
        Index("ix_rag_evaluation_cases_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_pkg.uuid4,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    question: Mapped[str] = mapped_column(String(800), nullable=False)
    expected_source_types: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    expected_keywords: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    expected_claims: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    grading_rubric: Mapped[str] = mapped_column(String(1200), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    case_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
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


class RagEvaluationRun(Base):
    __tablename__ = "rag_evaluation_runs"
    __table_args__ = (
        Index(
            "ix_rag_evaluation_runs_task_deleted_at",
            "research_task_id",
            "deleted_at",
        ),
        Index("ix_rag_evaluation_runs_status_deleted_at", "status", "deleted_at"),
        Index("ix_rag_evaluation_runs_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_pkg.uuid4,
    )
    research_task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("research_tasks.id"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    run_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    trace_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    summary_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    case_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    case_completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    case_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    case_skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_hit_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_recall: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_precision: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_mrr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_ndcg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_summary: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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


class RagEvaluationResult(Base):
    __tablename__ = "rag_evaluation_results"
    __table_args__ = (
        Index(
            "ix_rag_evaluation_results_run_deleted_at",
            "evaluation_run_id",
            "deleted_at",
        ),
        Index(
            "ix_rag_evaluation_results_case_deleted_at",
            "evaluation_case_id",
            "deleted_at",
        ),
        Index("ix_rag_evaluation_results_status_deleted_at", "status", "deleted_at"),
        Index("ix_rag_evaluation_results_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_pkg.uuid4,
    )
    evaluation_run_id: Mapped[int] = mapped_column(
        ForeignKey("rag_evaluation_runs.id"),
        nullable=False,
    )
    evaluation_case_id: Mapped[int] = mapped_column(
        ForeignKey("rag_evaluation_cases.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    question: Mapped[str] = mapped_column(String(800), nullable=False)
    case_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    retrieval_query: Mapped[str] = mapped_column(String(1200), nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    retrieval_status: Mapped[str] = mapped_column(String(32), nullable=False)
    retrieved_evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    relevant_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hit_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recall: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    precision: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mrr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ndcg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    scoring_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_summary: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
