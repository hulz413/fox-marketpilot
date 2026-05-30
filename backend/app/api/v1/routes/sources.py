from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.opportunities import service as opportunities_service
from app.modules.research_tasks import service as research_tasks_service
from app.modules.sources import service as sources_service
from app.modules.sources.schemas import ResearchSourceRead

router = APIRouter()


@router.get(
    "/research-tasks/{task_uuid}/sources",
    response_model=list[ResearchSourceRead],
)
def list_research_task_sources(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[ResearchSourceRead]:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    opportunities = opportunities_service.list_task_opportunities(db, task)
    opportunity_uuid_by_id = {
        opportunity.id: opportunity.uuid for opportunity in opportunities
    }

    return [
        sources_service.source_to_read(
            source,
            research_task_uuid=task.uuid,
            opportunity_uuid=opportunity_uuid_by_id.get(source.opportunity_id),
        )
        for source in sources_service.list_task_sources(db, task)
    ]


@router.get(
    "/opportunities/{opportunity_uuid}/sources",
    response_model=list[ResearchSourceRead],
)
def list_opportunity_sources(
    opportunity_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[ResearchSourceRead]:
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
        sources_service.source_to_read(
            source,
            research_task_uuid=task.uuid,
            opportunity_uuid=opportunity.uuid,
        )
        for source in sources_service.list_opportunity_sources(db, opportunity)
    ]
