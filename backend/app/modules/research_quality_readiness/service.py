from __future__ import annotations

import json
import logging
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from app.integrations.langsmith import langsmith_trace
from app.modules.action_plans import service as action_plans_service
from app.modules.agent_runs import service as agent_run_events_service
from app.modules.competitor_references import service as competitor_references_service
from app.modules.demand_insights import service as demand_insights_service
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunities.models import Opportunity
from app.modules.opportunity_risks import service as opportunity_risks_service
from app.modules.generation_quality_evaluation import (
    service as generation_quality_evaluation_service,
)
from app.modules.rag_quality_evaluation import service as rag_quality_evaluation_service
from app.modules.rag_retrieval import repository as rag_retrieval_repository
from app.modules.rag_retrieval.models import RagEvidenceChunk
from app.modules.report_sharing import service as report_sharing_service
from app.modules.report_sharing.schemas import ReportShareStatus
from app.modules.research_quality_readiness import repository
from app.modules.research_quality_readiness.models import (
    ResearchQualityReadinessRun,
    utc_now,
)
from app.modules.research_quality_readiness.schemas import (
    ReadinessCheckStatus,
    ReadinessOverallStatus,
    ReadinessRunStatus,
    ResearchQualityReadinessRunRead,
)
from app.modules.research_tasks.models import ResearchTask
from app.modules.research_tasks.schemas import ResearchTaskStage, ResearchTaskStatus
from app.modules.sources import service as sources_service
from app.modules.supply_candidates import service as supply_candidates_service
from app.modules.validation_budgets import service as validation_budgets_service

logger = logging.getLogger(__name__)

CRITICAL_STAGE_VALUES = [
    ResearchTaskStage.GENERATE_OPPORTUNITIES.value,
    ResearchTaskStage.VALIDATE_RESULTS.value,
    ResearchTaskStage.PERSIST_RESULTS.value,
]

READINESS_STAGE_VALUES = [
    *CRITICAL_STAGE_VALUES,
    ResearchTaskStage.COLLECT_RESEARCH_SOURCES.value,
    ResearchTaskStage.INDEX_RAG_EVIDENCE.value,
    ResearchTaskStage.GENERATE_DEMAND_INSIGHTS.value,
    ResearchTaskStage.GENERATE_SUPPLY_CANDIDATES.value,
    ResearchTaskStage.GENERATE_COMPETITOR_REFERENCES.value,
    ResearchTaskStage.ESTIMATE_VALIDATION_BUDGETS.value,
    ResearchTaskStage.REVIEW_OPPORTUNITY_RISKS.value,
    ResearchTaskStage.CREATE_ACTION_PLANS.value,
]

STAGE_LABELS = {
    ResearchTaskStage.GENERATE_OPPORTUNITIES.value: "生成基础推荐",
    ResearchTaskStage.VALIDATE_RESULTS.value: "校验推荐结果",
    ResearchTaskStage.PERSIST_RESULTS.value: "保存研究结果",
    ResearchTaskStage.COLLECT_RESEARCH_SOURCES.value: "收集公开来源线索",
    ResearchTaskStage.INDEX_RAG_EVIDENCE.value: "整理公开来源证据",
    ResearchTaskStage.GENERATE_DEMAND_INSIGHTS.value: "生成需求洞察",
    ResearchTaskStage.GENERATE_SUPPLY_CANDIDATES.value: "生成货源候选",
    ResearchTaskStage.GENERATE_COMPETITOR_REFERENCES.value: "生成竞品参考",
    ResearchTaskStage.ESTIMATE_VALIDATION_BUDGETS.value: "估算验证预算",
    ResearchTaskStage.REVIEW_OPPORTUNITY_RISKS.value: "复核商机风险",
    ResearchTaskStage.CREATE_ACTION_PLANS.value: "生成行动计划",
}

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
    "已确认库存",
    "保证利润",
    "自动联系供应商",
    "自动发布内容",
    "自动上架",
    "完成真实验证",
    "已经完成真实验证",
]


