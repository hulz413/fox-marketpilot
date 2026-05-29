from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        Index("ix_opportunities_research_task_id_rank", "research_task_id", "rank"),
        Index("ix_opportunities_deleted_at", "deleted_at"),
        Index(
            "ix_opportunities_research_task_id_deleted_at",
            "research_task_id",
            "deleted_at",
        ),
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
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    product_direction: Mapped[str] = mapped_column(String(240), nullable=False)
    target_audience: Mapped[str] = mapped_column(String(240), nullable=False)
    recommendation_reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    suitable_channels: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    price_band: Mapped[str] = mapped_column(String(120), nullable=False)
    rough_margin: Mapped[str] = mapped_column(String(120), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    priority_label: Mapped[str] = mapped_column(String(120), nullable=False)
    next_step_summary: Mapped[str] = mapped_column(String(1000), nullable=False)
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
