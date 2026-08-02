"""Routers for catalog §15 Administrative API. Eight small `APIRouter`s in
one file (same reason as `app/routers/ai.py`'s 5-router split): the catalog
paths span many top-level prefixes under the shared `/v1/admin` surface.

Every router depends on `get_current_admin_session` (403 `ADMIN_REQUIRED`
for non-admin callers) rather than the plain `get_current_session` used
everywhere else in the API.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_admin_session
from app.core.errors import ApiError
from app.schemas.admin import (
    AdminAccountListResponse,
    AdminAccountResponse,
    AdminDashboardResponse,
    AdminProfileListResponse,
    AdminProfileResponse,
    AdminSubscriptionListResponse,
    AdminTransactionListResponse,
    AdminVerificationRequestListResponse,
    AdminVerificationRequestResponse,
    BrandConfigResponse,
    BrandConfigUpdateRequest,
    ExperienceConfigResponse,
    ExperienceConfigUpdateRequest,
    FeatureFlagResponse,
    FeatureFlagUpdateRequest,
    ModerationActionResponse,
    ModerationCaseActionRequest,
    ModerationCaseAssignRequest,
    ModerationCaseCloseRequest,
    ModerationCaseListResponse,
    ModerationCaseResponse,
    QueueHealthResponse,
    ReferenceDataItemCreateRequest,
    ReferenceDataItemDeactivateRequest,
    ReferenceDataItemListResponse,
    ReferenceDataItemResponse,
    ReferenceDataItemUpdateRequest,
    SupportTicketCreateRequest,
    SupportTicketListResponse,
    SupportTicketResponse,
    SupportTicketUpdateRequest,
    VerificationDecisionRequest,
)
from app.services import admin_billing as admin_billing_service
from app.services import admin_config as admin_config_service
from app.services import admin_dashboard as admin_dashboard_service
from app.services import admin_directory as admin_directory_service
from app.services import admin_moderation as admin_moderation_service
from app.services import admin_reference as admin_reference_service
from app.services import admin_verification as admin_verification_service

admin_dashboard_router = APIRouter(prefix="/v1/admin", tags=["admin"])
admin_directory_router = APIRouter(prefix="/v1/admin", tags=["admin"])
admin_moderation_router = APIRouter(prefix="/v1/admin/moderation", tags=["admin"])
admin_verification_router = APIRouter(prefix="/v1/admin/verification", tags=["admin"])
admin_billing_router = APIRouter(prefix="/v1/admin", tags=["admin"])
admin_support_router = APIRouter(prefix="/v1/admin/support", tags=["admin"])
admin_config_router = APIRouter(prefix="/v1/admin", tags=["admin"])
admin_reference_router = APIRouter(prefix="/v1/admin/reference", tags=["admin"])

_ACCOUNT_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="ACCOUNT_NOT_FOUND", title="Account not found"
)
_PROFILE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="PROFILE_NOT_FOUND", title="Profile not found"
)
_MODERATION_CASE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="MODERATION_CASE_NOT_FOUND", title="Moderation case not found"
)
_MODERATION_CASE_ALREADY_CLOSED_ERROR = ApiError(
    status=status.HTTP_409_CONFLICT,
    code="MODERATION_CASE_ALREADY_CLOSED",
    title="Moderation case already closed",
)
_VERIFICATION_REQUEST_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="VERIFICATION_REQUEST_NOT_FOUND",
    title="Verification request not found",
)
_VERIFICATION_REQUEST_NOT_SUBMITTED_ERROR = ApiError(
    status=status.HTTP_409_CONFLICT,
    code="VERIFICATION_REQUEST_NOT_SUBMITTED",
    title="Verification request is not awaiting a decision",
)
_SUPPORT_TICKET_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="SUPPORT_TICKET_NOT_FOUND", title="Support ticket not found"
)
_BRAND_CONFIG_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="BRAND_CONFIG_NOT_FOUND", title="Brand config not found"
)
_EXPERIENCE_CONFIG_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="EXPERIENCE_CONFIG_NOT_FOUND", title="Experience config not found"
)
_FEATURE_FLAG_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="FEATURE_FLAG_NOT_FOUND", title="Feature flag not found"
)
_REFERENCE_ITEM_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="REFERENCE_ITEM_NOT_FOUND", title="Reference data item not found"
)
_REFERENCE_ITEM_ALREADY_EXISTS_ERROR = ApiError(
    status=status.HTTP_409_CONFLICT,
    code="REFERENCE_ITEM_ALREADY_EXISTS",
    title="Reference data item already exists",
)


# ---- Dashboard --------------------------------------------------------------


@admin_dashboard_router.get("/dashboard", response_model=AdminDashboardResponse)
async def get_dashboard(
    current: CurrentSession = Depends(get_current_admin_session),
) -> AdminDashboardResponse:
    return AdminDashboardResponse(**admin_dashboard_service.get_dashboard())


@admin_dashboard_router.get("/health/queues", response_model=QueueHealthResponse)
async def get_queue_health(
    current: CurrentSession = Depends(get_current_admin_session),
) -> QueueHealthResponse:
    return QueueHealthResponse(**admin_dashboard_service.get_queue_health())


# ---- Accounts/profiles -------------------------------------------------------


@admin_directory_router.get("/accounts", response_model=AdminAccountListResponse)
async def list_accounts(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current: CurrentSession = Depends(get_current_admin_session),
) -> AdminAccountListResponse:
    result = admin_directory_service.list_accounts(cursor, limit)
    return AdminAccountListResponse(
        items=[AdminAccountResponse(**a.model_dump()) for a in result["items"]],
        next_cursor=result["next_cursor"],
    )


@admin_directory_router.get("/accounts/{account_id}", response_model=AdminAccountResponse)
async def get_account(
    account_id: str,
    current: CurrentSession = Depends(get_current_admin_session),
) -> AdminAccountResponse:
    try:
        account = admin_directory_service.get_account(account_id)
    except admin_directory_service.AccountNotFoundError as exc:
        raise _ACCOUNT_NOT_FOUND_ERROR from exc
    return AdminAccountResponse(**account.model_dump())


@admin_directory_router.get("/profiles", response_model=AdminProfileListResponse)
async def list_profiles(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current: CurrentSession = Depends(get_current_admin_session),
) -> AdminProfileListResponse:
    result = admin_directory_service.list_profiles(cursor, limit)
    return AdminProfileListResponse(
        items=[AdminProfileResponse(**p.model_dump()) for p in result["items"]],
        next_cursor=result["next_cursor"],
    )


@admin_directory_router.get("/profiles/{profile_id}", response_model=AdminProfileResponse)
async def get_profile(
    profile_id: str,
    current: CurrentSession = Depends(get_current_admin_session),
) -> AdminProfileResponse:
    try:
        profile = admin_directory_service.get_profile(profile_id)
    except admin_directory_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    return AdminProfileResponse(**profile.model_dump())


# ---- Moderation ---------------------------------------------------------------


@admin_moderation_router.get("/cases", response_model=ModerationCaseListResponse)
async def list_moderation_cases(
    status_filter: str | None = Query(default=None, alias="status"),
    current: CurrentSession = Depends(get_current_admin_session),
) -> ModerationCaseListResponse:
    cases = admin_moderation_service.list_cases(status_filter)
    return ModerationCaseListResponse(items=[ModerationCaseResponse(**c) for c in cases])


@admin_moderation_router.post("/cases/{case_id}/assign", response_model=ModerationCaseResponse)
async def assign_moderation_case(
    case_id: str,
    payload: ModerationCaseAssignRequest,
    current: CurrentSession = Depends(get_current_admin_session),
) -> ModerationCaseResponse:
    try:
        case = admin_moderation_service.assign_case(current.account_id, case_id, payload.reason)
    except admin_moderation_service.ModerationCaseNotFoundError as exc:
        raise _MODERATION_CASE_NOT_FOUND_ERROR from exc
    except admin_moderation_service.ModerationCaseAlreadyClosedError as exc:
        raise _MODERATION_CASE_ALREADY_CLOSED_ERROR from exc
    return ModerationCaseResponse(**case)


@admin_moderation_router.post("/cases/{case_id}/actions", response_model=ModerationActionResponse)
async def act_on_moderation_case(
    case_id: str,
    payload: ModerationCaseActionRequest,
    current: CurrentSession = Depends(get_current_admin_session),
) -> ModerationActionResponse:
    try:
        action = admin_moderation_service.act_on_case(
            current.account_id, case_id, payload.action_type, payload.reason
        )
    except admin_moderation_service.ModerationCaseNotFoundError as exc:
        raise _MODERATION_CASE_NOT_FOUND_ERROR from exc
    except admin_moderation_service.ModerationCaseAlreadyClosedError as exc:
        raise _MODERATION_CASE_ALREADY_CLOSED_ERROR from exc
    return ModerationActionResponse(**action)


@admin_moderation_router.post("/cases/{case_id}/close", response_model=ModerationCaseResponse)
async def close_moderation_case(
    case_id: str,
    payload: ModerationCaseCloseRequest,
    current: CurrentSession = Depends(get_current_admin_session),
) -> ModerationCaseResponse:
    try:
        case = admin_moderation_service.close_case(current.account_id, case_id, payload.reason)
    except admin_moderation_service.ModerationCaseNotFoundError as exc:
        raise _MODERATION_CASE_NOT_FOUND_ERROR from exc
    except admin_moderation_service.ModerationCaseAlreadyClosedError as exc:
        raise _MODERATION_CASE_ALREADY_CLOSED_ERROR from exc
    return ModerationCaseResponse(**case)


# ---- Verification -------------------------------------------------------------


@admin_verification_router.get("/requests", response_model=AdminVerificationRequestListResponse)
async def list_verification_requests(
    status_filter: str | None = Query(default=None, alias="status"),
    current: CurrentSession = Depends(get_current_admin_session),
) -> AdminVerificationRequestListResponse:
    requests = admin_verification_service.list_requests(status_filter)
    return AdminVerificationRequestListResponse(
        items=[AdminVerificationRequestResponse(**r) for r in requests]
    )


@admin_verification_router.post(
    "/requests/{request_id}/decisions", response_model=AdminVerificationRequestResponse
)
async def decide_verification_request(
    request_id: str,
    payload: VerificationDecisionRequest,
    current: CurrentSession = Depends(get_current_admin_session),
) -> AdminVerificationRequestResponse:
    try:
        request = admin_verification_service.decide(
            current.account_id, request_id, payload.decision, payload.reason
        )
    except admin_verification_service.VerificationRequestNotFoundError as exc:
        raise _VERIFICATION_REQUEST_NOT_FOUND_ERROR from exc
    except admin_verification_service.VerificationRequestNotSubmittedError as exc:
        raise _VERIFICATION_REQUEST_NOT_SUBMITTED_ERROR from exc
    return AdminVerificationRequestResponse(**request)


# ---- Billing / support ---------------------------------------------------------


@admin_billing_router.get("/subscriptions", response_model=AdminSubscriptionListResponse)
async def list_admin_subscriptions(
    current: CurrentSession = Depends(get_current_admin_session),
) -> AdminSubscriptionListResponse:
    subscriptions = admin_billing_service.list_subscriptions()
    return AdminSubscriptionListResponse(items=[dict(s) for s in subscriptions])


@admin_billing_router.get("/transactions", response_model=AdminTransactionListResponse)
async def list_admin_transactions(
    current: CurrentSession = Depends(get_current_admin_session),
) -> AdminTransactionListResponse:
    transactions = admin_billing_service.list_transactions()
    return AdminTransactionListResponse(items=[dict(t) for t in transactions])


@admin_support_router.get("/tickets", response_model=SupportTicketListResponse)
async def list_support_tickets(
    status_filter: str | None = Query(default=None, alias="status"),
    current: CurrentSession = Depends(get_current_admin_session),
) -> SupportTicketListResponse:
    tickets = admin_billing_service.list_support_tickets(status_filter)
    return SupportTicketListResponse(items=[SupportTicketResponse(**t) for t in tickets])


@admin_support_router.post(
    "/tickets", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED
)
async def create_support_ticket(
    payload: SupportTicketCreateRequest,
    current: CurrentSession = Depends(get_current_admin_session),
) -> SupportTicketResponse:
    ticket = admin_billing_service.create_support_ticket(
        current.account_id, payload.account_id, payload.subject, payload.body
    )
    return SupportTicketResponse(**ticket)


@admin_support_router.get("/tickets/{ticket_id}", response_model=SupportTicketResponse)
async def get_support_ticket(
    ticket_id: str,
    current: CurrentSession = Depends(get_current_admin_session),
) -> SupportTicketResponse:
    try:
        ticket = admin_billing_service.get_support_ticket(ticket_id)
    except admin_billing_service.SupportTicketNotFoundError as exc:
        raise _SUPPORT_TICKET_NOT_FOUND_ERROR from exc
    return SupportTicketResponse(**ticket)


@admin_support_router.patch("/tickets/{ticket_id}", response_model=SupportTicketResponse)
async def update_support_ticket(
    ticket_id: str,
    payload: SupportTicketUpdateRequest,
    current: CurrentSession = Depends(get_current_admin_session),
) -> SupportTicketResponse:
    try:
        ticket = admin_billing_service.update_support_ticket(
            current.account_id, ticket_id, payload.status, payload.reason
        )
    except admin_billing_service.SupportTicketNotFoundError as exc:
        raise _SUPPORT_TICKET_NOT_FOUND_ERROR from exc
    return SupportTicketResponse(**ticket)


# ---- Brands / experiences / feature flags ---------------------------------------


@admin_config_router.get("/brands/{brand_id}", response_model=BrandConfigResponse)
async def get_brand_config(
    brand_id: str,
    current: CurrentSession = Depends(get_current_admin_session),
) -> BrandConfigResponse:
    try:
        brand = admin_config_service.get_brand(brand_id)
    except admin_config_service.BrandConfigNotFoundError as exc:
        raise _BRAND_CONFIG_NOT_FOUND_ERROR from exc
    return BrandConfigResponse(**brand)


@admin_config_router.patch("/brands/{brand_id}", response_model=BrandConfigResponse)
async def update_brand_config(
    brand_id: str,
    payload: BrandConfigUpdateRequest,
    current: CurrentSession = Depends(get_current_admin_session),
) -> BrandConfigResponse:
    try:
        brand = admin_config_service.update_brand(
            current.account_id, brand_id, payload.name, payload.active, payload.reason
        )
    except admin_config_service.BrandConfigNotFoundError as exc:
        raise _BRAND_CONFIG_NOT_FOUND_ERROR from exc
    return BrandConfigResponse(**brand)


@admin_config_router.get("/experiences/{experience_id}", response_model=ExperienceConfigResponse)
async def get_experience_config(
    experience_id: str,
    current: CurrentSession = Depends(get_current_admin_session),
) -> ExperienceConfigResponse:
    try:
        experience = admin_config_service.get_experience(experience_id)
    except admin_config_service.ExperienceConfigNotFoundError as exc:
        raise _EXPERIENCE_CONFIG_NOT_FOUND_ERROR from exc
    return ExperienceConfigResponse(**experience)


@admin_config_router.patch("/experiences/{experience_id}", response_model=ExperienceConfigResponse)
async def update_experience_config(
    experience_id: str,
    payload: ExperienceConfigUpdateRequest,
    current: CurrentSession = Depends(get_current_admin_session),
) -> ExperienceConfigResponse:
    try:
        experience = admin_config_service.update_experience(
            current.account_id, experience_id, payload.name, payload.active, payload.reason
        )
    except admin_config_service.ExperienceConfigNotFoundError as exc:
        raise _EXPERIENCE_CONFIG_NOT_FOUND_ERROR from exc
    return ExperienceConfigResponse(**experience)


@admin_config_router.get("/feature-flags/{key}", response_model=FeatureFlagResponse)
async def get_feature_flag(
    key: str,
    current: CurrentSession = Depends(get_current_admin_session),
) -> FeatureFlagResponse:
    try:
        flag = admin_config_service.get_feature_flag(key)
    except admin_config_service.FeatureFlagNotFoundError as exc:
        raise _FEATURE_FLAG_NOT_FOUND_ERROR from exc
    return FeatureFlagResponse(**flag)


@admin_config_router.patch("/feature-flags/{key}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    key: str,
    payload: FeatureFlagUpdateRequest,
    current: CurrentSession = Depends(get_current_admin_session),
) -> FeatureFlagResponse:
    try:
        flag = admin_config_service.update_feature_flag(current.account_id, key, payload.enabled, payload.reason)
    except admin_config_service.FeatureFlagNotFoundError as exc:
        raise _FEATURE_FLAG_NOT_FOUND_ERROR from exc
    return FeatureFlagResponse(**flag)


# ---- Reference data (generic, keyed by list name) --------------------------------


@admin_reference_router.get("/{list_name}", response_model=ReferenceDataItemListResponse)
async def list_reference_items(
    list_name: str,
    include_inactive: bool = Query(default=False),
    current: CurrentSession = Depends(get_current_admin_session),
) -> ReferenceDataItemListResponse:
    items = admin_reference_service.list_items(list_name, include_inactive)
    return ReferenceDataItemListResponse(items=[ReferenceDataItemResponse(**i) for i in items])


@admin_reference_router.post(
    "/{list_name}", response_model=ReferenceDataItemResponse, status_code=status.HTTP_201_CREATED
)
async def create_reference_item(
    list_name: str,
    payload: ReferenceDataItemCreateRequest,
    current: CurrentSession = Depends(get_current_admin_session),
) -> ReferenceDataItemResponse:
    try:
        item = admin_reference_service.create_item(
            current.account_id, list_name, payload.id, payload.label, payload.value, payload.reason
        )
    except admin_reference_service.ReferenceDataItemAlreadyExistsError as exc:
        raise _REFERENCE_ITEM_ALREADY_EXISTS_ERROR from exc
    return ReferenceDataItemResponse(**item)


@admin_reference_router.patch("/{list_name}/{item_id}", response_model=ReferenceDataItemResponse)
async def update_reference_item(
    list_name: str,
    item_id: str,
    payload: ReferenceDataItemUpdateRequest,
    current: CurrentSession = Depends(get_current_admin_session),
) -> ReferenceDataItemResponse:
    try:
        item = admin_reference_service.update_item(
            current.account_id, list_name, item_id, payload.label, payload.value, payload.reason
        )
    except admin_reference_service.ReferenceDataItemNotFoundError as exc:
        raise _REFERENCE_ITEM_NOT_FOUND_ERROR from exc
    return ReferenceDataItemResponse(**item)


@admin_reference_router.post(
    "/{list_name}/{item_id}/deactivate", response_model=ReferenceDataItemResponse
)
async def deactivate_reference_item(
    list_name: str,
    item_id: str,
    payload: ReferenceDataItemDeactivateRequest,
    current: CurrentSession = Depends(get_current_admin_session),
) -> ReferenceDataItemResponse:
    try:
        item = admin_reference_service.deactivate_item(
            current.account_id, list_name, item_id, payload.reason
        )
    except admin_reference_service.ReferenceDataItemNotFoundError as exc:
        raise _REFERENCE_ITEM_NOT_FOUND_ERROR from exc
    return ReferenceDataItemResponse(**item)