class ReadinessUnavailableError(RuntimeError):
    pass


def get_latest_readiness_run(
    db: Session,
    task: ResearchTask,
) -> Optional[ResearchQualityReadinessRun]:
    return repository.get_latest_active_readiness_run_by_task_id(db, task.id)


def create_readiness_run(
    db: Session,
    task: ResearchTask,
    *,
    run_rag_evaluation: bool = True,
) -> ResearchQualityReadinessRun:
    if task.status != ResearchTaskStatus.COMPLETED.value:
        raise ReadinessUnavailableError(
            f"研究任务尚未完成，当前状态：{task.status}。"
        )

    readiness_run = repository.create_readiness_run(
        db,
        ResearchQualityReadinessRun(
            research_task_id=task.id,
            research_run_id=task.run_id,
            status=ReadinessRunStatus.RUNNING.value,
            overall_status=ReadinessOverallStatus.WARNING.value,
            summary="正在运行研究质量就绪检查。",
            checks=[],
            metrics={},
            started_at=utc_now(),
        ),
    )

    try:
        with langsmith_trace(
            "research_quality_readiness",
            inputs={"task_uuid": str(task.uuid), "run_id": task.run_id},
            metadata={
                "readiness_run_uuid": str(readiness_run.uuid),
                "task_uuid": str(task.uuid),
                "research_run_id": task.run_id,
            },
        ) as trace_context:
            if trace_context is not None:
                readiness_run.trace_id = trace_context.trace_id
                readiness_run.trace_url = trace_context.trace_url
                repository.save_readiness_run(db, readiness_run)

            (
                checks,
                rag_evaluation_run_uuid,
                generation_evaluation_run_uuid,
            ) = build_readiness_checks(
                db,
                task,
                run_rag_evaluation=run_rag_evaluation,
            )
            overall_status = aggregate_overall_status(checks)
            readiness_run.checks = checks
            readiness_run.metrics = aggregate_metrics(checks)
            readiness_run.rag_evaluation_run_uuid = rag_evaluation_run_uuid
            readiness_run.generation_evaluation_run_uuid = generation_evaluation_run_uuid
            readiness_run.overall_status = overall_status
            readiness_run.status = ReadinessRunStatus.COMPLETED.value
            readiness_run.summary = build_summary(overall_status, checks)
            readiness_run.error_summary = None
            readiness_run.completed_at = utc_now()

        saved = repository.save_readiness_run(db, readiness_run)
        logger.info(
            "Research quality readiness check completed",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": task.run_id,
                "readiness_run_uuid": str(saved.uuid),
                "overall_status": saved.overall_status,
                "check_count": len(saved.checks),
            },
        )
        return saved
    except Exception as exc:
        db.rollback()
        readiness_run.status = ReadinessRunStatus.FAILED.value
        readiness_run.overall_status = ReadinessOverallStatus.FAILED.value
        readiness_run.summary = "研究质量就绪检查失败，请查看应用日志。"
        readiness_run.error_summary = safe_error_summary(str(exc))
        readiness_run.completed_at = utc_now()
        saved = repository.save_readiness_run(db, readiness_run)
        logger.exception(
            "Research quality readiness check failed",
            extra={
                "task_uuid": str(task.uuid),
                "run_id": task.run_id,
                "readiness_run_uuid": str(saved.uuid),
                "error_type": type(exc).__name__,
            },
        )
        return saved


