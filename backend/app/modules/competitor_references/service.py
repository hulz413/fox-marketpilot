from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from openai import OpenAI
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.integrations.langsmith import is_langsmith_tracing_enabled
from app.integrations.llm import create_llm_client
from app.modules.competitor_references import repository
from app.modules.competitor_references.models import (
    CompetitorReference,
    CompetitorReferenceSource,
)
from app.modules.competitor_references.schemas import (
    CompetitorReferenceCreate,
    CompetitorReferenceGenerated,
    CompetitorReferenceGenerationResult,
    CompetitorReferenceSourceLinkCreate,
    CompetitorReferenceSourceStatus,
    CompetitorReferenceSourceSummary,
    HomogenizationLevel,
    OpportunityCompetitorReferenceRead,
)
from app.modules.demand_insights import service as demand_insights_service
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunities.models import Opportunity
from app.modules.research_tasks.models import ResearchTask
from app.modules.sources import service as sources_service
from app.modules.sources.models import ResearchSource
from app.modules.sources.schemas import ResearchSourceType
from app.modules.supply_candidates import service as supply_candidates_service

MAX_SOURCES_PER_OPPORTUNITY = 3
MAX_SOURCE_TEXT_LENGTH = 360
MIN_REFERENCES_PER_OPPORTUNITY = 2


@dataclass(frozen=True)
class CompetitorReferenceCollectionResult:
    status: str
    saved_count: int
    source_link_count: int
    error_summary: Optional[str] = None


class CompetitorReferenceGenerationError(RuntimeError):
    pass


