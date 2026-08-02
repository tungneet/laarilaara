"""Request/response models for profile media attachments (catalog §6:
`GET/POST /v1/profiles/{profileId}/media`,
`PATCH/DELETE /v1/profiles/{profileId}/media/{profileMediaId}`).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.profile_sections import VisibilityLevel


class ProfileMediaCreateRequest(BaseModel):
    asset_id: str = Field(min_length=1)
    is_primary: bool = False
    visibility: VisibilityLevel | None = None
    caption: str | None = Field(default=None, max_length=300)
    order: int | None = Field(default=None, ge=0)


class ProfileMediaPatchRequest(BaseModel):
    is_primary: bool | None = None
    visibility: VisibilityLevel | None = None
    caption: str | None = Field(default=None, max_length=300)
    order: int | None = Field(default=None, ge=0)


class ProfileMediaResponse(BaseModel):
    id: str
    asset_id: str
    is_primary: bool = False
    visibility: VisibilityLevel | None = None
    caption: str | None = None
    order: int | None = None
    created_at: datetime
    updated_at: datetime
