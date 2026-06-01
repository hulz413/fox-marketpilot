from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.research_quality_readiness import (
    service as readiness_service,
)
from app.modules.research_quality_readiness.schemas import (
    ResearchQualityReadinessRunRead,
)
from app.modules.research_tasks import service as research_tasks_service

router = APIRouter()


@router.post(
    "/research-tasks/{task_uuid}/readiness-runs",
    response_model=ResearchQualityReadinessRunRead,
    status_code=status.HTTP_201_CREATED,
)
def create_research_quality_readiness_run(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> ResearchQualityReadinessRunRead:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    try:
        readiness_run = readiness_service.create_readiness_run(db, task)
    except readiness_service.ReadinessUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return readiness_service.readiness_run_to_read(readiness_run, task=task)


@router.get(
    "/research-tasks/{task_uuid}/readiness-runs/latest",
    response_model=Optional[ResearchQualityReadinessRunRead],
)
def get_latest_research_quality_readiness_run(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> Optional[ResearchQualityReadinessRunRead]:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    readiness_run = readiness_service.get_latest_readiness_run(db, task)

    if readiness_run is None:
        return None

    return readiness_service.readiness_run_to_read(readiness_run, task=task)
