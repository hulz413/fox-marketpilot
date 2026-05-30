from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.demand_insights import service as demand_insights_service
from app.modules.demand_insights.schemas import OpportunityDemandInsightRead
from app.modules.opportunities import service as opportunities_service
from app.modules.research_tasks import service as research_tasks_service

router = APIRouter()


@router.get(
    "/research-tasks/{task_uuid}/demand-insights",
    response_model=list[OpportunityDemandInsightRead],
)
def list_research_task_demand_insights(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[OpportunityDemandInsightRead]:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    opportunities = opportunities_service.list_task_opportunities(db, task)
    opportunity_uuid_by_id = {
        opportunity.id: opportunity.uuid for opportunity in opportunities
    }

    return [
        demand_insights_service.demand_insight_to_read(
            db,
            insight,
            research_task_uuid=task.uuid,
            opportunity_uuid=opportunity_uuid_by_id[insight.opportunity_id],
        )
        for insight in demand_insights_service.list_task_demand_insights(db, task)
    ]


@router.get(
    "/opportunities/{opportunity_uuid}/demand-insight",
    response_model=Optional[OpportunityDemandInsightRead],
)
def get_opportunity_demand_insight(
    opportunity_uuid: UUID,
    db: Session = Depends(get_db),
) -> Optional[OpportunityDemandInsightRead]:
    opportunity = opportunities_service.get_opportunity(db, opportunity_uuid)

    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    task = research_tasks_service.get_research_task_by_id(
        db,
        opportunity.research_task_id,
    )

    if task is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    insight = demand_insights_service.get_opportunity_demand_insight(
        db,
        opportunity,
    )

    if insight is None:
        return None

    return demand_insights_service.demand_insight_to_read(
        db,
        insight,
        research_task_uuid=task.uuid,
        opportunity_uuid=opportunity.uuid,
    )
