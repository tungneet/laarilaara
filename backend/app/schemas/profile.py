"""Request/response models for /v1/profiles (catalog §5 — lifecycle block)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ProfileRelationshipIn(str, Enum):
    SELF = "self"
    OTHER = "other"


class CreateProfileRequest(BaseModel):
    relationship: ProfileRelationshipIn
    locale: str = Field(default="en", min_length=2, max_length=10)


class PatchProfileRequest(BaseModel):
    locale: str = Field(min_length=2, max_length=10)


class ProfileResponse(BaseModel):
    id: str
    relationship: str
    status: str
    version: int
    locale: str
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None
    published_at: datetime | None = None
    paused_at: datetime | None = None


class MyProfileItem(ProfileResponse):
    """A profile the current account manages, with its manager context."""

    my_role: str
    my_permissions: list[str]
    is_primary: bool


class MyProfilesResponse(BaseModel):
    items: list[MyProfileItem]


class ProfilePreviewResponse(BaseModel):
    profile_id: str
    status: str
    locale: str
    note: str


class ProfileCompletionResponse(BaseModel):
    profile_id: str
    score: int
    missing_sections: list[str]
