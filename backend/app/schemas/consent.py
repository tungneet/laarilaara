"""Consent request/response schemas (/v1/me/consents)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ConsentType(str, Enum):
    MARKETING = "marketing"
    AI = "ai"
    PROFILE = "profile"


class RecordConsentRequest(BaseModel):
    consent_type: ConsentType
    granted: bool
    policy_version: str


class ConsentRecord(BaseModel):
    consent_type: str
    granted: bool
    policy_version: str
    decided_at: datetime


class ConsentSummaryResponse(BaseModel):
    current: dict[str, ConsentRecord]
    history: list[ConsentRecord]
