from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ActionPlanStatus(str, Enum):
    DERIVED = "derived"
    FALLBACK = "fallback"
    INSUFFICIENT_DATA = "insufficient_data"


CONFIRMED_ACTION_TERMS = (
    "保证成交",
    "保证回本",
    "供应商已确认",
    "平台审核必过",
    "上架必过",
    "一定成交",
    "确定转化",
    "无需验证",
    "自动联系供应商",
    "自动发布内容",
    "自动上架",
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
    if any(term in value for term in CONFIRMED_ACTION_TERMS):
        raise ValueError("行动计划必须使用人工确认和待验证语气。")

    return value


class ActionPlanGenerated(BaseModel):
    opportunity_uuid: UUID
    validation_goal: str = Field(min_length=1, max_length=1000)
    first_batch_plan: str = Field(min_length=1, max_length=1000)
    product_validation_method: str = Field(min_length=1, max_length=1000)
    content_angles: List[str] = Field(min_length=1, max_length=8)
    title_suggestions: List[str] = Field(min_length=1, max_length=8)
    selling_point_suggestions: List[str] = Field(min_length=1, max_length=8)
    supplier_inquiry_script: str = Field(min_length=1, max_length=1200)
    prelaunch_checklist: List[str] = Field(min_length=1, max_length=10)
    plan_status: ActionPlanStatus

    @field_validator(
        "validation_goal",
        "first_batch_plan",
        "product_validation_method",
        "supplier_inquiry_script",
        mode="before",
    )
    @classmethod
    def strip_string(cls, value: Any) -> Any:
        return strip_text(value)

    @field_validator(
        "content_angles",
        "title_suggestions",
        "selling_point_suggestions",
        "prelaunch_checklist",
        mode="before",
    )
    @classmethod
    def normalize_lists(cls, value: Any) -> List[str]:
        return normalize_string_list(value)

    @field_validator(
        "validation_goal",
        "first_batch_plan",
        "product_validation_method",
        "supplier_inquiry_script",
    )
    @classmethod
    def require_cautious_scalar(cls, value: str) -> str:
        return ensure_cautious_text(value)

    @field_validator(
        "content_angles",
        "title_suggestions",
        "selling_point_suggestions",
        "prelaunch_checklist",
    )
    @classmethod
    def require_cautious_list(cls, value: List[str]) -> List[str]:
        return [ensure_cautious_text(item) for item in value]


class ActionPlanGenerationResult(BaseModel):
    action_plans: List[ActionPlanGenerated] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def require_unique_opportunity(self) -> "ActionPlanGenerationResult":
        opportunity_uuids = [item.opportunity_uuid for item in self.action_plans]

        if len(opportunity_uuids) != len(set(opportunity_uuids)):
            raise ValueError("同一商机下的行动计划不能重复。")

        return self


class ActionPlanCreate(BaseModel):
    opportunity_id: int
    validation_goal: str = Field(min_length=1, max_length=1000)
    first_batch_plan: str = Field(min_length=1, max_length=1000)
    product_validation_method: str = Field(min_length=1, max_length=1000)
    content_angles: List[str] = Field(min_length=1, max_length=8)
    title_suggestions: List[str] = Field(min_length=1, max_length=8)
    selling_point_suggestions: List[str] = Field(min_length=1, max_length=8)
    supplier_inquiry_script: str = Field(min_length=1, max_length=1200)
    prelaunch_checklist: List[str] = Field(min_length=1, max_length=10)
    plan_status: ActionPlanStatus

    @field_validator(
        "validation_goal",
        "first_batch_plan",
        "product_validation_method",
        "supplier_inquiry_script",
        mode="before",
    )
    @classmethod
    def strip_create_string(cls, value: Any) -> Any:
        return strip_text(value)

    @field_validator(
        "content_angles",
        "title_suggestions",
        "selling_point_suggestions",
        "prelaunch_checklist",
        mode="before",
    )
    @classmethod
    def normalize_create_lists(cls, value: Any) -> List[str]:
        return normalize_string_list(value)

    @field_validator(
        "validation_goal",
        "first_batch_plan",
        "product_validation_method",
        "supplier_inquiry_script",
    )
    @classmethod
    def require_cautious_create_scalar(cls, value: str) -> str:
        return ensure_cautious_text(value)

    @field_validator(
        "content_angles",
        "title_suggestions",
        "selling_point_suggestions",
        "prelaunch_checklist",
    )
    @classmethod
    def require_cautious_create_list(cls, value: List[str]) -> List[str]:
        return [ensure_cautious_text(item) for item in value]


class OpportunityActionPlanRead(BaseModel):
    uuid: UUID
    research_task_uuid: UUID
    opportunity_uuid: UUID
    validation_goal: str
    first_batch_plan: str
    product_validation_method: str
    content_angles: List[str]
    title_suggestions: List[str]
    selling_point_suggestions: List[str]
    supplier_inquiry_script: str
    prelaunch_checklist: List[str]
    plan_status: ActionPlanStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
