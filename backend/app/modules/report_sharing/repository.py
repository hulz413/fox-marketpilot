from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.report_sharing.models import ReportShare


def create_report_share(db: Session, report_share: ReportShare) -> ReportShare:
    db.add(report_share)
    db.commit()
    db.refresh(report_share)
    return report_share


def save_report_share(db: Session, report_share: ReportShare) -> ReportShare:
    db.add(report_share)
    db.commit()
    db.refresh(report_share)
    return report_share


def list_report_shares_by_task_id(
    db: Session,
    research_task_id: int,
) -> list[ReportShare]:
    statement = (
        select(ReportShare)
        .where(
            ReportShare.research_task_id == research_task_id,
            ReportShare.deleted_at.is_(None),
        )
        .order_by(ReportShare.created_at.desc(), ReportShare.id.desc())
    )

    return list(db.execute(statement).scalars().all())


def get_active_report_share_by_uuid(
    db: Session,
    share_uuid: UUID,
) -> Optional[ReportShare]:
    statement = select(ReportShare).where(
        ReportShare.uuid == share_uuid,
        ReportShare.deleted_at.is_(None),
    )

    return db.execute(statement).scalar_one_or_none()


def get_report_share_by_token(
    db: Session,
    share_token: str,
) -> Optional[ReportShare]:
    statement = select(ReportShare).where(ReportShare.share_token == share_token)

    return db.execute(statement).scalar_one_or_none()


def get_public_report_share_by_token(
    db: Session,
    share_token: str,
    *,
    active_status: str,
) -> Optional[ReportShare]:
    statement = select(ReportShare).where(
        ReportShare.share_token == share_token,
        ReportShare.status == active_status,
        ReportShare.deleted_at.is_(None),
    )

    return db.execute(statement).scalar_one_or_none()
