"""Request/response models for generated biodata documents (catalog §6:
`POST /v1/profiles/{profileId}/biodata`, `GET /v1/profiles/{profileId}/biodata/{documentId}`).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.media import BiodataStatus


class BiodataGenerateRequest(BaseModel):
    template: str = Field(min_length=1, max_length=64)
    locale: str = Field(min_length=1, max_length=10)


class BiodataResponse(BaseModel):
    id: str
    template: str
    locale: str
    status: BiodataStatus
    download_url: str | None = None
    created_at: datetime
    updated_at: datetime
