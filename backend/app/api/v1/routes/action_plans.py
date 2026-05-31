from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.action_plans import service as action_plans_service
from app.modules.action_plans.schemas import OpportunityActionPlanRead
from app.modules.opportunities import service as opportunities_service
from app.modules.research_tasks import service as research_tasks_service

router = APIRouter()


@router.get(
    "/research-tasks/{task_uuid}/action-plans",
    response_model=list[OpportunityActionPlanRead],
)
def list_research_task_action_plans(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[OpportunityActionPlanRead]:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    opportunities = opportunities_service.list_task_opportunities(db, task)
    opportunity_uuid_by_id = {
        opportunity.id: opportunity.uuid for opportunity in opportunities
    }

    return [
        action_plans_service.action_plan_to_read(
            action_plan,
            research_task_uuid=task.uuid,
            opportunity_uuid=opportunity_uuid_by_id[action_plan.opportunity_id],
        )
        for action_plan in action_plans_service.list_task_action_plans(db, task)
    ]


@router.get(
    "/opportunities/{opportunity_uuid}/action-plans",
    response_model=list[OpportunityActionPlanRead],
)
def list_opportunity_action_plans(
    opportunity_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[OpportunityActionPlanRead]:
    opportunity = opportunities_service.get_opportunity(db, opportunity_uuid)

    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    task = research_tasks_service.get_research_task_by_id(
        db,
        opportunity.research_task_id,
    )

    if task is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return [
        action_plans_service.action_plan_to_read(
            action_plan,
            research_task_uuid=task.uuid,
            opportunity_uuid=opportunity.uuid,
        )
        for action_plan in action_plans_service.list_opportunity_action_plans(
            db,
            opportunity,
        )
    ]
