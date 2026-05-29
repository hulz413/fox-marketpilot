from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.research_tasks import repository
from app.modules.research_tasks.models import ResearchTask
from app.modules.research_tasks.schemas import (
    ResearchTaskCreate,
    ResearchTaskStage,
    ResearchTaskStatus,
)

logger = logging.getLogger(__name__)

RUNNING_STATUSES = {
    ResearchTaskStatus.QUEUED.value,
    ResearchTaskStatus.RUNNING.value,
}


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


def get_research_task_by_id(db: Session, task_id: int) -> Optional[ResearchTask]:
    return repository.get_active_research_task_by_id(db, task_id)


def save_research_task(db: Session, task: ResearchTask) -> ResearchTask:
    return repository.save_research_task(db, task)


def enqueue_research_run(task_uuid: UUID, run_id: str) -> None:
    from app.workers.research import run_opportunity_research

    run_opportunity_research.delay(str(task_uuid), run_id)


def start_research_run(
    db: Session,
    task_uuid: UUID,
    enqueue: bool = True,
) -> Optional[ResearchTask]:
    task = get_research_task(db, task_uuid)

    if task is None:
        return None

    if task.status in RUNNING_STATUSES:
        return task

    task.run_id = f"research-{uuid4()}"
    task.status = ResearchTaskStatus.QUEUED.value
    task.current_stage = ResearchTaskStage.QUEUED.value
    task.failure_reason = None
    save_research_task(db, task)

    if not enqueue:
        return task

    try:
        enqueue_research_run(task.uuid, task.run_id)
    except Exception:
        logger.exception(
            "Failed to enqueue opportunity research task",
            extra={"task_uuid": str(task.uuid), "run_id": task.run_id},
        )
        task.status = ResearchTaskStatus.FAILED.value
        task.current_stage = ResearchTaskStage.FAILED.value
        task.failure_reason = "研究运行启动失败，请确认后台任务服务可用。"
        save_research_task(db, task)

    return task


def mark_task_failed(
    db: Session,
    task: ResearchTask,
    failure_reason: str,
) -> ResearchTask:
    task.status = ResearchTaskStatus.FAILED.value
    task.current_stage = ResearchTaskStage.FAILED.value
    task.failure_reason = failure_reason[:1000]
    return save_research_task(db, task)


def execute_research_run(
    db: Session,
    task_uuid: UUID,
    run_id: str,
    generator: Optional[Any] = None,
) -> Optional[ResearchTask]:
    task = get_research_task(db, task_uuid)

    if task is None:
        logger.warning(
            "Research task not found while executing run",
            extra={"task_uuid": str(task_uuid), "run_id": run_id},
        )
        return None

    if task.run_id and task.run_id != run_id:
        logger.info(
            "Skipping stale research run",
            extra={
                "task_uuid": str(task.uuid),
                "expected_run_id": task.run_id,
                "run_id": run_id,
            },
        )
        return task

    task.run_id = run_id
    task.status = ResearchTaskStatus.RUNNING.value
    task.current_stage = ResearchTaskStage.GENERATE_OPPORTUNITIES.value
    task.failure_reason = None
    save_research_task(db, task)

    try:
        from app.agents.graph import build_research_graph

        logger.info(
            "Starting opportunity research run",
            extra={"task_uuid": str(task.uuid), "run_id": run_id},
        )
        graph = build_research_graph()
        graph.invoke({"db": db, "task": task, "run_id": run_id, "generator": generator})
        db.refresh(task)
        logger.info(
            "Completed opportunity research run",
            extra={"task_uuid": str(task.uuid), "run_id": run_id},
        )
        return task
    except Exception as exc:
        db.rollback()
        task = get_research_task(db, task_uuid)

        if task is None:
            return None

        logger.exception(
            "Opportunity research run failed",
            extra={"task_uuid": str(task.uuid), "run_id": run_id},
        )
        return mark_task_failed(db, task, f"基础商机生成失败：{exc}")
