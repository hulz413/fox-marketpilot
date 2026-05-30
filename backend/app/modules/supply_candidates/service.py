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
from app.modules.demand_insights import service as demand_insights_service
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunities.models import Opportunity
from app.modules.research_tasks.models import ResearchTask
from app.modules.sources import service as sources_service
from app.modules.sources.models import ResearchSource
from app.modules.sources.schemas import ResearchSourceType
from app.modules.supply_candidates import repository
from app.modules.supply_candidates.models import (
    SupplyCandidate,
    SupplyCandidateSource,
)
from app.modules.supply_candidates.schemas import (
    OpportunitySupplyCandidateRead,
    SupplyCandidateCreate,
    SupplyCandidateGenerated,
    SupplyCandidateGenerationResult,
    SupplyCandidateSourceLinkCreate,
    SupplyCandidateSourceStatus,
    SupplyCandidateSourceSummary,
)

MAX_SOURCES_PER_OPPORTUNITY = 3
MAX_SOURCE_TEXT_LENGTH = 360
MIN_CANDIDATES_PER_OPPORTUNITY = 2


@dataclass(frozen=True)
class SupplyCandidateCollectionResult:
    status: str
    saved_count: int
    source_link_count: int
    error_summary: Optional[str] = None


class SupplyCandidateGenerationError(RuntimeError):
    pass


