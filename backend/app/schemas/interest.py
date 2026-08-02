"""Request/response models for interests (catalog §8:
`GET/POST /v1/interests`,
`POST /v1/interests/{interestId}/accept|decline|withdraw`).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

InterestStatus = Literal["pending", "accepted", "declined", "withdrawn"]


class InterestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_profile_id: str = Field(min_length=1)
    message: str | None = Field(default=None, max_length=1000)


class InterestDeclineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=1000)


class InterestResponse(BaseModel):
    id: str
    from_profile_id: str
    to_profile_id: str
    message: str | None = None
    status: InterestStatus
    decline_reason: str | None = None
    match_id: str | None = None
    created_at: datetime
    updated_at: datetime


class InterestListResponse(BaseModel):
    items: list[InterestResponse]
    next_cursor: str | None = None
