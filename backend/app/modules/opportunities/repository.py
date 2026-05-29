from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.opportunities.models import Opportunity
from app.modules.research_tasks.models import utc_now


def list_active_opportunities_by_task_id(
    db: Session,
    research_task_id: int,
) -> list[Opportunity]:
    statement = (
        select(Opportunity)
        .where(
            Opportunity.research_task_id == research_task_id,
            Opportunity.deleted_at.is_(None),
        )
        .order_by(Opportunity.rank.asc(), Opportunity.id.asc())
    )

    return list(db.execute(statement).scalars().all())


def get_active_opportunity_by_uuid(
    db: Session,
    opportunity_uuid: UUID,
) -> Optional[Opportunity]:
    statement = select(Opportunity).where(
        Opportunity.uuid == opportunity_uuid,
        Opportunity.deleted_at.is_(None),
    )

    return db.execute(statement).scalar_one_or_none()


def soft_delete_active_opportunities_by_task_id(
    db: Session,
    research_task_id: int,
) -> None:
    deleted_at = utc_now()

    for opportunity in list_active_opportunities_by_task_id(db, research_task_id):
        opportunity.deleted_at = deleted_at


def add_opportunities(db: Session, opportunities: list[Opportunity]) -> list[Opportunity]:
    db.add_all(opportunities)
    return opportunities
