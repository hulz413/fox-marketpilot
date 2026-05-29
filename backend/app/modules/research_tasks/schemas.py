from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchTaskStatus(str, Enum):
    CREATED = "created"


class ResearchTaskStage(str, Enum):
    INTAKE = "intake"


class ResearchTaskCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=160)
    brief: str = Field(min_length=1, max_length=2000)
    budget: Optional[str] = Field(default=None, max_length=120)
    target_channels: List[str] = Field(default_factory=list)
    preferred_categories: List[str] = Field(default_factory=list)
    excluded_categories: List[str] = Field(default_factory=list)
    target_audience: Optional[str] = Field(default=None, max_length=240)
    expected_profit: Optional[str] = Field(default=None, max_length=120)
    supply_preferences: List[str] = Field(default_factory=list)
    constraints: Optional[str] = Field(default=None, max_length=1000)

    @field_validator(
        "title",
        "brief",
        "budget",
        "target_audience",
        "expected_profit",
        "constraints",
        mode="before",
    )
    @classmethod
    def strip_string(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("brief")
    @classmethod
    def require_brief(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("请填写自然语言需求。")
        return value.strip()

    @field_validator(
        "target_channels",
        "preferred_categories",
        "excluded_categories",
        "supply_preferences",
        mode="before",
    )
    @classmethod
    def normalize_string_list(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return [str(item).strip() for item in value if str(item).strip()]


class ResearchTaskRead(BaseModel):
    uuid: UUID
    title: str
    brief: str
    budget: Optional[str]
    target_channels: List[str]
    preferred_categories: List[str]
    excluded_categories: List[str]
    target_audience: Optional[str]
    expected_profit: Optional[str]
    supply_preferences: List[str]
    constraints: Optional[str]
    status: ResearchTaskStatus
    current_stage: ResearchTaskStage
    run_id: Optional[str]
    trace_id: Optional[str]
    failure_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
