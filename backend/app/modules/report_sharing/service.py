from __future__ import annotations

import secrets
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.action_plans import service as action_plans_service
from app.modules.competitor_references import service as competitor_references_service
from app.modules.demand_insights import service as demand_insights_service
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunities.models import Opportunity
from app.modules.opportunities.schemas import OpportunityRead
from app.modules.opportunity_risks import service as opportunity_risks_service
from app.modules.report_sharing import repository
from app.modules.report_sharing.models import ReportShare, utc_now
from app.modules.report_sharing.schemas import (
    PublicReportShareRead,
    ReportShareRead,
    ReportShareStatus,
)
from app.modules.research_tasks.models import ResearchTask
from app.modules.sources import service as sources_service
from app.modules.supply_candidates import service as supply_candidates_service
from app.modules.validation_budgets import service as validation_budgets_service

TOKEN_BYTES = 32


class ReportShareUnavailableError(RuntimeError):
    pass


def create_report_share(db: Session, task: ResearchTask) -> ReportShare:
    opportunities = opportunities_service.list_task_opportunities(db, task)

    if not opportunities:
        raise ReportShareUnavailableError("Research task has no opportunity results")

    report_share = ReportShare(
        research_task_id=task.id,
        share_token=generate_unique_share_token(db),
        title=task.title,
        snapshot=build_report_snapshot(db, task, opportunities),
        status=ReportShareStatus.ACTIVE.value,
    )

    return repository.create_report_share(db, report_share)


def list_task_report_shares(db: Session, task: ResearchTask) -> list[ReportShare]:
    return repository.list_report_shares_by_task_id(db, task.id)


def revoke_report_share(
    db: Session,
    share_uuid: UUID,
) -> Optional[ReportShare]:
    report_share = repository.get_active_report_share_by_uuid(db, share_uuid)

    if report_share is None or report_share.status != ReportShareStatus.ACTIVE.value:
        return None

    report_share.status = ReportShareStatus.REVOKED.value
    report_share.revoked_at = utc_now()

    return repository.save_report_share(db, report_share)


def get_public_report_share(
    db: Session,
    share_token: str,
) -> Optional[ReportShare]:
    return repository.get_public_report_share_by_token(
        db,
        share_token,
        active_status=ReportShareStatus.ACTIVE.value,
    )


def generate_unique_share_token(db: Session) -> str:
    for _ in range(5):
        token = secrets.token_urlsafe(TOKEN_BYTES)

        if repository.get_report_share_by_token(db, token) is None:
            return token

    raise RuntimeError("Unable to generate a unique report share token")


def report_share_to_read(
    report_share: ReportShare,
    *,
    research_task_uuid: Any,
) -> ReportShareRead:
    return ReportShareRead(
        uuid=report_share.uuid,
        research_task_uuid=research_task_uuid,
        share_token=report_share.share_token,
        title=report_share.title,
        status=report_share.status,
        created_at=report_share.created_at,
        updated_at=report_share.updated_at,
        revoked_at=report_share.revoked_at,
        deleted_at=report_share.deleted_at,
    )


def report_share_to_public_read(report_share: ReportShare) -> PublicReportShareRead:
    return PublicReportShareRead(
        uuid=report_share.uuid,
        share_token=report_share.share_token,
        title=report_share.title,
        status=report_share.status,
        snapshot=report_share.snapshot,
        created_at=report_share.created_at,
        updated_at=report_share.updated_at,
    )