def build_readiness_checks(
    db: Session,
    task: ResearchTask,
    *,
    run_rag_evaluation: bool,
) -> tuple[list[dict[str, Any]], Optional[Any], Optional[Any]]:
    opportunities = opportunities_service.list_task_opportunities(db, task)
    events = (
        agent_run_events_service.list_run_events(db, task, task.run_id)
        if task.run_id
        else []
    )
    sources = sources_service.list_task_sources(db, task)
    chunks = rag_retrieval_repository.list_active_chunks_by_task_id(db, task.id)

    stage_check = check_stage_completeness(task, opportunities, events)
    rag_index_check = check_rag_index_health(sources, chunks, events)
    rag_evaluation_check, rag_evaluation_run_uuid = check_rag_retrieval_evaluation(
        db,
        task,
        chunks,
        run_rag_evaluation=run_rag_evaluation,
    )
    generation_evaluation_run = (
        generation_quality_evaluation_service.get_latest_generation_evaluation_run(
            db,
            task,
        )
    )
    content_check = check_generation_content_smoke(
        db,
        task,
        opportunities,
        generation_evaluation_run=generation_evaluation_run,
    )
    share_check = check_report_share_snapshot(db, task)

    return (
        [
            stage_check,
            rag_index_check,
            rag_evaluation_check,
            content_check,
            share_check,
        ],
        rag_evaluation_run_uuid,
        generation_evaluation_run.uuid if generation_evaluation_run else None,
    )


def check_stage_completeness(
    task: ResearchTask,
    opportunities: list[Opportunity],
    events: list[Any],
) -> dict[str, Any]:
    events_by_stage = {event.stage: event for event in events}
    missing_stages = [
        STAGE_LABELS[stage]
        for stage in READINESS_STAGE_VALUES
        if stage not in events_by_stage
    ]
    failed_stages = [
        STAGE_LABELS.get(event.stage, event.stage)
        for event in events
        if event.stage in READINESS_STAGE_VALUES
        and event.status == agent_run_events_service.STATUS_FAILED
    ]
    completed_stage_count = sum(
        1
        for stage in READINESS_STAGE_VALUES
        if events_by_stage.get(stage)
        and events_by_stage[stage].status == agent_run_events_service.STATUS_COMPLETED
    )
    reasons = []

    if len(opportunities) < 3:
        reasons.append("基础商机结果少于 3 个。")

    if missing_stages:
        reasons.append(f"缺少阶段事件：{'、'.join(missing_stages)}。")

    if failed_stages:
        reasons.append(f"存在失败阶段：{'、'.join(failed_stages)}。")

    if len(opportunities) < 3:
        status = ReadinessCheckStatus.FAILED.value
        severity = "critical"
        summary = "基础商机结果缺失或数量不足。"
    elif failed_stages or missing_stages:
        status = ReadinessCheckStatus.WARNING.value
        severity = "warning"
        summary = "研究阶段存在缺失或降级，需要演示前复查。"
    else:
        status = ReadinessCheckStatus.PASS.value
        severity = "info"
        summary = "关键研究阶段已经完成。"

    return make_check(
        "stage_completeness",
        "主流程完整性",
        status,
        severity,
        summary,
        metrics={
            "research_run_id": task.run_id,
            "opportunity_count": len(opportunities),
            "stage_total": len(READINESS_STAGE_VALUES),
            "completed_stage_count": completed_stage_count,
            "missing_stage_count": len(missing_stages),
            "failed_stage_count": len(failed_stages),
        },
        reasons=reasons,
        actions=["重新运行研究任务或查看阶段事件。"] if reasons else [],
    )


