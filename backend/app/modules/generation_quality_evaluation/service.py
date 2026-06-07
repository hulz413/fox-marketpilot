from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.integrations.langsmith import langsmith_trace
from app.modules.action_plans import service as action_plans_service
from app.modules.competitor_references import service as competitor_references_service
from app.modules.demand_insights import service as demand_insights_service
from app.modules.generation_quality_evaluation import repository
from app.modules.generation_quality_evaluation.fixtures import (
    DEFAULT_GENERATION_EVALUATION_CASES,
)
from app.modules.generation_quality_evaluation.models import (
    GenerationEvaluationCase,
    GenerationEvaluationResult,
    GenerationEvaluationRun,
)
from app.modules.generation_quality_evaluation.schemas import (
    GenerationEvaluationCaseCreate,
    GenerationEvaluationResultRead,
    GenerationEvaluationResultStatus,
    GenerationEvaluationRunRead,
    GenerationEvaluationRunStatus,
    GenerationEvaluationOverallStatus,
)
from app.modules.generation_quality_evaluation.scorer import (
    GenerationEvaluationContext,
    score_generation_case,
)
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunity_risks import service as opportunity_risks_service
from app.modules.rag_quality_evaluation import service as rag_quality_evaluation_service
from app.modules.research_tasks.models import ResearchTask
from app.modules.research_tasks.schemas import ResearchTaskStatus
from app.modules.supply_candidates import service as supply_candidates_service
from app.modules.validation_budgets import service as validation_budgets_service

logger = logging.getLogger(__name__)


class GenerationEvaluationUnavailableError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_default_evaluation_cases(db: Session) -> list[GenerationEvaluationCase]:
    cases: list[GenerationEvaluationCase] = []

    for item in DEFAULT_GENERATION_EVALUATION_CASES:
        payload = GenerationEvaluationCaseCreate.model_validate(item)
        existing = (
            repository.get_case_by_uuid(db, payload.uuid)
            if payload.uuid is not None
            else None
        )

        if existing is None:
            evaluation_case = GenerationEvaluationCase(
                uuid=payload.uuid,
                category=payload.category.value,
                name=payload.name,
                input_constraints=payload.input_constraints,
                expected_signals=payload.expected_signals,
                rubric=payload.rubric,
                grading_rubric=payload.grading_rubric,
                enabled=payload.enabled,
                case_metadata=payload.case_metadata,
            )
            repository.add_case(db, evaluation_case)
            cases.append(evaluation_case)
            continue

        if existing.deleted_at is None:
            existing.category = payload.category.value
            existing.name = payload.name
            existing.input_constraints = payload.input_constraints
            existing.expected_signals = payload.expected_signals
            existing.rubric = payload.rubric
            existing.grading_rubric = payload.grading_rubric
            existing.enabled = payload.enabled
            existing.case_metadata = payload.case_metadata
            db.add(existing)
            cases.append(existing)

    db.commit()

    for evaluation_case in cases:
        db.refresh(evaluation_case)

    return cases


def list_active_evaluation_cases(
    db: Session,
    *,
    categories: Optional[list[str]] = None,
) -> list[GenerationEvaluationCase]:
    return repository.list_active_cases(db, categories=categories)


def get_latest_generation_evaluation_run(
    db: Session,
    task: ResearchTask,
) -> Optional[GenerationEvaluationRun]:
    return repository.get_latest_active_run_by_task_id(db, task.id)


def build_case_snapshot(evaluation_case: GenerationEvaluationCase) -> dict[str, Any]:
    return {
        "uuid": str(evaluation_case.uuid),
        "category": evaluation_case.category,
        "name": evaluation_case.name,
        "input_constraints": dict(evaluation_case.input_constraints),
        "expected_signals": list(evaluation_case.expected_signals),
        "rubric": dict(evaluation_case.rubric),
        "grading_rubric": evaluation_case.grading_rubric,
    }


