from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentRunEventRead(BaseModel):
    uuid: UUID
    run_id: str
    trace_id: Optional[str]
    stage: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    error_summary: Optional[str]

    model_config = ConfigDict(from_attributes=True)
