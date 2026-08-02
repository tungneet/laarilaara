"""Request/response models for §11 reports (`POST/GET /v1/reports`)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReportSubjectType = Literal["profile", "message", "conversation", "media"]
ReportStatus = Literal["queued", "reviewing", "actioned", "dismissed"]


class ReportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_type: ReportSubjectType
    subject_id: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=64)
    details: str | None = Field(default=None, max_length=2000)
    evidence_asset_ids: list[str] = Field(default_factory=list)


class ReportResponse(BaseModel):
    id: str
    reporter_profile_id: str
    subject_type: ReportSubjectType
    subject_id: str
    status: ReportStatus
    created_at: datetime
