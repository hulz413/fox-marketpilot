from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.opportunities.schemas import OpportunityRiskLevel


class OpportunityRiskReviewStatus(str, Enum):
    DERIVED = "derived"
    FALLBACK = "fallback"
    INSUFFICIENT_DATA = "insufficient_data"


CONFIRMED_RISK_TERMS = (
    "合规已确认",
    "供应商履约已验证",
    "平台规则无风险",
    "库存风险已排除",
    "风险已经排除",
    "无合规风险",
    "无售后风险",
    "无质量风险",
    "履约已确认",
    "库存已确认",
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
    if any(term in value for term in CONFIRMED_RISK_TERMS):
        raise ValueError("风险复核必须使用待验证语气。")

    return value


class OpportunityRiskGenerated(BaseModel):
    opportunity_uuid: UUID
    overall_risk_level: OpportunityRiskLevel
    risk_summary: str = Field(min_length=1, max_length=1000)
    quality_risk: str = Field(min_length=1, max_length=1000)
    fulfillment_risk: str = Field(min_length=1, max_length=1000)
    after_sales_risk: str = Field(min_length=1, max_length=1000)
    compliance_risk: str = Field(min_length=1, max_length=1000)
    inventory_risk: str = Field(min_length=1, max_length=1000)
    competition_risk: str = Field(min_length=1, max_length=1000)
    platform_risk: str = Field(min_length=1, max_length=1000)
    risk_triggers: List[str] = Field(min_length=1, max_length=10)
    mitigation_suggestions: List[str] = Field(min_length=1, max_length=10)
    review_status: OpportunityRiskReviewStatus

    @field_validator(
        "risk_summary",
        "quality_risk",
        "fulfillment_risk",
        "after_sales_risk",
        "compliance_risk",
        "inventory_risk",
        "competition_risk",
        "platform_risk",
        mode="before",
    )
    @classmethod
    def strip_string(cls, value: Any) -> Any:
        return strip_text(value)

    @field_validator(
        "risk_triggers",
        "mitigation_suggestions",
        mode="before",
    )
    @classmethod
    def normalize_lists(cls, value: Any) -> List[str]:
        return normalize_string_list(value)

    @field_validator(
        "risk_summary",
        "quality_risk",
        "fulfillment_risk",
        "after_sales_risk",
        "compliance_risk",
        "inventory_risk",
        "competition_risk",
        "platform_risk",
    )
    @classmethod
    def require_cautious_scalar(cls, value: str) -> str:
        return ensure_cautious_text(value)

    @field_validator("risk_triggers", "mitigation_suggestions")
    @classmethod
    def require_cautious_list(cls, value: List[str]) -> List[str]:
        return [ensure_cautious_text(item) for item in value]


class OpportunityRiskGenerationResult(BaseModel):
    risks: List[OpportunityRiskGenerated] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def require_unique_opportunity(self) -> "OpportunityRiskGenerationResult":
        opportunity_uuids = [item.opportunity_uuid for item in self.risks]

        if len(opportunity_uuids) != len(set(opportunity_uuids)):
            raise ValueError("同一商机下的风险复核不能重复。")

        return self


class OpportunityRiskCreate(BaseModel):
    opportunity_id: int
    overall_risk_level: OpportunityRiskLevel
    risk_summary: str = Field(min_length=1, max_length=1000)
    quality_risk: str = Field(min_length=1, max_length=1000)
    fulfillment_risk: str = Field(min_length=1, max_length=1000)
    after_sales_risk: str = Field(min_length=1, max_length=1000)
    compliance_risk: str = Field(min_length=1, max_length=1000)
    inventory_risk: str = Field(min_length=1, max_length=1000)
    competition_risk: str = Field(min_length=1, max_length=1000)
    platform_risk: str = Field(min_length=1, max_length=1000)
    risk_triggers: List[str] = Field(min_length=1, max_length=10)
    mitigation_suggestions: List[str] = Field(min_length=1, max_length=10)
    review_status: OpportunityRiskReviewStatus

    @field_validator(
        "risk_summary",
        "quality_risk",
        "fulfillment_risk",
        "after_sales_risk",
        "compliance_risk",
        "inventory_risk",
        "competition_risk",
        "platform_risk",
        mode="before",
    )
    @classmethod
    def strip_create_string(cls, value: Any) -> Any:
        return strip_text(value)

    @field_validator(
        "risk_triggers",
        "mitigation_suggestions",
        mode="before",
    )
    @classmethod
    def normalize_create_lists(cls, value: Any) -> List[str]:
        return normalize_string_list(value)

    @field_validator(
        "risk_summary",
        "quality_risk",
        "fulfillment_risk",
        "after_sales_risk",
        "compliance_risk",
        "inventory_risk",
        "competition_risk",
        "platform_risk",
    )
    @classmethod
    def require_cautious_create_scalar(cls, value: str) -> str:
        return ensure_cautious_text(value)

    @field_validator("risk_triggers", "mitigation_suggestions")
    @classmethod
    def require_cautious_create_list(cls, value: List[str]) -> List[str]:
        return [ensure_cautious_text(item) for item in value]


class OpportunityRiskRead(BaseModel):
    uuid: UUID
    research_task_uuid: UUID
    opportunity_uuid: UUID
    overall_risk_level: OpportunityRiskLevel
    risk_summary: str
    quality_risk: str
    fulfillment_risk: str
    after_sales_risk: str
    compliance_risk: str
    inventory_risk: str
    competition_risk: str
    platform_risk: str
    risk_triggers: List[str]
    mitigation_suggestions: List[str]
    review_status: OpportunityRiskReviewStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