class SupplyCandidateGenerator(Protocol):
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate raw supply candidate data for current task opportunities."""


class DeterministicSupplyCandidateGenerator:
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        candidates: list[dict[str, Any]] = []
        preferred_supply = first_or_default(
            context["task"]["supply_preferences"],
            "国内公开供给市场",
        )

        for opportunity in context["opportunities"]:
            source_count = len(opportunity["sources"])
            source_hint = (
                f"结合 {source_count} 条供给公开线索做初步参考"
                if source_count
                else "当前缺少直接供给来源，需要继续搜索和询盘确认"
            )
            base_keywords = [
                opportunity["product_direction"],
                opportunity["name"],
                preferred_supply,
            ]
            candidates.extend(
                [
                    {
                        "opportunity_uuid": opportunity["uuid"],
                        "rank": 1,
                        "candidate_name": f"{opportunity['name']} 基础款候选",
                        "supply_market": f"{preferred_supply} 或同类公开批发市场",
                        "search_keywords": [
                            *base_keywords,
                            "批发",
                            "起订量",
                        ],
                        "price_range": (
                            f"可先按商机价格带 {opportunity['price_band']} "
                            "倒推询价，实际报价待供应商确认。"
                        ),
                        "minimum_order_quantity": (
                            "建议优先询问样品、20-50 件混批或低起订方案，"
                            "具体起订量待确认并由供应商说明。"
                        ),
                        "specification_notes": [
                            "优先确认材质、尺寸、颜色和包装是否支持小批量调整。",
                            "检查图片、详情页和样品是否适合内容平台展示。",
                        ],
                        "supplier_questions": [
                            "是否支持样品或小批量混批，样品费和发货周期如何？",
                            "不同规格的阶梯价、包装方式和售后边界是什么？",
                        ],
                        "recommendation_note": (
                            f"{source_hint}；该候选适合作为“{opportunity['name']}”"
                            "的小批量试单方向，价格、库存和履约能力仍需确认。"
                        ),
                    },
                    {
                        "opportunity_uuid": opportunity["uuid"],
                        "rank": 2,
                        "candidate_name": f"{opportunity['name']} 差异化组合候选",
                        "supply_market": "义乌小商品批发、1688 或国内公开供给市场",
                        "search_keywords": [
                            opportunity["product_direction"],
                            "组合装",
                            "礼盒",
                            "定制包装",
                            "混批",
                        ],
                        "price_range": (
                            "可先寻找低于目标售价 40%-60% 的候选报价，"
                            "最终毛利需结合运费和损耗待确认。"
                        ),
                        "minimum_order_quantity": (
                            "优先筛选支持低起订或可拆分组合的供应商，"
                            "具体起订量和补货周期待确认，避免首轮压库存。"
                        ),
                        "specification_notes": [
                            "关注组合件数量、外观一致性、包装体积和运输破损风险。",
                            "确认是否支持轻量贴标、替换配件或基础套装组合。",
                        ],
                        "supplier_questions": [
                            "组合款是否现货可配，缺货时替代规格如何处理？",
                            "是否能提供实拍素材、质检说明和售后处理规则？",
                        ],
                        "recommendation_note": (
                            "该候选偏向内容表达和差异化包装，可作为初步参考；"
                            "真实报价、库存和履约稳定性仍需逐项待验证。"
                        ),
                    },
                ]
            )

        return {"candidates": candidates}


class LLMSupplyCandidateGenerator:
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
                        "你是 MarketPilot 的中文小成本商机货源候选 Agent。"
                        "你只生成待确认的供给候选和询盘问题，不要声称供应商、价格、"
                        "库存或履约能力已经确认。必须输出 JSON，顶层 key 为 candidates。"
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
                "tags": ["marketpilot", "supply-candidates"],
            }

        completion = self.client.chat.completions.create(**create_kwargs)
        content = completion.choices[0].message.content

        if not content:
            raise SupplyCandidateGenerationError("模型没有返回货源候选内容。")

        return parse_json_content(content)


def list_task_supply_candidates(
    db: Session,
    task: ResearchTask,
) -> list[SupplyCandidate]:
    return repository.list_active_candidates_by_task_id(db, task.id)


def list_opportunity_supply_candidates(
    db: Session,
    opportunity: Opportunity,
) -> list[SupplyCandidate]:
    return repository.list_active_candidates_by_opportunity_id(db, opportunity.id)


def replace_task_supply_candidates(
    db: Session,
    task: ResearchTask,
    candidate_inputs: list[SupplyCandidateCreate],
) -> list[SupplyCandidate]:
    repository.soft_delete_active_candidates_by_task_id(db, task.id)

    candidates = [
        SupplyCandidate(
            research_task_id=task.id,
            opportunity_id=item.opportunity_id,
            rank=item.rank,
            candidate_name=item.candidate_name,
            supply_market=item.supply_market,
            search_keywords=item.search_keywords,
            price_range=item.price_range,
            minimum_order_quantity=item.minimum_order_quantity,
            specification_notes=item.specification_notes,
            supplier_questions=item.supplier_questions,
            recommendation_note=item.recommendation_note,
            source_status=item.source_status.value,
        )
        for item in candidate_inputs
    ]

    repository.add_candidates(db, candidates)
    db.flush()

    links: list[SupplyCandidateSource] = []
    for candidate, item in zip(candidates, candidate_inputs):
        links.extend(
            SupplyCandidateSource(
                supply_candidate_id=candidate.id,
                research_source_id=source_link.research_source_id,
                relevance_note=source_link.relevance_note,
            )
            for source_link in item.source_links
        )

    repository.add_source_links(db, links)
    db.commit()

    for candidate in candidates:
        db.refresh(candidate)

    return candidates


def collect_supply_candidates(
    db: Session,
    task: ResearchTask,
    *,
    generator: Optional[SupplyCandidateGenerator] = None,
) -> SupplyCandidateCollectionResult:
    opportunities = opportunities_service.list_task_opportunities(db, task)

    if not opportunities:
        replace_task_supply_candidates(db, task, [])
        return SupplyCandidateCollectionResult(
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
    active_generator = generator or get_supply_candidate_generator()
    generation_result = generate_validated_candidates(
        active_generator,
        build_generation_context(
            task,
            opportunities,
            selected_sources_by_opportunity,
            demand_summary_by_opportunity_id,
        ),
    )
    generated_by_uuid = group_candidates_by_opportunity(generation_result.candidates)
    missing_uuids = [
        str(opportunity.uuid)
        for opportunity in opportunities
        if len(generated_by_uuid[str(opportunity.uuid)])
        < MIN_CANDIDATES_PER_OPPORTUNITY
    ]

    if missing_uuids:
        raise SupplyCandidateGenerationError(
            f"货源候选缺少商机结果：{', '.join(missing_uuids[:3])}"
        )

    uses_fallback = isinstance(active_generator, DeterministicSupplyCandidateGenerator)
    candidate_inputs: list[SupplyCandidateCreate] = []
    for opportunity in opportunities:
        selected_sources = selected_sources_by_opportunity[opportunity.id]
        generated_items = sorted(
            generated_by_uuid[str(opportunity.uuid)],
            key=lambda candidate: candidate.rank,
        )
        candidate_inputs.extend(
            build_candidate_create(
                opportunity,
                generated,
                selected_sources,
                uses_fallback=uses_fallback,
            )
            for generated in generated_items
        )

    saved = replace_task_supply_candidates(db, task, candidate_inputs)

    return SupplyCandidateCollectionResult(
        status="fallback" if uses_fallback else "completed",
        saved_count=len(saved),
        source_link_count=sum(len(item.source_links) for item in candidate_inputs),
    )


def get_supply_candidate_generator() -> SupplyCandidateGenerator:
    settings = get_settings()

    if settings.llm_api_key:
        return LLMSupplyCandidateGenerator()

    if settings.environment.lower() in {"local", "test"}:
        return DeterministicSupplyCandidateGenerator()

    raise SupplyCandidateGenerationError("生产环境未配置 LLM_API_KEY。")


def generate_validated_candidates(
    generator: SupplyCandidateGenerator,
    context: dict[str, Any],
) -> SupplyCandidateGenerationResult:
    last_error: Optional[Exception] = None

    for _ in range(2):
        raw_result = generator.generate(context)

        try:
            return SupplyCandidateGenerationResult.model_validate(raw_result)
        except ValidationError as exc:
            last_error = exc

    raise SupplyCandidateGenerationError(f"货源候选输出未通过结构化校验：{last_error}")


def group_candidates_by_opportunity(
    candidates: list[SupplyCandidateGenerated],
) -> dict[str, list[SupplyCandidateGenerated]]:
    grouped: dict[str, list[SupplyCandidateGenerated]] = defaultdict(list)

    for candidate in candidates:
        grouped[str(candidate.opportunity_uuid)].append(candidate)

    return grouped


def select_sources_for_opportunity(
    opportunity: Opportunity,
    task_sources: list[ResearchSource],
    max_sources: int = MAX_SOURCES_PER_OPPORTUNITY,
) -> list[ResearchSource]:
    source_types = {
        ResearchSourceType.SUPPLY.value,
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


def build_candidate_create(
    opportunity: Opportunity,
    generated: SupplyCandidateGenerated,
    selected_sources: list[ResearchSource],
    *,
    uses_fallback: bool,
) -> SupplyCandidateCreate:
    source_status = (
        SupplyCandidateSourceStatus.LINKED
        if selected_sources
        else (
            SupplyCandidateSourceStatus.FALLBACK
            if uses_fallback
            else SupplyCandidateSourceStatus.NO_SOURCES
        )
    )

    return SupplyCandidateCreate(
        opportunity_id=opportunity.id,
        rank=generated.rank,
        candidate_name=generated.candidate_name,
        supply_market=generated.supply_market,
        search_keywords=generated.search_keywords,
        price_range=generated.price_range,
        minimum_order_quantity=generated.minimum_order_quantity,
        specification_notes=generated.specification_notes,
        supplier_questions=generated.supplier_questions,
        recommendation_note=generated.recommendation_note,
        source_status=source_status,
        source_links=[
            SupplyCandidateSourceLinkCreate(
                research_source_id=source.id,
                relevance_note=build_relevance_note(opportunity, generated, source),
            )
            for source in selected_sources
        ],
    )


def supply_candidate_to_read(
    db: Session,
    candidate: SupplyCandidate,
    *,
    research_task_uuid: Any,
    opportunity_uuid: Any,
) -> OpportunitySupplyCandidateRead:
    source_rows = repository.list_active_candidate_source_rows(db, candidate.id)

    return OpportunitySupplyCandidateRead(
        uuid=candidate.uuid,
        research_task_uuid=research_task_uuid,
        opportunity_uuid=opportunity_uuid,
        rank=candidate.rank,
        candidate_name=candidate.candidate_name,
        supply_market=candidate.supply_market,
        search_keywords=candidate.search_keywords,
        price_range=candidate.price_range,
        minimum_order_quantity=candidate.minimum_order_quantity,
        specification_notes=candidate.specification_notes,
        supplier_questions=candidate.supplier_questions,
        recommendation_note=candidate.recommendation_note,
        source_status=candidate.source_status,
        sources=[
            SupplyCandidateSourceSummary(
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
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        deleted_at=candidate.deleted_at,
    )


def build_generation_context(
    task: ResearchTask,
    opportunities: list[Opportunity],
    sources_by_opportunity: dict[int, list[ResearchSource]],
    demand_summary_by_opportunity_id: dict[int, str],
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
        "请为每个商机生成至少 2 个货源候选，JSON schema 如下：\n"
        "{\"candidates\":[{\"opportunity_uuid\":\"...\",\"rank\":1,"
        "\"candidate_name\":\"...\",\"supply_market\":\"...\","
        "\"search_keywords\":[\"...\"],\"price_range\":\"...\","
        "\"minimum_order_quantity\":\"...\",\"specification_notes\":[\"...\"],"
        "\"supplier_questions\":[\"...\"],\"recommendation_note\":\"...\"}]}\n\n"
        f"研究任务：{json.dumps(context['task'], ensure_ascii=False)}\n"
        f"商机、需求摘要和供给来源："
        f"{json.dumps(context['opportunities'], ensure_ascii=False)}\n\n"
        "要求：中文输出；每个商机至少 2 个候选且 rank 从 1 开始；"
        "覆盖供给市场、搜索关键词、价格区间、起订量、规格参考和询盘问题；"
        "只表达候选、可能、初步参考、待确认、待验证；"
        "不得使用“已确认供给”“供应商已核验”“价格已确认”“库存已确认”等结论。"
    )


def build_relevance_note(
    opportunity: Opportunity,
    candidate: SupplyCandidateGenerated,
    source: ResearchSource,
) -> str:
    note = (
        f"该来源关于“{clip_text(source.linked_claim, 160)}”的线索，"
        f"可作为“{opportunity.name}”下“{candidate.candidate_name}”"
        "继续找货和询盘的初步参考，价格、库存和履约能力仍需确认。"
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
        raise SupplyCandidateGenerationError("模型返回的 JSON 不是对象。")

    return parsed


def first_or_default(values: list[str], default: str) -> str:
    return values[0] if values else default


def clip_text(value: str, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 3)]}..."
