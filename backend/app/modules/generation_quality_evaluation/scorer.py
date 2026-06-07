from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import re
from typing import Any
from uuid import UUID

from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.exc import NoInspectionAvailable

from app.modules.action_plans.models import ActionPlan
from app.modules.competitor_references.models import CompetitorReference
from app.modules.demand_insights.models import OpportunityDemandInsight
from app.modules.generation_quality_evaluation.models import GenerationEvaluationCase
from app.modules.generation_quality_evaluation.schemas import (
    GenerationEvaluationResultStatus,
    GenerationEvaluationScore,
)
from app.modules.opportunities.models import Opportunity
from app.modules.opportunity_risks.models import OpportunityRisk
from app.modules.research_tasks.models import ResearchTask
from app.modules.supply_candidates.models import SupplyCandidate
from app.modules.validation_budgets.models import ValidationBudget

CAUTIOUS_TERMS = [
    "初步",
    "待验证",
    "待确认",
    "候选",
    "参考",
    "需要确认",
    "建议",
]

RISKY_CLAIMS = [
    "已核验",
    "已调研公开市场",
    "已核验竞品",
    "已确认库存",
    "供应商确认",
    "库存确认",
    "保证利润",
    "利润保证",
    "自动联系供应商",
    "自动发布内容",
    "自动上架",
    "完成真实验证",
    "已经完成真实验证",
]

REQUIRED_OPPORTUNITY_FIELDS = [
    ("name", "商机名称"),
    ("product_direction", "产品方向"),
    ("target_audience", "目标人群"),
    ("recommendation_reason", "推荐理由"),
    ("suitable_channels", "适合渠道"),
    ("price_band", "价格带"),
    ("rough_margin", "粗略利润"),
    ("risk_level", "风险等级"),
    ("priority_label", "推荐优先级"),
    ("next_step_summary", "下一步摘要"),
]


@dataclass(frozen=True)
class GenerationEvaluationContext:
    task: ResearchTask
    opportunities: list[Opportunity]
    demand_insights: list[OpportunityDemandInsight]
    supply_candidates: list[SupplyCandidate]
    competitor_references: list[CompetitorReference]
    validation_budgets: list[ValidationBudget]
    opportunity_risks: list[OpportunityRisk]
    action_plans: list[ActionPlan]


@dataclass(frozen=True)
class DimensionResult:
    status: GenerationEvaluationResultStatus
    reasons: list[str]
    actions: list[str]
    affected_opportunity_uuids: list[UUID]
    metrics: dict[str, Any]


def score_generation_case(
    evaluation_case: GenerationEvaluationCase,
    context: GenerationEvaluationContext,
) -> GenerationEvaluationScore:
    category = evaluation_case.category
    if category == "constraints":
        result = check_constraints(context)
    elif category == "structure":
        result = check_structure(context)
    elif category == "consistency":
        result = check_consistency(context)
    elif category == "risk_quality":
        result = check_risk_quality(context)
    elif category == "action_quality":
        result = check_action_quality(context)
    elif category == "cautious_boundary":
        result = check_cautious_boundary(context)
    else:
        result = DimensionResult(
            status=GenerationEvaluationResultStatus.SKIPPED,
            reasons=[f"暂不支持的生成质量评测类别：{category}。"],
            actions=["检查评测 case 配置。"],
            affected_opportunity_uuids=[],
            metrics={"category": category},
        )

    rubric_scores = {
        category: {
            "status": result.status.value,
            "reason_count": len(result.reasons),
            **result.metrics,
        }
    }
    return GenerationEvaluationScore(
        status=result.status,
        rubric_scores=rubric_scores,
        reasons=result.reasons,
        actions=result.actions,
        affected_opportunity_uuids=result.affected_opportunity_uuids,
        scoring_notes=build_scoring_notes(evaluation_case, result),
    )