def check_rag_index_health(
    sources: list[Any],
    chunks: list[RagEvidenceChunk],
    events: list[Any],
) -> dict[str, Any]:
    index_event = next(
        (
            event
            for event in events
            if event.stage == ResearchTaskStage.INDEX_RAG_EVIDENCE.value
        ),
        None,
    )
    embedding_models = sorted(
        {chunk.embedding_model for chunk in chunks if chunk.embedding_model}
    )
    embedding_dimensions = sorted(
        {chunk.embedding_dimension for chunk in chunks if chunk.embedding_dimension}
    )
    embedded_count = sum(1 for chunk in chunks if chunk.embedding)
    metadata = dict(getattr(index_event, "event_metadata", {}) or {})
    reasons = []

    if not sources:
        reasons.append("当前任务没有可用公开来源。")

    if sources and not chunks:
        reasons.append("当前任务没有 active RAG evidence chunks。")

    if index_event and index_event.status == agent_run_events_service.STATUS_FAILED:
        reasons.append(index_event.error_summary or "RAG 证据索引阶段失败。")

    skipped_reason = metadata.get("skipped_reason")
    if skipped_reason:
        reasons.append(f"RAG 索引跳过原因：{skipped_reason}。")

    if not sources or (sources and not chunks) or (
        index_event and index_event.status == agent_run_events_service.STATUS_FAILED
    ):
        status = ReadinessCheckStatus.WARNING.value
        severity = "warning"
        summary = "RAG 索引证据链需要复查。"
    else:
        status = ReadinessCheckStatus.PASS.value
        severity = "info"
        summary = "RAG 来源和 evidence chunks 可用于内部检查。"

    return make_check(
        "rag_index_health",
        "RAG 索引健康",
        status,
        severity,
        summary,
        metrics={
            "source_count": len(sources),
            "active_chunk_count": len(chunks),
            "embedded_chunk_count": embedded_count,
            "embedding_models": embedding_models,
            "embedding_dimensions": embedding_dimensions,
            "index_event_status": getattr(index_event, "status", None),
            "rag_index_status": metadata.get("rag_index_status"),
            "skipped_reason": skipped_reason,
        },
        reasons=reasons,
        actions=["重新运行研究任务或检查 embedding 配置。"] if reasons else [],
    )


def check_rag_retrieval_evaluation(
    db: Session,
    task: ResearchTask,
    chunks: list[RagEvidenceChunk],
    *,
    run_rag_evaluation: bool,
) -> tuple[dict[str, Any], Optional[Any]]:
    if not chunks:
        return (
            make_check(
                "rag_retrieval_evaluation",
                "RAG 检索评测",
                ReadinessCheckStatus.SKIPPED.value,
                "warning",
                "缺少 RAG chunks，未运行检索评测。",
                metrics={"active_chunk_count": 0},
                reasons=["当前任务没有可检索证据。"],
                actions=["先修复来源收集或 RAG 索引。"],
            ),
            None,
        )

    if not run_rag_evaluation:
        return (
            make_check(
                "rag_retrieval_evaluation",
                "RAG 检索评测",
                ReadinessCheckStatus.SKIPPED.value,
                "info",
                "本次就绪检查跳过 RAG 检索评测。",
                metrics={"active_chunk_count": len(chunks)},
            ),
            None,
        )

    try:
        evaluation_run = rag_quality_evaluation_service.run_retrieval_evaluation(
            db,
            task,
            name=f"Readiness RAG 检索评测 - {task.title}",
        )
    except Exception as exc:
        db.rollback()
        return (
            make_check(
                "rag_retrieval_evaluation",
                "RAG 检索评测",
                ReadinessCheckStatus.WARNING.value,
                "warning",
                "RAG 检索评测运行失败，不影响研究结果阅读。",
                metrics={"active_chunk_count": len(chunks)},
                reasons=[safe_error_summary(str(exc)) or "RAG 检索评测失败。"],
                actions=["查看应用日志或单独运行 RAG 检索评测 runner。"],
            ),
            None,
        )

    metrics = {
        "evaluation_run_uuid": str(evaluation_run.uuid),
        "status": evaluation_run.status,
        "case_total": evaluation_run.case_total,
        "case_completed_count": evaluation_run.case_completed_count,
        "case_failed_count": evaluation_run.case_failed_count,
        "case_skipped_count": evaluation_run.case_skipped_count,
        "hit_rate@k": evaluation_run.average_hit_rate,
        "recall@k": evaluation_run.average_recall,
        "precision@k": evaluation_run.average_precision,
        "mrr@k": evaluation_run.average_mrr,
        "ndcg@k": evaluation_run.average_ndcg,
    }
    has_issues = (
        evaluation_run.status != "completed"
        or evaluation_run.case_failed_count > 0
        or evaluation_run.case_completed_count == 0
    )

    return (
        make_check(
            "rag_retrieval_evaluation",
            "RAG 检索评测",
            ReadinessCheckStatus.WARNING.value
            if has_issues
            else ReadinessCheckStatus.PASS.value,
            "warning" if has_issues else "info",
            "RAG 检索评测需要复查。"
            if has_issues
            else "RAG 检索评测已完成。",
            metrics=metrics,
            reasons=[evaluation_run.error_summary]
            if has_issues and evaluation_run.error_summary
            else [],
            actions=["查看 RAG 检索评测结果。"] if has_issues else [],
        ),
        evaluation_run.uuid,
    )


