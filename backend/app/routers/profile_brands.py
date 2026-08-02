"""Router for brands and experiences (catalog §5 — "Sections" batch F)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.profile_sets import ProfileSetPutRequest, ProfileSetResponse
from app.services import profile_brands as profile_brands_service
from app.services import profiles as profiles_service
from app.services.profile_sets import InvalidSetValueError

router = APIRouter(prefix="/v1/profiles", tags=["profiles"])

_PROFILE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PROFILE_NOT_FOUND",
    title="Profile not found",
)

_PROFILE_FORBIDDEN_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="PROFILE_FORBIDDEN",
    title="You do not have permission to perform this action on this profile",
)


def _invalid_set_value_error(exc: InvalidSetValueError) -> ApiError:
    return ApiError(
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="PROFILE_SET_INVALID_VALUE",
        title="One or more values are not valid",
        detail=f"Invalid values: {', '.join(exc.invalid_values)}",
    )


@router.get(
    "/{profile_id}/brands", response_model=ProfileSetResponse, status_code=status.HTTP_200_OK
)
async def get_brands(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> ProfileSetResponse:
    try:
        data = profile_brands_service.get_brands(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ProfileSetResponse(**data)


@router.put(
    "/{profile_id}/brands", response_model=ProfileSetResponse, status_code=status.HTTP_200_OK
)
async def put_brands(
    profile_id: str,
    payload: ProfileSetPutRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileSetResponse:
    try:
        data = profile_brands_service.put_brands(current.account_id, profile_id, payload.values)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except InvalidSetValueError as exc:
        raise _invalid_set_value_error(exc) from exc
    return ProfileSetResponse(**data)


@router.get(
    "/{profile_id}/experiences", response_model=ProfileSetResponse, status_code=status.HTTP_200_OK
)
async def get_experiences(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> ProfileSetResponse:
    try:
        data = profile_brands_service.get_experiences(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ProfileSetResponse(**data)


@router.put(
    "/{profile_id}/experiences", response_model=ProfileSetResponse, status_code=status.HTTP_200_OK
)
async def put_experiences(
    profile_id: str,
    payload: ProfileSetPutRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileSetResponse:
    try:
        data = profile_brands_service.put_experiences(
            current.account_id, profile_id, payload.values
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except InvalidSetValueError as exc:
        raise _invalid_set_value_error(exc) from exc
    return ProfileSetResponse(**data)
