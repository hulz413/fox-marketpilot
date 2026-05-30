from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.opportunities import service as opportunities_service
from app.modules.research_tasks import service as research_tasks_service
from app.modules.supply_candidates import service as supply_candidates_service
from app.modules.supply_candidates.schemas import OpportunitySupplyCandidateRead

router = APIRouter()


@router.get(
    "/research-tasks/{task_uuid}/supply-candidates",
    response_model=list[OpportunitySupplyCandidateRead],
)
def list_research_task_supply_candidates(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[OpportunitySupplyCandidateRead]:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    opportunities = opportunities_service.list_task_opportunities(db, task)
    opportunity_uuid_by_id = {
        opportunity.id: opportunity.uuid for opportunity in opportunities
    }

    return [
        supply_candidates_service.supply_candidate_to_read(
            db,
            candidate,
            research_task_uuid=task.uuid,
            opportunity_uuid=opportunity_uuid_by_id[candidate.opportunity_id],
        )
        for candidate in supply_candidates_service.list_task_supply_candidates(db, task)
    ]


@router.get(
    "/opportunities/{opportunity_uuid}/supply-candidates",
    response_model=list[OpportunitySupplyCandidateRead],
)
def list_opportunity_supply_candidates(
    opportunity_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[OpportunitySupplyCandidateRead]:
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
        supply_candidates_service.supply_candidate_to_read(
            db,
            candidate,
            research_task_uuid=task.uuid,
            opportunity_uuid=opportunity.uuid,
        )
        for candidate in supply_candidates_service.list_opportunity_supply_candidates(
            db,
            opportunity,
        )
    ]
