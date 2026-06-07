from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReadinessRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class ReadinessOverallStatus(str, Enum):
    READY = "ready"
    WARNING = "warning"
    FAILED = "failed"


class ReadinessCheckStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


class ReadinessCheckRead(BaseModel):
    key: str
    label: str
    status: ReadinessCheckStatus
    severity: str
    summary: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)


class ResearchQualityReadinessRunRead(BaseModel):
    uuid: UUID
    research_task_uuid: UUID
    research_run_id: Optional[str]
    status: ReadinessRunStatus
    overall_status: ReadinessOverallStatus
    summary: str
    checks: list[ReadinessCheckRead]
    metrics: dict[str, Any]
    rag_evaluation_run_uuid: Optional[UUID]
    generation_evaluation_run_uuid: Optional[UUID]
    trace_id: Optional[str]
    trace_url: Optional[str]
    stale: bool
    started_at: datetime
    completed_at: Optional[datetime]
    error_summary: Optional[str]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
