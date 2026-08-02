"""Request/response models for compatibility analyses (catalog §8:
`POST /v1/compatibility-analyses`, `GET /v1/compatibility-analyses/{analysisId}`).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompatibilityAnalysisCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_profile_id: str = Field(min_length=1)


class CompatibilityAnalysisResponse(BaseModel):
    id: str
    acting_profile_id: str
    target_profile_id: str
    score: int
    factors: dict[str, int]
    created_at: datetime
    updated_at: datetime
