from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.opportunities import service as opportunities_service
from app.modules.research_tasks import service as research_tasks_service
from app.modules.competitor_references import service as competitor_references_service
from app.modules.competitor_references.schemas import OpportunityCompetitorReferenceRead

router = APIRouter()


@router.get(
    "/research-tasks/{task_uuid}/competitor-references",
    response_model=list[OpportunityCompetitorReferenceRead],
)
def list_research_task_competitor_references(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[OpportunityCompetitorReferenceRead]:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    opportunities = opportunities_service.list_task_opportunities(db, task)
    opportunity_uuid_by_id = {
        opportunity.id: opportunity.uuid for opportunity in opportunities
    }

    return [
        competitor_references_service.competitor_reference_to_read(
            db,
            reference,
            research_task_uuid=task.uuid,
            opportunity_uuid=opportunity_uuid_by_id[reference.opportunity_id],
        )
        for reference in competitor_references_service.list_task_competitor_references(
            db,
            task,
        )
    ]


@router.get(
    "/opportunities/{opportunity_uuid}/competitor-references",
    response_model=list[OpportunityCompetitorReferenceRead],
)
def list_opportunity_competitor_references(
    opportunity_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[OpportunityCompetitorReferenceRead]:
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
        competitor_references_service.competitor_reference_to_read(
            db,
            reference,
            research_task_uuid=task.uuid,
            opportunity_uuid=opportunity.uuid,
        )
        for reference in competitor_references_service.list_opportunity_competitor_references(
            db,
            opportunity,
        )
    ]
