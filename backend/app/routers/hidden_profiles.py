"""Router for hidden profiles (catalog §7:
`PUT/DELETE /v1/hidden-profiles/{targetProfileId}`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.hidden_profile import HiddenProfileResponse
from app.services import hidden_profiles as hidden_profiles_service
from app.services import profiles as profiles_service

router = APIRouter(prefix="/v1/hidden-profiles", tags=["discovery"])

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


@router.put(
    "/{target_profile_id}", response_model=HiddenProfileResponse, status_code=status.HTTP_200_OK
)
async def hide_profile(
    target_profile_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> HiddenProfileResponse:
    try:
        record = hidden_profiles_service.hide_profile(
            current.account_id, acting_profile_id, target_profile_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return HiddenProfileResponse(**record)


@router.delete("/{target_profile_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def unhide_profile(
    target_profile_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> None:
    try:
        hidden_profiles_service.unhide_profile(current.account_id, acting_profile_id, target_profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
