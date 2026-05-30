from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CompetitorReference(Base):
    __tablename__ = "competitor_references"
    __table_args__ = (
        Index(
            "ix_competitor_references_task_deleted_at",
            "research_task_id",
            "deleted_at",
        ),
        Index(
            "ix_competitor_references_opportunity_rank",
            "opportunity_id",
            "rank",
        ),
        Index(
            "ix_competitor_references_opportunity_deleted_at",
            "opportunity_id",
            "deleted_at",
        ),
        Index("ix_competitor_references_deleted_at", "deleted_at"),
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
    opportunity_id: Mapped[int] = mapped_column(
        ForeignKey("opportunities.id"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(nullable=False)
    reference_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reference_market: Mapped[str] = mapped_column(String(240), nullable=False)
    price_range: Mapped[str] = mapped_column(String(160), nullable=False)
    common_selling_points: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    homogenization_level: Mapped[str] = mapped_column(String(32), nullable=False)
    differentiation_angles: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    reference_note: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_status: Mapped[str] = mapped_column(String(32), nullable=False)
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


class CompetitorReferenceSource(Base):
    __tablename__ = "competitor_reference_sources"
    __table_args__ = (
        Index(
            "ix_competitor_reference_sources_reference_deleted_at",
            "competitor_reference_id",
            "deleted_at",
        ),
        Index(
            "ix_competitor_reference_sources_source_deleted_at",
            "research_source_id",
            "deleted_at",
        ),
        Index("ix_competitor_reference_sources_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_pkg.uuid4,
    )
    competitor_reference_id: Mapped[int] = mapped_column(
        ForeignKey("competitor_references.id"),
        nullable=False,
    )
    research_source_id: Mapped[int] = mapped_column(
        ForeignKey("research_sources.id"),
        nullable=False,
    )
    relevance_note: Mapped[str] = mapped_column(String(1000), nullable=False)
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
