from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OpportunityRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OpportunityGenerated(BaseModel):
    rank: int = Field(ge=1, le=5)
    name: str = Field(min_length=1, max_length=160)
    product_direction: str = Field(min_length=1, max_length=240)
    target_audience: str = Field(min_length=1, max_length=240)
    recommendation_reason: str = Field(min_length=1, max_length=1000)
    suitable_channels: List[str] = Field(min_length=1)
    price_band: str = Field(min_length=1, max_length=120)
    rough_margin: str = Field(min_length=1, max_length=120)
    risk_level: OpportunityRiskLevel
    priority_label: str = Field(min_length=1, max_length=120)
    next_step_summary: str = Field(min_length=1, max_length=1000)

    @field_validator(
        "name",
        "product_direction",
        "target_audience",
        "recommendation_reason",
        "price_band",
        "rough_margin",
        "priority_label",
        "next_step_summary",
        mode="before",
    )
    @classmethod
    def strip_string(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("suitable_channels", mode="before")
    @classmethod
    def normalize_channels(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return [str(item).strip() for item in value if str(item).strip()]


class OpportunityGenerationResult(BaseModel):
    opportunities: List[OpportunityGenerated] = Field(min_length=3, max_length=5)

    @model_validator(mode="after")
    def require_unique_ranks(self) -> "OpportunityGenerationResult":
        ranks = [item.rank for item in self.opportunities]

        if len(ranks) != len(set(ranks)):
            raise ValueError("商机推荐排序不能重复。")

        return self


class OpportunityRead(BaseModel):
    uuid: UUID
    research_task_uuid: UUID
    rank: int
    name: str
    product_direction: str
    target_audience: str
    recommendation_reason: str
    suitable_channels: List[str]
    price_band: str
    rough_margin: str
    risk_level: OpportunityRiskLevel
    priority_label: str
    next_step_summary: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
