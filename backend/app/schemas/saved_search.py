"""Request/response models for saved searches (catalog §7:
`GET/POST /v1/saved-searches`, `PATCH/DELETE /v1/saved-searches/{searchId}`).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.discovery import DiscoverySearchFilters


class SavedSearchCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    filters: DiscoverySearchFilters = Field(default_factory=DiscoverySearchFilters)
    alert: bool = False


class SavedSearchPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    filters: DiscoverySearchFilters | None = None
    alert: bool | None = None


class SavedSearchResponse(BaseModel):
    id: str
    name: str
    filters: DiscoverySearchFilters
    alert: bool = False
    created_at: datetime
    updated_at: datetime
