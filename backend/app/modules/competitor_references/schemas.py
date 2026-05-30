from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.sources.schemas import ResearchSourceType, SourceSupportLevel


class CompetitorReferenceSourceStatus(str, Enum):
    LINKED = "linked"
    NO_SOURCES = "no_sources"
    FALLBACK = "fallback"


class HomogenizationLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


CONFIRMED_COMPETITOR_TERMS = (
    "竞品已全面核验",
    "竞品已核验",
    "售价已确认",
    "价格已确认",
    "销量已确认",
    "市场已证明",
    "确定有市场",
    "已证明有市场",
    "已确认竞品",
    "已核验售价",
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
    if any(term in value for term in CONFIRMED_COMPETITOR_TERMS):
        raise ValueError("竞品参考必须使用待验证语气。")

    return value


class CompetitorReferenceGenerated(BaseModel):
    opportunity_uuid: UUID
    rank: int = Field(ge=1, le=5)
    reference_name: str = Field(min_length=1, max_length=200)
    reference_market: str = Field(min_length=1, max_length=240)
    price_range: str = Field(min_length=1, max_length=160)
    common_selling_points: List[str] = Field(min_length=1, max_length=8)
    homogenization_level: HomogenizationLevel
    differentiation_angles: List[str] = Field(min_length=1, max_length=8)
    reference_note: str = Field(min_length=1, max_length=1000)

    @field_validator(
        "reference_name",
        "reference_market",
        "price_range",
        "reference_note",
        mode="before",
    )
    @classmethod
    def strip_string(cls, value: Any) -> Any:
        return strip_text(value)

    @field_validator(
        "common_selling_points",
        "differentiation_angles",
        mode="before",
    )
    @classmethod
    def normalize_lists(cls, value: Any) -> List[str]:
        return normalize_string_list(value)

    @field_validator(
        "reference_name",
        "reference_market",
        "price_range",
        "reference_note",
    )
    @classmethod
    def require_cautious_scalar(cls, value: str) -> str:
        return ensure_cautious_text(value)

    @field_validator(
        "common_selling_points",
        "differentiation_angles",
    )
    @classmethod
    def require_cautious_list(cls, value: List[str]) -> List[str]:
        return [ensure_cautious_text(item) for item in value]


class CompetitorReferenceGenerationResult(BaseModel):
    references: List[CompetitorReferenceGenerated] = Field(
        min_length=1,
        max_length=25,
    )

    @model_validator(mode="after")
    def require_unique_opportunity_rank(self) -> "CompetitorReferenceGenerationResult":
        keys = [(item.opportunity_uuid, item.rank) for item in self.references]

        if len(keys) != len(set(keys)):
            raise ValueError("同一商机下的竞品参考排序不能重复。")

        return self


class CompetitorReferenceSourceLinkCreate(BaseModel):
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


class CompetitorReferenceCreate(BaseModel):
    opportunity_id: int
    rank: int = Field(ge=1, le=5)
    reference_name: str = Field(min_length=1, max_length=200)
    reference_market: str = Field(min_length=1, max_length=240)
    price_range: str = Field(min_length=1, max_length=160)
    common_selling_points: List[str] = Field(min_length=1, max_length=8)
    homogenization_level: HomogenizationLevel
    differentiation_angles: List[str] = Field(min_length=1, max_length=8)
    reference_note: str = Field(min_length=1, max_length=1000)
    source_status: CompetitorReferenceSourceStatus
    source_links: List[CompetitorReferenceSourceLinkCreate] = Field(
        default_factory=list,
    )

    @field_validator(
        "reference_name",
        "reference_market",
        "price_range",
        "reference_note",
        mode="before",
    )
    @classmethod
    def strip_create_string(cls, value: Any) -> Any:
        return strip_text(value)

    @field_validator(
        "common_selling_points",
        "differentiation_angles",
        mode="before",
    )
    @classmethod
    def normalize_create_lists(cls, value: Any) -> List[str]:
        return normalize_string_list(value)

    @field_validator(
        "reference_name",
        "reference_market",
        "price_range",
        "reference_note",
    )
    @classmethod
    def require_cautious_create_scalar(cls, value: str) -> str:
        return ensure_cautious_text(value)

    @field_validator(
        "common_selling_points",
        "differentiation_angles",
    )
    @classmethod
    def require_cautious_create_list(cls, value: List[str]) -> List[str]:
        return [ensure_cautious_text(item) for item in value]


class CompetitorReferenceSourceSummary(BaseModel):
    uuid: UUID
    source_type: ResearchSourceType
    title: str
    url: str
    summary: str
    support_level: SourceSupportLevel
    relevance_note: str


class OpportunityCompetitorReferenceRead(BaseModel):
    uuid: UUID
    research_task_uuid: UUID
    opportunity_uuid: UUID
    rank: int
    reference_name: str
    reference_market: str
    price_range: str
    common_selling_points: List[str]
    homogenization_level: HomogenizationLevel
    differentiation_angles: List[str]
    reference_note: str
    source_status: CompetitorReferenceSourceStatus
    sources: List[CompetitorReferenceSourceSummary]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
