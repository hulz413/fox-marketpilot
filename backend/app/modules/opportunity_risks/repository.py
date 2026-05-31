from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.opportunities.models import Opportunity
from app.modules.opportunity_risks.models import OpportunityRisk


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def add_risks(
    db: Session,
    risks: list[OpportunityRisk],
) -> list[OpportunityRisk]:
    db.add_all(risks)
    return risks


def list_active_risks_by_task_id(
    db: Session,
    research_task_id: int,
) -> list[OpportunityRisk]:
    statement = (
        select(OpportunityRisk)
        .join(Opportunity, OpportunityRisk.opportunity_id == Opportunity.id)
        .where(
            OpportunityRisk.research_task_id == research_task_id,
            OpportunityRisk.deleted_at.is_(None),
            Opportunity.deleted_at.is_(None),
        )
        .order_by(Opportunity.rank.asc(), OpportunityRisk.id.asc())
    )

    return list(db.execute(statement).scalars().all())


def list_active_risks_by_opportunity_id(
    db: Session,
    opportunity_id: int,
) -> list[OpportunityRisk]:
    statement = (
        select(OpportunityRisk)
        .where(
            OpportunityRisk.opportunity_id == opportunity_id,
            OpportunityRisk.deleted_at.is_(None),
        )
        .order_by(OpportunityRisk.id.asc())
    )

    return list(db.execute(statement).scalars().all())


def list_active_risks_for_soft_delete(
    db: Session,
    research_task_id: int,
) -> list[OpportunityRisk]:
    statement = select(OpportunityRisk).where(
        OpportunityRisk.research_task_id == research_task_id,
        OpportunityRisk.deleted_at.is_(None),
    )

    return list(db.execute(statement).scalars().all())


def soft_delete_active_risks_by_task_id(
    db: Session,
    research_task_id: int,
) -> None:
    deleted_at = utc_now()

    for risk in list_active_risks_for_soft_delete(db, research_task_id):
        risk.deleted_at = deleted_at
