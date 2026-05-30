from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.opportunities.models import Opportunity
from app.modules.sources.models import ResearchSource
from app.modules.competitor_references.models import (
    CompetitorReference,
    CompetitorReferenceSource,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def add_references(
    db: Session,
    references: list[CompetitorReference],
) -> list[CompetitorReference]:
    db.add_all(references)
    return references


def add_source_links(
    db: Session,
    links: list[CompetitorReferenceSource],
) -> list[CompetitorReferenceSource]:
    db.add_all(links)
    return links


def list_active_references_by_task_id(
    db: Session,
    research_task_id: int,
) -> list[CompetitorReference]:
    statement = (
        select(CompetitorReference)
        .join(Opportunity, CompetitorReference.opportunity_id == Opportunity.id)
        .where(
            CompetitorReference.research_task_id == research_task_id,
            CompetitorReference.deleted_at.is_(None),
            Opportunity.deleted_at.is_(None),
        )
        .order_by(
            Opportunity.rank.asc(),
            CompetitorReference.rank.asc(),
            CompetitorReference.id.asc(),
        )
    )

    return list(db.execute(statement).scalars().all())


def list_active_references_by_opportunity_id(
    db: Session,
    opportunity_id: int,
) -> list[CompetitorReference]:
    statement = (
        select(CompetitorReference)
        .where(
            CompetitorReference.opportunity_id == opportunity_id,
            CompetitorReference.deleted_at.is_(None),
        )
        .order_by(CompetitorReference.rank.asc(), CompetitorReference.id.asc())
    )

    return list(db.execute(statement).scalars().all())


def list_active_reference_source_rows(
    db: Session,
    reference_id: int,
) -> list[tuple[CompetitorReferenceSource, ResearchSource]]:
    statement = (
        select(CompetitorReferenceSource, ResearchSource)
        .join(
            ResearchSource,
            CompetitorReferenceSource.research_source_id == ResearchSource.id,
        )
        .where(
            CompetitorReferenceSource.competitor_reference_id == reference_id,
            CompetitorReferenceSource.deleted_at.is_(None),
            ResearchSource.deleted_at.is_(None),
        )
        .order_by(CompetitorReferenceSource.id.asc())
    )

    return [(row[0], row[1]) for row in db.execute(statement).all()]


def list_active_references_for_soft_delete(
    db: Session,
    research_task_id: int,
) -> list[CompetitorReference]:
    statement = select(CompetitorReference).where(
        CompetitorReference.research_task_id == research_task_id,
        CompetitorReference.deleted_at.is_(None),
    )

    return list(db.execute(statement).scalars().all())


def soft_delete_active_references_by_task_id(
    db: Session,
    research_task_id: int,
) -> None:
    deleted_at = utc_now()

    for reference in list_active_references_for_soft_delete(db, research_task_id):
        reference.deleted_at = deleted_at

        for link, _ in list_active_reference_source_rows(db, reference.id):
            link.deleted_at = deleted_at
