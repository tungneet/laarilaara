"""Request/response models for discovery search, recommendations, profile
views, and public profile projections (catalog §7: `POST /v1/discovery/search`,
`GET /v1/discovery/profiles/{profileId}`, `GET /v1/discovery/recommendations`,
`POST /v1/discovery/views`).

Search filters reject unknown fields (``extra="forbid"``) rather than
silently ignoring them, per the catalog note. Cursors are a simplified
base64-encoded offset — the catalog's "ranking version" concept is deferred
until real ranking/search infrastructure exists (see KNOWN SIMPLIFICATION in
`app.repositories.profiles.list_published_profiles`).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.profile_sections import Gender, MaritalStatus


class DiscoverySearchFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_age: int | None = Field(default=None, ge=18, le=120)
    max_age: int | None = Field(default=None, ge=18, le=120)
    gender: Gender | None = None
    communities: list[str] | None = None


class DiscoverySearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filters: DiscoverySearchFilters = Field(default_factory=DiscoverySearchFilters)
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class DiscoveryProfileSummary(BaseModel):
    profile_id: str
    age: int | None = None
    gender: Gender | None = None
    height_cm: int | None = None
    marital_status: MaritalStatus | None = None
    headline: str | None = None


class DiscoveryProfileDetailResponse(DiscoveryProfileSummary):
    bio: str | None = None


class DiscoverySearchResponse(BaseModel):
    items: list[DiscoveryProfileSummary]
    next_cursor: str | None = None


class DiscoveryViewResponse(BaseModel):
    target_profile_id: str
    viewed_at: datetime


class DiscoveryViewCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_profile_id: str = Field(min_length=1)
