"""Request/response models for §13 billing, entitlements, and
promo-redemptions.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CheckoutSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str


class CheckoutSessionResponse(BaseModel):
    id: str
    plan_id: str
    status: str
    checkout_url: str
    created_at: datetime


class SubscriptionResponse(BaseModel):
    plan_id: str
    status: str
    cancel_at_period_end: bool
    updated_at: datetime


class TransactionResponse(BaseModel):
    id: str
    type: str
    amount_cents: int
    currency: str
    status: str
    created_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    next_cursor: str | None = None


class EntitlementResponse(BaseModel):
    action: str
    allowed: bool
    reason: str | None = None


class EntitlementsResponse(BaseModel):
    tier: str
    entitlements: list[EntitlementResponse]


class PromoRedemptionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)


class PromoRedemptionResponse(BaseModel):
    code: str
    status: str
    applied_at: datetime
