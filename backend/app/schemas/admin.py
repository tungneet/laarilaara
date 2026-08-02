"""Request/response models for catalog §15 Administrative API.

One file for all seven admin sub-areas (dashboard, accounts/profiles,
moderation, verification, billing/support, brands/config, reference data) —
same rationale as `app/schemas/billing.py` bundling a whole catalog section.

Every mutating admin request includes a required ``reason`` field (catalog:
"reason capture for sensitive reads/actions... immutable audit"); each
mutating admin service call writes one row to `admin_audit.py`.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

_ReasonField = Field(min_length=1, max_length=500)


# ---- Dashboard --------------------------------------------------------------


class AdminDashboardResponse(BaseModel):
    account_count: int
    profile_count: int
    published_profile_count: int
    open_moderation_case_count: int
    submitted_verification_request_count: int
    open_support_ticket_count: int


class QueueHealthResponse(BaseModel):
    queues: list[dict]


# ---- Accounts/profiles -------------------------------------------------------


class AdminAccountResponse(BaseModel):
    id: str
    email: str
    status: str
    tier: str
    role: str
    locale: str
    created_at: datetime
    updated_at: datetime


class AdminAccountListResponse(BaseModel):
    items: list[AdminAccountResponse]
    next_cursor: str | None = None


class AdminProfileResponse(BaseModel):
    id: str
    owner_account_id: str
    relationship: str
    status: str
    version: int
    locale: str
    created_at: datetime
    updated_at: datetime


class AdminProfileListResponse(BaseModel):
    items: list[AdminProfileResponse]
    next_cursor: str | None = None


# ---- Moderation cases ---------------------------------------------------------


class ModerationCaseResponse(BaseModel):
    id: str
    subject_account_id: str
    report_id: str | None = None
    status: str
    assigned_admin_id: str | None = None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None


class ModerationCaseListResponse(BaseModel):
    items: list[ModerationCaseResponse]
    next_cursor: str | None = None


class ModerationCaseAssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = _ReasonField


class ModerationCaseActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: str = Field(min_length=1, max_length=64)
    reason: str = _ReasonField


class ModerationActionResponse(BaseModel):
    id: str
    affected_account_id: str
    action_type: str
    reason: str
    created_at: datetime


class ModerationCaseCloseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = _ReasonField


# ---- Verification -------------------------------------------------------------


class AdminVerificationRequestResponse(BaseModel):
    id: str
    profile_id: str
    check_type: str
    status: str
    created_at: datetime
    submitted_at: datetime | None = None
    decided_at: datetime | None = None
    decision_reason: str | None = None


class AdminVerificationRequestListResponse(BaseModel):
    items: list[AdminVerificationRequestResponse]
    next_cursor: str | None = None


class VerificationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str = _ReasonField


# ---- Billing / support ---------------------------------------------------------


class AdminSubscriptionResponse(BaseModel):
    account_id: str
    plan_id: str
    status: str
    cancel_at_period_end: bool
    updated_at: datetime


class AdminSubscriptionListResponse(BaseModel):
    items: list[AdminSubscriptionResponse]
    next_cursor: str | None = None


class AdminTransactionResponse(BaseModel):
    id: str
    account_id: str
    type: str
    amount_cents: int
    currency: str
    status: str
    created_at: datetime


class AdminTransactionListResponse(BaseModel):
    items: list[AdminTransactionResponse]
    next_cursor: str | None = None


class SupportTicketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str | None = None
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)


class SupportTicketUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(pattern="^(open|pending|closed)$")
    reason: str = _ReasonField


class SupportTicketResponse(BaseModel):
    id: str
    account_id: str | None = None
    subject: str
    body: str
    status: str
    created_at: datetime
    updated_at: datetime


class SupportTicketListResponse(BaseModel):
    items: list[SupportTicketResponse]
    next_cursor: str | None = None


# ---- Brands / experiences / feature flags ---------------------------------------


class BrandConfigResponse(BaseModel):
    id: str
    name: str
    active: bool
    updated_at: datetime


class BrandConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=128)
    active: bool | None = None
    reason: str = _ReasonField


class ExperienceConfigResponse(BaseModel):
    id: str
    name: str
    active: bool
    updated_at: datetime


class ExperienceConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=128)
    active: bool | None = None
    reason: str = _ReasonField


class FeatureFlagResponse(BaseModel):
    key: str
    enabled: bool
    updated_at: datetime


class FeatureFlagUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    reason: str = _ReasonField


# ---- Reference data (generic, keyed by list name) --------------------------------


class ReferenceDataItemResponse(BaseModel):
    list_name: str
    id: str
    label: str
    value: dict | None = None
    active: bool
    created_at: datetime
    updated_at: datetime


class ReferenceDataItemListResponse(BaseModel):
    items: list[ReferenceDataItemResponse]


class ReferenceDataItemCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=200)
    value: dict | None = None
    reason: str = _ReasonField


class ReferenceDataItemUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, min_length=1, max_length=200)
    value: dict | None = None
    reason: str = _ReasonField


class ReferenceDataItemDeactivateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = _ReasonField
