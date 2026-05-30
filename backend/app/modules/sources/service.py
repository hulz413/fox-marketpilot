from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.integrations.tavily import create_tavily_client
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunities.models import Opportunity
from app.modules.research_tasks.models import ResearchTask
from app.modules.sources import repository
from app.modules.sources.models import ResearchSource
from app.modules.sources.schemas import (
    ResearchSourceCreate,
    ResearchSourceRead,
    ResearchSourceType,
    SourceSupportLevel,
)

MAX_QUERIES_PER_TASK = 12
MAX_RESULTS_PER_QUERY = 3
MAX_EXTRACT_URLS_PER_QUERY = 2
MAX_SOURCES_PER_TASK = 15


@dataclass(frozen=True)
class SourceQuery:
    query: str
    source_type: ResearchSourceType
    linked_claim: str
    opportunity_id: Optional[int] = None
    opportunity_name: Optional[str] = None


@dataclass(frozen=True)
class SourceSearchResult:
    title: str
    url: str
    content: str
    score: Optional[float] = None
    raw_metadata: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class SourceCollectionResult:
    status: str
    saved_count: int
    query_count: int
    error_summary: Optional[str] = None


class SourceSearchClient(Protocol):
    def search(self, query: str, max_results: int) -> list[SourceSearchResult]:
        """Return public search results for a query."""

    def extract(self, urls: list[str]) -> dict[str, str]:
        """Return extracted raw content by URL."""


class TavilySourceSearchClient:
    def __init__(self, client: Optional[Any] = None) -> None:
        self.client = client or create_tavily_client()

    def search(self, query: str, max_results: int) -> list[SourceSearchResult]:
        response = self.client.search(query=query, max_results=max_results)
        results = response.get("results", []) if isinstance(response, dict) else []

        return [
            SourceSearchResult(
                title=str(item.get("title") or "").strip(),
                url=str(item.get("url") or "").strip(),
                content=str(item.get("content") or "").strip(),
                score=item.get("score"),
                raw_metadata={
                    "provider": "tavily",
                    "score": item.get("score"),
                    "query": query,
                },
            )
            for item in results
            if item.get("url") and item.get("title")
        ]

    def extract(self, urls: list[str]) -> dict[str, str]:
        if not urls:
            return {}

        response = self.client.extract(urls=urls, include_images=False)
        results = response.get("results", []) if isinstance(response, dict) else []

        return {
            str(item.get("url")): str(item.get("raw_content") or "").strip()
            for item in results
            if item.get("url") and item.get("raw_content")
        }


def list_task_sources(db: Session, task: ResearchTask) -> list[ResearchSource]:
    return repository.list_active_sources_by_task_id(db, task.id)


def list_opportunity_sources(
    db: Session,
    opportunity: Opportunity,
) -> list[ResearchSource]:
    return repository.list_active_sources_by_opportunity_id(db, opportunity.id)


def replace_task_sources(
    db: Session,
    task: ResearchTask,
    source_inputs: list[ResearchSourceCreate],
) -> list[ResearchSource]:
    repository.soft_delete_active_sources_by_task_id(db, task.id)
    sources = [
        ResearchSource(
            research_task_id=task.id,
            opportunity_id=item.opportunity_id,
            source_type=item.source_type.value,
            title=item.title,
            url=item.url,
            summary=item.summary,
            snippet=item.snippet,
            publisher=item.publisher,
            score=item.score,
            query=item.query,
            linked_claim=item.linked_claim,
            support_level=item.support_level.value,
            raw_metadata=item.raw_metadata,
            collected_at=item.collected_at or repository.utc_now(),
        )
        for item in source_inputs
    ]
    repository.add_sources(db, sources)
    db.commit()

    for source in sources:
        db.refresh(source)

    return sources


def source_to_read(
    source: ResearchSource,
    *,
    research_task_uuid: Any,
    opportunity_uuid: Optional[Any],
) -> ResearchSourceRead:
    return ResearchSourceRead(
        uuid=source.uuid,
        research_task_uuid=research_task_uuid,
        opportunity_uuid=opportunity_uuid,
        source_type=source.source_type,
        title=source.title,
        url=source.url,
        summary=source.summary,
        snippet=source.snippet,
        publisher=source.publisher,
        score=source.score,
        query=source.query,
        linked_claim=source.linked_claim,
        support_level=source.support_level,
        collected_at=source.collected_at,
        created_at=source.created_at,
        updated_at=source.updated_at,
        deleted_at=source.deleted_at,
    )


