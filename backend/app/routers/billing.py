"""Routers for §13 billing, entitlements, and promo-redemptions. Three
small `APIRouter`s in one file (same reason as `app/routers/ai.py`'s 5-router
split and `app/routers/notifications.py`'s 3-router split): the catalog
paths span three different top-level prefixes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.billing import (
    CheckoutSessionCreateRequest,
    CheckoutSessionResponse,
    EntitlementsResponse,
    PromoRedemptionCreateRequest,
    PromoRedemptionResponse,
    SubscriptionResponse,
    TransactionListResponse,
)
from app.services import accounts as accounts_service
from app.services import billing as billing_service
from app.services import entitlements as entitlements_service
from app.services import promo_redemptions as promo_redemptions_service

billing_router = APIRouter(prefix="/v1/billing", tags=["billing"])
entitlements_router = APIRouter(prefix="/v1/entitlements", tags=["billing"])
promo_redemptions_router = APIRouter(prefix="/v1/promo-redemptions", tags=["billing"])

_PLAN_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PLAN_NOT_FOUND",
    title="Plan not found",
)

_PROMO_CODE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PROMO_CODE_NOT_FOUND",
    title="Promo code not found",
)


@billing_router.post(
    "/checkout-sessions", response_model=CheckoutSessionResponse, status_code=status.HTTP_201_CREATED
)
async def create_checkout_session(
    payload: CheckoutSessionCreateRequest,
    current: CurrentSession = Depends(get_current_session),
) -> CheckoutSessionResponse:
    try:
        session = billing_service.create_checkout_session(current.account_id, payload.plan_id)
    except billing_service.PlanNotFoundError as exc:
        raise _PLAN_NOT_FOUND_ERROR from exc
    return CheckoutSessionResponse(**session)


@billing_router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current: CurrentSession = Depends(get_current_session),
) -> SubscriptionResponse:
    subscription = billing_service.get_subscription(current.account_id)
    return SubscriptionResponse(**subscription)


@billing_router.post("/subscription/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    current: CurrentSession = Depends(get_current_session),
) -> SubscriptionResponse:
    subscription = billing_service.cancel_subscription(current.account_id)
    return SubscriptionResponse(**subscription)


@billing_router.post("/subscription/resume", response_model=SubscriptionResponse)
async def resume_subscription(
    current: CurrentSession = Depends(get_current_session),
) -> SubscriptionResponse:
    subscription = billing_service.resume_subscription(current.account_id)
    return SubscriptionResponse(**subscription)


@billing_router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current: CurrentSession = Depends(get_current_session),
) -> TransactionListResponse:
    result = billing_service.list_transactions(current.account_id, cursor, limit)
    return TransactionListResponse(**result)


@entitlements_router.get("", response_model=EntitlementsResponse)
async def get_entitlements(
    current: CurrentSession = Depends(get_current_session),
) -> EntitlementsResponse:
    account = accounts_service.get_profile(current.account_id)
    view = entitlements_service.effective_view(account)
    return EntitlementsResponse(tier=account.tier.value, entitlements=view)


@promo_redemptions_router.post(
    "", response_model=PromoRedemptionResponse, status_code=status.HTTP_200_OK
)
async def redeem_promo(
    payload: PromoRedemptionCreateRequest,
    current: CurrentSession = Depends(get_current_session),
) -> PromoRedemptionResponse:
    try:
        redemption = promo_redemptions_service.redeem_promo(current.account_id, payload.code)
    except promo_redemptions_service.PromoCodeNotFoundError as exc:
        raise _PROMO_CODE_NOT_FOUND_ERROR from exc
    return PromoRedemptionResponse(**redemption)
