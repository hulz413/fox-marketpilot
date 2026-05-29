from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.research_tasks import repository
from app.modules.research_tasks.models import ResearchTask
from app.modules.research_tasks.schemas import (
    ResearchTaskCreate,
    ResearchTaskStage,
    ResearchTaskStatus,
)


def make_task_title(brief: str) -> str:
    normalized = " ".join(brief.split())

    if len(normalized) <= 60:
        return normalized

    return f"{normalized[:60]}..."


def create_research_task(db: Session, payload: ResearchTaskCreate) -> ResearchTask:
    task = ResearchTask(
        title=payload.title or make_task_title(payload.brief),
        brief=payload.brief,
        budget=payload.budget,
        target_channels=payload.target_channels,
        preferred_categories=payload.preferred_categories,
        excluded_categories=payload.excluded_categories,
        target_audience=payload.target_audience,
        expected_profit=payload.expected_profit,
        supply_preferences=payload.supply_preferences,
        constraints=payload.constraints,
        status=ResearchTaskStatus.CREATED.value,
        current_stage=ResearchTaskStage.INTAKE.value,
    )

    return repository.create_research_task(db, task)


def list_research_tasks(db: Session, limit: int = 50) -> list[ResearchTask]:
    return repository.list_active_research_tasks(db, limit=limit)


def get_research_task(db: Session, task_uuid: UUID) -> Optional[ResearchTask]:
    return repository.get_active_research_task_by_uuid(db, task_uuid)
