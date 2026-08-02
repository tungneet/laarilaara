"""Router for the main partner-preferences summary plus its five preference-set
sub-collections (catalog §5 — "Sections" batch E).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.profile_preferences import PreferencesPutRequest, PreferencesResponse
from app.schemas.profile_sets import ProfileSetPutRequest, ProfileSetResponse
from app.services import profile_preferences as profile_preferences_service
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
        title="One or more values are not recognized options",
        detail=f"Invalid values: {', '.join(exc.invalid_values)}",
    )


@router.get(
    "/{profile_id}/preferences", response_model=PreferencesResponse, status_code=status.HTTP_200_OK
)
async def get_preferences(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> PreferencesResponse:
    try:
        data = profile_preferences_service.get_preferences(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return PreferencesResponse(**data)


@router.put(
    "/{profile_id}/preferences", response_model=PreferencesResponse, status_code=status.HTTP_200_OK
)
async def put_preferences(
    profile_id: str,
    payload: PreferencesPutRequest,
    current: CurrentSession = Depends(get_current_session),
) -> PreferencesResponse:
    try:
        data = profile_preferences_service.put_preferences(
            current.account_id, profile_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return PreferencesResponse(**data)


@router.get(
    "/{profile_id}/preferences/countries",
    response_model=ProfileSetResponse,
    status_code=status.HTTP_200_OK,
)
async def get_preferred_countries(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> ProfileSetResponse:
    try:
        data = profile_preferences_service.get_preferred_countries(
            current.account_id, profile_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ProfileSetResponse(**data)


@router.put(
    "/{profile_id}/preferences/countries",
    response_model=ProfileSetResponse,
    status_code=status.HTTP_200_OK,
)
async def put_preferred_countries(
    profile_id: str,
    payload: ProfileSetPutRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileSetResponse:
    try:
        data = profile_preferences_service.put_preferred_countries(
            current.account_id, profile_id, payload.values
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except InvalidSetValueError as exc:
        raise _invalid_set_value_error(exc) from exc
    return ProfileSetResponse(**data)


@router.get(
    "/{profile_id}/preferences/languages",
    response_model=ProfileSetResponse,
    status_code=status.HTTP_200_OK,
)
async def get_preferred_languages(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> ProfileSetResponse:
    try:
        data = profile_preferences_service.get_preferred_languages(
            current.account_id, profile_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ProfileSetResponse(**data)


@router.put(
    "/{profile_id}/preferences/languages",
    response_model=ProfileSetResponse,
    status_code=status.HTTP_200_OK,
)
async def put_preferred_languages(
    profile_id: str,
    payload: ProfileSetPutRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileSetResponse:
    try:
        data = profile_preferences_service.put_preferred_languages(
            current.account_id, profile_id, payload.values
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except InvalidSetValueError as exc:
        raise _invalid_set_value_error(exc) from exc
    return ProfileSetResponse(**data)


@router.get(
    "/{profile_id}/preferences/communities",
    response_model=ProfileSetResponse,
    status_code=status.HTTP_200_OK,
)
async def get_preferred_communities(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> ProfileSetResponse:
    try:
        data = profile_preferences_service.get_preferred_communities(
            current.account_id, profile_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ProfileSetResponse(**data)


@router.put(
    "/{profile_id}/preferences/communities",
    response_model=ProfileSetResponse,
    status_code=status.HTTP_200_OK,
)
async def put_preferred_communities(
    profile_id: str,
    payload: ProfileSetPutRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileSetResponse:
    try:
        data = profile_preferences_service.put_preferred_communities(
            current.account_id, profile_id, payload.values
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except InvalidSetValueError as exc:
        raise _invalid_set_value_error(exc) from exc
    return ProfileSetResponse(**data)


@router.get(
    "/{profile_id}/preferences/religious-practices",
    response_model=ProfileSetResponse,
    status_code=status.HTTP_200_OK,
)
async def get_preferred_religious_practices(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> ProfileSetResponse:
    try:
        data = profile_preferences_service.get_preferred_religious_practices(
            current.account_id, profile_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ProfileSetResponse(**data)


@router.put(
    "/{profile_id}/preferences/religious-practices",
    response_model=ProfileSetResponse,
    status_code=status.HTTP_200_OK,
)
async def put_preferred_religious_practices(
    profile_id: str,
    payload: ProfileSetPutRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileSetResponse:
    try:
        data = profile_preferences_service.put_preferred_religious_practices(
            current.account_id, profile_id, payload.values
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except InvalidSetValueError as exc:
        raise _invalid_set_value_error(exc) from exc
    return ProfileSetResponse(**data)


@router.get(
    "/{profile_id}/preferences/education-levels",
    response_model=ProfileSetResponse,
    status_code=status.HTTP_200_OK,
)
async def get_preferred_education_levels(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> ProfileSetResponse:
    try:
        data = profile_preferences_service.get_preferred_education_levels(
            current.account_id, profile_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ProfileSetResponse(**data)


@router.put(
    "/{profile_id}/preferences/education-levels",
    response_model=ProfileSetResponse,
    status_code=status.HTTP_200_OK,
)
async def put_preferred_education_levels(
    profile_id: str,
    payload: ProfileSetPutRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileSetResponse:
    try:
        data = profile_preferences_service.put_preferred_education_levels(
            current.account_id, profile_id, payload.values
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except InvalidSetValueError as exc:
        raise _invalid_set_value_error(exc) from exc
    return ProfileSetResponse(**data)
