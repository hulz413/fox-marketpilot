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
from app.modules.action_plans import repository
from app.modules.action_plans.models import ActionPlan
from app.modules.action_plans.schemas import (
    ActionPlanCreate,
    ActionPlanGenerated,
    ActionPlanGenerationResult,
    OpportunityActionPlanRead,
)
from app.modules.competitor_references import service as competitor_references_service
from app.modules.demand_insights import service as demand_insights_service
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunities.models import Opportunity
from app.modules.opportunity_risks import service as opportunity_risks_service
from app.modules.research_tasks.models import ResearchTask
from app.modules.sources import service as sources_service
from app.modules.supply_candidates import service as supply_candidates_service
from app.modules.validation_budgets import service as validation_budgets_service

MAX_SUMMARY_TEXT_LENGTH = 360


@dataclass(frozen=True)
class ActionPlanCollectionResult:
    status: str
    saved_count: int
    error_summary: Optional[str] = None


class ActionPlanGenerationError(RuntimeError):
    pass


class ActionPlanGenerator(Protocol):
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate raw action plans for current opportunities."""


class DeterministicActionPlanGenerator:
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        action_plans: list[dict[str, Any]] = []
        task_budget = context["task"].get("budget") or "用户填写预算"
        channels = context["task"].get("target_channels") or ["中文内容平台"]
        primary_channel = channels[0] if channels else "中文内容平台"

        for opportunity in context["opportunities"]:
            has_inputs = any(
                [
                    opportunity["supply_summaries"],
                    opportunity["competitor_summaries"],
                    opportunity["validation_budget_summaries"],
                    opportunity["risk_summaries"],
                ]
            )
            plan_status = "fallback" if has_inputs else "insufficient_data"
            action_plans.append(
                {
                    "opportunity_uuid": opportunity["uuid"],
                    "validation_goal": (
                        f"用小批量样品验证“{opportunity['name']}”是否能在"
                        f"{primary_channel} 吸引目标人群收藏、询单和下单意向。"
                    ),
                    "first_batch_plan": (
                        f"首轮把拿货、样品和内容测试控制在 {task_budget} 内的一小部分，"
                        "优先用 20-50 件或样品小单测试，不建议一次压大库存。"
                    ),
                    "product_validation_method": (
                        "先向 2-3 家供应商确认样品、小单起订量、包装和发货时效；"
                        "收到样品后拍摄真实场景内容，记录收藏、评论、询单和售后反馈。"
                    ),
                    "content_angles": [
                        f"围绕“{opportunity['product_direction']}”做使用前后对比内容。",
                        f"用目标人群“{opportunity['target_audience']}”的具体场景切入。",
                        "把预算、避坑点和真实体验拆成连续 3 条图文或短视频测试。",
                    ],
                    "title_suggestions": [
                        f"{opportunity['name']} 小预算试用记录",
                        f"{opportunity['target_audience']} 可以先看的选品清单",
                    ],
                    "selling_point_suggestions": [
                        "小批量可验证，先看样品和真实反馈。",
                        "场景明确，适合用内容测试收藏和询单。",
                        "先确认质量、包装和售后边界，再决定补货。",
                    ],
                    "supplier_inquiry_script": (
                        "你好，我想先做小批量验证，请帮忙确认样品价格、起订量、"
                        "阶梯报价、发货时效、包装方式、破损补发、退换货责任和是否支持"
                        "少量混批。当前只是首轮测试，后续会根据反馈决定是否补货。"
                    ),
                    "prelaunch_checklist": [
                        "检查样品材质、做工、气味、尺寸、包装和实际使用体验。",
                        "确认起订量、发货时效、破损补发、退换货责任和补货稳定性。",
                        "检查标题、卖点和内容表达，避免使用过度承诺或平台敏感说法。",
                        "记录首批预算、询单、收藏、成交意向和差评原因，作为补货依据。",
                    ],
                    "plan_status": plan_status,
                }
            )

        return {"action_plans": action_plans}


class LLMActionPlanGenerator:
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
                        "你是 MarketPilot 的中文小成本商机行动计划 Agent。"
                        "你只生成供用户人工执行和调整的首批验证建议，不要声称已经自动下单、"
                        "自动联系供应商、自动发布内容或保证成交回本。必须输出 JSON，"
                        "顶层 key 为 action_plans。"
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
                "tags": ["marketpilot", "action-plans"],
            }

        completion = self.client.chat.completions.create(**create_kwargs)
        content = completion.choices[0].message.content

        if not content:
            raise ActionPlanGenerationError("模型没有返回行动计划内容。")

        return parse_json_content(content)


def list_task_action_plans(
    db: Session,
    task: ResearchTask,
) -> list[ActionPlan]:
    return repository.list_active_action_plans_by_task_id(db, task.id)


def list_opportunity_action_plans(
    db: Session,
    opportunity: Opportunity,
) -> list[ActionPlan]:
    return repository.list_active_action_plans_by_opportunity_id(db, opportunity.id)


def replace_task_action_plans(
    db: Session,
    task: ResearchTask,
    action_plan_inputs: list[ActionPlanCreate],
) -> list[ActionPlan]:
    repository.soft_delete_active_action_plans_by_task_id(db, task.id)

    action_plans = [
        ActionPlan(
            research_task_id=task.id,
            opportunity_id=item.opportunity_id,
            validation_goal=item.validation_goal,
            first_batch_plan=item.first_batch_plan,
            product_validation_method=item.product_validation_method,
            content_angles=item.content_angles,
            title_suggestions=item.title_suggestions,
            selling_point_suggestions=item.selling_point_suggestions,
            supplier_inquiry_script=item.supplier_inquiry_script,
            prelaunch_checklist=item.prelaunch_checklist,
            plan_status=item.plan_status.value,
        )
        for item in action_plan_inputs
    ]

    repository.add_action_plans(db, action_plans)
    db.commit()

    for action_plan in action_plans:
        db.refresh(action_plan)

    return action_plans


def collect_action_plans(
    db: Session,
    task: ResearchTask,
    *,
    generator: Optional[ActionPlanGenerator] = None,
) -> ActionPlanCollectionResult:
    opportunities = opportunities_service.list_task_opportunities(db, task)

    if not opportunities:
        replace_task_action_plans(db, task, [])
        return ActionPlanCollectionResult(status="empty", saved_count=0)

    active_generator = generator or get_action_plan_generator()
    generation_result = generate_validated_action_plans(
        active_generator,
        build_generation_context(
            task,
            opportunities,
            build_source_summaries_by_opportunity_id(db, task),
            build_demand_summaries_by_opportunity_id(db, task),
            build_supply_summaries_by_opportunity_id(db, task),
            build_competitor_summaries_by_opportunity_id(db, task),
            build_validation_budget_summaries_by_opportunity_id(db, task),
            build_risk_summaries_by_opportunity_id(db, task),
        ),
    )
    generated_by_uuid = {
        str(plan.opportunity_uuid): plan for plan in generation_result.action_plans
    }
    missing_uuids = [
        str(opportunity.uuid)
        for opportunity in opportunities
        if str(opportunity.uuid) not in generated_by_uuid
    ]

    if missing_uuids:
        raise ActionPlanGenerationError(
            f"行动计划缺少商机结果：{', '.join(missing_uuids[:3])}"
        )

    action_plan_inputs = [
        build_action_plan_create(
            opportunity,
            generated_by_uuid[str(opportunity.uuid)],
        )
        for opportunity in opportunities
    ]
    saved = replace_task_action_plans(db, task, action_plan_inputs)

    return ActionPlanCollectionResult(
        status=make_collection_status(generation_result.action_plans),
        saved_count=len(saved),
    )


def get_action_plan_generator() -> ActionPlanGenerator:
    settings = get_settings()

    if settings.llm_api_key:
        return LLMActionPlanGenerator()

    if settings.environment.lower() in {"local", "test"}:
        return DeterministicActionPlanGenerator()

    raise ActionPlanGenerationError("生产环境未配置 LLM_API_KEY。")


def generate_validated_action_plans(
    generator: ActionPlanGenerator,
    context: dict[str, Any],
) -> ActionPlanGenerationResult:
    last_error: Optional[Exception] = None

    for _ in range(2):
        raw_result = generator.generate(context)

        try:
            return ActionPlanGenerationResult.model_validate(raw_result)
        except ValidationError as exc:
            last_error = exc

    raise ActionPlanGenerationError(f"行动计划输出未通过结构化校验：{last_error}")


def build_action_plan_create(
    opportunity: Opportunity,
    generated: ActionPlanGenerated,
) -> ActionPlanCreate:
    return ActionPlanCreate(
        opportunity_id=opportunity.id,
        validation_goal=generated.validation_goal,
        first_batch_plan=generated.first_batch_plan,
        product_validation_method=generated.product_validation_method,
        content_angles=generated.content_angles,
        title_suggestions=generated.title_suggestions,
        selling_point_suggestions=generated.selling_point_suggestions,
        supplier_inquiry_script=generated.supplier_inquiry_script,
        prelaunch_checklist=generated.prelaunch_checklist,
        plan_status=generated.plan_status,
    )


def action_plan_to_read(
    action_plan: ActionPlan,
    *,
    research_task_uuid: Any,
    opportunity_uuid: Any,
) -> OpportunityActionPlanRead:
    return OpportunityActionPlanRead(
        uuid=action_plan.uuid,
        research_task_uuid=research_task_uuid,
        opportunity_uuid=opportunity_uuid,
        validation_goal=action_plan.validation_goal,
        first_batch_plan=action_plan.first_batch_plan,
        product_validation_method=action_plan.product_validation_method,
        content_angles=action_plan.content_angles,
        title_suggestions=action_plan.title_suggestions,
        selling_point_suggestions=action_plan.selling_point_suggestions,
        supplier_inquiry_script=action_plan.supplier_inquiry_script,
        prelaunch_checklist=action_plan.prelaunch_checklist,
        plan_status=action_plan.plan_status,
        created_at=action_plan.created_at,
        updated_at=action_plan.updated_at,
        deleted_at=action_plan.deleted_at,
    )


def build_source_summaries_by_opportunity_id(
    db: Session,
    task: ResearchTask,
) -> dict[int, list[str]]:
    grouped: dict[int, list[str]] = {}

    for source in sources_service.list_task_sources(db, task):
        if source.opportunity_id is None:
            continue

        grouped.setdefault(source.opportunity_id, []).append(
            f"{source.source_type}：{source.title}；{source.summary}"
        )

    return grouped


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
                f"{candidate.price_range}，{candidate.minimum_order_quantity}；"
                f"待确认：{'、'.join(candidate.supplier_questions[:3])}"
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
                f"常见卖点：{'、'.join(reference.common_selling_points[:2])}；"
                f"差异化：{'、'.join(reference.differentiation_angles[:2])}"
            )
        )

    return grouped


def build_validation_budget_summaries_by_opportunity_id(
    db: Session,
    task: ResearchTask,
) -> dict[int, list[str]]:
    grouped: dict[int, list[str]] = {}

    for budget in validation_budgets_service.list_task_validation_budgets(db, task):
        assumption = budget.key_assumptions[0] if budget.key_assumptions else "待确认"
        grouped.setdefault(budget.opportunity_id, []).append(
            (
                f"首批预算 {budget.first_batch_budget}，"
                f"数量 {budget.first_batch_quantity}；关键假设：{assumption}"
            )
        )

    return grouped


def build_risk_summaries_by_opportunity_id(
    db: Session,
    task: ResearchTask,
) -> dict[int, list[str]]:
    grouped: dict[int, list[str]] = {}

    for risk in opportunity_risks_service.list_task_opportunity_risks(db, task):
        mitigation = (
            risk.mitigation_suggestions[0]
            if risk.mitigation_suggestions
            else "先做人工排查"
        )
        grouped.setdefault(risk.opportunity_id, []).append(
            (
                f"风险 {risk.overall_risk_level}：{risk.risk_summary}；"
                f"建议：{mitigation}"
            )
        )

    return grouped


def build_generation_context(
    task: ResearchTask,
    opportunities: list[Opportunity],
    source_summaries_by_opportunity_id: dict[int, list[str]],
    demand_summary_by_opportunity_id: dict[int, str],
    supply_summaries_by_opportunity_id: dict[int, list[str]],
    competitor_summaries_by_opportunity_id: dict[int, list[str]],
    validation_budget_summaries_by_opportunity_id: dict[int, list[str]],
    risk_summaries_by_opportunity_id: dict[int, list[str]],
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
                "source_summaries": [
                    clip_text(item, MAX_SUMMARY_TEXT_LENGTH)
                    for item in source_summaries_by_opportunity_id.get(
                        opportunity.id,
                        [],
                    )[:3]
                ],
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
                "validation_budget_summaries": [
                    clip_text(item, MAX_SUMMARY_TEXT_LENGTH)
                    for item in validation_budget_summaries_by_opportunity_id.get(
                        opportunity.id,
                        [],
                    )[:2]
                ],
                "risk_summaries": [
                    clip_text(item, MAX_SUMMARY_TEXT_LENGTH)
                    for item in risk_summaries_by_opportunity_id.get(
                        opportunity.id,
                        [],
                    )[:2]
                ],
            }
            for opportunity in opportunities
        ],
    }


def build_generation_prompt(context: dict[str, Any]) -> str:
    return (
        "请为每个商机生成 1 条行动计划，JSON schema 如下：\n"
        '{"action_plans":[{"opportunity_uuid":"...",'
        '"validation_goal":"...",'
        '"first_batch_plan":"...",'
        '"product_validation_method":"...",'
        '"content_angles":["..."],'
        '"title_suggestions":["..."],'
        '"selling_point_suggestions":["..."],'
        '"supplier_inquiry_script":"...",'
        '"prelaunch_checklist":["..."],'
        '"plan_status":"derived|fallback|insufficient_data"}]}\n\n'
        f"研究任务：{json.dumps(context['task'], ensure_ascii=False)}\n"
        f"商机、来源摘要、需求摘要、货源候选、竞品参考、验证预算和风险复核："
        f"{json.dumps(context['opportunities'], ensure_ascii=False)}\n\n"
        "要求：中文输出；每个商机必须且只能生成 1 条行动计划；"
        "至少包含选品验证方式、内容种草角度、商品标题建议、卖点建议、"
        "供应商询盘话术和上架前检查清单；询盘话术需要覆盖起订量、样品、"
        "价格、发货、包装或售后中的多个确认点；"
        "上架前检查清单需要覆盖质量、履约、售后、平台规则或内容表达中的多个检查点；"
        "只表达建议、待验证、需要确认或人工调整后使用；"
        "不得使用“保证成交”“保证回本”“供应商已确认”“平台审核必过”"
        "“自动联系供应商”“自动发布内容”“自动上架”等结论或自动执行表述。"
    )


def make_collection_status(action_plans: list[ActionPlanGenerated]) -> str:
    statuses = {action_plan.plan_status.value for action_plan in action_plans}

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
        raise ActionPlanGenerationError("模型返回的 JSON 不是对象。")

    return parsed


def clip_text(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 3)]}..."