def check_constraints(context: GenerationEvaluationContext) -> DimensionResult:
    reasons: list[str] = []
    actions: list[str] = []
    affected: set[UUID] = set()
    task = context.task
    opportunity_texts = opportunity_text_by_uuid(context.opportunities)
    generated_text = normalize_for_match(generated_visible_text(context))

    for category in task.excluded_categories:
        normalized = normalize_for_match(category)
        if not normalized:
            continue
        for opportunity in context.opportunities:
            if normalized in normalize_for_match(opportunity_texts[str(opportunity.uuid)]):
                reasons.append(f"{opportunity.name} 命中排除品类「{category}」。")
                affected.add(opportunity.uuid)
        if normalized in generated_text:
            reasons.append(f"用户可见增强分析中出现排除品类「{category}」。")

    budget_terms = constraint_terms(task.budget)
    if (
        task.budget
        and budget_terms
        and not any(term in generated_text for term in budget_terms)
    ):
        reasons.append("生成内容未体现预算约束。")

    expected_profit_terms = constraint_terms(task.expected_profit)
    if (
        task.expected_profit
        and expected_profit_terms
        and not any(term in generated_text for term in expected_profit_terms)
    ):
        reasons.append("生成内容未体现期望利润约束。")

    if task.target_channels:
        for opportunity in context.opportunities:
            channel_text = normalize_for_match(" ".join(opportunity.suitable_channels))
            if not any(
                normalize_for_match(channel) in channel_text
                for channel in task.target_channels
            ):
                reasons.append(f"{opportunity.name} 未体现目标渠道偏好。")
                affected.add(opportunity.uuid)

    if task.target_audience:
        expected_audience = normalize_for_match(task.target_audience)
        for opportunity in context.opportunities:
            audience_text = normalize_for_match(
                " ".join(
                    [
                        opportunity.target_audience,
                        opportunity.recommendation_reason,
                        opportunity.next_step_summary,
                    ]
                )
            )
            if expected_audience and expected_audience not in audience_text:
                reasons.append(f"{opportunity.name} 未明显贴合目标人群。")
                affected.add(opportunity.uuid)

    if task.supply_preferences and context.supply_candidates:
        for opportunity in context.opportunities:
            candidate_text = normalize_for_match(
                " ".join(
                    text_values(
                        candidate
                        for candidate in context.supply_candidates
                        if candidate.opportunity_id == opportunity.id
                    )
                )
            )
            if candidate_text and not any(
                normalize_for_match(preference) in candidate_text
                for preference in task.supply_preferences
            ):
                reasons.append(f"{opportunity.name} 的货源候选未体现供给偏好。")
                affected.add(opportunity.uuid)

    if reasons:
        actions.append("复查任务输入约束，重新生成或人工修正冲突商机。")

    return DimensionResult(
        status=GenerationEvaluationResultStatus.WARNING
        if reasons
        else GenerationEvaluationResultStatus.PASSED,
        reasons=dedupe(reasons),
        actions=actions,
        affected_opportunity_uuids=sorted(affected, key=str),
        metrics={
            "opportunity_count": len(context.opportunities),
            "excluded_category_count": len(task.excluded_categories),
            "target_channel_count": len(task.target_channels),
            "budget_term_count": len(budget_terms),
            "expected_profit_term_count": len(expected_profit_terms),
            "issue_count": len(dedupe(reasons)),
        },
    )


def check_structure(context: GenerationEvaluationContext) -> DimensionResult:
    reasons: list[str] = []
    affected: set[UUID] = set()

    if len(context.opportunities) < 3:
        reasons.append("active 商机少于 3 个。")
    if len(context.opportunities) > 5:
        reasons.append("active 商机超过 5 个。")

    for opportunity in context.opportunities:
        for field_name, label in REQUIRED_OPPORTUNITY_FIELDS:
            if is_empty_value(getattr(opportunity, field_name)):
                reasons.append(f"{opportunity.name}: {label} 缺失。")
                affected.add(opportunity.uuid)

    return DimensionResult(
        status=GenerationEvaluationResultStatus.FAILED
        if reasons
        else GenerationEvaluationResultStatus.PASSED,
        reasons=dedupe(reasons),
        actions=["补齐商机结果字段或重新运行研究任务。"] if reasons else [],
        affected_opportunity_uuids=sorted(affected, key=str),
        metrics={
            "opportunity_count": len(context.opportunities),
            "missing_field_count": len(dedupe(reasons)),
        },
    )


