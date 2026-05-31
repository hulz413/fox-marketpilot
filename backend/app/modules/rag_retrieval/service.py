from __future__ import annotations

import hashlib
import logging
import math
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.integrations.embeddings import EmbeddingClient, get_embedding_client
from app.modules.opportunities.models import Opportunity
from app.modules.rag_retrieval import repository
from app.modules.rag_retrieval.models import RagEvidenceChunk
from app.modules.rag_retrieval.schemas import (
    RagEvidenceChunkCreate,
    RagIndexResult,
    RagRetrievalEvidence,
    RagRetrievalResult,
)
from app.modules.research_tasks.models import ResearchTask
from app.modules.sources import service as sources_service
from app.modules.sources.models import ResearchSource
from app.modules.sources.schemas import ResearchSourceType

logger = logging.getLogger(__name__)

MAX_CHUNK_TEXT_LENGTH = 2400
MAX_RETRIEVAL_CANDIDATES = 50
DEFAULT_TOP_K = 5


def index_task_evidence(
    db: Session,
    task: ResearchTask,
    *,
    embedding_client: Optional[EmbeddingClient] = None,
) -> RagIndexResult:
    sources = sources_service.list_task_sources(db, task)
    repository.soft_delete_active_chunks_by_task_id(db, task.id)

    if not sources:
        db.commit()
        return RagIndexResult(
            status="skipped",
            indexed_count=0,
            source_count=0,
            skipped_reason="no_sources",
        )

    client = embedding_client or get_embedding_client()
    if client is None:
        db.commit()
        return RagIndexResult(
            status="skipped",
            indexed_count=0,
            source_count=len(sources),
            skipped_reason="embedding_unavailable",
        )

    chunk_specs = [
        (source, build_source_chunk_text(source))
        for source in sources
    ]
    chunk_specs = [
        (source, chunk_text)
        for source, chunk_text in chunk_specs
        if chunk_text
    ]

    if not chunk_specs:
        db.commit()
        return RagIndexResult(
            status="skipped",
            indexed_count=0,
            source_count=len(sources),
            skipped_reason="empty_chunks",
        )

    texts = [chunk_text for _, chunk_text in chunk_specs]

    try:
        embeddings = client.embed_texts(texts)
    except Exception as exc:  # pragma: no cover - provider errors vary
        logger.warning(
            "RAG evidence embedding failed",
            exc_info=True,
            extra={
                "task_uuid": str(task.uuid),
                "error_type": type(exc).__name__,
            },
        )
        db.commit()
        return RagIndexResult(
            status="failed",
            indexed_count=0,
            source_count=len(sources),
            error_summary="RAG 证据索引暂不可用，已回退到来源列表。",
        )

    if len(embeddings) != len(chunk_specs):
        db.commit()
        return RagIndexResult(
            status="failed",
            indexed_count=0,
            source_count=len(sources),
            error_summary="RAG 证据索引返回数量异常，已回退到来源列表。",
        )

    chunk_inputs = [
        build_chunk_create(
            task,
            source,
            chunk_text,
            embedding,
            embedding_model=client.model,
        )
        for (source, chunk_text), embedding in zip(chunk_specs, embeddings)
        if embedding
    ]

    chunks = [
        RagEvidenceChunk(
            research_task_id=item.research_task_id,
            opportunity_id=item.opportunity_id,
            research_source_id=item.research_source_id,
            source_type=item.source_type.value,
            support_level=item.support_level.value,
            title=item.title,
            url=item.url,
            publisher=item.publisher,
            chunk_index=item.chunk_index,
            chunk_text=item.chunk_text,
            content_hash=item.content_hash,
            embedding=item.embedding,
            embedding_model=item.embedding_model,
            embedding_dimension=item.embedding_dimension,
            token_count=item.token_count,
            raw_metadata=item.raw_metadata,
        )
        for item in chunk_inputs
    ]
    repository.add_chunks(db, chunks)
    db.commit()

    for chunk in chunks:
        db.refresh(chunk)

    return RagIndexResult(
        status="fallback" if client.is_fallback else "completed",
        indexed_count=len(chunks),
        source_count=len(sources),
    )


