from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.generation_quality_evaluation import (
    service as generation_evaluation_service,
)
from app.modules.generation_quality_evaluation.schemas import (
    GenerationEvaluationRunRead,
)
from app.modules.research_tasks import service as research_tasks_service

router = APIRouter()


@router.post(
    "/research-tasks/{task_uuid}/generation-evaluation-runs",
    response_model=GenerationEvaluationRunRead,
    status_code=status.HTTP_201_CREATED,
)
def create_generation_evaluation_run(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> GenerationEvaluationRunRead:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    try:
        evaluation_run = generation_evaluation_service.run_generation_evaluation(
            db,
            task,
        )
    except generation_evaluation_service.GenerationEvaluationUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return generation_evaluation_service.evaluation_run_to_read(
        evaluation_run,
        task=task,
    )


@router.get(
    "/research-tasks/{task_uuid}/generation-evaluation-runs/latest",
    response_model=Optional[GenerationEvaluationRunRead],
)
def get_latest_generation_evaluation_run(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> Optional[GenerationEvaluationRunRead]:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    evaluation_run = generation_evaluation_service.get_latest_generation_evaluation_run(
        db,
        task,
    )

    if evaluation_run is None:
        return None

    return generation_evaluation_service.evaluation_run_to_read(
        evaluation_run,
        task=task,
    )
