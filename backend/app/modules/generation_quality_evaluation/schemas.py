from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GenerationEvaluationCategory(str, Enum):
    CONSTRAINTS = "constraints"
    STRUCTURE = "structure"
    CONSISTENCY = "consistency"
    RISK_QUALITY = "risk_quality"
    ACTION_QUALITY = "action_quality"
    CAUTIOUS_BOUNDARY = "cautious_boundary"


class GenerationEvaluationRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class GenerationEvaluationOverallStatus(str, Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


class GenerationEvaluationResultStatus(str, Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


class GenerationEvaluationCaseCreate(BaseModel):
    uuid: Optional[UUID] = None
    category: GenerationEvaluationCategory
    name: str = Field(min_length=1, max_length=200)
    input_constraints: dict[str, Any] = Field(default_factory=dict)
    expected_signals: list[str] = Field(default_factory=list)
    rubric: dict[str, Any] = Field(default_factory=dict)
    grading_rubric: str = Field(min_length=1, max_length=1200)
    enabled: bool = True
    case_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "grading_rubric", mode="before")
    @classmethod
    def strip_string(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("expected_signals", mode="before")
    @classmethod
    def normalize_string_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return [str(item).strip() for item in value if str(item).strip()]


class GenerationEvaluationCaseRead(BaseModel):
    uuid: UUID
    category: GenerationEvaluationCategory
    name: str
    input_constraints: dict[str, Any]
    expected_signals: list[str]
    rubric: dict[str, Any]
    grading_rubric: str
    enabled: bool
    case_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class GenerationEvaluationResultRead(BaseModel):
    uuid: UUID
    evaluation_case_uuid: UUID
    status: GenerationEvaluationResultStatus
    category: GenerationEvaluationCategory
    name: str
    case_snapshot: dict[str, Any]
    target_scope: str
    affected_opportunity_uuids: list[UUID]
    rubric_scores: dict[str, Any]
    reasons: list[str]
    actions: list[str]
    scoring_notes: str
    error_summary: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class GenerationEvaluationRunRead(BaseModel):
    uuid: UUID
    research_task_uuid: UUID
    name: str
    status: GenerationEvaluationRunStatus
    overall_status: GenerationEvaluationOverallStatus
    research_run_id: Optional[str]
    trace_id: Optional[str]
    trace_url: Optional[str]
    config: dict[str, Any]
    summary_metrics: dict[str, Any]
    summary: str
    case_total: int
    case_passed_count: int
    case_warning_count: int
    case_failed_count: int
    case_skipped_count: int
    error_summary: Optional[str]
    stale: bool
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


@dataclass(frozen=True)
class GenerationEvaluationScore:
    status: GenerationEvaluationResultStatus
    rubric_scores: dict[str, Any]
    reasons: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    affected_opportunity_uuids: list[UUID] = field(default_factory=list)
    scoring_notes: str = ""

