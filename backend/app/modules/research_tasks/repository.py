from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.research_tasks.models import ResearchTask


def create_research_task(db: Session, task: ResearchTask) -> ResearchTask:
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_active_research_tasks(db: Session, limit: int = 50) -> list[ResearchTask]:
    statement = (
        select(ResearchTask)
        .where(ResearchTask.deleted_at.is_(None))
        .order_by(ResearchTask.created_at.desc(), ResearchTask.id.desc())
        .limit(limit)
    )

    return list(db.execute(statement).scalars().all())


def get_active_research_task_by_uuid(
    db: Session,
    task_uuid: UUID,
) -> Optional[ResearchTask]:
    statement = select(ResearchTask).where(
        ResearchTask.uuid == task_uuid,
        ResearchTask.deleted_at.is_(None),
    )

    return db.execute(statement).scalar_one_or_none()


def get_active_research_task_by_id(
    db: Session,
    task_id: int,
) -> Optional[ResearchTask]:
    statement = select(ResearchTask).where(
        ResearchTask.id == task_id,
        ResearchTask.deleted_at.is_(None),
    )

    return db.execute(statement).scalar_one_or_none()


def save_research_task(db: Session, task: ResearchTask) -> ResearchTask:
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
