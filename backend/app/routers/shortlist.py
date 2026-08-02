"""Router for the private shortlist (catalog §7: `GET /v1/shortlist`,
`PUT/DELETE /v1/shortlist/{targetProfileId}`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.shortlist import ShortlistItemResponse, ShortlistPutRequest
from app.services import profiles as profiles_service
from app.services import shortlist as shortlist_service

router = APIRouter(prefix="/v1/shortlist", tags=["discovery"])

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


@router.get("", response_model=list[ShortlistItemResponse], status_code=status.HTTP_200_OK)
async def list_shortlist(
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> list[ShortlistItemResponse]:
    try:
        records = shortlist_service.list_shortlist(current.account_id, acting_profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return [ShortlistItemResponse(**r) for r in records]


@router.put(
    "/{target_profile_id}", response_model=ShortlistItemResponse, status_code=status.HTTP_200_OK
)
async def put_shortlist(
    target_profile_id: str,
    payload: ShortlistPutRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> ShortlistItemResponse:
    try:
        record = shortlist_service.put_shortlist(
            current.account_id, acting_profile_id, target_profile_id, payload.note
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ShortlistItemResponse(**record)


@router.delete("/{target_profile_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_shortlist(
    target_profile_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> None:
    try:
        shortlist_service.delete_shortlist(current.account_id, acting_profile_id, target_profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
