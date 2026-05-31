from __future__ import annotations

import re
import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator, UserDefinedType

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PostgresVector(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw: Any) -> str:
        return "vector"


class EmbeddingVector(TypeDecorator[list[float]]):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgresVector())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect) -> Optional[Any]:
        if value is None:
            return None

        values = [float(item) for item in value]

        if dialect.name == "postgresql":
            return "[" + ",".join(f"{item:.8f}" for item in values) + "]"

        return values

    def process_result_value(self, value: Any, dialect) -> Optional[list[float]]:
        if value is None:
            return None

        if isinstance(value, str):
            items = re.findall(r"-?\d+(?:\.\d+)?(?:e[+-]?\d+)?", value.lower())
            return [float(item) for item in items]

        return [float(item) for item in value]


class RagEvidenceChunk(Base):
    __tablename__ = "rag_evidence_chunks"
    __table_args__ = (
        Index(
            "ix_rag_evidence_chunks_task_deleted_at",
            "research_task_id",
            "deleted_at",
        ),
        Index(
            "ix_rag_evidence_chunks_opportunity_deleted_at",
            "opportunity_id",
            "deleted_at",
        ),
        Index(
            "ix_rag_evidence_chunks_source_deleted_at",
            "research_source_id",
            "deleted_at",
        ),
        Index(
            "ix_rag_evidence_chunks_task_type_deleted_at",
            "research_task_id",
            "source_type",
            "deleted_at",
        ),
        Index(
            "ix_rag_evidence_chunks_task_hash_deleted_at",
            "research_task_id",
            "content_hash",
            "deleted_at",
        ),
        Index("ix_rag_evidence_chunks_deleted_at", "deleted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_pkg.uuid4,
    )
    research_task_id: Mapped[int] = mapped_column(
        ForeignKey("research_tasks.id"),
        nullable=False,
    )
    opportunity_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("opportunities.id"),
        nullable=True,
    )
    research_source_id: Mapped[int] = mapped_column(
        ForeignKey("research_sources.id"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    support_level: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    publisher: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(EmbeddingVector(), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(160), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
