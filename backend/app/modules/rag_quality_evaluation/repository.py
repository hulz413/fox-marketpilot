from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.rag_quality_evaluation.models import (
    RagEvaluationCase,
    RagEvaluationResult,
    RagEvaluationRun,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_case_by_uuid(
    db: Session,
    case_uuid: UUID,
) -> Optional[RagEvaluationCase]:
    statement = select(RagEvaluationCase).where(RagEvaluationCase.uuid == case_uuid)
    return db.execute(statement).scalar_one_or_none()


def list_active_cases(
    db: Session,
    *,
    categories: Optional[list[str]] = None,
    enabled_only: bool = True,
) -> list[RagEvaluationCase]:
    statement = select(RagEvaluationCase).where(RagEvaluationCase.deleted_at.is_(None))

    if enabled_only:
        statement = statement.where(RagEvaluationCase.enabled.is_(True))

    if categories:
        statement = statement.where(RagEvaluationCase.category.in_(categories))

    statement = statement.order_by(
        RagEvaluationCase.category.asc(),
        RagEvaluationCase.id.asc(),
    )

    return list(db.execute(statement).scalars().all())


def add_case(db: Session, evaluation_case: RagEvaluationCase) -> RagEvaluationCase:
    db.add(evaluation_case)
    return evaluation_case


def add_run(db: Session, evaluation_run: RagEvaluationRun) -> RagEvaluationRun:
    db.add(evaluation_run)
    return evaluation_run


def add_result(
    db: Session,
    evaluation_result: RagEvaluationResult,
) -> RagEvaluationResult:
    db.add(evaluation_result)
    return evaluation_result


def list_active_results_by_run_id(
    db: Session,
    evaluation_run_id: int,
) -> list[RagEvaluationResult]:
    statement = (
        select(RagEvaluationResult)
        .where(
            RagEvaluationResult.evaluation_run_id == evaluation_run_id,
            RagEvaluationResult.deleted_at.is_(None),
        )
        .order_by(RagEvaluationResult.id.asc())
    )

    return list(db.execute(statement).scalars().all())


def soft_delete_case(db: Session, evaluation_case: RagEvaluationCase) -> None:
    evaluation_case.deleted_at = utc_now()
    db.add(evaluation_case)
