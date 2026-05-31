from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ValidationBudgetEstimateStatus(str, Enum):
    DERIVED = "derived"
    FALLBACK = "fallback"
    INSUFFICIENT_DATA = "insufficient_data"


CONFIRMED_FINANCIAL_TERMS = (
    "利润已确认",
    "保证回本",
    "确定毛利",
    "真实成交价已确认",
    "采购价已确认",
    "售价已确认",
    "回本结果已确认",
    "稳赚",
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
    if any(term in value for term in CONFIRMED_FINANCIAL_TERMS):
        raise ValueError("验证预算估算必须使用待验证语气。")

    return value


class ValidationBudgetGenerated(BaseModel):
    opportunity_uuid: UUID
    estimated_unit_cost: str = Field(min_length=1, max_length=160)
    estimated_selling_price: str = Field(min_length=1, max_length=160)
    rough_gross_margin: str = Field(min_length=1, max_length=160)
    first_batch_quantity: str = Field(min_length=1, max_length=160)
    first_batch_budget: str = Field(min_length=1, max_length=160)
    key_assumptions: List[str] = Field(min_length=1, max_length=8)
    calculation_note: str = Field(min_length=1, max_length=1000)
    estimate_status: ValidationBudgetEstimateStatus

    @field_validator(
        "estimated_unit_cost",
        "estimated_selling_price",
        "rough_gross_margin",
        "first_batch_quantity",
        "first_batch_budget",
        "calculation_note",
        mode="before",
    )
    @classmethod
    def strip_string(cls, value: Any) -> Any:
        return strip_text(value)

    @field_validator("key_assumptions", mode="before")
    @classmethod
    def normalize_lists(cls, value: Any) -> List[str]:
        return normalize_string_list(value)

    @field_validator(
        "estimated_unit_cost",
        "estimated_selling_price",
        "rough_gross_margin",
        "first_batch_quantity",
        "first_batch_budget",
        "calculation_note",
    )
    @classmethod
    def require_cautious_scalar(cls, value: str) -> str:
        return ensure_cautious_text(value)

    @field_validator("key_assumptions")
    @classmethod
    def require_cautious_list(cls, value: List[str]) -> List[str]:
        return [ensure_cautious_text(item) for item in value]


class ValidationBudgetGenerationResult(BaseModel):
    budgets: List[ValidationBudgetGenerated] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def require_unique_opportunity(self) -> "ValidationBudgetGenerationResult":
        opportunity_uuids = [item.opportunity_uuid for item in self.budgets]

        if len(opportunity_uuids) != len(set(opportunity_uuids)):
            raise ValueError("同一商机下的验证预算估算不能重复。")

        return self


class ValidationBudgetCreate(BaseModel):
    opportunity_id: int
    estimated_unit_cost: str = Field(min_length=1, max_length=160)
    estimated_selling_price: str = Field(min_length=1, max_length=160)
    rough_gross_margin: str = Field(min_length=1, max_length=160)
    first_batch_quantity: str = Field(min_length=1, max_length=160)
    first_batch_budget: str = Field(min_length=1, max_length=160)
    key_assumptions: List[str] = Field(min_length=1, max_length=8)
    calculation_note: str = Field(min_length=1, max_length=1000)
    estimate_status: ValidationBudgetEstimateStatus

    @field_validator(
        "estimated_unit_cost",
        "estimated_selling_price",
        "rough_gross_margin",
        "first_batch_quantity",
        "first_batch_budget",
        "calculation_note",
        mode="before",
    )
    @classmethod
    def strip_create_string(cls, value: Any) -> Any:
        return strip_text(value)

    @field_validator("key_assumptions", mode="before")
    @classmethod
    def normalize_create_lists(cls, value: Any) -> List[str]:
        return normalize_string_list(value)

    @field_validator(
        "estimated_unit_cost",
        "estimated_selling_price",
        "rough_gross_margin",
        "first_batch_quantity",
        "first_batch_budget",
        "calculation_note",
    )
    @classmethod
    def require_cautious_create_scalar(cls, value: str) -> str:
        return ensure_cautious_text(value)

    @field_validator("key_assumptions")
    @classmethod
    def require_cautious_create_list(cls, value: List[str]) -> List[str]:
        return [ensure_cautious_text(item) for item in value]


class OpportunityValidationBudgetRead(BaseModel):
    uuid: UUID
    research_task_uuid: UUID
    opportunity_uuid: UUID
    estimated_unit_cost: str
    estimated_selling_price: str
    rough_gross_margin: str
    first_batch_quantity: str
    first_batch_budget: str
    key_assumptions: List[str]
    calculation_note: str
    estimate_status: ValidationBudgetEstimateStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
