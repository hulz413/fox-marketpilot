from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.modules.agent_runs import repository
from app.modules.agent_runs.models import AgentRunEvent
from app.modules.research_tasks.models import ResearchTask

logger = logging.getLogger(__name__)

STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _duration_ms(started_at: datetime, completed_at: datetime) -> int:
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)
    return max(0, int((completed_at - started_at).total_seconds() * 1000))


def _merge_metadata(
    event: AgentRunEvent,
    metadata: Optional[dict[str, Any]],
) -> dict[str, Any]:
    current = dict(event.event_metadata or {})
    if metadata:
        current.update(metadata)
    return current


def start_stage(
    db: Session,
    task: ResearchTask,
    *,
    run_id: str,
    stage: str,
    trace_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> AgentRunEvent:
    event = repository.get_active_event_by_run_and_stage(db, task.id, run_id, stage)

    if event is None:
        event = AgentRunEvent(
            research_task_id=task.id,
            run_id=run_id,
            trace_id=trace_id,
            stage=stage,
            status=STATUS_RUNNING,
            started_at=utc_now(),
            event_metadata=metadata or {},
        )
        saved = repository.add_event(db, event)
    else:
        event.trace_id = trace_id or event.trace_id
        event.status = STATUS_RUNNING
        event.error_summary = None
        event.completed_at = None
        event.duration_ms = None
        event.event_metadata = _merge_metadata(event, metadata)
        saved = repository.save_event(db, event)

    logger.info(
        "Agent run stage started",
        extra={
            "task_uuid": str(task.uuid),
            "run_id": run_id,
            "trace_id": trace_id,
            "stage": stage,
        },
    )
    return saved


def complete_stage(
    db: Session,
    task: ResearchTask,
    *,
    run_id: str,
    stage: str,
    trace_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> AgentRunEvent:
    event = repository.get_active_event_by_run_and_stage(db, task.id, run_id, stage)
    completed_at = utc_now()

    if event is None:
        event = AgentRunEvent(
            research_task_id=task.id,
            run_id=run_id,
            trace_id=trace_id,
            stage=stage,
            status=STATUS_COMPLETED,
            started_at=completed_at,
            completed_at=completed_at,
            duration_ms=0,
            event_metadata=metadata or {},
        )
    else:
        event.trace_id = trace_id or event.trace_id
        event.status = STATUS_COMPLETED
        event.completed_at = completed_at
        event.duration_ms = _duration_ms(event.started_at, completed_at)
        event.error_summary = None
        event.event_metadata = _merge_metadata(event, metadata)

    saved = repository.save_event(db, event)
    logger.info(
        "Agent run stage completed",
        extra={
            "task_uuid": str(task.uuid),
            "run_id": run_id,
            "trace_id": trace_id,
            "stage": stage,
            "duration_ms": saved.duration_ms,
        },
    )
    return saved


def fail_stage(
    db: Session,
    task: ResearchTask,
    *,
    run_id: str,
    stage: str,
    trace_id: Optional[str] = None,
    error_summary: str,
    metadata: Optional[dict[str, Any]] = None,
) -> AgentRunEvent:
    event = repository.get_active_event_by_run_and_stage(db, task.id, run_id, stage)
    completed_at = utc_now()

    if event is None:
        event = AgentRunEvent(
            research_task_id=task.id,
            run_id=run_id,
            trace_id=trace_id,
            stage=stage,
            status=STATUS_FAILED,
            started_at=completed_at,
            completed_at=completed_at,
            duration_ms=0,
            error_summary=error_summary[:1000],
            event_metadata=metadata or {},
        )
    else:
        event.trace_id = trace_id or event.trace_id
        event.status = STATUS_FAILED
        event.completed_at = completed_at
        event.duration_ms = _duration_ms(event.started_at, completed_at)
        event.error_summary = error_summary[:1000]
        event.event_metadata = _merge_metadata(event, metadata)

    saved = repository.save_event(db, event)
    logger.error(
        "Agent run stage failed",
        extra={
            "task_uuid": str(task.uuid),
            "run_id": run_id,
            "trace_id": trace_id,
            "stage": stage,
            "duration_ms": saved.duration_ms,
            "error_summary": saved.error_summary,
        },
    )
    return saved


def list_run_events(
    db: Session,
    task: ResearchTask,
    run_id: str,
) -> list[AgentRunEvent]:
    return repository.list_active_events_by_run(db, task.id, run_id)
