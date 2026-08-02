"""Request/response models for §11 moderation-action appeals."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModerationAppealCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=2000)


class ModerationAppealResponse(BaseModel):
    action_id: str
    account_id: str
    reason: str
    status: str
    created_at: datetime