def check_generation_content_smoke(
    db: Session,
    task: ResearchTask,
    opportunities: list[Opportunity],
    *,
    generation_evaluation_run: Optional[Any] = None,
) -> dict[str, Any]:
    demand_insights = demand_insights_service.list_task_demand_insights(db, task)
    supply_candidates = supply_candidates_service.list_task_supply_candidates(db, task)
    competitor_references = (
        competitor_references_service.list_task_competitor_references(db, task)
    )
    validation_budgets = validation_budgets_service.list_task_validation_budgets(
        db,
        task,
    )
    opportunity_risks = opportunity_risks_service.list_task_opportunity_risks(db, task)
    action_plans = action_plans_service.list_task_action_plans(db, task)

    required_opportunity_fields = [
        ("name", "商机名称"),
        ("product_direction", "产品方向"),
        ("target_audience", "目标人群"),
        ("recommendation_reason", "推荐理由"),
        ("suitable_channels", "适合渠道"),
        ("price_band", "价格带"),
        ("rough_margin", "粗略利润"),
        ("risk_level", "风险等级"),
        ("next_step_summary", "下一步摘要"),
    ]
    missing_fields = []
    for opportunity in opportunities:
        for field_name, label in required_opportunity_fields:
            value = getattr(opportunity, field_name)
            if is_empty_value(value):
                missing_fields.append(f"{opportunity.name}: {label}")

    enhancement_groups = {
        "需求洞察": demand_insights,
        "货源候选": supply_candidates,
        "竞品参考": competitor_references,
        "验证预算": validation_budgets,
        "风险复核": opportunity_risks,
        "行动计划": action_plans,
    }
    missing_enhancements = []
    for label, records in enhancement_groups.items():
        opportunity_ids = {record.opportunity_id for record in records}
        missing_count = sum(
            1 for opportunity in opportunities if opportunity.id not in opportunity_ids
        )
        if missing_count:
            missing_enhancements.append(f"{label}缺少 {missing_count} 个商机")

    visible_text = " ".join(
        extract_text_values(
            [
                *demand_insights,
                *supply_candidates,
                *competitor_references,
                *validation_budgets,
                *opportunity_risks,
                *action_plans,
            ]
        )
    )
    risky_hits = [term for term in RISKY_CLAIMS if term in visible_text]
    has_cautious_terms = any(term in visible_text for term in CAUTIOUS_TERMS)
    reasons = []

    if len(opportunities) < 3:
        reasons.append("active 商机少于 3 个。")
    if missing_fields:
        reasons.append(f"商机字段缺失：{'；'.join(missing_fields[:6])}。")
    if missing_enhancements:
        reasons.append(f"增强分析缺失：{'；'.join(missing_enhancements)}。")
    if risky_hits:
        reasons.append(f"命中高风险断言：{'、'.join(risky_hits)}。")
    if visible_text and not has_cautious_terms:
        reasons.append("增强分析文案缺少初步参考或待验证类谨慎表达。")

    generation_metrics: dict[str, Any] = {}
    generation_actions: list[str] = []
    if generation_evaluation_run is None:
        reasons.append("尚未运行生成质量评测。")
        generation_actions.append("运行生成质量评测 runner 后重新执行 readiness。")
        generation_metrics["generation_evaluation_status"] = "unchecked"
    else:
        generation_stale = generation_quality_evaluation_service.is_stale(
            generation_evaluation_run,
            task,
        )
        generation_metrics.update(
            {
                "generation_evaluation_run_uuid": str(generation_evaluation_run.uuid),
                "generation_evaluation_status": generation_evaluation_run.status,
                "generation_evaluation_overall_status": (
                    generation_evaluation_run.overall_status
                ),
                "generation_evaluation_stale": generation_stale,
                "generation_evaluation_case_total": generation_evaluation_run.case_total,
                "generation_evaluation_case_failed_count": (
                    generation_evaluation_run.case_failed_count
                ),
                "generation_evaluation_case_warning_count": (
                    generation_evaluation_run.case_warning_count
                ),
            }
        )
        if generation_evaluation_run.overall_status == "failed":
            reasons.append("生成质量评测存在 failed case。")
            generation_actions.append("查看生成质量评测结果并复查失败 case。")
        elif generation_evaluation_run.overall_status == "warning":
            reasons.append("生成质量评测存在 warning case。")
            generation_actions.append("查看生成质量评测结果并复查 warning case。")
        if generation_stale:
            reasons.append("生成质量评测结果已过期。")
            generation_actions.append("重新运行生成质量评测。")

    if len(opportunities) < 3 or missing_fields:
        status = ReadinessCheckStatus.FAILED.value
        severity = "critical"
        summary = "生成内容结构不完整。"
    elif (
        missing_enhancements
        or risky_hits
        or (visible_text and not has_cautious_terms)
        or generation_metrics.get("generation_evaluation_status") == "unchecked"
        or (
            generation_evaluation_run is not None
            and (
                generation_evaluation_run.overall_status != "passed"
                or generation_metrics.get("generation_evaluation_stale")
            )
        )
    ):
        status = ReadinessCheckStatus.WARNING.value
        severity = "warning"
        summary = "生成内容需要演示前复查。"
    else:
        status = ReadinessCheckStatus.PASS.value
        severity = "info"
        summary = "生成内容结构和谨慎边界通过 smoke check。"

    return make_check(
        "generation_content_smoke",
        "生成内容结构",
        status,
        severity,
        summary,
        metrics={
            "opportunity_count": len(opportunities),
            "demand_insight_count": len(demand_insights),
            "supply_candidate_count": len(supply_candidates),
            "competitor_reference_count": len(competitor_references),
            "validation_budget_count": len(validation_budgets),
            "opportunity_risk_count": len(opportunity_risks),
            "action_plan_count": len(action_plans),
            "missing_field_count": len(missing_fields),
            "missing_enhancement_group_count": len(missing_enhancements),
            "risky_claim_count": len(risky_hits),
            **generation_metrics,
        },
        reasons=reasons,
        actions=[
            *(
                ["补齐增强分析或重新运行研究任务。"]
                if missing_fields or missing_enhancements or risky_hits
                else []
            ),
            *generation_actions,
        ]
        if reasons
        else [],
    )


