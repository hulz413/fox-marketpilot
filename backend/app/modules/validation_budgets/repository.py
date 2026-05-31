from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.opportunities.models import Opportunity
from app.modules.validation_budgets.models import ValidationBudget


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def add_budgets(
    db: Session,
    budgets: list[ValidationBudget],
) -> list[ValidationBudget]:
    db.add_all(budgets)
    return budgets


def list_active_budgets_by_task_id(
    db: Session,
    research_task_id: int,
) -> list[ValidationBudget]:
    statement = (
        select(ValidationBudget)
        .join(Opportunity, ValidationBudget.opportunity_id == Opportunity.id)
        .where(
            ValidationBudget.research_task_id == research_task_id,
            ValidationBudget.deleted_at.is_(None),
            Opportunity.deleted_at.is_(None),
        )
        .order_by(Opportunity.rank.asc(), ValidationBudget.id.asc())
    )

    return list(db.execute(statement).scalars().all())


def list_active_budgets_by_opportunity_id(
    db: Session,
    opportunity_id: int,
) -> list[ValidationBudget]:
    statement = (
        select(ValidationBudget)
        .where(
            ValidationBudget.opportunity_id == opportunity_id,
            ValidationBudget.deleted_at.is_(None),
        )
        .order_by(ValidationBudget.id.asc())
    )

    return list(db.execute(statement).scalars().all())


def list_active_budgets_for_soft_delete(
    db: Session,
    research_task_id: int,
) -> list[ValidationBudget]:
    statement = select(ValidationBudget).where(
        ValidationBudget.research_task_id == research_task_id,
        ValidationBudget.deleted_at.is_(None),
    )

    return list(db.execute(statement).scalars().all())


def soft_delete_active_budgets_by_task_id(
    db: Session,
    research_task_id: int,
) -> None:
    deleted_at = utc_now()

    for budget in list_active_budgets_for_soft_delete(db, research_task_id):
        budget.deleted_at = deleted_at
