"""Routers for §12 notifications, notification-preferences, and
push-endpoints. Three small `APIRouter`s in one file (same reason as
`app/routers/ai.py`'s 5-router split and `app/routers/verification.py`'s
2-router split): the catalog paths span three different top-level prefixes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.notification import (
    MarkAllReadRequest,
    NotificationListResponse,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
    NotificationResponse,
    PushEndpointCreateRequest,
    PushEndpointResponse,
)
from app.services import notification_center as notification_center_service

notifications_router = APIRouter(prefix="/v1/notifications", tags=["notifications"])
notification_preferences_router = APIRouter(
    prefix="/v1/notification-preferences", tags=["notifications"]
)
push_endpoints_router = APIRouter(prefix="/v1/push-endpoints", tags=["notifications"])

_NOTIFICATION_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="NOTIFICATION_NOT_FOUND",
    title="Notification not found",
)

_INVALID_PREFERENCE_VALUE_ERROR_CODE = "NOTIFICATION_PREFERENCE_INVALID_VALUE"

_PUSH_ENDPOINT_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PUSH_ENDPOINT_NOT_FOUND",
    title="Push endpoint not found",
)


@notifications_router.get("", response_model=NotificationListResponse)
async def list_notifications(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current: CurrentSession = Depends(get_current_session),
) -> NotificationListResponse:
    result = notification_center_service.list_notifications(current.account_id, cursor, limit)
    return NotificationListResponse(**result)


@notifications_router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> NotificationResponse:
    try:
        notification = notification_center_service.mark_read(current.account_id, notification_id)
    except notification_center_service.NotificationNotFoundError as exc:
        raise _NOTIFICATION_NOT_FOUND_ERROR from exc
    return NotificationResponse(**notification)


@notifications_router.post("/read-all", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    payload: MarkAllReadRequest,
    current: CurrentSession = Depends(get_current_session),
) -> None:
    through = payload.through.isoformat() if payload.through else None
    notification_center_service.mark_all_read(current.account_id, through)


@notification_preferences_router.get("", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current: CurrentSession = Depends(get_current_session),
) -> NotificationPreferencesResponse:
    prefs = notification_center_service.get_preferences(current.account_id)
    return NotificationPreferencesResponse(**prefs)


@notification_preferences_router.put("", response_model=NotificationPreferencesResponse)
async def put_notification_preferences(
    payload: NotificationPreferencesRequest,
    current: CurrentSession = Depends(get_current_session),
) -> NotificationPreferencesResponse:
    try:
        prefs = notification_center_service.put_preferences(current.account_id, payload.categories)
    except notification_center_service.InvalidPreferenceValueError as exc:
        raise ApiError(
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code=_INVALID_PREFERENCE_VALUE_ERROR_CODE,
            title="Invalid notification preference category or channel",
            detail=str(exc),
        ) from exc
    return NotificationPreferencesResponse(**prefs)


@push_endpoints_router.post(
    "", response_model=PushEndpointResponse, status_code=status.HTTP_201_CREATED
)
async def create_push_endpoint(
    payload: PushEndpointCreateRequest,
    current: CurrentSession = Depends(get_current_session),
) -> PushEndpointResponse:
    endpoint = notification_center_service.create_push_endpoint(
        current.account_id, payload.platform, payload.token
    )
    return PushEndpointResponse(**endpoint)


@push_endpoints_router.delete(
    "/{endpoint_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_push_endpoint(
    endpoint_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> None:
    try:
        notification_center_service.revoke_push_endpoint(current.account_id, endpoint_id)
    except notification_center_service.PushEndpointNotFoundError as exc:
        raise _PUSH_ENDPOINT_NOT_FOUND_ERROR from exc
