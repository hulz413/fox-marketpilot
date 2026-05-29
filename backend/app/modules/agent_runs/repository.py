from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.agent_runs.models import AgentRunEvent


def add_event(db: Session, event: AgentRunEvent) -> AgentRunEvent:
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def save_event(db: Session, event: AgentRunEvent) -> AgentRunEvent:
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_active_event_by_run_and_stage(
    db: Session,
    research_task_id: int,
    run_id: str,
    stage: str,
) -> Optional[AgentRunEvent]:
    statement = (
        select(AgentRunEvent)
        .where(
            AgentRunEvent.research_task_id == research_task_id,
            AgentRunEvent.run_id == run_id,
            AgentRunEvent.stage == stage,
            AgentRunEvent.deleted_at.is_(None),
        )
        .order_by(AgentRunEvent.started_at.desc(), AgentRunEvent.id.desc())
        .limit(1)
    )

    return db.execute(statement).scalar_one_or_none()


def list_active_events_by_run(
    db: Session,
    research_task_id: int,
    run_id: str,
) -> list[AgentRunEvent]:
    statement = (
        select(AgentRunEvent)
        .where(
            AgentRunEvent.research_task_id == research_task_id,
            AgentRunEvent.run_id == run_id,
            AgentRunEvent.deleted_at.is_(None),
        )
        .order_by(AgentRunEvent.started_at.asc(), AgentRunEvent.id.asc())
    )

    return list(db.execute(statement).scalars().all())
