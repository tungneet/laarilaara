"""Request/response models for the replace-set profile sections (catalog §5
— "Sections" batch B: communities, religious-practices, languages, interests).

All four share the same shape, so one pair of schemas covers all of them.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProfileSetPutRequest(BaseModel):
    values: list[str] = Field(default_factory=list, max_length=50)


class ProfileSetResponse(BaseModel):
    values: list[str]
    updated_at: datetime | None = None
