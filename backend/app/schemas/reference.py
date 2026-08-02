"""Response schemas for public/reference/platform endpoints (catalog §3)."""
from __future__ import annotations

from pydantic import BaseModel


class ContextResponse(BaseModel):
    experience: str
    service_name: str
    api_version: str
    default_locale: str = "en"
    default_currency: str = "USD"


class CountryOut(BaseModel):
    code: str
    name: str


class RegionOut(BaseModel):
    code: str
    name: str


class LanguageOut(BaseModel):
    code: str
    name: str


class LabelOption(BaseModel):
    id: str
    label: str


class PlanOut(BaseModel):
    id: str
    name: str
    price_cents: int
    currency: str
    interval: str