def build_source_queries(
    task: ResearchTask,
    opportunities: list[Opportunity],
    max_queries: int = MAX_QUERIES_PER_TASK,
) -> list[SourceQuery]:
    channel = first_or_default(task.target_channels, "中文内容平台")
    supply = first_or_default(task.supply_preferences, "1688 批发")
    queries: list[SourceQuery] = []

    for opportunity in opportunities:
        query_specs = [
            (
                ResearchSourceType.DEMAND,
                f"{opportunity.product_direction} {opportunity.target_audience} {channel} 需求 场景",
                f"{opportunity.name} 在 {opportunity.target_audience} 场景下可能存在需求信号",
            ),
            (
                ResearchSourceType.SUPPLY,
                f"{opportunity.product_direction} {supply} 批发 起订量 价格",
                f"{opportunity.name} 的产品方向可能存在公开供给线索",
            ),
            (
                ResearchSourceType.COMPETITOR,
                f"{opportunity.product_direction} 同类产品 售价 卖点",
                f"{opportunity.name} 的同类产品和售价信息可作为竞品初步参考",
            ),
            (
                ResearchSourceType.RISK,
                f"{opportunity.product_direction} 质量 售后 投诉 避坑",
                f"{opportunity.name} 可能存在质量、售后或同质化风险线索",
            ),
        ]

        for source_type, query, linked_claim in query_specs:
            queries.append(
                SourceQuery(
                    query=normalize_space(query),
                    source_type=source_type,
                    linked_claim=linked_claim,
                    opportunity_id=opportunity.id,
                    opportunity_name=opportunity.name,
                )
            )

            if len(queries) >= max_queries:
                return queries

    return queries


def collect_research_sources(
    db: Session,
    task: ResearchTask,
    *,
    search_client: Optional[SourceSearchClient] = None,
) -> SourceCollectionResult:
    opportunities = opportunities_service.list_task_opportunities(db, task)

    if not opportunities:
        replace_task_sources(db, task, [])
        return SourceCollectionResult(status="skipped", saved_count=0, query_count=0)

    client = search_client or get_source_search_client()

    if client is None:
        settings = get_settings()
        if settings.environment.lower() in {"local", "test"}:
            generated = build_deterministic_sources(task, opportunities)
            saved = replace_task_sources(db, task, generated)
            return SourceCollectionResult(
                status="fallback",
                saved_count=len(saved),
                query_count=0,
            )

        replace_task_sources(db, task, [])
        return SourceCollectionResult(
            status="skipped",
            saved_count=0,
            query_count=0,
            error_summary="来源收集已跳过，公开搜索服务暂不可用。",
        )

    queries = build_source_queries(task, opportunities)
    generated: list[ResearchSourceCreate] = []
    errors: list[str] = []
    seen_urls: set[str] = set()

    for source_query in queries:
        if len(generated) >= MAX_SOURCES_PER_TASK:
            break

        try:
            results = client.search(source_query.query, MAX_RESULTS_PER_QUERY)
        except Exception as exc:  # pragma: no cover - exact SDK errors vary
            errors.append(type(exc).__name__)
            continue

        extract_content_by_url = extract_top_results(client, results)

        for result in results:
            if len(generated) >= MAX_SOURCES_PER_TASK:
                break

            normalized_url = normalize_url(result.url)
            if not normalized_url or normalized_url in seen_urls:
                continue

            seen_urls.add(normalized_url)
            generated.append(
                build_source_create(
                    source_query,
                    result,
                    extracted_content=extract_content_by_url.get(result.url)
                    or extract_content_by_url.get(normalized_url),
                    normalized_url=normalized_url,
                )
            )

    saved = replace_task_sources(db, task, generated)

    if saved:
        return SourceCollectionResult(
            status="partial" if errors else "completed",
            saved_count=len(saved),
            query_count=len(queries),
            error_summary=make_safe_error_summary(errors) if errors else None,
        )

    return SourceCollectionResult(
        status="failed" if errors else "empty",
        saved_count=0,
        query_count=len(queries),
        error_summary=make_safe_error_summary(errors)
        or "来源收集未获得可保存的公开来源线索。",
    )


def get_source_search_client() -> Optional[SourceSearchClient]:
    settings = get_settings()

    if not settings.tavily_api_key:
        return None

    return TavilySourceSearchClient()


def extract_top_results(
    client: SourceSearchClient,
    results: list[SourceSearchResult],
) -> dict[str, str]:
    urls = [result.url for result in results[:MAX_EXTRACT_URLS_PER_QUERY] if result.url]

    try:
        return client.extract(urls)
    except Exception:  # pragma: no cover - extract is best-effort
        return {}


