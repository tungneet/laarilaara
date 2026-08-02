"""Request/response models for profile managers, invitations, and candidate
consent (catalog §5 — "Managers and consent" block)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ManagerResponse(BaseModel):
    account_id: str
    role: str
    permissions: list[str]
    is_primary: bool
    created_at: datetime


class PendingInvitationResponse(BaseModel):
    id: str
    role: str
    permissions: list[str]
    status: str
    invited_email: str
    created_at: datetime
    expires_at: datetime


class ManagersListResponse(BaseModel):
    managers: list[ManagerResponse]
    pending_invitations: list[PendingInvitationResponse]


class InviteManagerRequest(BaseModel):
    invited_email: EmailStr
    role: str = Field(pattern="^(parent|candidate|collaborator)$")
    permissions: list[str] = Field(default_factory=lambda: ["profile.read_private"])


class PatchManagerRequest(BaseModel):
    permissions: list[str] | None = None
    is_primary: bool | None = None


class CandidateConsentRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=64)
    granted: bool


class CandidateConsentResponse(BaseModel):
    profile_id: str
    decision: str
    granted: bool
    decided_at: datetime
