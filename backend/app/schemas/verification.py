"""Request/response models for §11 trust-summary and verification endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TrustLabel = Literal["unverified", "verified"]


class TrustSummaryResponse(BaseModel):
    profile_id: str
    trust_label: TrustLabel
    verified_checks: list[str]


class VerificationCheckOption(BaseModel):
    id: str
    label: str


class VerificationRequestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_type: str = Field(min_length=1, max_length=64)


VerificationRequestStatus = Literal["draft", "submitted"]


class VerificationRequestResponse(BaseModel):
    id: str
    profile_id: str
    check_type: str
    status: VerificationRequestStatus
    evidence_asset_ids: list[str]
    created_at: datetime
    submitted_at: datetime | None = None


class VerificationEvidenceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1)


class VerificationClaim(BaseModel):
    check_type: str
    status: VerificationRequestStatus
