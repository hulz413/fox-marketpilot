from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ValidationBudget(Base):
    __tablename__ = "validation_budgets"
    __table_args__ = (
        Index(
            "ix_validation_budgets_task_deleted_at",
            "research_task_id",
            "deleted_at",
        ),
        Index(
            "ix_validation_budgets_opportunity_deleted_at",
            "opportunity_id",
            "deleted_at",
        ),
        Index("ix_validation_budgets_deleted_at", "deleted_at"),
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
    estimated_unit_cost: Mapped[str] = mapped_column(String(160), nullable=False)
    estimated_selling_price: Mapped[str] = mapped_column(String(160), nullable=False)
    rough_gross_margin: Mapped[str] = mapped_column(String(160), nullable=False)
    first_batch_quantity: Mapped[str] = mapped_column(String(160), nullable=False)
    first_batch_budget: Mapped[str] = mapped_column(String(160), nullable=False)
    key_assumptions: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    calculation_note: Mapped[str] = mapped_column(String(1000), nullable=False)
    estimate_status: Mapped[str] = mapped_column(String(32), nullable=False)
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
