from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.sources.schemas import ResearchSourceType, SourceSupportLevel


class RagEvidenceChunkCreate(BaseModel):
    research_task_id: int
    opportunity_id: Optional[int] = None
    research_source_id: int
    source_type: ResearchSourceType
    support_level: SourceSupportLevel
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=1, max_length=1000)
    publisher: Optional[str] = Field(default=None, max_length=200)
    chunk_index: int = Field(ge=0)
    chunk_text: str = Field(min_length=1)
    content_hash: str = Field(min_length=64, max_length=64)
    embedding: list[float] = Field(min_length=1)
    embedding_model: str = Field(min_length=1, max_length=160)
    embedding_dimension: int = Field(ge=1)
    token_count: int = Field(ge=0)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "title",
        "url",
        "publisher",
        "chunk_text",
        "content_hash",
        "embedding_model",
        mode="before",
    )
    @classmethod
    def strip_string(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class RagEvidenceChunkRead(BaseModel):
    uuid: UUID
    research_task_uuid: UUID
    opportunity_uuid: Optional[UUID]
    research_source_uuid: UUID
    source_type: ResearchSourceType
    support_level: SourceSupportLevel
    title: str
    url: str
    publisher: Optional[str]
    chunk_index: int
    chunk_text: str
    content_hash: str
    embedding_model: str
    embedding_dimension: int
    token_count: int
    indexed_at: datetime
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


@dataclass(frozen=True)
class RagIndexResult:
    status: str
    indexed_count: int
    source_count: int
    skipped_reason: Optional[str] = None
    error_summary: Optional[str] = None


@dataclass(frozen=True)
class RagRetrievalEvidence:
    chunk_uuid: UUID
    research_source_id: int
    research_source_uuid: UUID
    opportunity_id: Optional[int]
    opportunity_uuid: Optional[UUID]
    source_type: str
    support_level: str
    title: str
    url: str
    summary: str
    linked_claim: str
    chunk_text: str
    relevance_score: float


@dataclass(frozen=True)
class RagRetrievalResult:
    status: str
    query: str
    top_k: int
    source_types: list[str]
    evidence: list[RagRetrievalEvidence]
    fallback_reason: Optional[str] = None
    error_summary: Optional[str] = None