class CompetitorReferenceGenerator(Protocol):
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate raw competitor reference data for current task opportunities."""


class DeterministicCompetitorReferenceGenerator:
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        references: list[dict[str, Any]] = []
        channel = first_or_default(context["task"]["target_channels"], "中文内容平台")

        for opportunity in context["opportunities"]:
            source_count = len(opportunity["sources"])
            source_hint = (
                f"结合 {source_count} 条竞品公开线索做初步参考"
                if source_count
                else "当前缺少直接竞品来源，需要继续搜索公开资料确认"
            )
            references.extend(
                [
                    {
                        "opportunity_uuid": opportunity["uuid"],
                        "rank": 1,
                        "reference_name": f"{opportunity['name']} 同类基础款参考",
                        "reference_market": f"{channel}、电商搜索或公开内容平台",
                        "price_range": (
                            f"可先围绕商机价格带 {opportunity['price_band']} "
                            "观察类似产品价位，真实售价仍需继续核对。"
                        ),
                        "common_selling_points": [
                            "常见表达可能集中在场景改善、低门槛试用和外观展示。",
                            "内容卖点通常需要用使用前后对比或清单式种草验证。",
                        ],
                        "homogenization_level": HomogenizationLevel.MEDIUM.value,
                        "differentiation_angles": [
                            "用更明确的人群场景和组合方式降低同质化表达。",
                            "优先测试包装、规格、赠品或内容脚本上的轻量差异。",
                        ],
                        "reference_note": (
                            f"{source_hint}；该参考可帮助判断“{opportunity['name']}”"
                            "的常见卖点和价格区间，仍需用公开资料和小批量反馈继续验证。"
                        ),
                    },
                    {
                        "opportunity_uuid": opportunity["uuid"],
                        "rank": 2,
                        "reference_name": f"{opportunity['name']} 差异化内容款参考",
                        "reference_market": "小红书、短视频、电商详情页或公开榜单线索",
                        "price_range": (
                            "可观察同类产品的中低价位和组合装价位，"
                            "成交价、优惠和运费影响仍需待确认。"
                        ),
                        "common_selling_points": [
                            "类似产品可能强调颜值、便携、组合套装或省心解决方案。",
                            "常见内容切入可能围绕新手友好、避坑和预算友好展开。",
                        ],
                        "homogenization_level": HomogenizationLevel.MEDIUM.value,
                        "differentiation_angles": [
                            "从目标人群的具体使用场景切入，而不是只拼低价。",
                            "用标题、主图、套装命名和询单话术做初步差异化。",
                        ],
                        "reference_note": (
                            "该参考偏向内容表达和卖点差异化，可作为公开线索下的待验证方向；"
                            "市场热度和售价仍需继续核对。"
                        ),
                    },
                ]
            )

        return {"references": references}


class LLMCompetitorReferenceGenerator:
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
                        "你是 MarketPilot 的中文小成本商机竞品参考 Agent。"
                        "你只生成类似产品参考、常见售价、常见卖点和差异化切入点，"
                        "不要声称竞品、销量、售价或市场规模已经被全面核验。"
                        "必须输出 JSON，顶层 key 为 references。"
                    ),
                },
                {
                    "role": "user",
                    "content": build_generation_prompt(context),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }

        if is_langsmith_tracing_enabled():
            create_kwargs["langsmith_extra"] = {
                "metadata": {
                    "provider": self.provider,
                    "model": self.model,
                    "task_uuid": context["task"].get("uuid"),
                    "run_id": context["task"].get("run_id"),
                },
                "tags": ["marketpilot", "competitor-references"],
            }

        completion = self.client.chat.completions.create(**create_kwargs)
        content = completion.choices[0].message.content

        if not content:
            raise CompetitorReferenceGenerationError("模型没有返回竞品参考内容。")

        return parse_json_content(content)


def list_task_competitor_references(
    db: Session,
    task: ResearchTask,
) -> list[CompetitorReference]:
    return repository.list_active_references_by_task_id(db, task.id)


def list_opportunity_competitor_references(
    db: Session,
    opportunity: Opportunity,
) -> list[CompetitorReference]:
    return repository.list_active_references_by_opportunity_id(db, opportunity.id)


def replace_task_competitor_references(
    db: Session,
    task: ResearchTask,
    reference_inputs: list[CompetitorReferenceCreate],
) -> list[CompetitorReference]:
    repository.soft_delete_active_references_by_task_id(db, task.id)

    references = [
        CompetitorReference(
            research_task_id=task.id,
            opportunity_id=item.opportunity_id,
            rank=item.rank,
            reference_name=item.reference_name,
            reference_market=item.reference_market,
            price_range=item.price_range,
            common_selling_points=item.common_selling_points,
            homogenization_level=item.homogenization_level.value,
            differentiation_angles=item.differentiation_angles,
            reference_note=item.reference_note,
            source_status=item.source_status.value,
        )
        for item in reference_inputs
    ]

    repository.add_references(db, references)
    db.flush()

    links: list[CompetitorReferenceSource] = []
    for reference, item in zip(references, reference_inputs):
        links.extend(
            CompetitorReferenceSource(
                competitor_reference_id=reference.id,
                research_source_id=source_link.research_source_id,
                relevance_note=source_link.relevance_note,
            )
            for source_link in item.source_links
        )

    repository.add_source_links(db, links)
    db.commit()

    for reference in references:
        db.refresh(reference)

    return references


def collect_competitor_references(
    db: Session,
    task: ResearchTask,
    *,
    generator: Optional[CompetitorReferenceGenerator] = None,
) -> CompetitorReferenceCollectionResult:
    opportunities = opportunities_service.list_task_opportunities(db, task)

    if not opportunities:
        replace_task_competitor_references(db, task, [])
        return CompetitorReferenceCollectionResult(
            status="empty",
            saved_count=0,
            source_link_count=0,
        )

    task_sources = sources_service.list_task_sources(db, task)
    selected_sources_by_opportunity = {
        opportunity.id: select_sources_for_opportunity(opportunity, task_sources)
        for opportunity in opportunities
    }
    demand_summary_by_opportunity_id = {
        insight.opportunity_id: insight.summary
        for insight in demand_insights_service.list_task_demand_insights(db, task)
    }
    supply_summaries_by_opportunity_id = build_supply_summaries_by_opportunity_id(
        db,
        task,
    )
    active_generator = generator or get_competitor_reference_generator()
    generation_result = generate_validated_references(
        active_generator,
        build_generation_context(
            task,
            opportunities,
            selected_sources_by_opportunity,
            demand_summary_by_opportunity_id,
            supply_summaries_by_opportunity_id,
        ),
    )
    generated_by_uuid = group_references_by_opportunity(generation_result.references)
    missing_uuids = [
        str(opportunity.uuid)
        for opportunity in opportunities
        if len(generated_by_uuid[str(opportunity.uuid)])
        < MIN_REFERENCES_PER_OPPORTUNITY
    ]

    if missing_uuids:
        raise CompetitorReferenceGenerationError(
            f"竞品参考缺少商机结果：{', '.join(missing_uuids[:3])}"
        )

    uses_fallback = isinstance(active_generator, DeterministicCompetitorReferenceGenerator)
    reference_inputs: list[CompetitorReferenceCreate] = []
    for opportunity in opportunities:
        selected_sources = selected_sources_by_opportunity[opportunity.id]
        generated_items = sorted(
            generated_by_uuid[str(opportunity.uuid)],
            key=lambda reference: reference.rank,
        )
        reference_inputs.extend(
            build_reference_create(
                opportunity,
                generated,
                selected_sources,
                uses_fallback=uses_fallback,
            )
            for generated in generated_items
        )

    saved = replace_task_competitor_references(db, task, reference_inputs)

    return CompetitorReferenceCollectionResult(
        status="fallback" if uses_fallback else "completed",
        saved_count=len(saved),
        source_link_count=sum(len(item.source_links) for item in reference_inputs),
    )


def get_competitor_reference_generator() -> CompetitorReferenceGenerator:
    settings = get_settings()

    if settings.llm_api_key:
        return LLMCompetitorReferenceGenerator()

    if settings.environment.lower() in {"local", "test"}:
        return DeterministicCompetitorReferenceGenerator()

    raise CompetitorReferenceGenerationError("生产环境未配置 LLM_API_KEY。")


def generate_validated_references(
    generator: CompetitorReferenceGenerator,
    context: dict[str, Any],
) -> CompetitorReferenceGenerationResult:
    last_error: Optional[Exception] = None

    for _ in range(2):
        raw_result = generator.generate(context)

        try:
            return CompetitorReferenceGenerationResult.model_validate(raw_result)
        except ValidationError as exc:
            last_error = exc

    raise CompetitorReferenceGenerationError(f"竞品参考输出未通过结构化校验：{last_error}")


def group_references_by_opportunity(
    references: list[CompetitorReferenceGenerated],
) -> dict[str, list[CompetitorReferenceGenerated]]:
    grouped: dict[str, list[CompetitorReferenceGenerated]] = defaultdict(list)

    for reference in references:
        grouped[str(reference.opportunity_uuid)].append(reference)

    return grouped


def select_sources_for_opportunity(
    opportunity: Opportunity,
    task_sources: list[ResearchSource],
    max_sources: int = MAX_SOURCES_PER_OPPORTUNITY,
) -> list[ResearchSource]:
    source_types = {
        ResearchSourceType.COMPETITOR.value,
        ResearchSourceType.GENERAL.value,
    }
    direct_sources = [
        source
        for source in task_sources
        if source.opportunity_id == opportunity.id and source.source_type in source_types
    ]

    if direct_sources:
        return direct_sources[:max_sources]

    task_sources_without_opportunity = [
        source
        for source in task_sources
        if source.opportunity_id is None and source.source_type in source_types
    ]

    if task_sources_without_opportunity:
        return task_sources_without_opportunity[:max_sources]

    return [
        source
        for source in task_sources
        if source.source_type in source_types
    ][:max_sources]


def build_reference_create(
    opportunity: Opportunity,
    generated: CompetitorReferenceGenerated,
    selected_sources: list[ResearchSource],
    *,
    uses_fallback: bool,
) -> CompetitorReferenceCreate:
    source_status = (
        CompetitorReferenceSourceStatus.LINKED
        if selected_sources
        else (
            CompetitorReferenceSourceStatus.FALLBACK
            if uses_fallback
            else CompetitorReferenceSourceStatus.NO_SOURCES
        )
    )

    return CompetitorReferenceCreate(
        opportunity_id=opportunity.id,
        rank=generated.rank,
        reference_name=generated.reference_name,
        reference_market=generated.reference_market,
        price_range=generated.price_range,
        common_selling_points=generated.common_selling_points,
        homogenization_level=generated.homogenization_level,
        differentiation_angles=generated.differentiation_angles,
        reference_note=generated.reference_note,
        source_status=source_status,
        source_links=[
            CompetitorReferenceSourceLinkCreate(
                research_source_id=source.id,
                relevance_note=build_relevance_note(opportunity, generated, source),
            )
            for source in selected_sources
        ],
    )


def competitor_reference_to_read(
    db: Session,
    reference: CompetitorReference,
    *,
    research_task_uuid: Any,
    opportunity_uuid: Any,
) -> OpportunityCompetitorReferenceRead:
    source_rows = repository.list_active_reference_source_rows(db, reference.id)

    return OpportunityCompetitorReferenceRead(
        uuid=reference.uuid,
        research_task_uuid=research_task_uuid,
        opportunity_uuid=opportunity_uuid,
        rank=reference.rank,
        reference_name=reference.reference_name,
        reference_market=reference.reference_market,
        price_range=reference.price_range,
        common_selling_points=reference.common_selling_points,
        homogenization_level=reference.homogenization_level,
        differentiation_angles=reference.differentiation_angles,
        reference_note=reference.reference_note,
        source_status=reference.source_status,
        sources=[
            CompetitorReferenceSourceSummary(
                uuid=source.uuid,
                source_type=source.source_type,
                title=source.title,
                url=source.url,
                summary=source.summary,
                support_level=source.support_level,
                relevance_note=link.relevance_note,
            )
            for link, source in source_rows
        ],
        created_at=reference.created_at,
        updated_at=reference.updated_at,
        deleted_at=reference.deleted_at,
    )


def build_supply_summaries_by_opportunity_id(
    db: Session,
    task: ResearchTask,
) -> dict[int, list[str]]:
    grouped: dict[int, list[str]] = defaultdict(list)

    for candidate in supply_candidates_service.list_task_supply_candidates(db, task):
        grouped[candidate.opportunity_id].append(
            (
                f"{candidate.candidate_name}：{candidate.supply_market}，"
                f"{candidate.price_range}"
            )
        )

    return grouped


def build_generation_context(
    task: ResearchTask,
    opportunities: list[Opportunity],
    sources_by_opportunity: dict[int, list[ResearchSource]],
    demand_summary_by_opportunity_id: dict[int, str],
    supply_summaries_by_opportunity_id: dict[int, list[str]],
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
                "supply_summaries": supply_summaries_by_opportunity_id.get(
                    opportunity.id,
                    [],
                )[:3],
                "sources": [
                    {
                        "title": source.title,
                        "summary": clip_text(source.summary, MAX_SOURCE_TEXT_LENGTH),
                        "linked_claim": source.linked_claim,
                        "support_level": source.support_level,
                    }
                    for source in sources_by_opportunity[opportunity.id]
                ],
            }
            for opportunity in opportunities
        ],
    }


def build_generation_prompt(context: dict[str, Any]) -> str:
    return (
        "请为每个商机生成至少 2 个竞品或类似产品参考，JSON schema 如下：\n"
        "{\"references\":[{\"opportunity_uuid\":\"...\",\"rank\":1,"
        "\"reference_name\":\"...\",\"reference_market\":\"...\","
        "\"price_range\":\"...\",\"common_selling_points\":[\"...\"],"
        "\"homogenization_level\":\"low|medium|high\","
        "\"differentiation_angles\":[\"...\"],\"reference_note\":\"...\"}]}\n\n"
        f"研究任务：{json.dumps(context['task'], ensure_ascii=False)}\n"
        f"商机、需求摘要、货源候选和竞品来源："
        f"{json.dumps(context['opportunities'], ensure_ascii=False)}\n\n"
        "要求：中文输出；每个商机至少 2 个参考且 rank 从 1 开始；"
        "覆盖类似产品示例、常见售价区间、常见卖点、同质化程度和差异化切入点；"
        "只表达类似产品参考、公开线索、可能、待确认、待验证；"
        "不得使用“竞品已全面核验”“售价已确认”“销量已确认”“市场已证明”等结论。"
    )


def build_relevance_note(
    opportunity: Opportunity,
    reference: CompetitorReferenceGenerated,
    source: ResearchSource,
) -> str:
    note = (
        f"该来源关于“{clip_text(source.linked_claim, 160)}”的线索，"
        f"可作为“{opportunity.name}”下“{reference.reference_name}”"
        "判断常见售价、卖点和差异化空间的初步参考，仍需继续验证。"
    )

    return clip_text(note, 1000)


def parse_json_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    parsed = json.loads(cleaned)

    if not isinstance(parsed, dict):
        raise CompetitorReferenceGenerationError("模型返回的 JSON 不是对象。")

    return parsed


def first_or_default(values: list[str], default: str) -> str:
    return values[0] if values else default


def clip_text(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 3)]}..."
