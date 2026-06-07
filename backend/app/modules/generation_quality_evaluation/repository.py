from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.generation_quality_evaluation.models import (
    GenerationEvaluationCase,
    GenerationEvaluationResult,
    GenerationEvaluationRun,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_case_by_uuid(
    db: Session,
    case_uuid: UUID,
) -> Optional[GenerationEvaluationCase]:
    statement = select(GenerationEvaluationCase).where(
        GenerationEvaluationCase.uuid == case_uuid
    )
    return db.execute(statement).scalar_one_or_none()


def list_active_cases(
    db: Session,
    *,
    categories: Optional[list[str]] = None,
    enabled_only: bool = True,
) -> list[GenerationEvaluationCase]:
    statement = select(GenerationEvaluationCase).where(
        GenerationEvaluationCase.deleted_at.is_(None)
    )

    if enabled_only:
        statement = statement.where(GenerationEvaluationCase.enabled.is_(True))

    if categories:
        statement = statement.where(GenerationEvaluationCase.category.in_(categories))

    statement = statement.order_by(
        GenerationEvaluationCase.category.asc(),
        GenerationEvaluationCase.id.asc(),
    )

    return list(db.execute(statement).scalars().all())


def add_case(
    db: Session,
    evaluation_case: GenerationEvaluationCase,
) -> GenerationEvaluationCase:
    db.add(evaluation_case)
    return evaluation_case


def add_run(
    db: Session,
    evaluation_run: GenerationEvaluationRun,
) -> GenerationEvaluationRun:
    db.add(evaluation_run)
    return evaluation_run


def add_result(
    db: Session,
    evaluation_result: GenerationEvaluationResult,
) -> GenerationEvaluationResult:
    db.add(evaluation_result)
    return evaluation_result


def get_latest_active_run_by_task_id(
    db: Session,
    research_task_id: int,
) -> Optional[GenerationEvaluationRun]:
    statement = (
        select(GenerationEvaluationRun)
        .where(
            GenerationEvaluationRun.research_task_id == research_task_id,
            GenerationEvaluationRun.deleted_at.is_(None),
        )
        .order_by(
            GenerationEvaluationRun.created_at.desc(),
            GenerationEvaluationRun.id.desc(),
        )
    )

    return db.execute(statement).scalars().first()


def list_active_results_by_run_id(
    db: Session,
    evaluation_run_id: int,
) -> list[GenerationEvaluationResult]:
    statement = (
        select(GenerationEvaluationResult)
        .where(
            GenerationEvaluationResult.evaluation_run_id == evaluation_run_id,
            GenerationEvaluationResult.deleted_at.is_(None),
        )
        .order_by(GenerationEvaluationResult.id.asc())
    )

    return list(db.execute(statement).scalars().all())


def soft_delete_case(db: Session, evaluation_case: GenerationEvaluationCase) -> None:
    evaluation_case.deleted_at = utc_now()
    db.add(evaluation_case)