def check_consistency(context: GenerationEvaluationContext) -> DimensionResult:
    enhancement_groups = {
        "需求洞察": context.demand_insights,
        "货源候选": context.supply_candidates,
        "竞品参考": context.competitor_references,
        "验证预算": context.validation_budgets,
    }
    reasons: list[str] = []
    affected: set[UUID] = set()

    for label, records in enhancement_groups.items():
        opportunity_ids = {record.opportunity_id for record in records}
        for opportunity in context.opportunities:
            if opportunity.id not in opportunity_ids:
                reasons.append(f"{opportunity.name} 缺少{label}记录。")
                affected.add(opportunity.uuid)

    for category in context.task.excluded_categories:
        normalized = normalize_for_match(category)
        if normalized and normalized in normalize_for_match(
            generated_visible_text(context)
        ):
            reasons.append(f"增强分析中出现排除品类「{category}」。")

    return DimensionResult(
        status=GenerationEvaluationResultStatus.WARNING
        if reasons
        else GenerationEvaluationResultStatus.PASSED,
        reasons=dedupe(reasons),
        actions=["补齐缺失增强分析或复查冲突内容。"] if reasons else [],
        affected_opportunity_uuids=sorted(affected, key=str),
        metrics={
            "demand_insight_count": len(context.demand_insights),
            "supply_candidate_count": len(context.supply_candidates),
            "competitor_reference_count": len(context.competitor_references),
            "validation_budget_count": len(context.validation_budgets),
            "issue_count": len(dedupe(reasons)),
        },
    )


def check_risk_quality(context: GenerationEvaluationContext) -> DimensionResult:
    reasons: list[str] = []
    affected: set[UUID] = set()
    risks_by_opportunity = group_by_opportunity_id(context.opportunity_risks)
    required_fields = [
        ("quality_risk", "质量风险"),
        ("fulfillment_risk", "履约风险"),
        ("after_sales_risk", "售后风险"),
        ("competition_risk", "竞争风险"),
    ]

    for opportunity in context.opportunities:
        risks = risks_by_opportunity.get(opportunity.id, [])
        if not risks:
            reasons.append(f"{opportunity.name} 缺少风险复核。")
            affected.add(opportunity.uuid)
            continue
        for risk in risks:
            for field_name, label in required_fields:
                value = getattr(risk, field_name)
                if is_empty_value(value) or len(normalize_space(value)) < 12:
                    reasons.append(f"{opportunity.name}: {label} 过于空泛或缺失。")
                    affected.add(opportunity.uuid)
            if not risk.risk_triggers or not risk.mitigation_suggestions:
                reasons.append(f"{opportunity.name}: 风险触发点或缓解建议缺失。")
                affected.add(opportunity.uuid)

    return DimensionResult(
        status=GenerationEvaluationResultStatus.WARNING
        if reasons
        else GenerationEvaluationResultStatus.PASSED,
        reasons=dedupe(reasons),
        actions=["补充具体风险维度、触发点和缓解建议。"] if reasons else [],
        affected_opportunity_uuids=sorted(affected, key=str),
        metrics={
            "opportunity_risk_count": len(context.opportunity_risks),
            "issue_count": len(dedupe(reasons)),
        },
    )


def check_action_quality(context: GenerationEvaluationContext) -> DimensionResult:
    reasons: list[str] = []
    affected: set[UUID] = set()
    plans_by_opportunity = group_by_opportunity_id(context.action_plans)

    for opportunity in context.opportunities:
        plans = plans_by_opportunity.get(opportunity.id, [])
        if not plans:
            reasons.append(f"{opportunity.name} 缺少行动计划。")
            affected.add(opportunity.uuid)
            continue
        for plan in plans:
            if is_empty_value(plan.product_validation_method):
                reasons.append(f"{opportunity.name}: 缺少产品验证方式。")
                affected.add(opportunity.uuid)
            if is_empty_value(plan.supplier_inquiry_script):
                reasons.append(f"{opportunity.name}: 缺少供应商询盘话术。")
                affected.add(opportunity.uuid)
            if not plan.prelaunch_checklist:
                reasons.append(f"{opportunity.name}: 缺少上架前检查清单。")
                affected.add(opportunity.uuid)
            plan_text = normalize_for_match(" ".join(text_values([plan])))
            if not any(term in plan_text for term in ["样品", "小批量", "询单", "反馈", "验证"]):
                reasons.append(f"{opportunity.name}: 行动建议缺少小预算验证动作。")
                affected.add(opportunity.uuid)

    return DimensionResult(
        status=GenerationEvaluationResultStatus.WARNING
        if reasons
        else GenerationEvaluationResultStatus.PASSED,
        reasons=dedupe(reasons),
        actions=["补充可执行验证动作、询盘话术和检查清单。"] if reasons else [],
        affected_opportunity_uuids=sorted(affected, key=str),
        metrics={
            "action_plan_count": len(context.action_plans),
            "issue_count": len(dedupe(reasons)),
        },
    )


