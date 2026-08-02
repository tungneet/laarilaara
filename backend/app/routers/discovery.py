"""Router for discovery search, profile view, recommendations, and view
recording (catalog §7: `POST /v1/discovery/search`,
`GET /v1/discovery/profiles/{profileId}`, `GET /v1/discovery/recommendations`,
`POST /v1/discovery/views`).

All endpoints take ``acting_profile_id`` as a required query parameter: this
codebase has no session-level "current profile" concept yet (an account may
manage several profiles), so the caller must state which managed profile is
acting.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.discovery import (
    DiscoveryProfileDetailResponse,
    DiscoverySearchRequest,
    DiscoverySearchResponse,
    DiscoveryViewCreateRequest,
    DiscoveryViewResponse,
)
from app.services import discovery as discovery_service
from app.services import profiles as profiles_service

router = APIRouter(prefix="/v1/discovery", tags=["discovery"])

_PROFILE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PROFILE_NOT_FOUND",
    title="Profile not found",
)

_PROFILE_FORBIDDEN_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="PROFILE_FORBIDDEN",
    title="You do not have permission to act as this profile",
)

_TARGET_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="DISCOVERY_TARGET_PROFILE_NOT_FOUND",
    title="Target profile not found",
)


@router.post("/search", response_model=DiscoverySearchResponse, status_code=status.HTTP_200_OK)
async def search(
    payload: DiscoverySearchRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> DiscoverySearchResponse:
    try:
        result = discovery_service.search(
            current.account_id,
            acting_profile_id,
            payload.filters.model_dump(mode="json"),
            payload.cursor,
            payload.limit,
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return DiscoverySearchResponse(**result)


@router.get(
    "/profiles/{profile_id}",
    response_model=DiscoveryProfileDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_profile(
    profile_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> DiscoveryProfileDetailResponse:
    try:
        result = discovery_service.get_public_profile(current.account_id, acting_profile_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except discovery_service.TargetProfileNotFoundError as exc:
        raise _TARGET_NOT_FOUND_ERROR from exc
    return DiscoveryProfileDetailResponse(**result)


@router.get(
    "/recommendations", response_model=DiscoverySearchResponse, status_code=status.HTTP_200_OK
)
async def recommendations(
    acting_profile_id: str = Query(...),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current: CurrentSession = Depends(get_current_session),
) -> DiscoverySearchResponse:
    try:
        result = discovery_service.recommendations(current.account_id, acting_profile_id, cursor, limit)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return DiscoverySearchResponse(**result)


@router.post("/views", response_model=DiscoveryViewResponse, status_code=status.HTTP_201_CREATED)
async def record_view(
    payload: DiscoveryViewCreateRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> DiscoveryViewResponse:
    try:
        result = discovery_service.record_view(
            current.account_id, acting_profile_id, payload.target_profile_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return DiscoveryViewResponse(**result)
