"""Router for saved searches (catalog §7: `GET/POST /v1/saved-searches`,
`PATCH/DELETE /v1/saved-searches/{searchId}`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.saved_search import (
    SavedSearchCreateRequest,
    SavedSearchPatchRequest,
    SavedSearchResponse,
)
from app.services import profiles as profiles_service
from app.services import saved_searches as saved_searches_service

router = APIRouter(prefix="/v1/saved-searches", tags=["discovery"])

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

_SAVED_SEARCH_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="SAVED_SEARCH_NOT_FOUND",
    title="Saved search not found",
)


@router.get("", response_model=list[SavedSearchResponse], status_code=status.HTTP_200_OK)
async def list_saved_searches(
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> list[SavedSearchResponse]:
    try:
        records = saved_searches_service.list_saved_searches(current.account_id, acting_profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return [SavedSearchResponse(**r) for r in records]


@router.post("", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED)
async def create_saved_search(
    payload: SavedSearchCreateRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> SavedSearchResponse:
    try:
        record = saved_searches_service.create_saved_search(
            current.account_id, acting_profile_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return SavedSearchResponse(**record)


@router.patch(
    "/{search_id}", response_model=SavedSearchResponse, status_code=status.HTTP_200_OK
)
async def patch_saved_search(
    search_id: str,
    payload: SavedSearchPatchRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> SavedSearchResponse:
    try:
        record = saved_searches_service.patch_saved_search(
            current.account_id, acting_profile_id, search_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except saved_searches_service.SavedSearchNotFoundError as exc:
        raise _SAVED_SEARCH_NOT_FOUND_ERROR from exc
    return SavedSearchResponse(**record)


@router.delete("/{search_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    search_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> None:
    try:
        saved_searches_service.delete_saved_search(current.account_id, acting_profile_id, search_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except saved_searches_service.SavedSearchNotFoundError as exc:
        raise _SAVED_SEARCH_NOT_FOUND_ERROR from exc
