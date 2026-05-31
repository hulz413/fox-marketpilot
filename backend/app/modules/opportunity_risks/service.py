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
from app.modules.opportunity_risks import repository
from app.modules.opportunity_risks.models import OpportunityRisk
from app.modules.opportunity_risks.schemas import (
    OpportunityRiskCreate,
    OpportunityRiskGenerated,
    OpportunityRiskGenerationResult,
    OpportunityRiskRead,
)
from app.modules.research_tasks.models import ResearchTask
from app.modules.sources import service as sources_service
from app.modules.supply_candidates import service as supply_candidates_service
from app.modules.validation_budgets import service as validation_budgets_service

MAX_SUMMARY_TEXT_LENGTH = 360


@dataclass(frozen=True)
class OpportunityRiskCollectionResult:
    status: str
    saved_count: int
    error_summary: Optional[str] = None


class OpportunityRiskGenerationError(RuntimeError):
    pass


class OpportunityRiskGenerator(Protocol):
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate raw risk reviews for current opportunities."""


class DeterministicOpportunityRiskGenerator:
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        risks: list[dict[str, Any]] = []

        for opportunity in context["opportunities"]:
            has_inputs = any(
                [
                    opportunity["source_summaries"],
                    opportunity["supply_summaries"],
                    opportunity["competitor_summaries"],
                    opportunity["validation_budget_summaries"],
                ]
            )
            review_status = "fallback" if has_inputs else "insufficient_data"
            risk_level = opportunity["risk_level"]
            risk_summary = (
                f"{opportunity['name']} 当前更适合先做小批量验证；"
                "产品体验、供应商履约、售后反馈和同质化竞争都需要继续确认。"
            )
            risks.append(
                {
                    "opportunity_uuid": opportunity["uuid"],
                    "overall_risk_level": risk_level,
                    "risk_summary": risk_summary,
                    "quality_risk": (
                        "需要先用样品检查材质、做工、气味、包装和实际使用体验，"
                        "避免只凭图片判断产品质量。"
                    ),
                    "fulfillment_risk": (
                        "供应商起订量、发货时效、包装破损率和补货稳定性仍需询问确认，"
                        "首轮不建议压大库存。"
                    ),
                    "after_sales_risk": (
                        "售后重点在破损、色差、气味、尺寸不符和使用效果落差，"
                        "需要提前准备退换货口径和质检标准。"
                    ),
                    "compliance_risk": (
                        "上架前需要继续确认产品标签、材质说明、禁限售规则和宣传边界，"
                        "不要把当前提示视为合规结论。"
                    ),
                    "inventory_risk": (
                        "建议先用样品或 20-50 件小单验证收藏、询单和转化，"
                        "根据反馈再决定是否补货。"
                    ),
                    "competition_risk": (
                        "类似产品容易被价格和卖点同质化影响，需要先测试组合、场景内容"
                        "或包装差异化。"
                    ),
                    "platform_risk": (
                        "内容平台和电商平台的标题、功效表达、类目和售后规则需要继续排查，"
                        "避免使用过度承诺文案。"
                    ),
                    "risk_triggers": [
                        "当前判断主要来自基础商机字段和已有增强信息，供应商履约与平台规则仍待确认。",
                        "首批预算和竞品参考只能作为初步参考，需要用样品和小单反馈验证。",
                    ],
                    "mitigation_suggestions": [
                        "先向 2-3 家供应商确认起订量、发货时效、包装方式和退换货责任。",
                        "先采购样品或小批量做内容测试，记录破损、差评、询单和转化反馈。",
                    ],
                    "review_status": review_status,
                }
            )

        return {"risks": risks}


class LLMOpportunityRiskGenerator:
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
                        "你是 MarketPilot 的中文小成本商机风险复核 Agent。"
                        "你只生成待验证风险提示和缓解建议，不要声称已经完成法律、"
                        "合规、平台规则或供应链尽调。必须输出 JSON，顶层 key 为 risks。"
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
                "tags": ["marketpilot", "opportunity-risks"],
            }

        completion = self.client.chat.completions.create(**create_kwargs)
        content = completion.choices[0].message.content

        if not content:
            raise OpportunityRiskGenerationError("模型没有返回风险复核内容。")

        return parse_json_content(content)


def list_task_opportunity_risks(
    db: Session,
    task: ResearchTask,
) -> list[OpportunityRisk]:
    return repository.list_active_risks_by_task_id(db, task.id)


def list_opportunity_risks(
    db: Session,
    opportunity: Opportunity,
) -> list[OpportunityRisk]:
    return repository.list_active_risks_by_opportunity_id(db, opportunity.id)


def replace_task_opportunity_risks(
    db: Session,
    task: ResearchTask,
    risk_inputs: list[OpportunityRiskCreate],
) -> list[OpportunityRisk]:
    repository.soft_delete_active_risks_by_task_id(db, task.id)

    risks = [
        OpportunityRisk(
            research_task_id=task.id,
            opportunity_id=item.opportunity_id,
            overall_risk_level=item.overall_risk_level.value,
            risk_summary=item.risk_summary,
            quality_risk=item.quality_risk,
            fulfillment_risk=item.fulfillment_risk,
            after_sales_risk=item.after_sales_risk,
            compliance_risk=item.compliance_risk,
            inventory_risk=item.inventory_risk,
            competition_risk=item.competition_risk,
            platform_risk=item.platform_risk,
            risk_triggers=item.risk_triggers,
            mitigation_suggestions=item.mitigation_suggestions,
            review_status=item.review_status.value,
        )
        for item in risk_inputs
    ]

    repository.add_risks(db, risks)
    db.commit()

    for risk in risks:
        db.refresh(risk)

    return risks


def collect_opportunity_risks(
    db: Session,
    task: ResearchTask,
    *,
    generator: Optional[OpportunityRiskGenerator] = None,
) -> OpportunityRiskCollectionResult:
    opportunities = opportunities_service.list_task_opportunities(db, task)

    if not opportunities:
        replace_task_opportunity_risks(db, task, [])
        return OpportunityRiskCollectionResult(status="empty", saved_count=0)

    active_generator = generator or get_opportunity_risk_generator()
    generation_result = generate_validated_risks(
        active_generator,
        build_generation_context(
            task,
            opportunities,
            build_source_summaries_by_opportunity_id(db, task),
            build_demand_summaries_by_opportunity_id(db, task),
            build_supply_summaries_by_opportunity_id(db, task),
            build_competitor_summaries_by_opportunity_id(db, task),
            build_validation_budget_summaries_by_opportunity_id(db, task),
        ),
    )
    generated_by_uuid = {
        str(risk.opportunity_uuid): risk for risk in generation_result.risks
    }
    missing_uuids = [
        str(opportunity.uuid)
        for opportunity in opportunities
        if str(opportunity.uuid) not in generated_by_uuid
    ]

    if missing_uuids:
        raise OpportunityRiskGenerationError(
            f"风险复核缺少商机结果：{', '.join(missing_uuids[:3])}"
        )

    risk_inputs = [
        build_risk_create(opportunity, generated_by_uuid[str(opportunity.uuid)])
        for opportunity in opportunities
    ]
    saved = replace_task_opportunity_risks(db, task, risk_inputs)

    return OpportunityRiskCollectionResult(
        status=make_collection_status(generation_result.risks),
        saved_count=len(saved),
    )


def get_opportunity_risk_generator() -> OpportunityRiskGenerator:
    settings = get_settings()

    if settings.llm_api_key:
        return LLMOpportunityRiskGenerator()

    if settings.environment.lower() in {"local", "test"}:
        return DeterministicOpportunityRiskGenerator()

    raise OpportunityRiskGenerationError("生产环境未配置 LLM_API_KEY。")


def generate_validated_risks(
    generator: OpportunityRiskGenerator,
    context: dict[str, Any],
) -> OpportunityRiskGenerationResult:
    last_error: Optional[Exception] = None

    for _ in range(2):
        raw_result = generator.generate(context)

        try:
            return OpportunityRiskGenerationResult.model_validate(raw_result)
        except ValidationError as exc:
            last_error = exc

    raise OpportunityRiskGenerationError(f"风险复核输出未通过结构化校验：{last_error}")


def build_risk_create(
    opportunity: Opportunity,
    generated: OpportunityRiskGenerated,
) -> OpportunityRiskCreate:
    return OpportunityRiskCreate(
        opportunity_id=opportunity.id,
        overall_risk_level=generated.overall_risk_level,
        risk_summary=generated.risk_summary,
        quality_risk=generated.quality_risk,
        fulfillment_risk=generated.fulfillment_risk,
        after_sales_risk=generated.after_sales_risk,
        compliance_risk=generated.compliance_risk,
        inventory_risk=generated.inventory_risk,
        competition_risk=generated.competition_risk,
        platform_risk=generated.platform_risk,
        risk_triggers=generated.risk_triggers,
        mitigation_suggestions=generated.mitigation_suggestions,
        review_status=generated.review_status,
    )


def opportunity_risk_to_read(
    risk: OpportunityRisk,
    *,
    research_task_uuid: Any,
    opportunity_uuid: Any,
) -> OpportunityRiskRead:
    return OpportunityRiskRead(
        uuid=risk.uuid,
        research_task_uuid=research_task_uuid,
        opportunity_uuid=opportunity_uuid,
        overall_risk_level=risk.overall_risk_level,
        risk_summary=risk.risk_summary,
        quality_risk=risk.quality_risk,
        fulfillment_risk=risk.fulfillment_risk,
        after_sales_risk=risk.after_sales_risk,
        compliance_risk=risk.compliance_risk,
        inventory_risk=risk.inventory_risk,
        competition_risk=risk.competition_risk,
        platform_risk=risk.platform_risk,
        risk_triggers=risk.risk_triggers,
        mitigation_suggestions=risk.mitigation_suggestions,
        review_status=risk.review_status,
        created_at=risk.created_at,
        updated_at=risk.updated_at,
        deleted_at=risk.deleted_at,
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
                f"{candidate.candidate_name}：{candidate.price_range}，"
                f"{candidate.minimum_order_quantity}；待确认："
                f"{'、'.join(candidate.supplier_questions[:2])}"
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
                f"同质化 {reference.homogenization_level}；差异化："
                f"{'、'.join(reference.differentiation_angles[:2])}"
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


def build_generation_context(
    task: ResearchTask,
    opportunities: list[Opportunity],
    source_summaries_by_opportunity_id: dict[int, list[str]],
    demand_summary_by_opportunity_id: dict[int, str],
    supply_summaries_by_opportunity_id: dict[int, list[str]],
    competitor_summaries_by_opportunity_id: dict[int, list[str]],
    validation_budget_summaries_by_opportunity_id: dict[int, list[str]],
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
                    )[:4]
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
            }
            for opportunity in opportunities
        ],
    }


def build_generation_prompt(context: dict[str, Any]) -> str:
    return (
        "请为每个商机生成 1 条风险复核，JSON schema 如下：\n"
        '{"risks":[{"opportunity_uuid":"...",'
        '"overall_risk_level":"low|medium|high",'
        '"risk_summary":"...",'
        '"quality_risk":"...",'
        '"fulfillment_risk":"...",'
        '"after_sales_risk":"...",'
        '"compliance_risk":"...",'
        '"inventory_risk":"...",'
        '"competition_risk":"...",'
        '"platform_risk":"...",'
        '"risk_triggers":["..."],'
        '"mitigation_suggestions":["..."],'
        '"review_status":"derived|fallback|insufficient_data"}]}\n\n'
        f"研究任务：{json.dumps(context['task'], ensure_ascii=False)}\n"
        f"商机、来源摘要、需求摘要、货源候选、竞品参考和验证预算："
        f"{json.dumps(context['opportunities'], ensure_ascii=False)}\n\n"
        "要求：中文输出；每个商机必须且只能生成 1 条风险复核；"
        "至少覆盖产品质量、发货履约、售后和同质化竞争风险；"
        "在信息可用时覆盖合规、库存积压和平台规则风险；"
        "至少给出 1 个风险触发原因和 1 个可执行缓解建议；"
        "只表达风险提示、初步参考、待验证、需要确认或建议先排查；"
        "不得使用“合规已确认”“供应商履约已验证”“平台规则无风险”"
        "“库存风险已排除”等结论。"
    )


def make_collection_status(risks: list[OpportunityRiskGenerated]) -> str:
    statuses = {risk.review_status.value for risk in risks}

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
        raise OpportunityRiskGenerationError("模型返回的 JSON 不是对象。")

    return parsed


def clip_text(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 3)]}..."
