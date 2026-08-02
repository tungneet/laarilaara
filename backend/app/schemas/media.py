"""Request/response models for raw media assets (catalog §6:
`POST /v1/uploads`, `POST /v1/uploads/{uploadId}/complete`,
`GET/DELETE /v1/media/{assetId}`).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.media import MediaAssetStatus


class UploadCreateRequest(BaseModel):
    purpose: str = Field(min_length=1, max_length=64)
    content_type: str = Field(min_length=1, max_length=128)
    size_bytes: int = Field(gt=0, le=20 * 1024 * 1024)
    checksum: str = Field(min_length=32, max_length=128)


class UploadResponse(BaseModel):
    id: str
    purpose: str
    content_type: str
    size_bytes: int
    checksum: str
    status: MediaAssetStatus
    upload_url: str
    created_at: datetime
    updated_at: datetime


class MediaAssetResponse(BaseModel):
    id: str
    purpose: str
    content_type: str
    size_bytes: int
    checksum: str
    status: MediaAssetStatus
    created_at: datetime
    updated_at: datetime


class MediaAccessResponse(MediaAssetResponse):
    download_url: str | None = None
