from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OpportunityRisk(Base):
    __tablename__ = "opportunity_risks"
    __table_args__ = (
        Index(
            "ix_opportunity_risks_task_deleted_at",
            "research_task_id",
            "deleted_at",
        ),
        Index(
            "ix_opportunity_risks_opportunity_deleted_at",
            "opportunity_id",
            "deleted_at",
        ),
        Index("ix_opportunity_risks_deleted_at", "deleted_at"),
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
    overall_risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    quality_risk: Mapped[str] = mapped_column(String(1000), nullable=False)
    fulfillment_risk: Mapped[str] = mapped_column(String(1000), nullable=False)
    after_sales_risk: Mapped[str] = mapped_column(String(1000), nullable=False)
    compliance_risk: Mapped[str] = mapped_column(String(1000), nullable=False)
    inventory_risk: Mapped[str] = mapped_column(String(1000), nullable=False)
    competition_risk: Mapped[str] = mapped_column(String(1000), nullable=False)
    platform_risk: Mapped[str] = mapped_column(String(1000), nullable=False)
    risk_triggers: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    mitigation_suggestions: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
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