def check_cautious_boundary(context: GenerationEvaluationContext) -> DimensionResult:
    text = generated_visible_text(context)
    normalized = normalize_for_match(text)
    risky_hits = [term for term in RISKY_CLAIMS if risky_claim_present(term, normalized)]
    has_cautious_terms = any(
        normalize_for_match(term) in normalized for term in CAUTIOUS_TERMS
    )
    reasons: list[str] = []

    if risky_hits:
        reasons.append(f"命中高风险断言：{'、'.join(risky_hits)}。")
    if text and not has_cautious_terms:
        reasons.append("用户可见文案缺少初步参考或待验证类谨慎表达。")

    if risky_hits:
        status = GenerationEvaluationResultStatus.FAILED
    elif reasons:
        status = GenerationEvaluationResultStatus.WARNING
    else:
        status = GenerationEvaluationResultStatus.PASSED

    return DimensionResult(
        status=status,
        reasons=reasons,
        actions=["修正文案，避免把待验证建议表述为已核验结论。"] if reasons else [],
        affected_opportunity_uuids=[],
        metrics={
            "risky_claim_count": len(risky_hits),
            "has_cautious_terms": has_cautious_terms,
        },
    )


def build_scoring_notes(
    evaluation_case: GenerationEvaluationCase,
    result: DimensionResult,
) -> str:
    if result.reasons:
        return f"{evaluation_case.name}: {'；'.join(result.reasons[:5])}"
    return f"{evaluation_case.name}: rubric 检查未发现明显问题。"


def group_by_opportunity_id(records: Iterable[Any]) -> dict[int, list[Any]]:
    grouped: dict[int, list[Any]] = {}
    for record in records:
        grouped.setdefault(record.opportunity_id, []).append(record)
    return grouped


def opportunity_text_by_uuid(opportunities: list[Opportunity]) -> dict[str, str]:
    return {
        str(opportunity.uuid): " ".join(text_values([opportunity]))
        for opportunity in opportunities
    }


def visible_text(context: GenerationEvaluationContext) -> str:
    return " ".join(
        text_values(
            [
                context.task,
                *generated_output_values(context),
            ]
        )
    )


def generated_visible_text(context: GenerationEvaluationContext) -> str:
    return " ".join(text_values(generated_output_values(context)))


def generated_output_values(context: GenerationEvaluationContext) -> list[Any]:
    return [
        *context.opportunities,
        *context.demand_insights,
        *context.supply_candidates,
        *context.competitor_references,
        *context.validation_budgets,
        *context.opportunity_risks,
        *context.action_plans,
    ]


def text_values(values: Iterable[Any]) -> list[str]:
    output: list[str] = []

    def walk(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            if value.strip():
                output.append(value.strip())
            return
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                walk(item)
            return
        if hasattr(value, "__dict__"):
            try:
                mapper = sqlalchemy_inspect(value).mapper
            except NoInspectionAvailable:
                mapper = None

            if mapper is not None:
                for column_attr in mapper.column_attrs:
                    key = column_attr.key
                    if key.startswith("_") or key.endswith("_id") or key == "id":
                        continue
                    walk(getattr(value, key))
                return

            for key, item in vars(value).items():
                if key.startswith("_") or key.endswith("_id") or key == "id":
                    continue
                walk(item)

    for value in values:
        walk(value)

    return output


def is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not value
    return False


def normalize_for_match(value: str) -> str:
    return normalize_space(value).lower()


def normalize_space(value: str) -> str:
    return " ".join(str(value).split())


def risky_claim_present(term: str, normalized_text: str) -> bool:
    compact_text = normalized_text.replace(" ", "")
    compact_term = normalize_for_match(term).replace(" ", "")
    cautious_prefixes = ["待", "需", "需要", "仍需", "继续", "待向", "待由"]
    start = 0

    while compact_term:
        index = compact_text.find(compact_term, start)
        if index < 0:
            return False

        prefix = compact_text[max(0, index - 4) : index]
        if not any(prefix.endswith(item) for item in cautious_prefixes):
            return True
        start = index + len(compact_term)

    return False


def constraint_terms(value: str | None) -> list[str]:
    if not value:
        return []

    terms = [
        normalize_for_match(match)
        for match in re.findall(r"\d+(?:\.\d+)?\s*%?", value)
    ]
    normalized = normalize_for_match(value)
    if normalized and len(normalized) <= 24:
        terms.append(normalized)
    return dedupe([term for term in terms if term])


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output
