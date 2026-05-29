from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunities.schemas import OpportunityRead
from app.modules.research_tasks import service as research_tasks_service

router = APIRouter()


@router.get(
    "/research-tasks/{task_uuid}/opportunities",
    response_model=list[OpportunityRead],
)
def list_research_task_opportunities(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[OpportunityRead]:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    opportunities = opportunities_service.list_task_opportunities(db, task)

    return [
        OpportunityRead(
            uuid=opportunity.uuid,
            research_task_uuid=task.uuid,
            rank=opportunity.rank,
            name=opportunity.name,
            product_direction=opportunity.product_direction,
            target_audience=opportunity.target_audience,
            recommendation_reason=opportunity.recommendation_reason,
            suitable_channels=opportunity.suitable_channels,
            price_band=opportunity.price_band,
            rough_margin=opportunity.rough_margin,
            risk_level=opportunity.risk_level,
            priority_label=opportunity.priority_label,
            next_step_summary=opportunity.next_step_summary,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
            deleted_at=opportunity.deleted_at,
        )
        for opportunity in opportunities
    ]


@router.get("/opportunities/{opportunity_uuid}", response_model=OpportunityRead)
def get_opportunity(
    opportunity_uuid: UUID,
    db: Session = Depends(get_db),
) -> OpportunityRead:
    opportunity = opportunities_service.get_opportunity(db, opportunity_uuid)

    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    task = research_tasks_service.get_research_task_by_id(db, opportunity.research_task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return OpportunityRead(
        uuid=opportunity.uuid,
        research_task_uuid=task.uuid,
        rank=opportunity.rank,
        name=opportunity.name,
        product_direction=opportunity.product_direction,
        target_audience=opportunity.target_audience,
        recommendation_reason=opportunity.recommendation_reason,
        suitable_channels=opportunity.suitable_channels,
        price_band=opportunity.price_band,
        rough_margin=opportunity.rough_margin,
        risk_level=opportunity.risk_level,
        priority_label=opportunity.priority_label,
        next_step_summary=opportunity.next_step_summary,
        created_at=opportunity.created_at,
        updated_at=opportunity.updated_at,
        deleted_at=opportunity.deleted_at,
    )