def run_generation_evaluation(
    db: Session,
    task: ResearchTask,
    *,
    name: Optional[str] = None,
    categories: Optional[list[str]] = None,
    load_defaults: bool = True,
) -> GenerationEvaluationRun:
    if task.status != ResearchTaskStatus.COMPLETED.value:
        raise GenerationEvaluationUnavailableError(
            f"研究任务尚未完成，当前状态：{task.status}。"
        )

    if load_defaults:
        load_default_evaluation_cases(db)

    evaluation_cases = list_active_evaluation_cases(db, categories=categories)
    evaluation_run = GenerationEvaluationRun(
        research_task_id=task.id,
        name=name or f"生成质量评测 - {task.title}",
        status=GenerationEvaluationRunStatus.RUNNING.value,
        overall_status=GenerationEvaluationOverallStatus.WARNING.value,
        research_run_id=task.run_id,
        config={"categories": categories or [], "scorer": "deterministic_rubric"},
        summary_metrics={},
        summary="正在运行生成质量评测。",
        case_total=len(evaluation_cases),
        started_at=utc_now(),
    )
    repository.add_run(db, evaluation_run)
    db.commit()
    db.refresh(evaluation_run)

    with langsmith_trace(
        "generation_quality_evaluation",
        inputs={
            "task_uuid": str(task.uuid),
            "case_count": len(evaluation_cases),
        },
        metadata={
            "evaluation_run_uuid": str(evaluation_run.uuid),
            "task_uuid": str(task.uuid),
            "research_run_id": task.run_id,
            "case_count": len(evaluation_cases),
            "categories": categories or [],
        },
    ) as trace_context:
        if trace_context is not None:
            evaluation_run.trace_id = trace_context.trace_id
            evaluation_run.trace_url = trace_context.trace_url
            db.add(evaluation_run)
            db.commit()
            db.refresh(evaluation_run)

        if not evaluation_cases:
            evaluation_run.status = GenerationEvaluationRunStatus.FAILED.value
            evaluation_run.overall_status = GenerationEvaluationOverallStatus.FAILED.value
            evaluation_run.summary = "没有可用的生成质量评测 case。"
            evaluation_run.error_summary = "没有可用的生成质量评测 case。"
            evaluation_run.completed_at = utc_now()
            db.add(evaluation_run)
            db.commit()
            db.refresh(evaluation_run)
            return evaluation_run

        context = build_evaluation_context(db, task)
        for evaluation_case in evaluation_cases:
            execute_evaluation_case(db, task, evaluation_run, evaluation_case, context)

    complete_evaluation_run(db, evaluation_run)
    db.refresh(evaluation_run)
    logger.info(
        "Generation quality evaluation completed",
        extra={
            "task_uuid": str(task.uuid),
            "evaluation_run_uuid": str(evaluation_run.uuid),
            "overall_status": evaluation_run.overall_status,
            "case_total": evaluation_run.case_total,
        },
    )
    return evaluation_run


def build_evaluation_context(
    db: Session,
    task: ResearchTask,
) -> GenerationEvaluationContext:
    return GenerationEvaluationContext(
        task=task,
        opportunities=opportunities_service.list_task_opportunities(db, task),
        demand_insights=demand_insights_service.list_task_demand_insights(db, task),
        supply_candidates=supply_candidates_service.list_task_supply_candidates(db, task),
        competitor_references=competitor_references_service.list_task_competitor_references(
            db,
            task,
        ),
        validation_budgets=validation_budgets_service.list_task_validation_budgets(
            db,
            task,
        ),
        opportunity_risks=opportunity_risks_service.list_task_opportunity_risks(
            db,
            task,
        ),
        action_plans=action_plans_service.list_task_action_plans(db, task),
    )


def execute_evaluation_case(
    db: Session,
    task: ResearchTask,
    evaluation_run: GenerationEvaluationRun,
    evaluation_case: GenerationEvaluationCase,
    context: GenerationEvaluationContext,
) -> GenerationEvaluationResult:
    started_at = utc_now()
    case_snapshot = build_case_snapshot(evaluation_case)

    try:
        with langsmith_trace(
            "generation_quality_evaluation_case",
            inputs={
                "case_uuid": str(evaluation_case.uuid),
                "category": evaluation_case.category,
            },
            metadata={
                "evaluation_run_uuid": str(evaluation_run.uuid),
                "case_uuid": str(evaluation_case.uuid),
                "task_uuid": str(task.uuid),
                "category": evaluation_case.category,
            },
        ):
            score = score_generation_case(evaluation_case, context)

        evaluation_result = GenerationEvaluationResult(
            evaluation_run_id=evaluation_run.id,
            evaluation_case_id=evaluation_case.id,
            status=score.status.value,
            category=evaluation_case.category,
            name=evaluation_case.name,
            case_snapshot=case_snapshot,
            target_scope="task",
            affected_opportunity_uuids=[
                str(item) for item in score.affected_opportunity_uuids
            ],
            rubric_scores=score.rubric_scores,
            reasons=score.reasons,
            actions=score.actions,
            scoring_notes=score.scoring_notes,
            error_summary=None,
            started_at=started_at,
            completed_at=utc_now(),
        )
    except Exception as exc:
        evaluation_result = GenerationEvaluationResult(
            evaluation_run_id=evaluation_run.id,
            evaluation_case_id=evaluation_case.id,
            status=GenerationEvaluationResultStatus.FAILED.value,
            category=evaluation_case.category,
            name=evaluation_case.name,
            case_snapshot=case_snapshot,
            target_scope="task",
            affected_opportunity_uuids=[],
            rubric_scores={
                evaluation_case.category: {
                    "status": GenerationEvaluationResultStatus.FAILED.value,
                    "reason_count": 1,
                }
            },
            reasons=["生成质量评测 case 执行失败。"],
            actions=["查看应用日志或单独运行生成质量评测 runner。"],
            scoring_notes="生成质量评测 case 执行失败。",
            error_summary=(
                safe_error_summary(str(exc))
                or f"生成质量评测 case 执行失败（{type(exc).__name__}）。"
            ),
            started_at=started_at,
            completed_at=utc_now(),
        )

    repository.add_result(db, evaluation_result)
    db.commit()
    db.refresh(evaluation_result)
    trace_case_result(task, evaluation_run, evaluation_result)
    return evaluation_result


