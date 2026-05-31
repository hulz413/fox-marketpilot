from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunity_risks import service as opportunity_risks_service
from app.modules.opportunity_risks.schemas import OpportunityRiskRead
from app.modules.research_tasks import service as research_tasks_service

router = APIRouter()


@router.get(
    "/research-tasks/{task_uuid}/opportunity-risks",
    response_model=list[OpportunityRiskRead],
)
def list_research_task_opportunity_risks(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[OpportunityRiskRead]:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    opportunities = opportunities_service.list_task_opportunities(db, task)
    opportunity_uuid_by_id = {
        opportunity.id: opportunity.uuid for opportunity in opportunities
    }

    return [
        opportunity_risks_service.opportunity_risk_to_read(
            risk,
            research_task_uuid=task.uuid,
            opportunity_uuid=opportunity_uuid_by_id[risk.opportunity_id],
        )
        for risk in opportunity_risks_service.list_task_opportunity_risks(db, task)
    ]


@router.get(
    "/opportunities/{opportunity_uuid}/opportunity-risks",
    response_model=list[OpportunityRiskRead],
)
def list_opportunity_risks(
    opportunity_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[OpportunityRiskRead]:
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
        opportunity_risks_service.opportunity_risk_to_read(
            risk,
            research_task_uuid=task.uuid,
            opportunity_uuid=opportunity.uuid,
        )
        for risk in opportunity_risks_service.list_opportunity_risks(
            db,
            opportunity,
        )
    ]
