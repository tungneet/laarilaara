"""Request/response models for education and employment records (catalog §5
— "Sections" batch C).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EducationCreateRequest(BaseModel):
    institution: str = Field(min_length=1, max_length=200)
    education_level: str = Field(min_length=1, max_length=64)
    field_of_study: str | None = Field(default=None, max_length=200)
    start_year: int | None = Field(default=None, ge=1900, le=2100)
    end_year: int | None = Field(default=None, ge=1900, le=2100)
    is_current: bool = False


class EducationPatchRequest(BaseModel):
    institution: str | None = Field(default=None, min_length=1, max_length=200)
    education_level: str | None = Field(default=None, min_length=1, max_length=64)
    field_of_study: str | None = Field(default=None, max_length=200)
    start_year: int | None = Field(default=None, ge=1900, le=2100)
    end_year: int | None = Field(default=None, ge=1900, le=2100)
    is_current: bool | None = None


class EducationResponse(BaseModel):
    id: str
    institution: str
    education_level: str
    field_of_study: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    is_current: bool = False
    created_at: datetime
    updated_at: datetime


class EmploymentCreateRequest(BaseModel):
    employer: str = Field(min_length=1, max_length=200)
    occupation_category: str = Field(min_length=1, max_length=64)
    job_title: str | None = Field(default=None, max_length=200)
    start_year: int | None = Field(default=None, ge=1900, le=2100)
    end_year: int | None = Field(default=None, ge=1900, le=2100)
    is_current: bool = False


class EmploymentPatchRequest(BaseModel):
    employer: str | None = Field(default=None, min_length=1, max_length=200)
    occupation_category: str | None = Field(default=None, min_length=1, max_length=64)
    job_title: str | None = Field(default=None, max_length=200)
    start_year: int | None = Field(default=None, ge=1900, le=2100)
    end_year: int | None = Field(default=None, ge=1900, le=2100)
    is_current: bool | None = None


class EmploymentResponse(BaseModel):
    id: str
    employer: str
    occupation_category: str
    job_title: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    is_current: bool = False
    created_at: datetime
    updated_at: datetime
