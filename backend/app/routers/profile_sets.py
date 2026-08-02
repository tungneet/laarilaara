"""Router for the replace-set profile sections (catalog §5 — "Sections"
batch B: communities, religious-practices, languages, interests).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.profile_sets import ProfileSetPutRequest, ProfileSetResponse
from app.services import profile_sets as profile_sets_service
from app.services import profiles as profiles_service

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


def _invalid_set_value_error(exc: profile_sets_service.InvalidSetValueError) -> ApiError:
    return ApiError(
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="PROFILE_SET_INVALID_VALUE",
        title="One or more values are not recognized options",
        detail=f"Invalid values: {', '.join(exc.invalid_values)}",
    )


@router.get(
    "/{profile_id}/communities", response_model=ProfileSetResponse, status_code=status.HTTP_200_OK
)
async def get_communities(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> ProfileSetResponse:
    try:
        data = profile_sets_service.get_communities(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ProfileSetResponse(**data)


@router.put(
    "/{profile_id}/communities", response_model=ProfileSetResponse, status_code=status.HTTP_200_OK
)
async def put_communities(
    profile_id: str,
    payload: ProfileSetPutRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileSetResponse:
    try:
        data = profile_sets_service.put_communities(
            current.account_id, profile_id, payload.values
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_sets_service.InvalidSetValueError as exc:
        raise _invalid_set_value_error(exc) from exc
    return ProfileSetResponse(**data)


@router.get(
    "/{profile_id}/religious-practices",
    response_model=ProfileSetResponse,
    status_code=status.HTTP_200_OK,
)
async def get_religious_practices(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> ProfileSetResponse:
    try:
        data = profile_sets_service.get_religious_practices(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ProfileSetResponse(**data)


@router.put(
    "/{profile_id}/religious-practices",
    response_model=ProfileSetResponse,
    status_code=status.HTTP_200_OK,
)
async def put_religious_practices(
    profile_id: str,
    payload: ProfileSetPutRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileSetResponse:
    try:
        data = profile_sets_service.put_religious_practices(
            current.account_id, profile_id, payload.values
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_sets_service.InvalidSetValueError as exc:
        raise _invalid_set_value_error(exc) from exc
    return ProfileSetResponse(**data)


@router.get(
    "/{profile_id}/languages", response_model=ProfileSetResponse, status_code=status.HTTP_200_OK
)
async def get_languages(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> ProfileSetResponse:
    try:
        data = profile_sets_service.get_languages(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ProfileSetResponse(**data)


@router.put(
    "/{profile_id}/languages", response_model=ProfileSetResponse, status_code=status.HTTP_200_OK
)
async def put_languages(
    profile_id: str,
    payload: ProfileSetPutRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileSetResponse:
    try:
        data = profile_sets_service.put_languages(current.account_id, profile_id, payload.values)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_sets_service.InvalidSetValueError as exc:
        raise _invalid_set_value_error(exc) from exc
    return ProfileSetResponse(**data)


@router.get(
    "/{profile_id}/interests", response_model=ProfileSetResponse, status_code=status.HTTP_200_OK
)
async def get_interests(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> ProfileSetResponse:
    try:
        data = profile_sets_service.get_interests(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ProfileSetResponse(**data)


@router.put(
    "/{profile_id}/interests", response_model=ProfileSetResponse, status_code=status.HTTP_200_OK
)
async def put_interests(
    profile_id: str,
    payload: ProfileSetPutRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileSetResponse:
    try:
        data = profile_sets_service.put_interests(current.account_id, profile_id, payload.values)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_sets_service.InvalidSetValueError as exc:
        raise _invalid_set_value_error(exc) from exc
    return ProfileSetResponse(**data)
