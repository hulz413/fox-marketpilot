from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.sources.models import ResearchSource


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def add_sources(
    db: Session,
    sources: list[ResearchSource],
) -> list[ResearchSource]:
    db.add_all(sources)
    return sources


def list_active_sources_by_task_id(
    db: Session,
    research_task_id: int,
) -> list[ResearchSource]:
    statement = (
        select(ResearchSource)
        .where(
            ResearchSource.research_task_id == research_task_id,
            ResearchSource.deleted_at.is_(None),
        )
        .order_by(
            ResearchSource.source_type.asc(),
            ResearchSource.opportunity_id.asc().nullsfirst(),
            ResearchSource.collected_at.asc(),
            ResearchSource.id.asc(),
        )
    )

    return list(db.execute(statement).scalars().all())


def list_active_sources_by_opportunity_id(
    db: Session,
    opportunity_id: int,
) -> list[ResearchSource]:
    statement = (
        select(ResearchSource)
        .where(
            ResearchSource.opportunity_id == opportunity_id,
            ResearchSource.deleted_at.is_(None),
        )
        .order_by(
            ResearchSource.source_type.asc(),
            ResearchSource.collected_at.asc(),
            ResearchSource.id.asc(),
        )
    )

    return list(db.execute(statement).scalars().all())


def soft_delete_active_sources_by_task_id(
    db: Session,
    research_task_id: int,
) -> None:
    deleted_at = utc_now()

    for source in list_active_sources_by_task_id(db, research_task_id):
        source.deleted_at = deleted_at


def active_urls_by_task_id(db: Session, research_task_id: int) -> set[str]:
    return {
        source.url
        for source in list_active_sources_by_task_id(db, research_task_id)
        if source.url
    }