def check_report_share_snapshot(db: Session, task: ResearchTask) -> dict[str, Any]:
    shares = report_sharing_service.list_task_report_shares(db, task)
    active_shares = [
        share
        for share in shares
        if share.status == ReportShareStatus.ACTIVE.value and share.deleted_at is None
    ]

    if active_shares:
        return make_check(
            "report_share_snapshot",
            "分享报告快照",
            ReadinessCheckStatus.PASS.value,
            "info",
            "已存在 active 只读分享快照。",
            metrics={
                "share_count": len(shares),
                "active_share_count": len(active_shares),
            },
        )

    return make_check(
        "report_share_snapshot",
        "分享报告快照",
        ReadinessCheckStatus.SKIPPED.value,
        "info",
        "尚未生成只读分享快照，可在需要分享演示结果时生成。",
        metrics={"share_count": len(shares), "active_share_count": 0},
        actions=["如需对外演示链接，请在报告页生成分享链接。"],
    )


def aggregate_overall_status(checks: list[dict[str, Any]]) -> str:
    statuses = [check["status"] for check in checks]

    if ReadinessCheckStatus.FAILED.value in statuses:
        return ReadinessOverallStatus.FAILED.value

    if (
        ReadinessCheckStatus.WARNING.value in statuses
        or ReadinessCheckStatus.SKIPPED.value in statuses
    ):
        return ReadinessOverallStatus.WARNING.value

    return ReadinessOverallStatus.READY.value


