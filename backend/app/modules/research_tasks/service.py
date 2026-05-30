from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.integrations.langsmith import TraceContext, langsmith_trace
from app.modules.agent_runs import service as agent_run_events_service
from app.modules.research_tasks import repository
from app.modules.research_tasks.models import ResearchTask
from app.modules.research_tasks.schemas import (
    ResearchProgressAction,
    ResearchTaskCreate,
    ResearchTaskProgressRead,
    ResearchTaskRead,
    ResearchTaskStage,
    ResearchTaskStatus,
)

logger = logging.getLogger(__name__)

RUNNING_STATUSES = {
    ResearchTaskStatus.QUEUED.value,
    ResearchTaskStatus.RUNNING.value,
}

ROOT_STAGE = "opportunity_research"

FAILURE_STAGE_LABELS = {
    ROOT_STAGE: "基础研究",
    ResearchTaskStage.NORMALIZE_INTAKE.value: "需求整理",
    ResearchTaskStage.GENERATE_OPPORTUNITIES.value: "基础商机生成",
    ResearchTaskStage.VALIDATE_RESULTS.value: "结果校验",
    ResearchTaskStage.PERSIST_RESULTS.value: "结果保存",
    ResearchTaskStage.COLLECT_RESEARCH_SOURCES.value: "来源收集",
    ResearchTaskStage.GENERATE_DEMAND_INSIGHTS.value: "需求洞察生成",
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


def _safe_event_error_summary(error_summary: Optional[str]) -> Optional[str]:
    if not error_summary:
        return None

    first_line = error_summary.splitlines()[0].strip()

    if not first_line:
        return None

    if "Traceback" in first_line or first_line.lstrip().startswith('File "'):
        return "阶段执行失败，请查看任务失败原因。"

    return first_line[:300]


def _progress_actions(task: ResearchTask) -> list[ResearchProgressAction]:
    actions = [ResearchProgressAction.BACK_TO_TASKS]

    if task.status == ResearchTaskStatus.CREATED.value:
        actions.append(ResearchProgressAction.START)

    if task.status == ResearchTaskStatus.FAILED.value:
        actions.append(ResearchProgressAction.RERUN)

    if task.status == ResearchTaskStatus.COMPLETED.value:
        actions.extend(
            [
                ResearchProgressAction.VIEW_OPPORTUNITIES,
                ResearchProgressAction.VIEW_REPORT,
            ]
        )

    if task.trace_url:
        actions.append(ResearchProgressAction.OPEN_TRACE)

    return actions


def get_research_progress(
    db: Session,
    task_uuid: UUID,
) -> Optional[ResearchTaskProgressRead]:
    task = get_research_task(db, task_uuid)

    if task is None:
        return None

    events = []
    if task.run_id:
        events = agent_run_events_service.list_run_events(db, task, task.run_id)

    return ResearchTaskProgressRead(
        task=ResearchTaskRead.model_validate(task),
        run_id=task.run_id,
        trace_id=task.trace_id,
        trace_url=task.trace_url,
        status=task.status,
        current_stage=task.current_stage,
        failure_reason=task.failure_reason,
        events=[
            {
                "uuid": event.uuid,
                "run_id": event.run_id,
                "trace_id": event.trace_id,
                "stage": event.stage,
                "status": event.status,
                "started_at": event.started_at,
                "completed_at": event.completed_at,
                "duration_ms": event.duration_ms,
                "error_summary": _safe_event_error_summary(event.error_summary),
            }
            for event in events
        ],
        available_actions=_progress_actions(task),
    )


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
    task.trace_id = None
    task.trace_url = None
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


def update_task_trace(
    db: Session,
    task: ResearchTask,
    trace_context: Optional[TraceContext],
) -> ResearchTask:
    if trace_context is None:
        return task

    if trace_context.trace_id:
        task.trace_id = trace_context.trace_id

    if trace_context.trace_url:
        task.trace_url = trace_context.trace_url

    if trace_context.trace_id or trace_context.trace_url:
        return save_research_task(db, task)

    return task


def make_failure_reason(stage: str, exc: Exception) -> str:
    stage_label = FAILURE_STAGE_LABELS.get(stage, "基础研究")

    if stage == ResearchTaskStage.GENERATE_OPPORTUNITIES.value:
        return "基础商机生成失败：模型输出未通过结构化校验或生成过程异常。"

    if stage == ResearchTaskStage.PERSIST_RESULTS.value:
        return "基础商机生成失败：结果保存失败，请稍后重试。"

    if stage == ResearchTaskStage.COLLECT_RESEARCH_SOURCES.value:
        return "基础商机已生成，但来源收集失败；结果已保留，可稍后重试。"

    if stage == ResearchTaskStage.GENERATE_DEMAND_INSIGHTS.value:
        return "基础商机已生成，但需求洞察生成失败；结果已保留，可稍后重试。"

    if stage == ResearchTaskStage.VALIDATE_RESULTS.value:
        return "基础商机生成失败：结果校验失败，请稍后重试。"

    if stage == ResearchTaskStage.NORMALIZE_INTAKE.value:
        return "基础商机生成失败：需求整理失败，请检查任务输入后重试。"

    logger.debug("Research run failed in %s: %s", stage_label, type(exc).__name__)
    return f"基础商机生成失败：{stage_label}阶段异常，请稍后重试。"


def get_task_failure_stage(db: Session, task: ResearchTask, run_id: str) -> str:
    failed_events = [
        event
        for event in agent_run_events_service.list_run_events(db, task, run_id)
        if event.status == agent_run_events_service.STATUS_FAILED
        and event.stage != ROOT_STAGE
    ]

    if failed_events:
        return failed_events[-1].stage

    return task.current_stage or ROOT_STAGE


def make_trace_metadata(task: ResearchTask, run_id: str) -> dict[str, Any]:
    settings = get_settings()
    return {
        "task_uuid": str(task.uuid),
        "run_id": run_id,
        "environment": settings.environment,
        "research_boundary": "基础推荐，无外部前置调研",
        "langsmith_project": settings.langsmith_project,
    }


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
    task.current_stage = ResearchTaskStage.NORMALIZE_INTAKE.value
    task.failure_reason = None
    save_research_task(db, task)

    try:
        from app.agents.graph import build_research_graph

        logger.info(
            "Starting opportunity research run",
            extra={"task_uuid": str(task.uuid), "run_id": run_id},
        )
        graph = build_research_graph()

        with langsmith_trace(
            ROOT_STAGE,
            inputs={
                "task_uuid": str(task.uuid),
                "brief": task.brief,
            },
            metadata=make_trace_metadata(task, run_id),
        ) as trace_context:
            task = update_task_trace(db, task, trace_context)
            agent_run_events_service.start_stage(
                db,
                task,
                run_id=run_id,
                stage=ROOT_STAGE,
                trace_id=task.trace_id,
                metadata=make_trace_metadata(task, run_id),
            )
            graph.invoke(
                {
                    "db": db,
                    "task": task,
                    "run_id": run_id,
                    "trace_id": task.trace_id,
                    "generator": generator,
                }
            )
            db.refresh(task)
            agent_run_events_service.complete_stage(
                db,
                task,
                run_id=run_id,
                stage=ROOT_STAGE,
                trace_id=task.trace_id,
                metadata={"status": ResearchTaskStatus.COMPLETED.value},
            )
        db.refresh(task)
        logger.info(
            "Completed opportunity research run",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                "trace_id": task.trace_id,
                "stage": ROOT_STAGE,
            },
        )
        return task
    except Exception as exc:
        db.rollback()
        task = get_research_task(db, task_uuid)

        if task is None:
            return None

        failed_stage = get_task_failure_stage(db, task, run_id)
        failure_reason = make_failure_reason(failed_stage, exc)

        try:
            agent_run_events_service.fail_stage(
                db,
                task,
                run_id=run_id,
                stage=ROOT_STAGE,
                trace_id=task.trace_id,
                error_summary=failure_reason,
                metadata={"failed_stage": failed_stage},
            )
        except Exception:
            logger.warning(
                "Failed to persist root agent run failure event",
                exc_info=True,
                extra={
                    "task_uuid": str(task.uuid),
                    "run_id": run_id,
                    "trace_id": task.trace_id,
                    "stage": ROOT_STAGE,
                },
            )

        logger.exception(
            "Opportunity research run failed",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                "trace_id": task.trace_id,
                "stage": failed_stage,
            },
        )
        return mark_task_failed(db, task, failure_reason)
