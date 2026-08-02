"""Request/response models for matches (catalog §8: `GET /v1/matches`,
`GET /v1/matches/{matchId}`, `POST /v1/matches/{matchId}/end|feedback|outcomes`).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MatchStatus = Literal["active", "ended"]
MatchOutcome = Literal["engaged", "married", "ended_amicably", "other"]


class MatchResponse(BaseModel):
    id: str
    interest_id: str
    profile_a_id: str
    profile_b_id: str
    status: MatchStatus
    conversation_id: str | None = None
    created_at: datetime
    updated_at: datetime
    ended_at: datetime | None = None


class MatchListResponse(BaseModel):
    items: list[MatchResponse]
    next_cursor: str | None = None


class MatchFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class MatchFeedbackResponse(BaseModel):
    author_profile_id: str
    rating: int
    comment: str | None = None
    created_at: datetime


class MatchOutcomeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: MatchOutcome
    consent: bool


class MatchOutcomeResponse(BaseModel):
    author_profile_id: str
    outcome: MatchOutcome
    consent: bool
    created_at: datetime
