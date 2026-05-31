from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.report_sharing import service as report_sharing_service
from app.modules.report_sharing.schemas import (
    PublicReportShareRead,
    ReportShareRead,
)
from app.modules.research_tasks import service as research_tasks_service

router = APIRouter()


@router.post(
    "/research-tasks/{task_uuid}/report-shares",
    response_model=ReportShareRead,
    status_code=status.HTTP_201_CREATED,
)
def create_report_share(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> ReportShareRead:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    try:
        report_share = report_sharing_service.create_report_share(db, task)
    except report_sharing_service.ReportShareUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return report_sharing_service.report_share_to_read(
        report_share,
        research_task_uuid=task.uuid,
    )


@router.get(
    "/research-tasks/{task_uuid}/report-shares",
    response_model=list[ReportShareRead],
)
def list_report_shares(
    task_uuid: UUID,
    db: Session = Depends(get_db),
) -> list[ReportShareRead]:
    task = research_tasks_service.get_research_task(db, task_uuid)

    if task is None:
        raise HTTPException(status_code=404, detail="Research task not found")

    return [
        report_sharing_service.report_share_to_read(
            report_share,
            research_task_uuid=task.uuid,
        )
        for report_share in report_sharing_service.list_task_report_shares(db, task)
    ]


@router.post(
    "/report-shares/{share_uuid}/revoke",
    response_model=ReportShareRead,
)
def revoke_report_share(
    share_uuid: UUID,
    db: Session = Depends(get_db),
) -> ReportShareRead:
    report_share = report_sharing_service.revoke_report_share(db, share_uuid)

    if report_share is None:
        raise HTTPException(status_code=404, detail="Report share not found")

    task = research_tasks_service.get_research_task_by_id(
        db,
        report_share.research_task_id,
    )

    if task is None:
        raise HTTPException(status_code=404, detail="Report share not found")

    return report_sharing_service.report_share_to_read(
        report_share,
        research_task_uuid=task.uuid,
    )


@router.get(
    "/report-shares/{share_token}",
    response_model=PublicReportShareRead,
)
def get_public_report_share(
    share_token: str,
    db: Session = Depends(get_db),
) -> PublicReportShareRead:
    report_share = report_sharing_service.get_public_report_share(db, share_token)

    if report_share is None:
        raise HTTPException(status_code=404, detail="Report share not found")

    return report_sharing_service.report_share_to_public_read(report_share)
