"""Request/response models for the private shortlist (catalog §7:
`GET /v1/shortlist`, `PUT/DELETE /v1/shortlist/{targetProfileId}`).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ShortlistPutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, max_length=500)


class ShortlistItemResponse(BaseModel):
    target_profile_id: str
    note: str | None = None
    created_at: datetime
    updated_at: datetime