def aggregate_metrics(checks: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = {
        status.value: sum(1 for check in checks if check["status"] == status.value)
        for status in ReadinessCheckStatus
    }
    metrics: dict[str, Any] = {
        "check_total": len(checks),
        "status_counts": status_counts,
    }

    for check in checks:
        for key in (
            "opportunity_count",
            "source_count",
            "active_chunk_count",
            "case_total",
            "case_failed_count",
            "generation_evaluation_case_total",
            "generation_evaluation_case_failed_count",
            "generation_evaluation_case_warning_count",
        ):
            if key in check.get("metrics", {}):
                metrics[key] = check["metrics"][key]

    return metrics


def build_summary(overall_status: str, checks: list[dict[str, Any]]) -> str:
    failed_count = sum(
        1 for check in checks if check["status"] == ReadinessCheckStatus.FAILED.value
    )
    warning_count = sum(
        1 for check in checks if check["status"] == ReadinessCheckStatus.WARNING.value
    )
    skipped_count = sum(
        1 for check in checks if check["status"] == ReadinessCheckStatus.SKIPPED.value
    )

    if overall_status == ReadinessOverallStatus.READY.value:
        return "演示就绪检查通过，可以作为候选演示任务。"

    if overall_status == ReadinessOverallStatus.FAILED.value:
        return f"演示就绪检查未通过，{failed_count} 项失败，建议先复查后再演示。"

    return (
        "演示就绪检查存在需要复查的项目，"
        f"{warning_count} 项警告，{skipped_count} 项跳过。"
    )


def readiness_run_to_read(
    readiness_run: ResearchQualityReadinessRun,
    *,
    task: ResearchTask,
) -> ResearchQualityReadinessRunRead:
    return ResearchQualityReadinessRunRead(
        uuid=readiness_run.uuid,
        research_task_uuid=task.uuid,
        research_run_id=readiness_run.research_run_id,
        status=readiness_run.status,
        overall_status=readiness_run.overall_status,
        summary=readiness_run.summary,
        checks=readiness_run.checks,
        metrics=readiness_run.metrics,
        rag_evaluation_run_uuid=readiness_run.rag_evaluation_run_uuid,
        generation_evaluation_run_uuid=readiness_run.generation_evaluation_run_uuid,
        trace_id=readiness_run.trace_id,
        trace_url=readiness_run.trace_url,
        stale=is_stale(readiness_run, task),
        started_at=readiness_run.started_at,
        completed_at=readiness_run.completed_at,
        error_summary=safe_error_summary(readiness_run.error_summary),
        created_at=readiness_run.created_at,
        updated_at=readiness_run.updated_at,
        deleted_at=readiness_run.deleted_at,
    )


def is_stale(readiness_run: ResearchQualityReadinessRun, task: ResearchTask) -> bool:
    return bool(task.run_id and readiness_run.research_run_id != task.run_id)


def make_check(
    key: str,
    label: str,
    status: str,
    severity: str,
    summary: str,
    *,
    metrics: Optional[dict[str, Any]] = None,
    reasons: Optional[list[str]] = None,
    actions: Optional[list[str]] = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "status": status,
        "severity": severity,
        "summary": summary,
        "metrics": metrics or {},
        "reasons": [item for item in reasons or [] if item],
        "actions": actions or [],
    }


def is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not value
    return False


def extract_text_values(values: Iterable[Any]) -> list[str]:
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
            for key, item in vars(value).items():
                if key.startswith("_") or key in {"id", "research_task_id"}:
                    continue
                walk(item)

    for value in values:
        walk(value)

    return output


def safe_error_summary(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return rag_quality_evaluation_service.safe_error_summary(value) or (
        "研究质量就绪检查失败，请查看应用日志。"
    )


def dump_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