def trace_case_result(
    task: ResearchTask,
    evaluation_run: GenerationEvaluationRun,
    evaluation_result: GenerationEvaluationResult,
) -> None:
    with langsmith_trace(
        "generation_quality_evaluation_case_result",
        inputs={
            "case_uuid": str(evaluation_result.case_snapshot.get("uuid")),
            "category": evaluation_result.category,
        },
        metadata={
            "evaluation_run_uuid": str(evaluation_run.uuid),
            "task_uuid": str(task.uuid),
            "case_uuid": str(evaluation_result.case_snapshot.get("uuid")),
            "category": evaluation_result.category,
            "status": evaluation_result.status,
            "reason_count": len(evaluation_result.reasons),
            "affected_opportunity_uuids": evaluation_result.affected_opportunity_uuids,
        },
    ):
        return None


def complete_evaluation_run(
    db: Session,
    evaluation_run: GenerationEvaluationRun,
) -> None:
    results = repository.list_active_results_by_run_id(db, evaluation_run.id)
    passed = [
        result
        for result in results
        if result.status == GenerationEvaluationResultStatus.PASSED.value
    ]
    warning = [
        result
        for result in results
        if result.status == GenerationEvaluationResultStatus.WARNING.value
    ]
    failed = [
        result
        for result in results
        if result.status == GenerationEvaluationResultStatus.FAILED.value
    ]
    skipped = [
        result
        for result in results
        if result.status == GenerationEvaluationResultStatus.SKIPPED.value
    ]

    evaluation_run.case_total = len(results)
    evaluation_run.case_passed_count = len(passed)
    evaluation_run.case_warning_count = len(warning)
    evaluation_run.case_failed_count = len(failed)
    evaluation_run.case_skipped_count = len(skipped)
    evaluation_run.summary_metrics = build_summary_metrics(results)
    evaluation_run.overall_status = aggregate_overall_status(results)
    evaluation_run.status = aggregate_run_status(results)
    evaluation_run.summary = build_summary(evaluation_run.overall_status, results)
    evaluation_run.completed_at = utc_now()
    db.add(evaluation_run)
    db.commit()


def aggregate_run_status(results: list[GenerationEvaluationResult]) -> str:
    if not results:
        return GenerationEvaluationRunStatus.FAILED.value

    failed = [
        result
        for result in results
        if result.status == GenerationEvaluationResultStatus.FAILED.value
    ]
    if failed and len(failed) == len(results):
        return GenerationEvaluationRunStatus.FAILED.value
    if failed:
        return GenerationEvaluationRunStatus.PARTIAL.value
    return GenerationEvaluationRunStatus.COMPLETED.value


def aggregate_overall_status(results: list[GenerationEvaluationResult]) -> str:
    statuses = [result.status for result in results]
    if GenerationEvaluationResultStatus.FAILED.value in statuses:
        return GenerationEvaluationOverallStatus.FAILED.value
    if (
        GenerationEvaluationResultStatus.WARNING.value in statuses
        or GenerationEvaluationResultStatus.SKIPPED.value in statuses
    ):
        return GenerationEvaluationOverallStatus.WARNING.value
    return GenerationEvaluationOverallStatus.PASSED.value


def build_summary_metrics(
    results: list[GenerationEvaluationResult],
) -> dict[str, Any]:
    status_counts = {
        status.value: sum(1 for result in results if result.status == status.value)
        for status in GenerationEvaluationResultStatus
    }
    dimensions: dict[str, dict[str, int]] = {}
    for result in results:
        for dimension, score in (result.rubric_scores or {}).items():
            dimension_status = str(score.get("status") or result.status)
            dimension_metrics = dimensions.setdefault(
                dimension,
                {"passed": 0, "warning": 0, "failed": 0, "skipped": 0},
            )
            if dimension_status in dimension_metrics:
                dimension_metrics[dimension_status] += 1

    return {
        "case_total": len(results),
        "status_counts": status_counts,
        "rubric_dimensions": dimensions,
    }


