from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.sources.schemas import ResearchSourceType, SourceSupportLevel


class DemandInsightSourceStatus(str, Enum):
    LINKED = "linked"
    NO_SOURCES = "no_sources"
    FALLBACK = "fallback"


PROOF_LIKE_TERMS = (
    "已证明",
    "确定有市场",
    "需求已验证",
    "趋势已确认",
    "已经证明",
    "证明成立",
)


def strip_text(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, str):
        return value.strip()

    return value


def normalize_string_list(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, str):
        value = [value]

    return [str(item).strip() for item in value if str(item).strip()]


def ensure_cautious_text(value: str) -> str:
    if any(term in value for term in PROOF_LIKE_TERMS):
        raise ValueError("需求洞察必须使用待验证语气。")

    return value


class DemandInsightGenerated(BaseModel):
    opportunity_uuid: UUID
    summary: str = Field(min_length=1, max_length=1200)
    audience_profile: str = Field(min_length=1, max_length=800)
    use_cases: List[str] = Field(min_length=1, max_length=6)
    purchase_motivations: List[str] = Field(min_length=1, max_length=6)
    content_angles: List[str] = Field(min_length=1, max_length=6)
    trend_signals: List[str] = Field(min_length=1, max_length=6)
    seasonality_notes: str = Field(min_length=1, max_length=800)

    @field_validator(
        "summary",
        "audience_profile",
        "seasonality_notes",
        mode="before",
    )
    @classmethod
    def strip_string(cls, value: Any) -> Any:
        return strip_text(value)

    @field_validator(
        "use_cases",
        "purchase_motivations",
        "content_angles",
        "trend_signals",
        mode="before",
    )
    @classmethod
    def normalize_lists(cls, value: Any) -> List[str]:
        return normalize_string_list(value)

    @field_validator(
        "summary",
        "audience_profile",
        "seasonality_notes",
    )
    @classmethod
    def require_cautious_scalar(cls, value: str) -> str:
        return ensure_cautious_text(value)

    @field_validator(
        "use_cases",
        "purchase_motivations",
        "content_angles",
        "trend_signals",
    )
    @classmethod
    def require_cautious_list(cls, value: List[str]) -> List[str]:
        return [ensure_cautious_text(item) for item in value]


class DemandInsightGenerationResult(BaseModel):
    insights: List[DemandInsightGenerated] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def require_unique_opportunities(self) -> "DemandInsightGenerationResult":
        opportunity_uuids = [item.opportunity_uuid for item in self.insights]

        if len(opportunity_uuids) != len(set(opportunity_uuids)):
            raise ValueError("需求洞察不能重复关联同一个商机。")

        return self


class DemandInsightSourceLinkCreate(BaseModel):
    research_source_id: int
    relevance_note: str = Field(min_length=1, max_length=1000)

    @field_validator("relevance_note", mode="before")
    @classmethod
    def strip_relevance_note(cls, value: Any) -> Any:
        return strip_text(value)

    @field_validator("relevance_note")
    @classmethod
    def require_cautious_relevance_note(cls, value: str) -> str:
        return ensure_cautious_text(value)


class DemandInsightCreate(BaseModel):
    opportunity_id: int
    summary: str = Field(min_length=1, max_length=1200)
    audience_profile: str = Field(min_length=1, max_length=800)
    use_cases: List[str] = Field(min_length=1, max_length=6)
    purchase_motivations: List[str] = Field(min_length=1, max_length=6)
    content_angles: List[str] = Field(min_length=1, max_length=6)
    trend_signals: List[str] = Field(min_length=1, max_length=6)
    seasonality_notes: str = Field(min_length=1, max_length=800)
    source_status: DemandInsightSourceStatus
    source_links: List[DemandInsightSourceLinkCreate] = Field(default_factory=list)

    @field_validator(
        "summary",
        "audience_profile",
        "seasonality_notes",
        mode="before",
    )
    @classmethod
    def strip_create_string(cls, value: Any) -> Any:
        return strip_text(value)

    @field_validator(
        "use_cases",
        "purchase_motivations",
        "content_angles",
        "trend_signals",
        mode="before",
    )
    @classmethod
    def normalize_create_lists(cls, value: Any) -> List[str]:
        return normalize_string_list(value)


class DemandInsightSourceSummary(BaseModel):
    uuid: UUID
    source_type: ResearchSourceType
    title: str
    url: str
    summary: str
    support_level: SourceSupportLevel
    relevance_note: str


class OpportunityDemandInsightRead(BaseModel):
    uuid: UUID
    research_task_uuid: UUID
    opportunity_uuid: UUID
    summary: str
    audience_profile: str
    use_cases: List[str]
    purchase_motivations: List[str]
    content_angles: List[str]
    trend_signals: List[str]
    seasonality_notes: str
    source_status: DemandInsightSourceStatus
    sources: List[DemandInsightSourceSummary]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
