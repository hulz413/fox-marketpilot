from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.rag_retrieval.models import RagEvidenceChunk
from app.modules.sources.models import ResearchSource


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def add_chunks(
    db: Session,
    chunks: list[RagEvidenceChunk],
) -> list[RagEvidenceChunk]:
    db.add_all(chunks)
    return chunks


def list_active_chunks_by_task_id(
    db: Session,
    research_task_id: int,
) -> list[RagEvidenceChunk]:
    statement = (
        select(RagEvidenceChunk)
        .where(
            RagEvidenceChunk.research_task_id == research_task_id,
            RagEvidenceChunk.deleted_at.is_(None),
        )
        .order_by(
            RagEvidenceChunk.source_type.asc(),
            RagEvidenceChunk.opportunity_id.asc().nullsfirst(),
            RagEvidenceChunk.chunk_index.asc(),
            RagEvidenceChunk.id.asc(),
        )
    )

    return list(db.execute(statement).scalars().all())


def list_active_chunk_source_rows(
    db: Session,
    research_task_id: int,
    *,
    opportunity_id: Optional[int] = None,
    source_types: Optional[list[str]] = None,
) -> list[tuple[RagEvidenceChunk, ResearchSource]]:
    statement = (
        select(RagEvidenceChunk, ResearchSource)
        .join(ResearchSource, RagEvidenceChunk.research_source_id == ResearchSource.id)
        .where(
            RagEvidenceChunk.research_task_id == research_task_id,
            RagEvidenceChunk.deleted_at.is_(None),
            ResearchSource.deleted_at.is_(None),
        )
    )

    if source_types:
        statement = statement.where(RagEvidenceChunk.source_type.in_(source_types))

    if opportunity_id is not None:
        statement = statement.where(
            (RagEvidenceChunk.opportunity_id == opportunity_id)
            | (RagEvidenceChunk.opportunity_id.is_(None))
        )

    statement = statement.order_by(
        RagEvidenceChunk.opportunity_id.asc().nullsfirst(),
        RagEvidenceChunk.source_type.asc(),
        RagEvidenceChunk.id.asc(),
    )

    return [(row[0], row[1]) for row in db.execute(statement).all()]


def soft_delete_active_chunks_by_task_id(
    db: Session,
    research_task_id: int,
) -> None:
    deleted_at = utc_now()

    for chunk in list_active_chunks_by_task_id(db, research_task_id):
        chunk.deleted_at = deleted_at