def build_summary(
    overall_status: str,
    results: list[GenerationEvaluationResult],
) -> str:
    failed_count = sum(
        1
        for result in results
        if result.status == GenerationEvaluationResultStatus.FAILED.value
    )
    warning_count = sum(
        1
        for result in results
        if result.status == GenerationEvaluationResultStatus.WARNING.value
    )
    skipped_count = sum(
        1
        for result in results
        if result.status == GenerationEvaluationResultStatus.SKIPPED.value
    )

    if overall_status == GenerationEvaluationOverallStatus.PASSED.value:
        return "生成质量评测通过，未发现明显约束或谨慎边界问题。"
    if overall_status == GenerationEvaluationOverallStatus.FAILED.value:
        return f"生成质量评测未通过，{failed_count} 个 case 失败，建议复查后再演示。"
    return (
        "生成质量评测存在需要复查的项目，"
        f"{warning_count} 个 warning，{skipped_count} 个 skipped。"
    )


def is_stale(
    evaluation_run: GenerationEvaluationRun,
    task: ResearchTask,
) -> bool:
    return bool(task.run_id and evaluation_run.research_run_id != task.run_id)


def evaluation_run_to_read(
    evaluation_run: GenerationEvaluationRun,
    *,
    task: ResearchTask,
) -> GenerationEvaluationRunRead:
    return GenerationEvaluationRunRead(
        uuid=evaluation_run.uuid,
        research_task_uuid=task.uuid,
        name=evaluation_run.name,
        status=evaluation_run.status,
        overall_status=evaluation_run.overall_status,
        research_run_id=evaluation_run.research_run_id,
        trace_id=evaluation_run.trace_id,
        trace_url=evaluation_run.trace_url,
        config=evaluation_run.config,
        summary_metrics=evaluation_run.summary_metrics,
        summary=evaluation_run.summary,
        case_total=evaluation_run.case_total,
        case_passed_count=evaluation_run.case_passed_count,
        case_warning_count=evaluation_run.case_warning_count,
        case_failed_count=evaluation_run.case_failed_count,
        case_skipped_count=evaluation_run.case_skipped_count,
        error_summary=safe_error_summary(evaluation_run.error_summary),
        stale=is_stale(evaluation_run, task),
        started_at=evaluation_run.started_at,
        completed_at=evaluation_run.completed_at,
        created_at=evaluation_run.created_at,
        updated_at=evaluation_run.updated_at,
        deleted_at=evaluation_run.deleted_at,
    )


def evaluation_result_to_read(
    evaluation_result: GenerationEvaluationResult,
    *,
    evaluation_case_uuid: UUID,
) -> GenerationEvaluationResultRead:
    return GenerationEvaluationResultRead(
        uuid=evaluation_result.uuid,
        evaluation_case_uuid=evaluation_case_uuid,
        status=evaluation_result.status,
        category=evaluation_result.category,
        name=evaluation_result.name,
        case_snapshot=evaluation_result.case_snapshot,
        target_scope=evaluation_result.target_scope,
        affected_opportunity_uuids=evaluation_result.affected_opportunity_uuids,
        rubric_scores=evaluation_result.rubric_scores,
        reasons=evaluation_result.reasons,
        actions=evaluation_result.actions,
        scoring_notes=evaluation_result.scoring_notes,
        error_summary=safe_error_summary(evaluation_result.error_summary),
        started_at=evaluation_result.started_at,
        completed_at=evaluation_result.completed_at,
        created_at=evaluation_result.created_at,
        updated_at=evaluation_result.updated_at,
        deleted_at=evaluation_result.deleted_at,
    )


def export_run_results(
    db: Session,
    task: ResearchTask,
    evaluation_run: GenerationEvaluationRun,
) -> dict[str, Any]:
    results = repository.list_active_results_by_run_id(db, evaluation_run.id)
    return {
        "run": evaluation_run_to_read(evaluation_run, task=task).model_dump(mode="json"),
        "results": [
            evaluation_result_to_read(
                result,
                evaluation_case_uuid=UUID(str(result.case_snapshot["uuid"])),
            ).model_dump(mode="json")
            for result in results
        ],
    }


def safe_error_summary(value: Optional[str]) -> Optional[str]:
    return rag_quality_evaluation_service.safe_error_summary(value)


def dump_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)

