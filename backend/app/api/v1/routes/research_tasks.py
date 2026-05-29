from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.research_tasks import service
from app.modules.research_tasks.schemas import ResearchTaskCreate, ResearchTaskRead

router = APIRouter(prefix="/research-tasks")


@router.post(
    "",
    response_model=ResearchTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_research_task(
    payload: ResearchTaskCreate,
    db: Session = Depends(get_db),
) -> ResearchTaskRead:
    return service.create_research_task(db, payload)


@router.get("", response_model=list[ResearchTaskRead])
def list_research_tasks(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[ResearchTaskRead]:
    return service.list_research_tasks(db, limit=limit)


@router.get("/{task_uuid}", response_model=ResearchTaskRead)
def get_research_task(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> ResearchTaskRead:
    task = service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    return task


@router.post("/{task_uuid}/runs", response_model=ResearchTaskRead)
def start_research_run(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> ResearchTaskRead:
    task = service.start_research_run(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    return task
