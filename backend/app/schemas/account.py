"""Account (/v1/me) request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MeResponse(BaseModel):
    id: str
    email: str | None = None
    phone: str | None = None
    display_name: str | None = None
    gender: str | None = None
    status: str
    tier: str
    locale: str
    created_at: datetime


class UpdateMeRequest(BaseModel):
    locale: str | None = Field(default=None, max_length=10)