def build_source_create(
    source_query: SourceQuery,
    result: SourceSearchResult,
    *,
    extracted_content: Optional[str],
    normalized_url: str,
) -> ResearchSourceCreate:
    evidence_text = clip_text(extracted_content or result.content or result.title, 220)
    snippet = clip_text(result.content or extracted_content or result.title, 1200)
    summary = (
        f"该公开来源提到“{evidence_text}”，可作为“{source_query.linked_claim}”"
        "的初步参考，仍需通过小批量验证继续确认。"
    )

    return ResearchSourceCreate(
        opportunity_id=source_query.opportunity_id,
        source_type=source_query.source_type,
        title=clip_text(result.title, 300) or "公开来源线索",
        url=normalized_url,
        summary=clip_text(summary, 1200),
        snippet=snippet,
        publisher=parse_publisher(normalized_url),
        score=result.score,
        query=source_query.query,
        linked_claim=source_query.linked_claim,
        support_level=support_level_from_score(result.score),
        raw_metadata={
            **(result.raw_metadata or {}),
            "extract_used": bool(extracted_content),
            "opportunity_name": source_query.opportunity_name,
        },
    )


def build_deterministic_sources(
    task: ResearchTask,
    opportunities: list[Opportunity],
) -> list[ResearchSourceCreate]:
    sources: list[ResearchSourceCreate] = []
    channel = first_or_default(task.target_channels, "中文内容平台")
    supply = first_or_default(task.supply_preferences, "1688 批发")

    for opportunity in opportunities[:3]:
        sources.extend(
            [
                ResearchSourceCreate(
                    opportunity_id=opportunity.id,
                    source_type=ResearchSourceType.DEMAND,
                    title=f"{opportunity.name} 需求线索示例",
                    url=f"https://example.com/marketpilot/{opportunity.uuid}/demand",
                    summary=(
                        f"该示例来源提示 {opportunity.product_direction} 与 {channel} "
                        "内容场景可能相关，可作为需求判断的初步参考，仍需验证。"
                    ),
                    snippet=f"{opportunity.target_audience} 对 {opportunity.product_direction} 可能存在使用场景。",
                    publisher="MarketPilot fallback",
                    score=0.62,
                    query=f"{opportunity.product_direction} {channel} 需求 场景",
                    linked_claim=(
                        f"{opportunity.name} 在 {opportunity.target_audience} "
                        "场景下可能存在需求信号"
                    ),
                    support_level=SourceSupportLevel.MEDIUM,
                    raw_metadata={"provider": "deterministic_fallback"},
                ),
                ResearchSourceCreate(
                    opportunity_id=opportunity.id,
                    source_type=ResearchSourceType.SUPPLY,
                    title=f"{opportunity.name} 供给线索示例",
                    url=f"https://example.com/marketpilot/{opportunity.uuid}/supply",
                    summary=(
                        f"该示例来源提示 {supply} 可作为供给方向的初步参考，"
                        "仍需向供应商确认价格、起订量和履约能力。"
                    ),
                    snippet=f"{opportunity.product_direction} 可以先从公开供给市场寻找候选商品。",
                    publisher="MarketPilot fallback",
                    score=0.58,
                    query=f"{opportunity.product_direction} {supply} 批发 起订量",
                    linked_claim=f"{opportunity.name} 的产品方向可能存在公开供给线索",
                    support_level=SourceSupportLevel.MEDIUM,
                    raw_metadata={"provider": "deterministic_fallback"},
                ),
            ]
        )

        if len(sources) >= MAX_SOURCES_PER_TASK:
            break

    return sources[:MAX_SOURCES_PER_TASK]


def support_level_from_score(score: Optional[float]) -> SourceSupportLevel:
    if score is None:
        return SourceSupportLevel.MEDIUM
    if score >= 0.75:
        return SourceSupportLevel.STRONG
    if score >= 0.45:
        return SourceSupportLevel.MEDIUM
    return SourceSupportLevel.WEAK


def make_safe_error_summary(errors: list[str]) -> Optional[str]:
    if not errors:
        return None

    unique_errors = ", ".join(sorted(set(errors))[:3])
    return f"来源收集部分失败，基础商机结果已保留。错误类型：{unique_errors}。"


def first_or_default(values: list[str], default: str) -> str:
    return values[0] if values else default


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def normalize_url(url: str) -> str:
    return url.strip()


def parse_publisher(url: str) -> Optional[str]:
    host = urlparse(url).netloc.strip()
    return host or None


def clip_text(value: str, limit: int) -> str:
    normalized = normalize_space(value)
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 3)]}..."