def retrieve_evidence(
    db: Session,
    task: ResearchTask,
    *,
    query: str,
    opportunity: Optional[Opportunity] = None,
    source_types: Optional[list[ResearchSourceType]] = None,
    top_k: int = DEFAULT_TOP_K,
    embedding_client: Optional[EmbeddingClient] = None,
) -> RagRetrievalResult:
    normalized_query = clean_text(query)
    if not normalized_query:
        return RagRetrievalResult(
            status="skipped",
            query="",
            top_k=top_k,
            source_types=[item.value for item in source_types or []],
            evidence=[],
            fallback_reason="empty_query",
        )

    client = embedding_client or get_embedding_client()
    source_type_values = [item.value for item in source_types or []]

    if client is None:
        return RagRetrievalResult(
            status="skipped",
            query=normalized_query,
            top_k=top_k,
            source_types=source_type_values,
            evidence=[],
            fallback_reason="embedding_unavailable",
        )

    try:
        query_embedding = client.embed_texts([normalized_query])[0]
    except Exception as exc:  # pragma: no cover - provider errors vary
        logger.warning(
            "RAG evidence query embedding failed",
            exc_info=True,
            extra={
                "task_uuid": str(task.uuid),
                "run_id": task.run_id,
                "error_type": type(exc).__name__,
            },
        )
        return RagRetrievalResult(
            status="failed",
            query=normalized_query,
            top_k=top_k,
            source_types=source_type_values,
            evidence=[],
            error_summary="RAG 证据检索暂不可用，已回退到来源列表。",
        )

    rows = repository.list_active_chunk_source_rows(
        db,
        task.id,
        opportunity_id=opportunity.id if opportunity is not None else None,
        source_types=source_type_values,
    )

    if not rows and opportunity is not None:
        rows = repository.list_active_chunk_source_rows(
            db,
            task.id,
            source_types=source_type_values,
        )

    if not rows:
        return RagRetrievalResult(
            status="empty",
            query=normalized_query,
            top_k=top_k,
            source_types=source_type_values,
            evidence=[],
            fallback_reason="no_chunks",
        )

    scored = sorted(
        (
            (
                score_chunk(
                    chunk,
                    query_embedding,
                    opportunity_id=opportunity.id if opportunity is not None else None,
                ),
                chunk,
                source,
            )
            for chunk, source in rows[:MAX_RETRIEVAL_CANDIDATES]
        ),
        key=lambda item: item[0],
        reverse=True,
    )[:top_k]

    evidence = [
        RagRetrievalEvidence(
            chunk_uuid=chunk.uuid,
            research_source_id=source.id,
            research_source_uuid=source.uuid,
            opportunity_id=source.opportunity_id,
            opportunity_uuid=None,
            source_type=source.source_type,
            support_level=source.support_level,
            title=source.title,
            url=source.url,
            summary=source.summary,
            linked_claim=source.linked_claim,
            chunk_text=chunk.chunk_text,
            relevance_score=round(score, 6),
        )
        for score, chunk, source in scored
    ]

    return RagRetrievalResult(
        status="fallback" if client.is_fallback else "completed",
        query=normalized_query,
        top_k=top_k,
        source_types=source_type_values,
        evidence=evidence,
    )


def build_chunk_create(
    task: ResearchTask,
    source: ResearchSource,
    chunk_text: str,
    embedding: list[float],
    *,
    embedding_model: str,
) -> RagEvidenceChunkCreate:
    metadata = {
        "source_uuid": str(source.uuid),
        "task_uuid": str(task.uuid),
        "opportunity_id": source.opportunity_id,
        "source_score": source.score,
        "query": source.query,
    }

    return RagEvidenceChunkCreate(
        research_task_id=task.id,
        opportunity_id=source.opportunity_id,
        research_source_id=source.id,
        source_type=source.source_type,
        support_level=source.support_level,
        title=source.title,
        url=source.url,
        publisher=source.publisher,
        chunk_index=0,
        chunk_text=chunk_text,
        content_hash=hash_chunk(source, chunk_text),
        embedding=[float(value) for value in embedding],
        embedding_model=embedding_model,
        embedding_dimension=len(embedding),
        token_count=estimate_token_count(chunk_text),
        raw_metadata=metadata,
    )


def build_source_chunk_text(source: ResearchSource) -> str:
    lines = [
        ("标题", source.title),
        ("摘要", source.summary),
        ("片段", source.snippet),
        ("关联判断", source.linked_claim),
    ]
    chunk_text = "\n".join(
        f"{label}：{cleaned}"
        for label, value in lines
        if (cleaned := clean_text(value))
    )
    return clip_text(chunk_text, MAX_CHUNK_TEXT_LENGTH)


def hash_chunk(source: ResearchSource, chunk_text: str) -> str:
    payload = "|".join(
        [
            str(source.uuid),
            source.url or "",
            source.source_type or "",
            chunk_text,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def score_chunk(
    chunk: RagEvidenceChunk,
    query_embedding: list[float],
    *,
    opportunity_id: Optional[int],
) -> float:
    score = cosine_similarity(query_embedding, chunk.embedding)

    if opportunity_id is not None and chunk.opportunity_id == opportunity_id:
        score += 0.1

    if chunk.source_type == ResearchSourceType.COMPETITOR.value:
        score += 0.08
    elif chunk.source_type == ResearchSourceType.GENERAL.value:
        score += 0.03

    if chunk.support_level == "strong":
        score += 0.05
    elif chunk.support_level == "medium":
        score += 0.02

    return score


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0

    length = min(len(left), len(right))
    dot = sum(left[index] * right[index] for index in range(length))
    left_norm = math.sqrt(sum(value * value for value in left[:length]))
    right_norm = math.sqrt(sum(value * value for value in right[:length]))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot / (left_norm * right_norm)


def estimate_token_count(value: str) -> int:
    return max(1, len(value) // 2)


def clean_text(value: Optional[str]) -> str:
    if not value:
        return ""

    unescaped = re.sub(r"<[^>]+>", " ", value)
    return " ".join(unescaped.split())


def clip_text(value: str, limit: int) -> str:
    normalized = clean_text(value)
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 3)]}..."
