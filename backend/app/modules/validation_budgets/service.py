from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from openai import OpenAI
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.integrations.langsmith import is_langsmith_tracing_enabled
from app.integrations.llm import create_llm_client
from app.modules.competitor_references import service as competitor_references_service
from app.modules.demand_insights import service as demand_insights_service
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunities.models import Opportunity
from app.modules.research_tasks.models import ResearchTask
from app.modules.supply_candidates import service as supply_candidates_service
from app.modules.validation_budgets import repository
from app.modules.validation_budgets.models import ValidationBudget
from app.modules.validation_budgets.schemas import (
    OpportunityValidationBudgetRead,
    ValidationBudgetCreate,
    ValidationBudgetGenerated,
    ValidationBudgetGenerationResult,
)

MAX_SUMMARY_TEXT_LENGTH = 360


@dataclass(frozen=True)
class ValidationBudgetCollectionResult:
    status: str
    saved_count: int
    error_summary: Optional[str] = None


class ValidationBudgetGenerationError(RuntimeError):
    pass


class ValidationBudgetGenerator(Protocol):
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate raw validation budget estimates for current opportunities."""


class DeterministicValidationBudgetGenerator:
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        budgets: list[dict[str, Any]] = []
        task_budget = context["task"].get("budget") or "用户填写预算"

        for opportunity in context["opportunities"]:
            has_inputs = bool(opportunity["supply_summaries"]) or bool(
                opportunity["competitor_summaries"]
            )
            estimate_status = "fallback" if has_inputs else "insufficient_data"
            evidence_note = (
                "结合已有货源候选和竞品参考做粗略估算"
                if has_inputs
                else "当前缺少直接货源或竞品价格线索，只能基于商机价格带做保守粗算"
            )
            budgets.append(
                {
                    "opportunity_uuid": opportunity["uuid"],
                    "estimated_unit_cost": (
                        "可先按目标售价的 40%-60% 倒推询价，"
                        "实际采购价、样品费和运费需要继续确认。"
                    ),
                    "estimated_selling_price": (
                        f"可先围绕商机价格带 {opportunity['price_band']} 做测试，"
                        "真实成交价需要用询单和小批量反馈验证。"
                    ),
                    "rough_gross_margin": (
                        f"基础推荐给出的粗略利润空间为 {opportunity['rough_margin']}；"
                        "扣除运费、损耗和平台费用后需要重新核算。"
                    ),
                    "first_batch_quantity": (
                        "建议先 20-50 件或样品小单验证，避免首轮压库存。"
                    ),
                    "first_batch_budget": (
                        f"建议把首批拿货、样品和基础内容测试控制在 {task_budget} "
                        "内的一小部分，优先保留补样和调整空间。"
                    ),
                    "key_assumptions": [
                        "供应商能够支持小批量或样品验证，且起订量不会明显推高首批预算。",
                        "测试售价能被目标人群接受，且不会因为运费、损耗和售后压缩毛利。",
                    ],
                    "calculation_note": (
                        f"{evidence_note}；该预算只适合作为首批验证前的初步参考，"
                        "采购价、售价、运费和转化反馈仍需逐项确认。"
                    ),
                    "estimate_status": estimate_status,
                }
            )

        return {"budgets": budgets}


class LLMValidationBudgetGenerator:
    def __init__(self, client: Optional[OpenAI] = None) -> None:
        settings = get_settings()
        self.client = client or create_llm_client()
        self.model = settings.llm_model
        self.provider = settings.llm_provider

    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 MarketPilot 的中文小成本商机验证预算 Agent。"
                        "你只生成首批验证预算粗算和待验证假设，不要声称采购价、"
                        "售价、毛利、成交价或回本结果已经确认。必须输出 JSON，"
                        "顶层 key 为 budgets。"
                    ),
                },
                {
                    "role": "user",
                    "content": build_generation_prompt(context),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.25,
        }

        if is_langsmith_tracing_enabled():
            create_kwargs["langsmith_extra"] = {
                "metadata": {
                    "provider": self.provider,
                    "model": self.model,
                    "task_uuid": context["task"].get("uuid"),
                    "run_id": context["task"].get("run_id"),
                },
                "tags": ["marketpilot", "validation-budgets"],
            }

        completion = self.client.chat.completions.create(**create_kwargs)
        content = completion.choices[0].message.content

        if not content:
            raise ValidationBudgetGenerationError("模型没有返回验证预算估算内容。")

        return parse_json_content(content)


def list_task_validation_budgets(
    db: Session,
    task: ResearchTask,
) -> list[ValidationBudget]:
    return repository.list_active_budgets_by_task_id(db, task.id)


def list_opportunity_validation_budgets(
    db: Session,
    opportunity: Opportunity,
) -> list[ValidationBudget]:
    return repository.list_active_budgets_by_opportunity_id(db, opportunity.id)


def replace_task_validation_budgets(
    db: Session,
    task: ResearchTask,
    budget_inputs: list[ValidationBudgetCreate],
) -> list[ValidationBudget]:
    repository.soft_delete_active_budgets_by_task_id(db, task.id)

    budgets = [
        ValidationBudget(
            research_task_id=task.id,
            opportunity_id=item.opportunity_id,
            estimated_unit_cost=item.estimated_unit_cost,
            estimated_selling_price=item.estimated_selling_price,
            rough_gross_margin=item.rough_gross_margin,
            first_batch_quantity=item.first_batch_quantity,
            first_batch_budget=item.first_batch_budget,
            key_assumptions=item.key_assumptions,
            calculation_note=item.calculation_note,
            estimate_status=item.estimate_status.value,
        )
        for item in budget_inputs
    ]

    repository.add_budgets(db, budgets)
    db.commit()

    for budget in budgets:
        db.refresh(budget)

    return budgets


def collect_validation_budgets(
    db: Session,
    task: ResearchTask,
    *,
    generator: Optional[ValidationBudgetGenerator] = None,
) -> ValidationBudgetCollectionResult:
    opportunities = opportunities_service.list_task_opportunities(db, task)

    if not opportunities:
        replace_task_validation_budgets(db, task, [])
        return ValidationBudgetCollectionResult(status="empty", saved_count=0)

    active_generator = generator or get_validation_budget_generator()
    generation_result = generate_validated_budgets(
        active_generator,
        build_generation_context(
            task,
            opportunities,
            build_demand_summaries_by_opportunity_id(db, task),
            build_supply_summaries_by_opportunity_id(db, task),
            build_competitor_summaries_by_opportunity_id(db, task),
        ),
    )
    generated_by_uuid = {
        str(budget.opportunity_uuid): budget for budget in generation_result.budgets
    }
    missing_uuids = [
        str(opportunity.uuid)
        for opportunity in opportunities
        if str(opportunity.uuid) not in generated_by_uuid
    ]

    if missing_uuids:
        raise ValidationBudgetGenerationError(
            f"验证预算估算缺少商机结果：{', '.join(missing_uuids[:3])}"
        )

    budget_inputs = [
        build_budget_create(opportunity, generated_by_uuid[str(opportunity.uuid)])
        for opportunity in opportunities
    ]
    saved = replace_task_validation_budgets(db, task, budget_inputs)

    return ValidationBudgetCollectionResult(
        status=make_collection_status(generation_result.budgets),
        saved_count=len(saved),
    )


def get_validation_budget_generator() -> ValidationBudgetGenerator:
    settings = get_settings()

    if settings.llm_api_key:
        return LLMValidationBudgetGenerator()

    if settings.environment.lower() in {"local", "test"}:
        return DeterministicValidationBudgetGenerator()

    raise ValidationBudgetGenerationError("生产环境未配置 LLM_API_KEY。")


def generate_validated_budgets(
    generator: ValidationBudgetGenerator,
    context: dict[str, Any],
) -> ValidationBudgetGenerationResult:
    last_error: Optional[Exception] = None

    for _ in range(2):
        raw_result = generator.generate(context)

        try:
            return ValidationBudgetGenerationResult.model_validate(raw_result)
        except ValidationError as exc:
            last_error = exc

    raise ValidationBudgetGenerationError(f"验证预算估算输出未通过结构化校验：{last_error}")


def build_budget_create(
    opportunity: Opportunity,
    generated: ValidationBudgetGenerated,
) -> ValidationBudgetCreate:
    return ValidationBudgetCreate(
        opportunity_id=opportunity.id,
        estimated_unit_cost=generated.estimated_unit_cost,
        estimated_selling_price=generated.estimated_selling_price,
        rough_gross_margin=generated.rough_gross_margin,
        first_batch_quantity=generated.first_batch_quantity,
        first_batch_budget=generated.first_batch_budget,
        key_assumptions=generated.key_assumptions,
        calculation_note=generated.calculation_note,
        estimate_status=generated.estimate_status,
    )


def validation_budget_to_read(
    budget: ValidationBudget,
    *,
    research_task_uuid: Any,
    opportunity_uuid: Any,
) -> OpportunityValidationBudgetRead:
    return OpportunityValidationBudgetRead(
        uuid=budget.uuid,
        research_task_uuid=research_task_uuid,
        opportunity_uuid=opportunity_uuid,
        estimated_unit_cost=budget.estimated_unit_cost,
        estimated_selling_price=budget.estimated_selling_price,
        rough_gross_margin=budget.rough_gross_margin,
        first_batch_quantity=budget.first_batch_quantity,
        first_batch_budget=budget.first_batch_budget,
        key_assumptions=budget.key_assumptions,
        calculation_note=budget.calculation_note,
        estimate_status=budget.estimate_status,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
        deleted_at=budget.deleted_at,
    )


def build_demand_summaries_by_opportunity_id(
    db: Session,
    task: ResearchTask,
) -> dict[int, str]:
    return {
        insight.opportunity_id: insight.summary
        for insight in demand_insights_service.list_task_demand_insights(db, task)
    }


def build_supply_summaries_by_opportunity_id(
    db: Session,
    task: ResearchTask,
) -> dict[int, list[str]]:
    grouped: dict[int, list[str]] = {}

    for candidate in supply_candidates_service.list_task_supply_candidates(db, task):
        grouped.setdefault(candidate.opportunity_id, []).append(
            (
                f"{candidate.candidate_name}：{candidate.supply_market}，"
                f"{candidate.price_range}，{candidate.minimum_order_quantity}"
            )
        )

    return grouped


def build_competitor_summaries_by_opportunity_id(
    db: Session,
    task: ResearchTask,
) -> dict[int, list[str]]:
    grouped: dict[int, list[str]] = {}

    for reference in competitor_references_service.list_task_competitor_references(
        db,
        task,
    ):
        grouped.setdefault(reference.opportunity_id, []).append(
            (
                f"{reference.reference_name}：{reference.price_range}，"
                f"同质化 {reference.homogenization_level}"
            )
        )

    return grouped


def build_generation_context(
    task: ResearchTask,
    opportunities: list[Opportunity],
    demand_summary_by_opportunity_id: dict[int, str],
    supply_summaries_by_opportunity_id: dict[int, list[str]],
    competitor_summaries_by_opportunity_id: dict[int, list[str]],
) -> dict[str, Any]:
    return {
        "task": {
            "uuid": str(task.uuid),
            "run_id": task.run_id,
            "title": task.title,
            "brief": task.brief,
            "budget": task.budget,
            "target_channels": task.target_channels,
            "preferred_categories": task.preferred_categories,
            "excluded_categories": task.excluded_categories,
            "target_audience": task.target_audience,
            "expected_profit": task.expected_profit,
            "supply_preferences": task.supply_preferences,
            "constraints": task.constraints,
        },
        "opportunities": [
            {
                "uuid": str(opportunity.uuid),
                "name": opportunity.name,
                "product_direction": opportunity.product_direction,
                "target_audience": opportunity.target_audience,
                "recommendation_reason": opportunity.recommendation_reason,
                "suitable_channels": opportunity.suitable_channels,
                "price_band": opportunity.price_band,
                "rough_margin": opportunity.rough_margin,
                "risk_level": opportunity.risk_level,
                "next_step_summary": opportunity.next_step_summary,
                "demand_summary": demand_summary_by_opportunity_id.get(opportunity.id),
                "supply_summaries": [
                    clip_text(item, MAX_SUMMARY_TEXT_LENGTH)
                    for item in supply_summaries_by_opportunity_id.get(
                        opportunity.id,
                        [],
                    )[:3]
                ],
                "competitor_summaries": [
                    clip_text(item, MAX_SUMMARY_TEXT_LENGTH)
                    for item in competitor_summaries_by_opportunity_id.get(
                        opportunity.id,
                        [],
                    )[:3]
                ],
            }
            for opportunity in opportunities
        ],
    }


def build_generation_prompt(context: dict[str, Any]) -> str:
    return (
        "请为每个商机生成 1 条验证预算估算，JSON schema 如下：\n"
        "{\"budgets\":[{\"opportunity_uuid\":\"...\","
        "\"estimated_unit_cost\":\"...\","
        "\"estimated_selling_price\":\"...\","
        "\"rough_gross_margin\":\"...\","
        "\"first_batch_quantity\":\"...\","
        "\"first_batch_budget\":\"...\","
        "\"key_assumptions\":[\"...\"],"
        "\"calculation_note\":\"...\","
        "\"estimate_status\":\"derived|fallback|insufficient_data\"}]}\n\n"
        f"研究任务：{json.dumps(context['task'], ensure_ascii=False)}\n"
        f"商机、需求摘要、货源候选和竞品参考："
        f"{json.dumps(context['opportunities'], ensure_ascii=False)}\n\n"
        "要求：中文输出；每个商机必须且只能生成 1 条预算估算；"
        "字段可以使用区间或文字表达，不要伪造精确数字；"
        "至少给出 1 个最需要验证的关键假设；"
        "只表达粗略估算、初步参考、待验证、需要确认；"
        "不得使用“利润已确认”“保证回本”“确定毛利”“真实成交价已确认”等结论。"
    )


def make_collection_status(budgets: list[ValidationBudgetGenerated]) -> str:
    statuses = {budget.estimate_status.value for budget in budgets}

    if statuses == {"derived"}:
        return "completed"

    if "insufficient_data" in statuses:
        return "insufficient_data"

    return "fallback"


def parse_json_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    parsed = json.loads(cleaned)

    if not isinstance(parsed, dict):
        raise ValidationBudgetGenerationError("模型返回的 JSON 不是对象。")

    return parsed


def clip_text(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 3)]}..."
