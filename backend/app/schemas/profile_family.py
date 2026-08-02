"""Request/response models for the family section (catalog §5 — "Sections"
batch D: `GET/PUT .../family` summary + `GET/POST .../family/members` +
`PATCH/DELETE .../family/members/{memberId}`).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.profile_sections import FamilyMemberRelation, FamilyType


class FamilyPutRequest(BaseModel):
    family_type: FamilyType | None = None
    father_living: bool | None = None
    mother_living: bool | None = None
    siblings_count: int | None = Field(default=None, ge=0, le=50)
    family_values: str | None = Field(default=None, max_length=1000)


class FamilyResponse(BaseModel):
    family_type: FamilyType | None = None
    father_living: bool | None = None
    mother_living: bool | None = None
    siblings_count: int | None = None
    family_values: str | None = None
    updated_at: datetime | None = None


class FamilyMemberCreateRequest(BaseModel):
    relation: FamilyMemberRelation
    name: str = Field(min_length=1, max_length=200)
    age: int | None = Field(default=None, ge=0, le=120)
    occupation: str | None = Field(default=None, max_length=200)
    is_married: bool | None = None


class FamilyMemberPatchRequest(BaseModel):
    relation: FamilyMemberRelation | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    age: int | None = Field(default=None, ge=0, le=120)
    occupation: str | None = Field(default=None, max_length=200)
    is_married: bool | None = None


class FamilyMemberResponse(BaseModel):
    id: str
    relation: FamilyMemberRelation
    name: str
    age: int | None = None
    occupation: str | None = None
    is_married: bool | None = None
    created_at: datetime
    updated_at: datetime
