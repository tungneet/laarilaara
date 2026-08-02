"""Request/response models for the main partner-preferences summary
(catalog §5 — "Sections" batch E: `GET/PUT .../preferences`).

The five preference *sets* (countries/languages/communities/
religious-practices/education-levels) reuse the existing
`ProfileSetPutRequest`/`ProfileSetResponse` shape from
`app.schemas.profile_sets` since they are identical `{values: [...]}`
replace-set resources — no new schema classes needed for those.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PreferencesPutRequest(BaseModel):
    age_min: int | None = Field(default=None, ge=18, le=100)
    age_max: int | None = Field(default=None, ge=18, le=100)
    height_min_cm: int | None = Field(default=None, ge=100, le=250)
    height_max_cm: int | None = Field(default=None, ge=100, le=250)
    priorities: list[str] = Field(default_factory=list, max_length=10)
    notes: str | None = Field(default=None, max_length=1000)


class PreferencesResponse(BaseModel):
    age_min: int | None = None
    age_max: int | None = None
    height_min_cm: int | None = None
    height_max_cm: int | None = None
    priorities: list[str] = Field(default_factory=list)
    notes: str | None = None
    updated_at: datetime | None = None
