from __future__ import annotations

import json
import logging
from contextlib import nullcontext
from operator import add
from threading import RLock
from typing import Annotated, Any, Callable, Optional, Protocol, TypedDict

from openai import OpenAI
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from langgraph.graph import END, START, StateGraph

from app.core.settings import get_settings
from app.integrations.langsmith import is_langsmith_tracing_enabled, langsmith_trace
from app.integrations.llm import create_llm_client
from app.modules.agent_runs import service as agent_run_events_service
from app.modules.action_plans import service as action_plans_service
from app.modules.competitor_references import service as competitor_references_service
from app.modules.demand_insights import service as demand_insights_service
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunity_risks import service as opportunity_risks_service
from app.modules.opportunities.schemas import (
    OpportunityGenerated,
    OpportunityGenerationResult,
)
from app.modules.rag_retrieval import service as rag_retrieval_service
from app.modules.research_tasks.models import ResearchTask
from app.modules.research_tasks.schemas import ResearchTaskStage, ResearchTaskStatus
from app.modules.sources import service as sources_service
from app.modules.supply_candidates import service as supply_candidates_service
from app.modules.validation_budgets import service as validation_budgets_service

logger = logging.getLogger(__name__)
ANALYSIS_GROUP = "research_analysis"


class OpportunityGenerator(Protocol):
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate raw opportunity data for the research context."""


class ResearchGraphState(TypedDict, total=False):
    db: Session
    task: ResearchTask
    run_id: str
    trace_id: str
    session_factory: Callable[[], Session]
    analysis_db_lock: RLock
    context: dict[str, Any]
    raw_result: dict[str, Any]
    opportunities: list[OpportunityGenerated]
    generator: OpportunityGenerator
    stage_event: dict[str, Any]
    analysis_branch_results: Annotated[list[dict[str, Any]], add]


class OpportunityGenerationError(RuntimeError):
    pass


class ResearchAnalysisBranchError(RuntimeError):
    pass


class DeterministicDemoGenerator:
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        channel = first_or_default(context["target_channels"], "小红书种草")
        audience = context.get("target_audience") or "小预算验证人群"
        budget = context.get("budget") or "5000 元以内"
        excluded = "、".join(context["excluded_categories"]) or "高履约风险品类"

        return {
            "opportunities": [
                {
                    "rank": 1,
                    "name": "桌面收纳香薰托盘",
                    "product_direction": "租房办公桌面整理与氛围改善",
                    "target_audience": audience,
                    "recommendation_reason": (
                        f"适合用 {channel} 做图文种草，客单价轻、视觉表达直观，"
                        f"可在 {budget} 内做小批量验证。"
                    ),
                    "suitable_channels": [channel, "私域社群"],
                    "price_band": "29-69 元",
                    "rough_margin": "30%-45%",
                    "risk_level": "low",
                    "priority_label": "优先验证",
                    "next_step_summary": "先测试 3 组桌面改造内容，记录收藏率和询单率。",
                },
                {
                    "rank": 2,
                    "name": "便携衣物护理喷雾",
                    "product_direction": "通勤和差旅场景的轻护理用品",
                    "target_audience": audience,
                    "recommendation_reason": (
                        "使用场景明确，内容切入点容易围绕通勤、出差和租房衣柜展开，"
                        f"同时避开 {excluded}。"
                    ),
                    "suitable_channels": [channel, "短视频"],
                    "price_band": "19-49 元",
                    "rough_margin": "28%-40%",
                    "risk_level": "medium",
                    "priority_label": "备选验证",
                    "next_step_summary": "先确认气味、包装和运输限制，再做 50 件以内试单。",
                },
                {
                    "rank": 3,
                    "name": "宠物外出清洁小包",
                    "product_direction": "新手养宠出门后的清洁补给",
                    "target_audience": "新手养宠家庭",
                    "recommendation_reason": (
                        "组合包容易做差异化，也适合社群团购小单验证，但需要关注材质和售后反馈。"
                    ),
                    "suitable_channels": ["社群团购", channel],
                    "price_band": "29-59 元",
                    "rough_margin": "32%-42%",
                    "risk_level": "medium",
                    "priority_label": "观察验证",
                    "next_step_summary": "先找 3 家供应商确认耗材规格，再用小样收集反馈。",
                },
            ]
        }


class LLMOpportunityGenerator:
    def __init__(self, client: Optional[OpenAI] = None) -> None:
        settings = get_settings()
        self.client = client or create_llm_client()
        self.model = settings.llm_model
        self.provider = settings.llm_provider

    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "你是 MarketPilot 的小成本商机顾问 Agent。"
                    "只基于用户输入、表单条件、默认国内中文演示场景和你的已有知识"
                    "生成基础推荐，不要声称已经做过公开调研、来源引用或竞品核验。"
                    "必须输出 JSON，顶层 key 为 opportunities。"
                ),
            },
            {
                "role": "user",
                "content": build_generation_prompt(context),
            },
        ]
        last_error: Optional[Exception] = None

        for attempt in range(2):
            create_kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": 0.4,
            }

            if is_langsmith_tracing_enabled():
                create_kwargs["langsmith_extra"] = {
                    "metadata": {
                        "provider": self.provider,
                        "model": self.model,
                        "task_uuid": context.get("task_uuid"),
                        "run_id": context.get("run_id"),
                        "attempt": attempt + 1,
                    },
                    "tags": ["marketpilot", "opportunity-research"],
                }

            completion = self.client.chat.completions.create(**create_kwargs)
            content = completion.choices[0].message.content

            if not content:
                last_error = OpportunityGenerationError("模型没有返回内容。")
            else:
                try:
                    return parse_json_content(content)
                except OpportunityGenerationError as exc:
                    last_error = exc
                    logger.warning(
                        "Invalid opportunity generation JSON",
                        extra={
                            "task_uuid": context.get("task_uuid"),
                            "run_id": context.get("run_id"),
                            "attempt": attempt + 1,
                            "error_type": type(exc).__name__,
                        },
                    )
                    messages.append({"role": "assistant", "content": content})

            if attempt == 0:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "上一次输出不是合法 JSON。请只返回一个可被 json.loads 解析的 "
                            "JSON 对象，不要 Markdown，不要注释，不要多余文本；"
                            "顶层 key 必须为 opportunities。"
                        ),
                    }
                )

        raise OpportunityGenerationError("模型输出不是合法 JSON。") from last_error


def first_or_default(values: list[str], default: str) -> str:
    return values[0] if values else default


def parse_json_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise OpportunityGenerationError("模型返回的内容不是合法 JSON。") from exc

    if not isinstance(parsed, dict):
        raise OpportunityGenerationError("模型返回的 JSON 不是对象。")

    return parsed


def build_generation_prompt(context: dict[str, Any]) -> str:
    return (
        "请生成 3-5 个待验证商机草案，JSON schema 如下：\n"
        '{"opportunities":[{"rank":1,"name":"...",'
        '"product_direction":"...","target_audience":"...",'
        '"recommendation_reason":"...","suitable_channels":["..."],'
        '"price_band":"...","rough_margin":"...",'
        '"risk_level":"low|medium|high","priority_label":"...",'
        '"next_step_summary":"..."}]}\n\n'
        f"研究标题：{context['title']}\n"
        f"自然语言需求：{context['brief']}\n"
        f"预算：{context.get('budget') or '未填写'}\n"
        f"目标渠道：{', '.join(context['target_channels']) or '未填写'}\n"
        f"偏好品类：{', '.join(context['preferred_categories']) or '未填写'}\n"
        f"排除品类：{', '.join(context['excluded_categories']) or '未填写'}\n"
        f"目标人群：{context.get('target_audience') or '未填写'}\n"
        f"期望利润：{context.get('expected_profit') or '未填写'}\n"
        f"供给来源偏好：{', '.join(context['supply_preferences']) or '国内公开供给市场'}\n"
        f"其他限制：{context.get('constraints') or '小预算、轻库存、先验证'}\n\n"
        "要求：中文输出；适合国内中文内容平台演示；不要食品、电子产品等被排除品类；"
        "结果是基础推荐，不要包含来源链接或声称已调研。"
    )


def get_opportunity_generator() -> OpportunityGenerator:
    settings = get_settings()

    if settings.llm_api_key:
        return LLMOpportunityGenerator()

    if settings.environment.lower() in {"local", "test"}:
        return DeterministicDemoGenerator()

    raise OpportunityGenerationError("生产环境未配置 LLM_API_KEY。")


def normalize_intake(state: ResearchGraphState) -> dict[str, Any]:
    task = state["task"]
    context = {
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
        "language": "zh-CN",
        "research_boundary": "基础推荐，无外部前置调研",
        "task_uuid": str(task.uuid),
        "run_id": state.get("run_id"),
    }
    logger.info(
        "Normalized research intake",
        extra={"task_uuid": str(task.uuid), "run_id": state.get("run_id")},
    )

    return {"context": context}


def generate_opportunities(state: ResearchGraphState) -> dict[str, Any]:
    generator = state.get("generator") or get_opportunity_generator()
    last_error: Optional[Exception] = None

    for attempt in range(2):
        raw_result = generator.generate(state["context"])

        try:
            result = OpportunityGenerationResult.model_validate(raw_result)
            logger.info(
                "Generated opportunity candidates",
                extra={
                    "task_uuid": str(state["task"].uuid),
                    "run_id": state.get("run_id"),
                    "attempt": attempt + 1,
                },
            )
            return {
                "raw_result": raw_result,
                "opportunities": result.opportunities,
            }
        except ValidationError as exc:
            last_error = exc
            logger.warning(
                "Invalid opportunity generation output",
                extra={
                    "task_uuid": str(state["task"].uuid),
                    "run_id": state.get("run_id"),
                    "attempt": attempt + 1,
                },
            )

    raise OpportunityGenerationError(f"模型输出未通过结构化校验：{last_error}")


def validate_results(state: ResearchGraphState) -> dict[str, Any]:
    OpportunityGenerationResult(opportunities=state["opportunities"])
    return {}


def persist_results(state: ResearchGraphState) -> dict[str, Any]:
    db = state["db"]
    task = state["task"]

    opportunities_service.replace_task_opportunities(
        db,
        task,
        state["opportunities"],
    )
    task.status = ResearchTaskStatus.COMPLETED.value
    task.current_stage = ResearchTaskStage.COMPLETED.value
    task.failure_reason = None
    db.add(task)
    db.commit()
    db.refresh(task)

    logger.info(
        "Persisted opportunity research results",
        extra={"task_uuid": str(task.uuid), "run_id": state.get("run_id")},
    )

    return {"task": task}


def collect_research_sources(state: ResearchGraphState) -> dict[str, Any]:
    db = state["db"]
    task = state["task"]
    run_id = state.get("run_id")

    try:
        result = sources_service.collect_research_sources(db, task)
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        task.failure_reason = None
        db.add(task)
        db.commit()
        db.refresh(task)

        metadata = {
            "source_collection_status": result.status,
            "saved_source_count": result.saved_count,
            "query_count": result.query_count,
        }
        logger.info(
            "Collected research sources",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                **metadata,
            },
        )

        if result.status == "failed":
            return {
                "task": task,
                "stage_event": {
                    "status": "failed",
                    "error_summary": result.error_summary
                    or "来源收集失败，基础商机结果已保留。",
                    "metadata": metadata,
                },
            }

        if result.error_summary:
            metadata["error_summary"] = result.error_summary

        return {
            "task": task,
            "stage_event": {
                "status": "completed",
                "metadata": metadata,
            },
        }
    except Exception as exc:  # pragma: no cover - defensive non-blocking fallback
        db.rollback()
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.warning(
            "Research source collection failed after opportunities were persisted",
            exc_info=True,
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                "error_type": type(exc).__name__,
            },
        )
        return {
            "task": task,
            "stage_event": {
                "status": "failed",
                "error_summary": "来源收集失败，基础商机结果已保留。",
                "metadata": {
                    "source_collection_status": "failed",
                    "error_type": type(exc).__name__,
                },
            },
        }


def index_rag_evidence(state: ResearchGraphState) -> dict[str, Any]:
    db = state["db"]
    task = state["task"]
    run_id = state.get("run_id")

    try:
        result = rag_retrieval_service.index_task_evidence(db, task)
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        task.failure_reason = None
        db.add(task)
        db.commit()
        db.refresh(task)

        metadata = {
            "rag_index_status": result.status,
            "indexed_chunk_count": result.indexed_count,
            "source_count": result.source_count,
        }
        if result.skipped_reason:
            metadata["skipped_reason"] = result.skipped_reason
        if result.error_summary:
            metadata["error_summary"] = result.error_summary

        logger.info(
            "Indexed RAG evidence",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                **metadata,
            },
        )

        if result.status == "failed":
            return {
                "task": task,
                "stage_event": {
                    "status": "failed",
                    "error_summary": result.error_summary
                    or "RAG 证据索引失败，基础商机结果已保留。",
                    "metadata": metadata,
                },
            }

        return {
            "task": task,
            "stage_event": {
                "status": "completed",
                "metadata": metadata,
            },
        }
    except Exception as exc:  # pragma: no cover - defensive non-blocking fallback
        db.rollback()
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.warning(
            "RAG evidence indexing failed after sources were collected",
            exc_info=True,
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                "error_type": type(exc).__name__,
            },
        )
        return {
            "task": task,
            "stage_event": {
                "status": "failed",
                "error_summary": "RAG 证据索引失败，基础商机结果已保留。",
                "metadata": {
                    "rag_index_status": "failed",
                    "error_type": type(exc).__name__,
                },
            },
        }


def begin_research_analysis(state: ResearchGraphState) -> dict[str, Any]:
    return {
        "analysis_branch_results": [],
        "stage_event": {
            "status": "completed",
            "metadata": {
                "analysis_group": ANALYSIS_GROUP,
                "branch_stages": [
                    ResearchTaskStage.GENERATE_DEMAND_INSIGHTS.value,
                    ResearchTaskStage.GENERATE_SUPPLY_CANDIDATES.value,
                    ResearchTaskStage.GENERATE_COMPETITOR_REFERENCES.value,
                ],
            },
        },
    }


def generate_demand_insights(state: ResearchGraphState) -> dict[str, Any]:
    db = state["db"]
    task = state["task"]
    run_id = state.get("run_id")

    try:
        result = demand_insights_service.collect_demand_insights(db, task)
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        task.failure_reason = None
        db.add(task)
        db.commit()
        db.refresh(task)

        metadata = {
            "demand_insight_status": result.status,
            "saved_demand_insight_count": result.saved_count,
            "source_link_count": result.source_link_count,
        }
        logger.info(
            "Generated demand insights",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                **metadata,
            },
        )

        return {
            "task": task,
            "stage_event": {
                "status": "completed",
                "metadata": metadata,
            },
        }
    except Exception as exc:  # pragma: no cover - defensive non-blocking fallback
        db.rollback()
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.warning(
            "Demand insight generation failed after opportunities were persisted",
            exc_info=True,
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                "error_type": type(exc).__name__,
            },
        )
        return {
            "task": task,
            "stage_event": {
                "status": "failed",
                "error_summary": "需求洞察生成失败，基础商机结果已保留。",
                "metadata": {
                    "demand_insight_status": "failed",
                    "error_type": type(exc).__name__,
                },
            },
        }


def generate_supply_candidates(state: ResearchGraphState) -> dict[str, Any]:
    db = state["db"]
    task = state["task"]
    run_id = state.get("run_id")

    try:
        result = supply_candidates_service.collect_supply_candidates(db, task)
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        task.failure_reason = None
        db.add(task)
        db.commit()
        db.refresh(task)

        metadata = {
            "supply_candidate_status": result.status,
            "saved_supply_candidate_count": result.saved_count,
            "source_link_count": result.source_link_count,
        }
        logger.info(
            "Generated supply candidates",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                **metadata,
            },
        )

        return {
            "task": task,
            "stage_event": {
                "status": "completed",
                "metadata": metadata,
            },
        }
    except Exception as exc:  # pragma: no cover - defensive non-blocking fallback
        db.rollback()
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.warning(
            "Supply candidate generation failed after opportunities were persisted",
            exc_info=True,
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                "error_type": type(exc).__name__,
            },
        )
        return {
            "task": task,
            "stage_event": {
                "status": "failed",
                "error_summary": "货源候选生成失败，基础商机结果已保留。",
                "metadata": {
                    "supply_candidate_status": "failed",
                    "error_type": type(exc).__name__,
                },
            },
        }


def generate_competitor_references(state: ResearchGraphState) -> dict[str, Any]:
    db = state["db"]
    task = state["task"]
    run_id = state.get("run_id")

    try:
        result = competitor_references_service.collect_competitor_references(db, task)
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        task.failure_reason = None
        db.add(task)
        db.commit()
        db.refresh(task)

        metadata = {
            "competitor_reference_status": result.status,
            "saved_competitor_reference_count": result.saved_count,
            "source_link_count": result.source_link_count,
            "retrieval_query_count": result.retrieval_query_count,
            "retrieval_result_count": result.retrieval_result_count,
            "retrieval_fallback_count": result.retrieval_fallback_count,
            "retrieval_top_k": result.retrieval_top_k,
            "retrieval_source_types": list(result.retrieval_source_types),
            "retrieval_scope": result.retrieval_scope,
            "retrieval_queries": list(result.retrieval_queries),
        }
        logger.info(
            "Generated competitor references",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                **metadata,
            },
        )

        return {
            "task": task,
            "stage_event": {
                "status": "completed",
                "metadata": metadata,
            },
        }
    except Exception as exc:  # pragma: no cover - defensive non-blocking fallback
        db.rollback()
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.warning(
            "Competitor reference generation failed after opportunities were persisted",
            exc_info=True,
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                "error_type": type(exc).__name__,
            },
        )
        return {
            "task": task,
            "stage_event": {
                "status": "failed",
                "error_summary": "竞品参考生成失败，基础商机结果已保留。",
                "metadata": {
                    "competitor_reference_status": "failed",
                    "error_type": type(exc).__name__,
                },
            },
        }


def collect_demand_insights_branch(
    db: Session,
    task: ResearchTask,
    state: ResearchGraphState,
) -> dict[str, Any]:
    run_id = state.get("run_id")

    try:
        result = demand_insights_service.collect_demand_insights(db, task)
        metadata = {
            "demand_insight_status": result.status,
            "saved_demand_insight_count": result.saved_count,
            "source_link_count": result.source_link_count,
        }
        logger.info(
            "Generated demand insights in analysis branch",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                **metadata,
            },
        )
        return {
            "status": "completed",
            "metadata": metadata,
        }
    except Exception as exc:  # pragma: no cover - defensive non-blocking fallback
        db.rollback()
        logger.warning(
            "Demand insight analysis branch failed",
            exc_info=True,
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                "error_type": type(exc).__name__,
            },
        )
        return {
            "status": "failed",
            "error_summary": "需求洞察生成失败，基础商机结果已保留。",
            "metadata": {
                "demand_insight_status": "failed",
                "error_type": type(exc).__name__,
            },
        }


def collect_supply_candidates_branch(
    db: Session,
    task: ResearchTask,
    state: ResearchGraphState,
) -> dict[str, Any]:
    run_id = state.get("run_id")

    try:
        result = supply_candidates_service.collect_supply_candidates(db, task)
        metadata = {
            "supply_candidate_status": result.status,
            "saved_supply_candidate_count": result.saved_count,
            "source_link_count": result.source_link_count,
        }
        logger.info(
            "Generated supply candidates in analysis branch",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                **metadata,
            },
        )
        return {
            "status": "completed",
            "metadata": metadata,
        }
    except Exception as exc:  # pragma: no cover - defensive non-blocking fallback
        db.rollback()
        logger.warning(
            "Supply candidate analysis branch failed",
            exc_info=True,
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                "error_type": type(exc).__name__,
            },
        )
        return {
            "status": "failed",
            "error_summary": "货源候选生成失败，基础商机结果已保留。",
            "metadata": {
                "supply_candidate_status": "failed",
                "error_type": type(exc).__name__,
            },
        }


def collect_competitor_references_branch(
    db: Session,
    task: ResearchTask,
    state: ResearchGraphState,
) -> dict[str, Any]:
    run_id = state.get("run_id")

    try:
        result = competitor_references_service.collect_competitor_references(db, task)
        metadata = {
            "competitor_reference_status": result.status,
            "saved_competitor_reference_count": result.saved_count,
            "source_link_count": result.source_link_count,
            "retrieval_query_count": result.retrieval_query_count,
            "retrieval_result_count": result.retrieval_result_count,
            "retrieval_fallback_count": result.retrieval_fallback_count,
            "retrieval_top_k": result.retrieval_top_k,
            "retrieval_source_types": list(result.retrieval_source_types),
            "retrieval_scope": result.retrieval_scope,
            "retrieval_queries": list(result.retrieval_queries),
        }
        logger.info(
            "Generated competitor references in analysis branch",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                **metadata,
            },
        )
        return {
            "status": "completed",
            "metadata": metadata,
        }
    except Exception as exc:  # pragma: no cover - defensive non-blocking fallback
        db.rollback()
        logger.warning(
            "Competitor reference analysis branch failed",
            exc_info=True,
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                "error_type": type(exc).__name__,
            },
        )
        return {
            "status": "failed",
            "error_summary": "竞品参考生成失败，基础商机结果已保留。",
            "metadata": {
                "competitor_reference_status": "failed",
                "error_type": type(exc).__name__,
            },
        }


def synthesize_research_findings(state: ResearchGraphState) -> dict[str, Any]:
    branch_results = state.get("analysis_branch_results", [])
    branch_statuses = {
        str(result.get("stage")): result.get("status", "unknown")
        for result in branch_results
    }
    failed_branches = [
        result for result in branch_results if result.get("status") == "failed"
    ]

    return {
        "stage_event": {
            "status": "completed",
            "metadata": {
                "analysis_group": ANALYSIS_GROUP,
                "analysis_branch_status": (
                    "partial" if failed_branches else "completed"
                ),
                "branch_statuses": branch_statuses,
                "branch_results": branch_results,
            },
        },
    }


def estimate_validation_budgets(state: ResearchGraphState) -> dict[str, Any]:
    db = state["db"]
    task = state["task"]
    run_id = state.get("run_id")

    try:
        result = validation_budgets_service.collect_validation_budgets(db, task)
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        task.failure_reason = None
        db.add(task)
        db.commit()
        db.refresh(task)

        metadata = {
            "validation_budget_status": result.status,
            "saved_validation_budget_count": result.saved_count,
        }
        logger.info(
            "Estimated validation budgets",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                **metadata,
            },
        )

        return {
            "task": task,
            "stage_event": {
                "status": "completed",
                "metadata": metadata,
            },
        }
    except Exception as exc:  # pragma: no cover - defensive non-blocking fallback
        db.rollback()
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.warning(
            "Validation budget estimation failed after opportunities were persisted",
            exc_info=True,
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                "error_type": type(exc).__name__,
            },
        )
        return {
            "task": task,
            "stage_event": {
                "status": "failed",
                "error_summary": "验证预算估算失败，基础商机结果已保留。",
                "metadata": {
                    "validation_budget_status": "failed",
                    "error_type": type(exc).__name__,
                },
            },
        }


def review_opportunity_risks(state: ResearchGraphState) -> dict[str, Any]:
    db = state["db"]
    task = state["task"]
    run_id = state.get("run_id")

    try:
        result = opportunity_risks_service.collect_opportunity_risks(db, task)
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        task.failure_reason = None
        db.add(task)
        db.commit()
        db.refresh(task)

        metadata = {
            "opportunity_risk_status": result.status,
            "saved_opportunity_risk_count": result.saved_count,
        }
        logger.info(
            "Reviewed opportunity risks",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                **metadata,
            },
        )

        return {
            "task": task,
            "stage_event": {
                "status": "completed",
                "metadata": metadata,
            },
        }
    except Exception as exc:  # pragma: no cover - defensive non-blocking fallback
        db.rollback()
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.warning(
            "Opportunity risk review failed after opportunities were persisted",
            exc_info=True,
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                "error_type": type(exc).__name__,
            },
        )
        return {
            "task": task,
            "stage_event": {
                "status": "failed",
                "error_summary": "风险复核失败，基础商机结果已保留。",
                "metadata": {
                    "opportunity_risk_status": "failed",
                    "error_type": type(exc).__name__,
                },
            },
        }


def create_action_plans(state: ResearchGraphState) -> dict[str, Any]:
    db = state["db"]
    task = state["task"]
    run_id = state.get("run_id")

    try:
        result = action_plans_service.collect_action_plans(db, task)
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        task.failure_reason = None
        db.add(task)
        db.commit()
        db.refresh(task)

        metadata = {
            "action_plan_status": result.status,
            "saved_action_plan_count": result.saved_count,
        }
        logger.info(
            "Created action plans",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                **metadata,
            },
        )

        return {
            "task": task,
            "stage_event": {
                "status": "completed",
                "metadata": metadata,
            },
        }
    except Exception as exc:  # pragma: no cover - defensive non-blocking fallback
        db.rollback()
        task.status = ResearchTaskStatus.COMPLETED.value
        task.current_stage = ResearchTaskStage.COMPLETED.value
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.warning(
            "Action plan generation failed after opportunities were persisted",
            exc_info=True,
            extra={
                "task_uuid": str(task.uuid),
                "run_id": run_id,
                "error_type": type(exc).__name__,
            },
        )
        return {
            "task": task,
            "stage_event": {
                "status": "failed",
                "error_summary": "行动计划生成失败，基础商机结果已保留。",
                "metadata": {
                    "action_plan_status": "failed",
                    "error_type": type(exc).__name__,
                },
            },
        }


def update_task_stage(
    db: Session,
    task: ResearchTask,
    stage: ResearchTaskStage,
) -> ResearchTask:
    task.current_stage = stage.value
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def stage_metadata(state: ResearchGraphState, stage: str) -> dict[str, Any]:
    task = state["task"]
    return {
        "task_uuid": str(task.uuid),
        "run_id": state.get("run_id"),
        "stage": stage,
        "trace_id": state.get("trace_id"),
    }


def observe_node(stage: ResearchTaskStage, node):
    def observed(state: ResearchGraphState) -> dict[str, Any]:
        db = state["db"]
        task = state["task"]
        run_id = state["run_id"]
        trace_id = state.get("trace_id")
        metadata = stage_metadata(state, stage.value)

        try:
            task = update_task_stage(db, task, stage)
            state["task"] = task
            agent_run_events_service.start_stage(
                db,
                task,
                run_id=run_id,
                stage=stage.value,
                trace_id=trace_id,
                metadata=metadata,
            )

            with langsmith_trace(
                stage.value,
                inputs={"task_uuid": str(task.uuid), "run_id": run_id},
                metadata=metadata,
            ):
                result = node(state)

            stage_event = (
                result.pop("stage_event", None) if isinstance(result, dict) else None
            )
            completion_metadata = dict(metadata)
            if isinstance(stage_event, dict):
                completion_metadata.update(stage_event.get("metadata") or {})

            if isinstance(stage_event, dict) and stage_event.get("status") == "failed":
                agent_run_events_service.fail_stage(
                    db,
                    task,
                    run_id=run_id,
                    stage=stage.value,
                    trace_id=trace_id,
                    error_summary=str(
                        stage_event.get("error_summary")
                        or "阶段执行失败，请查看任务失败原因。"
                    ),
                    metadata=completion_metadata,
                )
            else:
                agent_run_events_service.complete_stage(
                    db,
                    task,
                    run_id=run_id,
                    stage=stage.value,
                    trace_id=trace_id,
                    metadata=completion_metadata,
                )
            return result
        except Exception as exc:
            db.rollback()
            agent_run_events_service.fail_stage(
                db,
                task,
                run_id=run_id,
                stage=stage.value,
                trace_id=trace_id,
                error_summary=f"{stage.value} failed: {type(exc).__name__}",
                metadata=metadata,
            )
            raise

    return observed


def get_branch_session_factory(state: ResearchGraphState) -> Callable[[], Session]:
    if state.get("session_factory"):
        return state["session_factory"]

    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=state["db"].get_bind(),
    )


def load_branch_task(db: Session, state: ResearchGraphState) -> ResearchTask:
    task_id = state["task"].id
    task = db.get(ResearchTask, task_id)

    if task is None or task.deleted_at is not None:
        raise ResearchAnalysisBranchError("研究任务不存在或已删除。")

    run_id = state.get("run_id")
    if task.run_id and task.run_id != run_id:
        raise ResearchAnalysisBranchError("研究任务运行 ID 不匹配。")

    return task


def analysis_branch_metadata(
    task: ResearchTask,
    state: ResearchGraphState,
    stage: str,
) -> dict[str, Any]:
    return {
        "task_uuid": str(task.uuid),
        "run_id": state.get("run_id"),
        "stage": stage,
        "trace_id": state.get("trace_id"),
        "analysis_group": ANALYSIS_GROUP,
        "branch_stage": stage,
    }


def build_analysis_branch_result(
    stage: str,
    status: str,
    metadata: dict[str, Any],
    error_summary: Optional[str] = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "stage": stage,
        "status": status,
        "metadata": metadata,
    }

    if error_summary:
        result["error_summary"] = error_summary

    return result


def observe_analysis_branch(stage: ResearchTaskStage, node):
    def observed(state: ResearchGraphState) -> dict[str, Any]:
        session_factory = get_branch_session_factory(state)
        lock_context = state.get("analysis_db_lock") or nullcontext()
        run_id = state["run_id"]
        trace_id = state.get("trace_id")

        with lock_context, session_factory() as branch_db:
            task = load_branch_task(branch_db, state)
            metadata = analysis_branch_metadata(task, state, stage.value)

            try:
                agent_run_events_service.start_stage(
                    branch_db,
                    task,
                    run_id=run_id,
                    stage=stage.value,
                    trace_id=trace_id,
                    metadata=metadata,
                )

                with langsmith_trace(
                    stage.value,
                    inputs={"task_uuid": str(task.uuid), "run_id": run_id},
                    metadata=metadata,
                ):
                    stage_event = node(branch_db, task, state)

                status = str(stage_event.get("status") or "completed")
                completion_metadata = dict(metadata)
                completion_metadata.update(stage_event.get("metadata") or {})
                error_summary = stage_event.get("error_summary")

                if status == "failed":
                    agent_run_events_service.fail_stage(
                        branch_db,
                        task,
                        run_id=run_id,
                        stage=stage.value,
                        trace_id=trace_id,
                        error_summary=str(
                            error_summary or "阶段执行失败，请查看任务失败原因。"
                        ),
                        metadata=completion_metadata,
                    )
                else:
                    agent_run_events_service.complete_stage(
                        branch_db,
                        task,
                        run_id=run_id,
                        stage=stage.value,
                        trace_id=trace_id,
                        metadata=completion_metadata,
                    )

                return {
                    "analysis_branch_results": [
                        build_analysis_branch_result(
                            stage.value,
                            status,
                            completion_metadata,
                            str(error_summary) if error_summary else None,
                        )
                    ]
                }
            except Exception as exc:
                branch_db.rollback()
                failure_metadata = dict(metadata)
                failure_metadata["error_type"] = type(exc).__name__
                error_summary = f"{stage.value} failed: {type(exc).__name__}"
                agent_run_events_service.fail_stage(
                    branch_db,
                    task,
                    run_id=run_id,
                    stage=stage.value,
                    trace_id=trace_id,
                    error_summary=error_summary,
                    metadata=failure_metadata,
                )
                return {
                    "analysis_branch_results": [
                        build_analysis_branch_result(
                            stage.value,
                            "failed",
                            failure_metadata,
                            error_summary,
                        )
                    ]
                }

    return observed


def build_research_graph():
    graph = StateGraph(ResearchGraphState)
    graph.add_node(
        "normalize_intake",
        observe_node(ResearchTaskStage.NORMALIZE_INTAKE, normalize_intake),
    )
    graph.add_node(
        "generate_opportunities",
        observe_node(ResearchTaskStage.GENERATE_OPPORTUNITIES, generate_opportunities),
    )
    graph.add_node(
        "validate_results",
        observe_node(ResearchTaskStage.VALIDATE_RESULTS, validate_results),
    )
    graph.add_node(
        "persist_results",
        observe_node(ResearchTaskStage.PERSIST_RESULTS, persist_results),
    )
    graph.add_node(
        "collect_research_sources",
        observe_node(
            ResearchTaskStage.COLLECT_RESEARCH_SOURCES,
            collect_research_sources,
        ),
    )
    graph.add_node(
        "index_rag_evidence",
        observe_node(
            ResearchTaskStage.INDEX_RAG_EVIDENCE,
            index_rag_evidence,
        ),
    )
    graph.add_node(
        "analyze_research",
        observe_node(
            ResearchTaskStage.ANALYZE_RESEARCH,
            begin_research_analysis,
        ),
    )
    graph.add_node(
        "generate_demand_insights",
        observe_analysis_branch(
            ResearchTaskStage.GENERATE_DEMAND_INSIGHTS,
            collect_demand_insights_branch,
        ),
    )
    graph.add_node(
        "generate_supply_candidates",
        observe_analysis_branch(
            ResearchTaskStage.GENERATE_SUPPLY_CANDIDATES,
            collect_supply_candidates_branch,
        ),
    )
    graph.add_node(
        "generate_competitor_references",
        observe_analysis_branch(
            ResearchTaskStage.GENERATE_COMPETITOR_REFERENCES,
            collect_competitor_references_branch,
        ),
    )
    graph.add_node(
        "synthesize_research_findings",
        observe_node(
            ResearchTaskStage.SYNTHESIZE_RESEARCH_FINDINGS,
            synthesize_research_findings,
        ),
    )
    graph.add_node(
        "estimate_validation_budgets",
        observe_node(
            ResearchTaskStage.ESTIMATE_VALIDATION_BUDGETS,
            estimate_validation_budgets,
        ),
    )
    graph.add_node(
        "review_opportunity_risks",
        observe_node(
            ResearchTaskStage.REVIEW_OPPORTUNITY_RISKS,
            review_opportunity_risks,
        ),
    )
    graph.add_node(
        "create_action_plans",
        observe_node(
            ResearchTaskStage.CREATE_ACTION_PLANS,
            create_action_plans,
        ),
    )
    graph.add_edge(START, "normalize_intake")
    graph.add_edge("normalize_intake", "generate_opportunities")
    graph.add_edge("generate_opportunities", "validate_results")
    graph.add_edge("validate_results", "persist_results")
    graph.add_edge("persist_results", "collect_research_sources")
    graph.add_edge("collect_research_sources", "index_rag_evidence")
    graph.add_edge("index_rag_evidence", "analyze_research")
    graph.add_edge("analyze_research", "generate_demand_insights")
    graph.add_edge("analyze_research", "generate_supply_candidates")
    graph.add_edge("analyze_research", "generate_competitor_references")
    graph.add_edge("generate_demand_insights", "synthesize_research_findings")
    graph.add_edge("generate_supply_candidates", "synthesize_research_findings")
    graph.add_edge("generate_competitor_references", "synthesize_research_findings")
    graph.add_edge("synthesize_research_findings", "estimate_validation_budgets")
    graph.add_edge("estimate_validation_budgets", "review_opportunity_risks")
    graph.add_edge("review_opportunity_risks", "create_action_plans")
    graph.add_edge("create_action_plans", END)

    return graph.compile()
