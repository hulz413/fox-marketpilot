from __future__ import annotations

import json
import logging
from typing import Any, Optional, Protocol, TypedDict

from openai import OpenAI
from pydantic import ValidationError
from sqlalchemy.orm import Session

from langgraph.graph import END, START, StateGraph

from app.core.settings import get_settings
from app.integrations.langsmith import is_langsmith_tracing_enabled, langsmith_trace
from app.integrations.llm import create_llm_client
from app.modules.agent_runs import service as agent_run_events_service
from app.modules.competitor_references import service as competitor_references_service
from app.modules.demand_insights import service as demand_insights_service
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunities.schemas import (
    OpportunityGenerated,
    OpportunityGenerationResult,
)
from app.modules.research_tasks.models import ResearchTask
from app.modules.research_tasks.schemas import ResearchTaskStage, ResearchTaskStatus
from app.modules.sources import service as sources_service
from app.modules.supply_candidates import service as supply_candidates_service

logger = logging.getLogger(__name__)


class OpportunityGenerator(Protocol):
    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate raw opportunity data for the research context."""


class ResearchGraphState(TypedDict, total=False):
    db: Session
    task: ResearchTask
    run_id: str
    trace_id: str
    context: dict[str, Any]
    raw_result: dict[str, Any]
    opportunities: list[OpportunityGenerated]
    generator: OpportunityGenerator
    stage_event: dict[str, Any]


class OpportunityGenerationError(RuntimeError):
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
        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
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
            ],
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
                },
                "tags": ["marketpilot", "opportunity-research"],
            }

        completion = self.client.chat.completions.create(**create_kwargs)
        content = completion.choices[0].message.content

        if not content:
            raise OpportunityGenerationError("模型没有返回内容。")

        return parse_json_content(content)


def first_or_default(values: list[str], default: str) -> str:
    return values[0] if values else default


def parse_json_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    parsed = json.loads(cleaned)

    if not isinstance(parsed, dict):
        raise OpportunityGenerationError("模型返回的 JSON 不是对象。")

    return parsed


def build_generation_prompt(context: dict[str, Any]) -> str:
    return (
        "请生成 3-5 个待验证商机草案，JSON schema 如下：\n"
        "{\"opportunities\":[{\"rank\":1,\"name\":\"...\","
        "\"product_direction\":\"...\",\"target_audience\":\"...\","
        "\"recommendation_reason\":\"...\",\"suitable_channels\":[\"...\"],"
        "\"price_band\":\"...\",\"rough_margin\":\"...\","
        "\"risk_level\":\"low|medium|high\",\"priority_label\":\"...\","
        "\"next_step_summary\":\"...\"}]}\n\n"
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
                result.pop("stage_event", None)
                if isinstance(result, dict)
                else None
            )
            completion_metadata = dict(metadata)
            if isinstance(stage_event, dict):
                completion_metadata.update(stage_event.get("metadata") or {})

            if (
                isinstance(stage_event, dict)
                and stage_event.get("status") == "failed"
            ):
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
        "generate_demand_insights",
        observe_node(
            ResearchTaskStage.GENERATE_DEMAND_INSIGHTS,
            generate_demand_insights,
        ),
    )
    graph.add_node(
        "generate_supply_candidates",
        observe_node(
            ResearchTaskStage.GENERATE_SUPPLY_CANDIDATES,
            generate_supply_candidates,
        ),
    )
    graph.add_node(
        "generate_competitor_references",
        observe_node(
            ResearchTaskStage.GENERATE_COMPETITOR_REFERENCES,
            generate_competitor_references,
        ),
    )
    graph.add_edge(START, "normalize_intake")
    graph.add_edge("normalize_intake", "generate_opportunities")
    graph.add_edge("generate_opportunities", "validate_results")
    graph.add_edge("validate_results", "persist_results")
    graph.add_edge("persist_results", "collect_research_sources")
    graph.add_edge("collect_research_sources", "generate_demand_insights")
    graph.add_edge("generate_demand_insights", "generate_supply_candidates")
    graph.add_edge("generate_supply_candidates", "generate_competitor_references")
    graph.add_edge("generate_competitor_references", END)

    return graph.compile()
