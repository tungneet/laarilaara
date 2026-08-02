"""Data request request/response schemas (/v1/me/data-requests)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DataRequestType(str, Enum):
    EXPORT = "export"
    CORRECTION = "correction"
    DELETION = "deletion"


class CreateDataRequestRequest(BaseModel):
    type: DataRequestType
    details: str | None = Field(default=None, max_length=2000)


class DataRequestResponse(BaseModel):
    id: str
    type: str
    status: str
    details: str | None
    created_at: datetime
    completed_at: datetime | None
