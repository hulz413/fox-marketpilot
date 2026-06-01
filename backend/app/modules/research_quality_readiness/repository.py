from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.research_quality_readiness.models import (
    ResearchQualityReadinessRun,
)


def create_readiness_run(
    db: Session,
    readiness_run: ResearchQualityReadinessRun,
) -> ResearchQualityReadinessRun:
    db.add(readiness_run)
    db.commit()
    db.refresh(readiness_run)
    return readiness_run


def save_readiness_run(
    db: Session,
    readiness_run: ResearchQualityReadinessRun,
) -> ResearchQualityReadinessRun:
    db.add(readiness_run)
    db.commit()
    db.refresh(readiness_run)
    return readiness_run


def get_latest_active_readiness_run_by_task_id(
    db: Session,
    research_task_id: int,
) -> Optional[ResearchQualityReadinessRun]:
    statement = (
        select(ResearchQualityReadinessRun)
        .where(
            ResearchQualityReadinessRun.research_task_id == research_task_id,
            ResearchQualityReadinessRun.deleted_at.is_(None),
        )
        .order_by(
            ResearchQualityReadinessRun.created_at.desc(),
            ResearchQualityReadinessRun.id.desc(),
        )
    )

    return db.execute(statement).scalars().first()