def build_report_snapshot(
    db: Session,
    task: ResearchTask,
    opportunities: list[Opportunity],
) -> dict[str, Any]:
    opportunity_uuid_by_id = {
        opportunity.id: opportunity.uuid for opportunity in opportunities
    }
    shared_at = utc_now().isoformat()

    return {
        "schema_version": 1,
        "shared_at": shared_at,
        "task": {
            "uuid": str(task.uuid),
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
            "created_at": task.created_at.isoformat(),
        },
        "summary": {
            "opportunity_count": len(opportunities),
            "source_count": len(sources_service.list_task_sources(db, task)),
            "top_opportunity_name": opportunities[0].name if opportunities else None,
        },
        "opportunities": [
            _dump_read(
                OpportunityRead(
                    uuid=opportunity.uuid,
                    research_task_uuid=task.uuid,
                    rank=opportunity.rank,
                    name=opportunity.name,
                    product_direction=opportunity.product_direction,
                    target_audience=opportunity.target_audience,
                    recommendation_reason=opportunity.recommendation_reason,
                    suitable_channels=opportunity.suitable_channels,
                    price_band=opportunity.price_band,
                    rough_margin=opportunity.rough_margin,
                    risk_level=opportunity.risk_level,
                    priority_label=opportunity.priority_label,
                    next_step_summary=opportunity.next_step_summary,
                    created_at=opportunity.created_at,
                    updated_at=opportunity.updated_at,
                    deleted_at=opportunity.deleted_at,
                )
            )
            for opportunity in opportunities
        ],
        "sources": [
            _dump_read(
                sources_service.source_to_read(
                    source,
                    research_task_uuid=task.uuid,
                    opportunity_uuid=opportunity_uuid_by_id.get(source.opportunity_id),
                )
            )
            for source in sources_service.list_task_sources(db, task)
        ],
        "demand_insights": [
            _dump_read(
                demand_insights_service.demand_insight_to_read(
                    db,
                    insight,
                    research_task_uuid=task.uuid,
                    opportunity_uuid=opportunity_uuid_by_id[insight.opportunity_id],
                )
            )
            for insight in demand_insights_service.list_task_demand_insights(db, task)
            if insight.opportunity_id in opportunity_uuid_by_id
        ],
        "supply_candidates": [
            _dump_read(
                supply_candidates_service.supply_candidate_to_read(
                    db,
                    candidate,
                    research_task_uuid=task.uuid,
                    opportunity_uuid=opportunity_uuid_by_id[candidate.opportunity_id],
                )
            )
            for candidate in supply_candidates_service.list_task_supply_candidates(
                db,
                task,
            )
            if candidate.opportunity_id in opportunity_uuid_by_id
        ],
        "competitor_references": [
            _dump_read(
                competitor_references_service.competitor_reference_to_read(
                    db,
                    reference,
                    research_task_uuid=task.uuid,
                    opportunity_uuid=opportunity_uuid_by_id[reference.opportunity_id],
                )
            )
            for reference in competitor_references_service.list_task_competitor_references(
                db,
                task,
            )
            if reference.opportunity_id in opportunity_uuid_by_id
        ],
        "validation_budgets": [
            _dump_read(
                validation_budgets_service.validation_budget_to_read(
                    budget,
                    research_task_uuid=task.uuid,
                    opportunity_uuid=opportunity_uuid_by_id[budget.opportunity_id],
                )
            )
            for budget in validation_budgets_service.list_task_validation_budgets(
                db,
                task,
            )
            if budget.opportunity_id in opportunity_uuid_by_id
        ],
        "opportunity_risks": [
            _dump_read(
                opportunity_risks_service.opportunity_risk_to_read(
                    risk,
                    research_task_uuid=task.uuid,
                    opportunity_uuid=opportunity_uuid_by_id[risk.opportunity_id],
                )
            )
            for risk in opportunity_risks_service.list_task_opportunity_risks(
                db,
                task,
            )
            if risk.opportunity_id in opportunity_uuid_by_id
        ],
        "action_plans": [
            _dump_read(
                action_plans_service.action_plan_to_read(
                    plan,
                    research_task_uuid=task.uuid,
                    opportunity_uuid=opportunity_uuid_by_id[plan.opportunity_id],
                )
            )
            for plan in action_plans_service.list_task_action_plans(db, task)
            if plan.opportunity_id in opportunity_uuid_by_id
        ],
        "boundary_notes": [
            "该报告为待验证商机研究草案，仅用于筛选方向和规划小批量验证。",
            "公开来源、货源、竞品、预算、风险和行动计划均为初步参考，仍需人工核验。",
            "系统不会自动下单、联系供应商、发布内容或完成真实市场验证。",
        ],
    }


def _dump_read(read_model: Any) -> dict[str, Any]:
    return read_model.model_dump(mode="json")
