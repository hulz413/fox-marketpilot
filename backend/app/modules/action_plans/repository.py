from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.action_plans.models import ActionPlan
from app.modules.opportunities.models import Opportunity


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def add_action_plans(
    db: Session,
    action_plans: list[ActionPlan],
) -> list[ActionPlan]:
    db.add_all(action_plans)
    return action_plans


def list_active_action_plans_by_task_id(
    db: Session,
    research_task_id: int,
) -> list[ActionPlan]:
    statement = (
        select(ActionPlan)
        .join(Opportunity, ActionPlan.opportunity_id == Opportunity.id)
        .where(
            ActionPlan.research_task_id == research_task_id,
            ActionPlan.deleted_at.is_(None),
            Opportunity.deleted_at.is_(None),
        )
        .order_by(Opportunity.rank.asc(), ActionPlan.id.asc())
    )

    return list(db.execute(statement).scalars().all())


def list_active_action_plans_by_opportunity_id(
    db: Session,
    opportunity_id: int,
) -> list[ActionPlan]:
    statement = (
        select(ActionPlan)
        .where(
            ActionPlan.opportunity_id == opportunity_id,
            ActionPlan.deleted_at.is_(None),
        )
        .order_by(ActionPlan.id.asc())
    )

    return list(db.execute(statement).scalars().all())


def list_active_action_plans_for_soft_delete(
    db: Session,
    research_task_id: int,
) -> list[ActionPlan]:
    statement = select(ActionPlan).where(
        ActionPlan.research_task_id == research_task_id,
        ActionPlan.deleted_at.is_(None),
    )

    return list(db.execute(statement).scalars().all())


def soft_delete_active_action_plans_by_task_id(
    db: Session,
    research_task_id: int,
) -> None:
    deleted_at = utc_now()

    for action_plan in list_active_action_plans_for_soft_delete(
        db,
        research_task_id,
    ):
        action_plan.deleted_at = deleted_at
