from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.demand_insights.models import (
    OpportunityDemandInsight,
    OpportunityDemandInsightSource,
)
from app.modules.opportunities.models import Opportunity
from app.modules.sources.models import ResearchSource


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def add_insights(
    db: Session,
    insights: list[OpportunityDemandInsight],
) -> list[OpportunityDemandInsight]:
    db.add_all(insights)
    return insights


def add_source_links(
    db: Session,
    links: list[OpportunityDemandInsightSource],
) -> list[OpportunityDemandInsightSource]:
    db.add_all(links)
    return links


def list_active_insights_by_task_id(
    db: Session,
    research_task_id: int,
) -> list[OpportunityDemandInsight]:
    statement = (
        select(OpportunityDemandInsight)
        .join(Opportunity, OpportunityDemandInsight.opportunity_id == Opportunity.id)
        .where(
            OpportunityDemandInsight.research_task_id == research_task_id,
            OpportunityDemandInsight.deleted_at.is_(None),
            Opportunity.deleted_at.is_(None),
        )
        .order_by(Opportunity.rank.asc(), Opportunity.id.asc())
    )

    return list(db.execute(statement).scalars().all())


def get_active_insight_by_opportunity_id(
    db: Session,
    opportunity_id: int,
) -> Optional[OpportunityDemandInsight]:
    statement = select(OpportunityDemandInsight).where(
        OpportunityDemandInsight.opportunity_id == opportunity_id,
        OpportunityDemandInsight.deleted_at.is_(None),
    )

    return db.execute(statement).scalar_one_or_none()


def list_active_insight_source_rows(
    db: Session,
    insight_id: int,
) -> list[tuple[OpportunityDemandInsightSource, ResearchSource]]:
    statement = (
        select(OpportunityDemandInsightSource, ResearchSource)
        .join(
            ResearchSource,
            OpportunityDemandInsightSource.research_source_id == ResearchSource.id,
        )
        .where(
            OpportunityDemandInsightSource.demand_insight_id == insight_id,
            OpportunityDemandInsightSource.deleted_at.is_(None),
            ResearchSource.deleted_at.is_(None),
        )
        .order_by(OpportunityDemandInsightSource.id.asc())
    )

    return [(row[0], row[1]) for row in db.execute(statement).all()]


def list_active_insights_for_soft_delete(
    db: Session,
    research_task_id: int,
) -> list[OpportunityDemandInsight]:
    statement = select(OpportunityDemandInsight).where(
        OpportunityDemandInsight.research_task_id == research_task_id,
        OpportunityDemandInsight.deleted_at.is_(None),
    )

    return list(db.execute(statement).scalars().all())


def soft_delete_active_insights_by_task_id(
    db: Session,
    research_task_id: int,
) -> None:
    deleted_at = utc_now()

    for insight in list_active_insights_for_soft_delete(db, research_task_id):
        insight.deleted_at = deleted_at

        for link, _ in list_active_insight_source_rows(db, insight.id):
            link.deleted_at = deleted_at
