from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchSourceType(str, Enum):
    DEMAND = "demand"
    SUPPLY = "supply"
    COMPETITOR = "competitor"
    RISK = "risk"
    GENERAL = "general"


class SourceSupportLevel(str, Enum):
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


class ResearchSourceCreate(BaseModel):
    opportunity_id: Optional[int] = None
    source_type: ResearchSourceType
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=1, max_length=1000)
    summary: str = Field(min_length=1, max_length=1200)
    snippet: str = Field(default="", max_length=1200)
    publisher: Optional[str] = Field(default=None, max_length=200)
    score: Optional[float] = None
    query: Optional[str] = Field(default=None, max_length=500)
    linked_claim: str = Field(min_length=1, max_length=1000)
    support_level: SourceSupportLevel
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    collected_at: Optional[datetime] = None

    @field_validator(
        "title",
        "url",
        "summary",
        "snippet",
        "publisher",
        "query",
        "linked_claim",
        mode="before",
    )
    @classmethod
    def strip_string(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class ResearchSourceRead(BaseModel):
    uuid: UUID
    research_task_uuid: UUID
    opportunity_uuid: Optional[UUID]
    source_type: ResearchSourceType
    title: str
    url: str
    summary: str
    snippet: str
    publisher: Optional[str]
    score: Optional[float]
    query: Optional[str]
    linked_claim: str
    support_level: SourceSupportLevel
    collected_at: datetime
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
