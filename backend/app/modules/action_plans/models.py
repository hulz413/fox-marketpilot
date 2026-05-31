from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ActionPlan(Base):
    __tablename__ = "action_plans"
    __table_args__ = (
        Index(
            "ix_action_plans_task_deleted_at",
            "research_task_id",
            "deleted_at",
        ),
        Index(
            "ix_action_plans_opportunity_deleted_at",
            "opportunity_id",
            "deleted_at",
        ),
        Index("ix_action_plans_deleted_at", "deleted_at"),
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
    validation_goal: Mapped[str] = mapped_column(String(1000), nullable=False)
    first_batch_plan: Mapped[str] = mapped_column(String(1000), nullable=False)
    product_validation_method: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )
    content_angles: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    title_suggestions: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    selling_point_suggestions: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    supplier_inquiry_script: Mapped[str] = mapped_column(
        String(1200),
        nullable=False,
    )
    prelaunch_checklist: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    plan_status: Mapped[str] = mapped_column(String(32), nullable=False)
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
