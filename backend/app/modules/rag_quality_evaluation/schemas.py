from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.sources.schemas import ResearchSourceType


class RagEvaluationCategory(str, Enum):
    DEMAND = "demand"
    SUPPLY = "supply"
    COMPETITOR = "competitor"
    RISK = "risk"


class RagEvaluationRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class RagEvaluationResultStatus(str, Enum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class RagEvaluationCaseCreate(BaseModel):
    uuid: Optional[UUID] = None
    category: RagEvaluationCategory
    question: str = Field(min_length=1, max_length=800)
    expected_source_types: list[ResearchSourceType] = Field(default_factory=list)
    expected_keywords: list[str] = Field(default_factory=list)
    expected_claims: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)
    grading_rubric: str = Field(min_length=1, max_length=1200)
    enabled: bool = True
    case_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "question",
        "grading_rubric",
        mode="before",
    )
    @classmethod
    def strip_string(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator(
        "expected_keywords",
        "expected_claims",
        mode="before",
    )
    @classmethod
    def normalize_string_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return [str(item).strip() for item in value if str(item).strip()]


class RagEvaluationCaseRead(BaseModel):
    uuid: UUID
    category: RagEvaluationCategory
    question: str
    expected_source_types: list[ResearchSourceType]
    expected_keywords: list[str]
    expected_claims: list[str]
    top_k: int
    grading_rubric: str
    enabled: bool
    case_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class RetrievedEvidenceEvaluation(BaseModel):
    chunk_uuid: UUID
    research_source_uuid: UUID
    source_type: ResearchSourceType
    support_level: str
    title: str
    url: str
    summary: str
    linked_claim: str
    retriever_score: float
    relevance_grade: int = Field(ge=0, le=3)
    grading_note: str


class RagEvaluationResultRead(BaseModel):
    uuid: UUID
    evaluation_case_uuid: UUID
    status: RagEvaluationResultStatus
    category: RagEvaluationCategory
    question: str
    case_snapshot: dict[str, Any]
    retrieval_query: str
    top_k: int
    retrieval_status: str
    retrieved_evidence: list[RetrievedEvidenceEvaluation]
    relevant_count: int
    expected_count: int
    hit_rate: float
    recall: float
    precision: float
    mrr: float
    ndcg: float
    scoring_notes: str
    error_summary: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class RagEvaluationRunRead(BaseModel):
    uuid: UUID
    research_task_uuid: Optional[UUID]
    name: str
    status: RagEvaluationRunStatus
    run_id: Optional[str]
    trace_id: Optional[str]
    trace_url: Optional[str]
    config: dict[str, Any]
    summary_metrics: dict[str, Any]
    case_total: int
    case_completed_count: int
    case_failed_count: int
    case_skipped_count: int
    average_hit_rate: float
    average_recall: float
    average_precision: float
    average_mrr: float
    average_ndcg: float
    error_summary: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


@dataclass(frozen=True)
class EvidenceRelevanceScore:
    grade: int
    note: str


@dataclass(frozen=True)
class RetrievalMetricScores:
    hit_rate: float
    recall: float
    precision: float
    mrr: float
    ndcg: float
    relevant_count: int
    expected_count: int
