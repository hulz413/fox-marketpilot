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
from app.modules.demand_insights import repository
from app.modules.demand_insights.models import (
    OpportunityDemandInsight,
    OpportunityDemandInsightSource,
)
from app.modules.demand_insights.schemas import (
    DemandInsightCreate,
    DemandInsightGenerated,
    DemandInsightGenerationResult,
    DemandInsightSourceLinkCreate,
    DemandInsightSourceStatus,
    DemandInsightSourceSummary,
    OpportunityDemandInsightRead,
)
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunities.models import Opportunity
from app.modules.research_tasks.models import ResearchTask
from app.modules.sources import service as sources_service
from app.modules.sources.models import ResearchSource
from app.modules.sources.schemas import ResearchSourceType

MAX_SOURCES_PER_OPPORTUNITY = 3
MAX_SOURCE_TEXT_LENGTH = 360


@dataclass(frozen=True)
class DemandInsightCollectionResult:
    status: str
    saved_count: int
    source_link_count: int
    error_summary: Optional[str] = None


class DemandInsightGenerationError(RuntimeError):
    pass


class DemandInsightGenerator(Protocol):
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate raw demand insight data for current task opportunities."""


class DeterministicDemandInsightGenerator:
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        insights: list[dict[str, Any]] = []
        channel = first_or_default(context["task"]["target_channels"], "中文内容平台")

        for opportunity in context["opportunities"]:
            source_count = len(opportunity["sources"])
            source_hint = (
                f"结合 {source_count} 条公开线索可作为初步参考"
                if source_count
                else "当前缺少直接来源，需要继续用公开资料和小批量试单验证"
            )
            insights.append(
                {
                    "opportunity_uuid": opportunity["uuid"],
                    "summary": (
                        f"{opportunity['name']} 可能匹配"
                        f"{opportunity['target_audience']} 的具体使用场景，"
                        f"{source_hint}。"
                    ),
                    "audience_profile": (
                        f"优先观察 {opportunity['target_audience']} 中对"
                        f"{opportunity['product_direction']} 有即时改善诉求的人群。"
                    ),
                    "use_cases": [
                        f"在 {channel} 内容中展示真实使用前后的变化。",
                        "围绕低成本试用、轻量收纳或日常便利场景做待验证表达。",
                    ],
                    "purchase_motivations": [
                        "可能希望用低客单价解决一个具体小麻烦。",
                        "可能被场景化内容触发尝试，而不是长期计划性购买。",
                    ],
                    "content_angles": [
                        f"用 {opportunity['product_direction']} 的前后对比做种草。",
                        "用预算友好、小批量验证和避坑清单降低尝试门槛。",
                    ],
                    "trend_signals": [
                        "公开线索或任务输入提示该方向可能存在内容讨论空间。",
                        "仍需继续观察收藏、评论、询单和复购信号。",
                    ],
                    "seasonality_notes": (
                        "暂未确认强季节性，可先按日常高频场景验证；"
                        "如遇开学、搬家、节日前后，可单独观察需求波动。"
                    ),
                }
            )

        return {"insights": insights}


class LLMDemandInsightGenerator:
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
                        "你是 MarketPilot 的中文小成本商机需求分析 Agent。"
                        "你只生成待验证的需求洞察，不要声称需求已证明、市场已确认或趋势已验证。"
                        "必须输出 JSON，顶层 key 为 insights。"
                    ),
                },
                {
                    "role": "user",
                    "content": build_generation_prompt(context),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.35,
        }

        if is_langsmith_tracing_enabled():
            create_kwargs["langsmith_extra"] = {
                "metadata": {
                    "provider": self.provider,
                    "model": self.model,
                    "task_uuid": context["task"].get("uuid"),
                    "run_id": context["task"].get("run_id"),
                },
                "tags": ["marketpilot", "demand-insights"],
            }

        completion = self.client.chat.completions.create(**create_kwargs)
        content = completion.choices[0].message.content

        if not content:
            raise DemandInsightGenerationError("模型没有返回需求洞察内容。")

        return parse_json_content(content)


def list_task_demand_insights(
    db: Session,
    task: ResearchTask,
) -> list[OpportunityDemandInsight]:
    return repository.list_active_insights_by_task_id(db, task.id)


def get_opportunity_demand_insight(
    db: Session,
    opportunity: Opportunity,
) -> Optional[OpportunityDemandInsight]:
    return repository.get_active_insight_by_opportunity_id(db, opportunity.id)


def replace_task_demand_insights(
    db: Session,
    task: ResearchTask,
    insight_inputs: list[DemandInsightCreate],
) -> list[OpportunityDemandInsight]:
    repository.soft_delete_active_insights_by_task_id(db, task.id)

    insights = [
        OpportunityDemandInsight(
            research_task_id=task.id,
            opportunity_id=item.opportunity_id,
            summary=item.summary,
            audience_profile=item.audience_profile,
            use_cases=item.use_cases,
            purchase_motivations=item.purchase_motivations,
            content_angles=item.content_angles,
            trend_signals=item.trend_signals,
            seasonality_notes=item.seasonality_notes,
            source_status=item.source_status.value,
        )
        for item in insight_inputs
    ]

    repository.add_insights(db, insights)
    db.flush()

    links: list[OpportunityDemandInsightSource] = []
    for insight, item in zip(insights, insight_inputs):
        links.extend(
            OpportunityDemandInsightSource(
                demand_insight_id=insight.id,
                research_source_id=source_link.research_source_id,
                relevance_note=source_link.relevance_note,
            )
            for source_link in item.source_links
        )

    repository.add_source_links(db, links)
    db.commit()

    for insight in insights:
        db.refresh(insight)

    return insights


def collect_demand_insights(
    db: Session,
    task: ResearchTask,
    *,
    generator: Optional[DemandInsightGenerator] = None,
) -> DemandInsightCollectionResult:
    opportunities = opportunities_service.list_task_opportunities(db, task)

    if not opportunities:
        replace_task_demand_insights(db, task, [])
        return DemandInsightCollectionResult(
            status="empty",
            saved_count=0,
            source_link_count=0,
        )

    task_sources = sources_service.list_task_sources(db, task)
    selected_sources_by_opportunity = {
        opportunity.id: select_sources_for_opportunity(opportunity, task_sources)
        for opportunity in opportunities
    }
    active_generator = generator or get_demand_insight_generator()
    generation_result = generate_validated_insights(
        active_generator,
        build_generation_context(
            task,
            opportunities,
            selected_sources_by_opportunity,
        ),
    )
    generated_by_uuid = {
        str(insight.opportunity_uuid): insight
        for insight in generation_result.insights
    }
    missing_uuids = [
        str(opportunity.uuid)
        for opportunity in opportunities
        if str(opportunity.uuid) not in generated_by_uuid
    ]

    if missing_uuids:
        raise DemandInsightGenerationError(
            f"需求洞察缺少商机结果：{', '.join(missing_uuids[:3])}"
        )

    uses_fallback = isinstance(active_generator, DeterministicDemandInsightGenerator)
    insight_inputs = [
        build_insight_create(
            opportunity,
            generated_by_uuid[str(opportunity.uuid)],
            selected_sources_by_opportunity[opportunity.id],
            uses_fallback=uses_fallback,
        )
        for opportunity in opportunities
    ]
    saved = replace_task_demand_insights(db, task, insight_inputs)

    return DemandInsightCollectionResult(
        status="fallback" if uses_fallback else "completed",
        saved_count=len(saved),
        source_link_count=sum(len(item.source_links) for item in insight_inputs),
    )


def get_demand_insight_generator() -> DemandInsightGenerator:
    settings = get_settings()

    if settings.llm_api_key:
        return LLMDemandInsightGenerator()

    if settings.environment.lower() in {"local", "test"}:
        return DeterministicDemandInsightGenerator()

    raise DemandInsightGenerationError("生产环境未配置 LLM_API_KEY。")


def generate_validated_insights(
    generator: DemandInsightGenerator,
    context: dict[str, Any],
) -> DemandInsightGenerationResult:
    last_error: Optional[Exception] = None

    for _ in range(2):
        raw_result = generator.generate(context)

        try:
            return DemandInsightGenerationResult.model_validate(raw_result)
        except ValidationError as exc:
            last_error = exc

    raise DemandInsightGenerationError(f"需求洞察输出未通过结构化校验：{last_error}")


def select_sources_for_opportunity(
    opportunity: Opportunity,
    task_sources: list[ResearchSource],
    max_sources: int = MAX_SOURCES_PER_OPPORTUNITY,
) -> list[ResearchSource]:
    source_types = {
        ResearchSourceType.DEMAND.value,
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


def build_insight_create(
    opportunity: Opportunity,
    generated: DemandInsightGenerated,
    selected_sources: list[ResearchSource],
    *,
    uses_fallback: bool,
) -> DemandInsightCreate:
    source_status = (
        DemandInsightSourceStatus.LINKED
        if selected_sources
        else (
            DemandInsightSourceStatus.FALLBACK
            if uses_fallback
            else DemandInsightSourceStatus.NO_SOURCES
        )
    )

    return DemandInsightCreate(
        opportunity_id=opportunity.id,
        summary=generated.summary,
        audience_profile=generated.audience_profile,
        use_cases=generated.use_cases,
        purchase_motivations=generated.purchase_motivations,
        content_angles=generated.content_angles,
        trend_signals=generated.trend_signals,
        seasonality_notes=generated.seasonality_notes,
        source_status=source_status,
        source_links=[
            DemandInsightSourceLinkCreate(
                research_source_id=source.id,
                relevance_note=build_relevance_note(opportunity, source),
            )
            for source in selected_sources
        ],
    )


def demand_insight_to_read(
    db: Session,
    insight: OpportunityDemandInsight,
    *,
    research_task_uuid: Any,
    opportunity_uuid: Any,
) -> OpportunityDemandInsightRead:
    source_rows = repository.list_active_insight_source_rows(db, insight.id)

    return OpportunityDemandInsightRead(
        uuid=insight.uuid,
        research_task_uuid=research_task_uuid,
        opportunity_uuid=opportunity_uuid,
        summary=insight.summary,
        audience_profile=insight.audience_profile,
        use_cases=insight.use_cases,
        purchase_motivations=insight.purchase_motivations,
        content_angles=insight.content_angles,
        trend_signals=insight.trend_signals,
        seasonality_notes=insight.seasonality_notes,
        source_status=insight.source_status,
        sources=[
            DemandInsightSourceSummary(
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
        created_at=insight.created_at,
        updated_at=insight.updated_at,
        deleted_at=insight.deleted_at,
    )


def build_generation_context(
    task: ResearchTask,
    opportunities: list[Opportunity],
    sources_by_opportunity: dict[int, list[ResearchSource]],
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
        "请为每个商机生成需求洞察，JSON schema 如下：\n"
        "{\"insights\":[{\"opportunity_uuid\":\"...\","
        "\"summary\":\"...\",\"audience_profile\":\"...\","
        "\"use_cases\":[\"...\"],\"purchase_motivations\":[\"...\"],"
        "\"content_angles\":[\"...\"],\"trend_signals\":[\"...\"],"
        "\"seasonality_notes\":\"...\"}]}\n\n"
        f"研究任务：{json.dumps(context['task'], ensure_ascii=False)}\n"
        f"商机和来源：{json.dumps(context['opportunities'], ensure_ascii=False)}\n\n"
        "要求：中文输出；覆盖人群、场景、购买动机、内容种草角度、趋势信号和季节性；"
        "只表达可能性和待验证判断；不得使用“已证明”“确定有市场”“需求已验证”等结论。"
    )


def build_relevance_note(opportunity: Opportunity, source: ResearchSource) -> str:
    note = (
        f"该来源关于“{clip_text(source.linked_claim, 180)}”的线索，"
        f"可作为“{opportunity.name}”需求判断的初步参考，仍需继续验证。"
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
        raise DemandInsightGenerationError("模型返回的 JSON 不是对象。")

    return parsed


def first_or_default(values: list[str], default: str) -> str:
    return values[0] if values else default


def clip_text(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 3)]}..."
