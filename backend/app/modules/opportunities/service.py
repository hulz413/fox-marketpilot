from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.opportunities import repository
from app.modules.opportunities.models import Opportunity
from app.modules.opportunities.schemas import OpportunityGenerated
from app.modules.research_tasks.models import ResearchTask


def list_task_opportunities(db: Session, task: ResearchTask) -> list[Opportunity]:
    return repository.list_active_opportunities_by_task_id(db, task.id)


def get_opportunity(db: Session, opportunity_uuid: UUID) -> Optional[Opportunity]:
    return repository.get_active_opportunity_by_uuid(db, opportunity_uuid)


def replace_task_opportunities(
    db: Session,
    task: ResearchTask,
    generated_opportunities: list[OpportunityGenerated],
) -> list[Opportunity]:
    repository.soft_delete_active_opportunities_by_task_id(db, task.id)

    opportunities = [
        Opportunity(
            research_task_id=task.id,
            rank=item.rank,
            name=item.name,
            product_direction=item.product_direction,
            target_audience=item.target_audience,
            recommendation_reason=item.recommendation_reason,
            suitable_channels=item.suitable_channels,
            price_band=item.price_band,
            rough_margin=item.rough_margin,
            risk_level=item.risk_level.value,
            priority_label=item.priority_label,
            next_step_summary=item.next_step_summary,
        )
        for item in sorted(generated_opportunities, key=lambda opportunity: opportunity.rank)
    ]

    repository.add_opportunities(db, opportunities)
    db.flush()

    return opportunities
