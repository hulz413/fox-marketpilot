from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.opportunities.models import Opportunity
from app.modules.sources.models import ResearchSource
from app.modules.supply_candidates.models import (
    SupplyCandidate,
    SupplyCandidateSource,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def add_candidates(
    db: Session,
    candidates: list[SupplyCandidate],
) -> list[SupplyCandidate]:
    db.add_all(candidates)
    return candidates


def add_source_links(
    db: Session,
    links: list[SupplyCandidateSource],
) -> list[SupplyCandidateSource]:
    db.add_all(links)
    return links


def list_active_candidates_by_task_id(
    db: Session,
    research_task_id: int,
) -> list[SupplyCandidate]:
    statement = (
        select(SupplyCandidate)
        .join(Opportunity, SupplyCandidate.opportunity_id == Opportunity.id)
        .where(
            SupplyCandidate.research_task_id == research_task_id,
            SupplyCandidate.deleted_at.is_(None),
            Opportunity.deleted_at.is_(None),
        )
        .order_by(Opportunity.rank.asc(), SupplyCandidate.rank.asc(), SupplyCandidate.id.asc())
    )

    return list(db.execute(statement).scalars().all())


def list_active_candidates_by_opportunity_id(
    db: Session,
    opportunity_id: int,
) -> list[SupplyCandidate]:
    statement = (
        select(SupplyCandidate)
        .where(
            SupplyCandidate.opportunity_id == opportunity_id,
            SupplyCandidate.deleted_at.is_(None),
        )
        .order_by(SupplyCandidate.rank.asc(), SupplyCandidate.id.asc())
    )

    return list(db.execute(statement).scalars().all())


def list_active_candidate_source_rows(
    db: Session,
    candidate_id: int,
) -> list[tuple[SupplyCandidateSource, ResearchSource]]:
    statement = (
        select(SupplyCandidateSource, ResearchSource)
        .join(
            ResearchSource,
            SupplyCandidateSource.research_source_id == ResearchSource.id,
        )
        .where(
            SupplyCandidateSource.supply_candidate_id == candidate_id,
            SupplyCandidateSource.deleted_at.is_(None),
            ResearchSource.deleted_at.is_(None),
        )
        .order_by(SupplyCandidateSource.id.asc())
    )

    return [(row[0], row[1]) for row in db.execute(statement).all()]


def list_active_candidates_for_soft_delete(
    db: Session,
    research_task_id: int,
) -> list[SupplyCandidate]:
    statement = select(SupplyCandidate).where(
        SupplyCandidate.research_task_id == research_task_id,
        SupplyCandidate.deleted_at.is_(None),
    )

    return list(db.execute(statement).scalars().all())


def soft_delete_active_candidates_by_task_id(
    db: Session,
    research_task_id: int,
) -> None:
    deleted_at = utc_now()

    for candidate in list_active_candidates_for_soft_delete(db, research_task_id):
        candidate.deleted_at = deleted_at

        for link, _ in list_active_candidate_source_rows(db, candidate.id):
            link.deleted_at = deleted_at
