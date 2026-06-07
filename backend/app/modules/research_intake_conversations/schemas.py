from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchIntakeConversationStatus(str, Enum):
    ACTIVE = "active"
    CONVERTED = "converted"


class ResearchIntakeMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ResearchIntakeReadinessStatus(str, Enum):
    NEEDS_CLARIFICATION = "needs_clarification"
    READY = "ready"


class ResearchIntakeDraft(BaseModel):
    brief: Optional[str] = Field(default=None, max_length=2000)
    budget: Optional[str] = Field(default=None, max_length=120)
    target_channels: List[str] = Field(default_factory=list)
    preferred_categories: List[str] = Field(default_factory=list)
    excluded_categories: List[str] = Field(default_factory=list)
    target_audience: Optional[str] = Field(default=None, max_length=240)
    expected_profit: Optional[str] = Field(default=None, max_length=120)
    supply_preferences: List[str] = Field(default_factory=list)
    constraints: Optional[str] = Field(default=None, max_length=1000)

    @field_validator(
        "brief",
        "budget",
        "target_audience",
        "expected_profit",
        "constraints",
        mode="before",
    )
    @classmethod
    def strip_optional_string(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return value

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
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]


class ResearchIntakeConversationCreate(BaseModel):
    message: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class ResearchIntakeMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def require_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("请填写聊天内容。")
        return stripped


class ResearchIntakeMessageRead(BaseModel):
    uuid: UUID
    role: ResearchIntakeMessageRole
    content: str
    structured_delta: dict[str, Any]
    suggested_replies: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ResearchIntakeConversationRead(BaseModel):
    uuid: UUID
    status: ResearchIntakeConversationStatus
    draft: ResearchIntakeDraft
    missing_fields: List[str]
    assumptions: List[str]
    readiness_status: ResearchIntakeReadinessStatus
    can_create_task: bool
    research_task_uuid: Optional[UUID]
    trace_id: Optional[str]
    trace_url: Optional[str]
    error_summary: Optional[str]
    messages: List[ResearchIntakeMessageRead]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


class ResearchIntakeConversationConfirmRead(BaseModel):
    conversation: ResearchIntakeConversationRead
    research_task_uuid: Optional[UUID]
    error_summary: Optional[str] = None
