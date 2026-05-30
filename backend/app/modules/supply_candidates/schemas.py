from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.sources.schemas import ResearchSourceType, SourceSupportLevel


class SupplyCandidateSourceStatus(str, Enum):
    LINKED = "linked"
    NO_SOURCES = "no_sources"
    FALLBACK = "fallback"


CONFIRMED_SUPPLY_TERMS = (
    "已确认供给",
    "供应商已核验",
    "价格已确认",
    "库存已确认",
    "供给已确认",
    "履约已确认",
    "已核验供应商",
    "已确认库存",
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
    if any(term in value for term in CONFIRMED_SUPPLY_TERMS):
        raise ValueError("货源候选必须使用待确认语气。")

    return value


class SupplyCandidateGenerated(BaseModel):
    opportunity_uuid: UUID
    rank: int = Field(ge=1, le=5)
    candidate_name: str = Field(min_length=1, max_length=200)
    supply_market: str = Field(min_length=1, max_length=240)
    search_keywords: List[str] = Field(min_length=1, max_length=8)
    price_range: str = Field(min_length=1, max_length=160)
    minimum_order_quantity: str = Field(min_length=1, max_length=240)
    specification_notes: List[str] = Field(min_length=1, max_length=8)
    supplier_questions: List[str] = Field(min_length=1, max_length=8)
    recommendation_note: str = Field(min_length=1, max_length=1000)

    @field_validator(
        "candidate_name",
        "supply_market",
        "price_range",
        "minimum_order_quantity",
        "recommendation_note",
        mode="before",
    )
    @classmethod
    def strip_string(cls, value: Any) -> Any:
        return strip_text(value)

    @field_validator(
        "search_keywords",
        "specification_notes",
        "supplier_questions",
        mode="before",
    )
    @classmethod
    def normalize_lists(cls, value: Any) -> List[str]:
        return normalize_string_list(value)

    @field_validator(
        "candidate_name",
        "supply_market",
        "price_range",
        "minimum_order_quantity",
        "recommendation_note",
    )
    @classmethod
    def require_cautious_scalar(cls, value: str) -> str:
        return ensure_cautious_text(value)

    @field_validator(
        "search_keywords",
        "specification_notes",
        "supplier_questions",
    )
    @classmethod
    def require_cautious_list(cls, value: List[str]) -> List[str]:
        return [ensure_cautious_text(item) for item in value]


class SupplyCandidateGenerationResult(BaseModel):
    candidates: List[SupplyCandidateGenerated] = Field(min_length=1, max_length=25)

    @model_validator(mode="after")
    def require_unique_opportunity_rank(self) -> "SupplyCandidateGenerationResult":
        keys = [(item.opportunity_uuid, item.rank) for item in self.candidates]

        if len(keys) != len(set(keys)):
            raise ValueError("同一商机下的货源候选排序不能重复。")

        return self


class SupplyCandidateSourceLinkCreate(BaseModel):
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


class SupplyCandidateCreate(BaseModel):
    opportunity_id: int
    rank: int = Field(ge=1, le=5)
    candidate_name: str = Field(min_length=1, max_length=200)
    supply_market: str = Field(min_length=1, max_length=240)
    search_keywords: List[str] = Field(min_length=1, max_length=8)
    price_range: str = Field(min_length=1, max_length=160)
    minimum_order_quantity: str = Field(min_length=1, max_length=240)
    specification_notes: List[str] = Field(min_length=1, max_length=8)
    supplier_questions: List[str] = Field(min_length=1, max_length=8)
    recommendation_note: str = Field(min_length=1, max_length=1000)
    source_status: SupplyCandidateSourceStatus
    source_links: List[SupplyCandidateSourceLinkCreate] = Field(default_factory=list)

    @field_validator(
        "candidate_name",
        "supply_market",
        "price_range",
        "minimum_order_quantity",
        "recommendation_note",
        mode="before",
    )
    @classmethod
    def strip_create_string(cls, value: Any) -> Any:
        return strip_text(value)

    @field_validator(
        "search_keywords",
        "specification_notes",
        "supplier_questions",
        mode="before",
    )
    @classmethod
    def normalize_create_lists(cls, value: Any) -> List[str]:
        return normalize_string_list(value)

    @field_validator(
        "candidate_name",
        "supply_market",
        "price_range",
        "minimum_order_quantity",
        "recommendation_note",
    )
    @classmethod
    def require_cautious_create_scalar(cls, value: str) -> str:
        return ensure_cautious_text(value)

    @field_validator(
        "search_keywords",
        "specification_notes",
        "supplier_questions",
    )
    @classmethod
    def require_cautious_create_list(cls, value: List[str]) -> List[str]:
        return [ensure_cautious_text(item) for item in value]


class SupplyCandidateSourceSummary(BaseModel):
    uuid: UUID
    source_type: ResearchSourceType
    title: str
    url: str
    summary: str
    support_level: SourceSupportLevel
    relevance_note: str


class OpportunitySupplyCandidateRead(BaseModel):
    uuid: UUID
    research_task_uuid: UUID
    opportunity_uuid: UUID
    rank: int
    candidate_name: str
    supply_market: str
    search_keywords: List[str]
    price_range: str
    minimum_order_quantity: str
    specification_notes: List[str]
    supplier_questions: List[str]
    recommendation_note: str
    source_status: SupplyCandidateSourceStatus
    sources: List[SupplyCandidateSourceSummary]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
