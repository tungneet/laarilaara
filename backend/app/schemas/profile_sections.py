"""Request/response models for the single-resource profile sections
(catalog §5 — "Sections" batch: personal-details, narratives, lifestyle,
visibility).

Every PATCH request model has all-optional fields (partial update semantics);
every response model reports the full current section state.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.domain.profile_sections import DietType, Gender, HabitLevel, MaritalStatus, VisibilityLevel


class PersonalDetailsPatchRequest(BaseModel):
    date_of_birth: date | None = None
    gender: Gender | None = None
    height_cm: int | None = Field(default=None, ge=100, le=250)
    marital_status: MaritalStatus | None = None
    mother_tongue: str | None = Field(default=None, min_length=1, max_length=64)


class PersonalDetailsResponse(BaseModel):
    date_of_birth: date | None = None
    gender: Gender | None = None
    height_cm: int | None = None
    marital_status: MaritalStatus | None = None
    mother_tongue: str | None = None
    updated_at: datetime | None = None


class NarrativesPatchRequest(BaseModel):
    headline: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=4000)
    partner_expectations: str | None = Field(default=None, max_length=4000)
    family_narrative: str | None = Field(default=None, max_length=4000)


class NarrativesResponse(BaseModel):
    headline: str | None = None
    bio: str | None = None
    partner_expectations: str | None = None
    family_narrative: str | None = None
    updated_at: datetime | None = None


class LifestylePatchRequest(BaseModel):
    diet: DietType | None = None
    smoking: HabitLevel | None = None
    alcohol: HabitLevel | None = None
    fitness_routine: str | None = Field(default=None, max_length=1000)
    values: str | None = Field(default=None, max_length=1000)
    life_plans: str | None = Field(default=None, max_length=1000)


class LifestyleResponse(BaseModel):
    diet: DietType | None = None
    smoking: HabitLevel | None = None
    alcohol: HabitLevel | None = None
    fitness_routine: str | None = None
    values: str | None = None
    life_plans: str | None = None
    updated_at: datetime | None = None


class VisibilityPatchRequest(BaseModel):
    discoverable: bool | None = None
    photo_visibility: VisibilityLevel | None = None
    name_visibility: VisibilityLevel | None = None
    location_visibility: VisibilityLevel | None = None
    contact_visibility: VisibilityLevel | None = None


class VisibilityResponse(BaseModel):
    discoverable: bool | None = None
    photo_visibility: VisibilityLevel | None = None
    name_visibility: VisibilityLevel | None = None
    location_visibility: VisibilityLevel | None = None
    contact_visibility: VisibilityLevel | None = None
    updated_at: datetime | None = None
