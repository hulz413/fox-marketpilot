from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportShareStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class ReportShareRead(BaseModel):
    uuid: UUID
    research_task_uuid: UUID
    share_token: str
    title: str
    status: ReportShareStatus
    created_at: datetime
    updated_at: datetime
    revoked_at: Optional[datetime]
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PublicReportShareRead(BaseModel):
    uuid: UUID
    share_token: str
    title: str
    status: ReportShareStatus
    snapshot: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
